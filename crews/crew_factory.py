"""
OKAMIシステム用クルーファクトリー
クルーインスタンスの作成と管理
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

from crewai import Crew, Agent, Task, LLM
import crewai as _crewai_pkg
from crewai.memory.external.external_memory import ExternalMemory
from core.memory_manager import MemoryManager
from core.knowledge_manager import KnowledgeManager
from core.guardrail_manager import GuardrailManager
from crewai import Process
from crewai.project import CrewBase
from utils.config import get_config
from tools import get_mcp_tools_for_agent, search_knowledge, add_knowledge_to_base
from tools.mcp_docker_tool import get_docker_tools
from models.evolution_output import EvolutionChanges
# knowledge_loaderは削除 - CrewAI標準のknowledge_sourcesを使用
from guardrails import create_quality_guardrail, create_safety_guardrail, create_accuracy_guardrail
from utils.helpers import truncate_dict

logger = structlog.get_logger()


class CrewFactory:
    """クルーの作成と管理を行うファクトリー"""

    def __init__(self, config_dir: str = "config"):
        """
        クルーファクトリーの初期化

        Args:
            config_dir: クルー設定を含むディレクトリ
        """
        self.config_dir = Path(config_dir)
        self.config = get_config()
        self.active_crews: Dict[str, Crew] = {}
        
        # Monica LLMの初期化（既定のまま保持）
        self.monica_llm = LLM(
            model="gpt-4o",
            api_key=os.environ.get("MONICA_API_KEY"),
            base_url="https://openapi.monica.im/v1"
        )
        
        # 設定の読み込み
        self.agent_configs = self._load_configs("agents")
        self.task_configs = self._load_configs("tasks")
        self.crew_configs = self._load_configs("crews")
        
        # 共有KnowledgeManagerインスタンス（自動初期化）
        self._knowledge_manager = None
        self._initialize_knowledge_manager()
        
        # MemoryManagerの初期化（グラフメモリ対応、シンプル版）
        self.memory_manager = MemoryManager(use_graph_memory=True)
        
        # KnowledgeGraphIntegrationの初期化
        if self.memory_manager.kg_integration:
            # KnowledgeManagerを統合層に設定
            self.memory_manager.kg_integration.knowledge_manager = self._knowledge_manager
        
        logger.info(
            "Crew Factory initialized",
            agents=len(self.agent_configs),
            tasks=len(self.task_configs),
            crews=len(self.crew_configs)
        )

    def _load_configs(self, config_type: str) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        configs = {}
        config_path = self.config_dir / config_type
        
        if not config_path.exists():
            logger.warning(f"Config directory not found", path=str(config_path))
            return configs
        
        for file_path in config_path.glob("*.yaml"):
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    # 非推奨ファイルをスキップ
                    if "deprecated" in content.lower() or content.strip().startswith("#"):
                        logger.debug(f"Skipping deprecated config", file=file_path.name)
                        continue
                    
                    config_data = yaml.safe_load(content)
                    if config_data:
                        configs.update(config_data)
                        logger.debug(f"Loaded config", file=file_path.name, items=len(config_data))
            except Exception as e:
                logger.error(f"Failed to load config", file=file_path.name, error=str(e))
        
        return configs
    
    def _initialize_knowledge_manager(self):
        """KnowledgeManagerの初期化と自動セットアップ"""
        try:
            if self._knowledge_manager is None:
                self._knowledge_manager = KnowledgeManager(
                    knowledge_dir=self.config.knowledge_dir,
                    embedder_config=self.config.get_embedder_config()
                )
                
                # 知識の自動初期化
                success = self._knowledge_manager.auto_initialize_knowledge()
                if success:
                    logger.info("Knowledge manager auto-initialized successfully")
                else:
                    logger.warning("Knowledge manager auto-initialization had issues")
                    
        except Exception as e:
            logger.error(f"Failed to initialize knowledge manager: {e}")
            # フォールバック：基本的なKnowledgeManagerを作成
            self._knowledge_manager = KnowledgeManager(
                knowledge_dir=self.config.knowledge_dir,
                embedder_config=self.config.get_embedder_config()
            )
    
    def refresh_knowledge(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        知識を手動で更新
        
        Args:
            force_reload: 強制的に再読み込みするかどうか
            
        Returns:
            更新結果の統計
        """
        if self._knowledge_manager is None:
            self._initialize_knowledge_manager()
        
        return self._knowledge_manager.refresh_knowledge_from_directory(force_reload)

    def create_agent(self, agent_name: str) -> Optional[Agent]:
        """
        設定からエージェントを作成

        Args:
            agent_name: エージェント設定名

        Returns:
            エージェントインスタンスまたはNone
        """
        if agent_name not in self.agent_configs:
            logger.error(f"Agent config not found", agent_name=agent_name)
            return None
        
        config = self.agent_configs[agent_name].copy()
        
        try:
            # 指定されている場合、エージェントのツールを取得
            agent_tools = []
            if config.get("tools"):
                tools_config = config.get("tools", [])
                
                # MCPツールのチェック
                if any("mcp" in str(tool).lower() for tool in tools_config):
                    agent_tools.extend(get_mcp_tools_for_agent())
                
                # Dockerツールのチェック
                if any("docker" in str(tool).lower() for tool in tools_config):
                    # 特定のDockerツールを取得
                    docker_tools = get_docker_tools()
                    docker_tool_map = {
                        "docker_list_containers": docker_tools[0],
                        "docker_container_logs": docker_tools[1],
                        "docker_exec": docker_tools[2],
                        "docker_manage_container": docker_tools[3]
                    }
                    # リクエストされたDockerツールのみ追加
                    for tool_name in tools_config:
                        if tool_name in docker_tool_map:
                            agent_tools.append(docker_tool_map[tool_name])
                
                # 知識検索ツールのチェック
                if "knowledge_search" in tools_config:
                    agent_tools.append(search_knowledge)
                if "add_knowledge" in tools_config:
                    agent_tools.append(add_knowledge_to_base)
                
                # その他のツール名をチェック（将来的に拡張可能）
                for tool_name in tools_config:
                    if isinstance(tool_name, str) and tool_name not in ["mcp", "docker", "knowledge_search", "add_knowledge"]:
                        logger.warning(f"Unknown tool type", tool_name=tool_name)
            
            # エージェント用の知識ソースを設定（CrewAI標準機能）
            agent_knowledge_sources = []
            if config.get("knowledge_sources"):
                # 共有KnowledgeManagerインスタンスを使用
                if self._knowledge_manager is None:
                    self._knowledge_manager = KnowledgeManager(
                        knowledge_dir=self.config.knowledge_dir,
                        embedder_config=self.config.get_embedder_config()
                    )
                
                for source in config["knowledge_sources"]:
                    self._knowledge_manager.add_agent_knowledge(agent_name, source)
                
                agent_knowledge_sources = self._knowledge_manager.get_agent_knowledge_config(agent_name)
            
            # Update config with processed values
            config["tools"] = agent_tools
            config["llm"] = self.monica_llm
            
            # エージェント用の知識ソースを追加
            if agent_knowledge_sources:
                config.update(agent_knowledge_sources)
            
            # 指定されていない場合、デフォルト値を設定
            config.setdefault("verbose", True)
            config.setdefault("memory", True)
            config.setdefault("max_iter", self.config.default_max_iter)
            config.setdefault("allow_delegation", True)
            
            # すべての設定パラメータでエージェントを作成
            logger.info("Agent config used", agent_name=agent_name, config=truncate_dict(config))
            agent = Agent(**config)
            
            logger.info(f"Agent created", role=agent.role, tools=len(agent_tools))
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent", agent_name=agent_name, error=str(e))
            return None

    def create_task(self, task_name: str) -> Optional[Task]:
        """
        設定からタスクを作成

        Args:
            task_name: タスク設定名

        Returns:
            タスクインスタンスまたはNone
        """
        if task_name not in self.task_configs:
            logger.error(f"Task config not found", task_name=task_name)
            return None
        
        task_config = self.task_configs.get(task_name, {})
        if not isinstance(task_config, dict):
            logger.error(f"Invalid task config format", task_name=task_name, config_type=type(task_config))
            return None
        
        config = task_config.copy()
        
        try:
            # コンテキストの処理 - 後で解決するために保存
            context_names = None
            if "context" in config and isinstance(config["context"], list):
                context_names = config.pop("context")
            
            # Toolsの処理
            task_tools = []
            if config.get("tools"):
                tools_config = config.get("tools", [])
                
                # MCPツールのチェック
                if any("mcp" in str(tool).lower() for tool in tools_config):
                    task_tools.extend(get_mcp_tools_for_agent())
                
                # Dockerツールのチェック
                if any("docker" in str(tool).lower() for tool in tools_config):
                    # 特定のDockerツールを取得
                    docker_tools = get_docker_tools()
                    docker_tool_map = {
                        "docker_list_containers": docker_tools[0],
                        "docker_container_logs": docker_tools[1],
                        "docker_exec": docker_tools[2],
                        "docker_manage_container": docker_tools[3]
                    }
                    # リクエストされたDockerツールのみ追加
                    for tool_name in tools_config:
                        if tool_name in docker_tool_map:
                            task_tools.append(docker_tool_map[tool_name])
                
                # 知識検索ツールのチェック
                if "knowledge_search" in tools_config:
                    task_tools.append(search_knowledge)
                if "add_knowledge" in tools_config:
                    task_tools.append(add_knowledge_to_base)
                
                # その他のツール名をチェック（将来的に拡張可能）
                for tool_name in tools_config:
                    if isinstance(tool_name, str) and tool_name not in ["mcp", "docker", "knowledge_search", "add_knowledge"]:
                        logger.warning(f"Unknown tool type", tool_name=tool_name)
            
            # 処理されたツールを設定
            config["tools"] = task_tools
            
            # guardrailが文字列の場合は削除（後で処理）
            guardrail_name = None
            if "guardrail" in config and isinstance(config["guardrail"], str):
                guardrail_name = config.pop("guardrail")
            
            # agentが文字列の場合は後で解決するために保存
            agent_name = None
            if "agent" in config and isinstance(config["agent"], str):
                agent_name = config.pop("agent")
            
            # output_jsonが文字列の場合、対応するPydanticモデルに変換
            if "output_json" in config and isinstance(config["output_json"], str):
                if config["output_json"] == "EvolutionChanges":
                    config["output_json"] = EvolutionChanges
            
            # すべての設定パラメータでタスクを作成
            logger.info("Task config used", task_name=task_name, config=truncate_dict(config))
            task = Task(**config)
            
            # 一時的にエージェント名を保存
            if agent_name:
                task._agent_name = agent_name
            
            # 後で解決するためにコンテキスト名を保存
            if context_names:
                task._context_names = context_names
            
            logger.info(f"Task created", description=task.description[:50], tools=len(task_tools))
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task", task_name=task_name, error=str(e))
            return None

    def create_crew(self, crew_name: str) -> Optional[Crew]:
        """
        設定からクルーを作成

        Args:
            crew_name: クルー設定名

        Returns:
            クルーインスタンスまたはNone
        """
        if crew_name not in self.crew_configs:
            logger.error(f"Crew config not found", crew_name=crew_name)
            return None
        
        config = self.crew_configs[crew_name]
        
        try:
            # エージェントの作成
            agents = []
            for agent_name in config.get("agents", []):
                agent = self.create_agent(agent_name)
                if agent:
                    agents.append(agent)
            
            # まずプロセスタイプを決定
            process_str = config.get("process", "sequential")
            if process_str == "sequential":
                process = Process.sequential
            elif process_str == "hierarchical":
                process = Process.hierarchical
            else:
                process = Process.sequential
            
            # タスクの作成
            tasks = []
            task_map = {}  # コンテキスト解決のためにタスク名をタスクオブジェクトにマップ
            
            for task_name in config.get("tasks", []):
                task = self.create_task(task_name)
                if task:
                    tasks.append(task)
                    task_map[task_name] = task
            
            # エージェント名から実際のエージェントオブジェクトへのマッピングを作成
            agent_map = {agent.role: agent for agent in agents}
            
            # タスクのエージェント解決（sequentialプロセスのみ）
            if process == Process.sequential:
                for task in tasks:
                    if hasattr(task, '_agent_name'):
                        agent = self.create_agent(task._agent_name)
                        if agent:
                            task.agent = agent
                        else:
                            logger.error(f"Agent not found for task", agent_name=task._agent_name)
                        delattr(task, '_agent_name')
            
            # タスクコンテキストの解決
            for task in tasks:
                if hasattr(task, '_context_names'):
                    context_tasks = []
                    for context_name in task._context_names:
                        if context_name in task_map:
                            context_tasks.append(task_map[context_name])
                        else:
                            logger.warning(f"Context task not found", task_name=context_name)
                    if context_tasks:
                        task.context = context_tasks
                    delattr(task, '_context_names')
            
            # 階層プロセス用のマネージャーの処理
            manager_llm = None
            manager_agent = None
            _append_manager_after_create = False
            
            if process == Process.hierarchical:
                # 指定されている場合はmanager_llmを設定（CrewAIが独自のマネージャーを作成するため）
                if config.get("manager_llm"):
                    manager_llm = self.monica_llm
                
                # または指定されている場合はカスタムマネージャーエージェントを使用
                if config.get("manager_agent"):
                    manager_agent_name = config.get("manager_agent")
                    # マネージャーエージェントを作成（まだエージェントリストに含まれていない場合）
                    manager_agent = self.create_agent(manager_agent_name)
                    # CrewAIのバリデーションに従い、agents には含めず、
                    # 生成後にテスト互換性のため追加する
                    if manager_agent and manager_agent in agents:
                        agents = [a for a in agents if a is not manager_agent]
                    _append_manager_after_create = manager_agent is not None
                    # YAMLの文字列指定は除去して型不一致を防ぐ（下の設定で上書き）
                    if "manager_agent" in config:
                        config.pop("manager_agent", None)
            
            # エンベッダー設定の取得（ollamaを使用）
            # 環境変数からOllamaのURLを取得
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            embedder_model = os.getenv("EMBEDDER_MODEL", "mxbai-embed-large")
            
            embedder_config = {
                "provider": "ollama",  # ollamaを使用
                "config": {
                    "model": embedder_model,
                    # CrewAI 側は base_url を想定
                    "base_url": ollama_base_url
                }
            }
            
            # Knowledge sourcesの処理（Qdrantを使わないため簡素化、バックアップ版の復元）
            knowledge_sources = []
            if config.get("knowledge_sources"):
                # 共有KnowledgeManagerインスタンスを使用
                if self._knowledge_manager is None:
                    self._knowledge_manager = KnowledgeManager(
                        knowledge_dir=self.config.knowledge_dir,
                        embedder_config=embedder_config
                    )
                
                for source in config["knowledge_sources"]:
                    self._knowledge_manager.add_crew_knowledge(source)
                
                # KnowledgeManagerからBaseKnowledgeSourceインスタンスを取得
                knowledge_sources = self._knowledge_manager.crew_sources
                logger.info(f"Processed knowledge sources", count=len(knowledge_sources))
            
            # 処理された値で設定を更新
            config["agents"] = agents
            config["tasks"] = tasks
            config["process"] = process
            
            # knowledge_sourcesが存在する場合のみ追加
            if knowledge_sources:
                config["knowledge_sources"] = knowledge_sources
            
            # 指定されていない場合、デフォルト値を設定
            config.setdefault("name", crew_name)
            config.setdefault("memory", True)
            config.setdefault("cache", True)
            config.setdefault("verbose", True)
            
            # CrewAI のバージョンにより crew レベルの embedder バリデーションが厳しく
            # `ollama` が未対応扱いになるケースがあるため、ここでは設定しない。
            # 知識の埋め込みは KnowledgeManager 側で処理する。
            
            # mem0を使用する場合は、external_memoryとして設定（バックアップ版の復元）
            memory_config = config.get("memory_config", {})
            mem0_config = config.get("mem0_config", {})
            
            # env優先: USE_MEM0=true かつ MEM0_API_KEY があれば、YAMLが無くてもmem0を有効化
            use_mem0_env = os.getenv("USE_MEM0", "false").lower() == "true"
            mem0_api_key = os.getenv("MEM0_API_KEY")
            if (mem0_config or use_mem0_env) and mem0_api_key:
                try:
                    # user_id はYAML優先、なければ環境変数 MEM0_USER_ID、最後に既定
                    mem0_user_id = mem0_config.get("user_id") or os.getenv("MEM0_USER_ID", "okami_system")
                    
                    # ExternalMemoryを使用する設定（Mem0 v2 ストレージ差し替え）
                    from crewai.memory.external.external_memory import ExternalMemory
                    from core.mem0_v2_storage import Mem0V2Storage

                    storage = Mem0V2Storage(
                        user_id=mem0_user_id,
                        org_id=mem0_config.get("org_id"),
                        project_id=mem0_config.get("project_id"),
                        run_id=mem0_config.get("run_id"),
                        includes=mem0_config.get("includes"),
                        excludes=mem0_config.get("excludes"),
                        infer=mem0_config.get("infer", True),
                        api_key=mem0_api_key,
                        api_base=os.getenv("MEM0_API_BASE", "https://api.mem0.ai"),
                    )
                    external_memory = ExternalMemory(storage=storage)
                    
                    # CrewAIの正しい設定方法に従って設定
                    config["memory"] = True  # メモリを有効化
                    config["external_memory"] = external_memory  # ExternalMemoryを設定（mem0は内部でAPIキー参照）
                    
                    # mem0_configは削除（処理済みのため）
                    if "mem0_config" in config:
                        del config["mem0_config"]
                    
                    logger.info("Mem0 external memory configured (v2)", user_id=mem0_user_id, via_env=use_mem0_env and not mem0_config)
                    
                except Exception as e:
                    logger.error(f"Failed to configure mem0 external memory: {e}")
                    # フォールバック: 基本メモリ設定
                    config["memory"] = True
                    config["memory_config"] = {
                        "provider": "basic",
                        "config": {},
                        "user_memory": {}
                    }
            elif mem0_config and not os.getenv("MEM0_API_KEY"):
                # mem0_configが設定されているがAPIキーがない場合
                logger.warning("Mem0 configured but MEM0_API_KEY not found, using basic memory only")
                # mem0_configを削除
                if "mem0_config" in config:
                    del config["mem0_config"]
            
            # memory_configが設定されていない、または基本設定の場合
            if not memory_config or memory_config.get("provider") != "basic":
                # デフォルトのbasic memoryを設定
                config["memory"] = True
                config["memory_config"] = {
                    "provider": "basic",
                    "config": {},
                    "user_memory": {}
                }
            
            # グラフメモリの設定（crew_configから読み取るか、デフォルトで有効）
            use_graph_memory = config.get("graph_memory", True)
            if use_graph_memory and self.memory_manager.graph_memory:
                # グラフメモリ統計情報をログに記録
                stats = self.memory_manager.graph_memory.get_graph_statistics()
                logger.info(
                    "Graph memory enabled",
                    nodes=stats.get("total_nodes", 0),
                    edges=stats.get("total_edges", 0)
                )
            
            # マネージャー設定の処理
            if manager_llm:
                config["manager_llm"] = manager_llm
            elif manager_agent:
                # バリデーション順序の都合でこちらを優先的に渡す
                config["manager_agent"] = manager_agent
            
            # プランニングLLMの処理
            if config.get("planning") and config.get("planning_llm"):
                config["planning_llm"] = self.monica_llm
            
            # エンベッダー設定の処理（CrewAI >=0.160 では embedder/embedding 設定を要求するケースがある）
            # - 既定は Monica LLM + Ollama embeddings（.env/環境変数に基づく）
            # - まず OkamiConfig の embedder_config から Crew 用の embedder を組み立てる
            # - もしバリデーションで失敗したらフォールバックとして embedder を除去して再試行する
            provided_embedder = config.get("embedder")
            if not provided_embedder:
                try:
                    cfg_embedder = self.config.get_embedder_config()
                    # CrewAI は embedder に {provider, config} を期待
                    config["embedder"] = cfg_embedder
                    logger.info(
                        "Embedder configured for crew",
                        provider=cfg_embedder.get("provider"),
                        model=(cfg_embedder.get("config") or {}).get("model")
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to load embedder config from OkamiConfig, proceeding without explicit embedder",
                        error=str(e)
                    )
            else:
                # 既存の YAML embedder（ollama）の URL を Docker 内向けに正規化
                try:
                    if isinstance(provided_embedder, dict) and provided_embedder.get("provider") == "ollama":
                        cfg = provided_embedder.setdefault("config", {})
                        # YAMLにurlが明示されていればそれを優先し、無い場合のみ組み立てる
                        if not cfg.get("url"):
                            base = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
                            # コンテナ内から localhost を叩かないよう補正
                            try:
                                in_docker = os.path.exists("/.dockerenv") or os.getenv("IN_DOCKER") == "1"
                                if in_docker and ("localhost" in base or "127.0.0.1" in base):
                                    base = base.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                            except Exception:
                                pass
                            cfg["url"] = f"{base}/api/embeddings"
                            logger.info("Normalized Ollama embedder url", url=cfg.get("url"))
                        else:
                            logger.info("Using provided Ollama embedder url", url=cfg.get("url"))
                        config["embedder"] = {"provider": "ollama", "config": cfg}
                except Exception as e:
                    logger.warning("Failed to normalize provided embedder", error=str(e))
            # memory=True の場合は Short/Entity メモリに embedder_config を明示
            if config.get("memory"):
                try:
                    from crewai.memory.short_term.short_term_memory import ShortTermMemory
                    from crewai.memory.entity.entity_memory import EntityMemory
                    if "embedder" in config:
                        embedder_cfg = config["embedder"]
                    else:
                        embedder_cfg = self.config.get_embedder_config()
                    # デバッグログ: 実際に使われる URL/プロバイダ
                    try:
                        _prov = embedder_cfg.get("provider")
                        _url = (embedder_cfg.get("config") or {}).get("url")
                        logger.debug("Entity/Short embedder resolved", provider=_prov, url=_url)
                    except Exception:
                        pass
                    # 既に明示設定がなければ設定
                    config.setdefault("short_term_memory", ShortTermMemory(embedder_config=embedder_cfg))
                    config.setdefault("entity_memory", EntityMemory(embedder_config=embedder_cfg))
                except Exception as e:
                    logger.warning("Failed to configure short/entity memory embedder_config", error=str(e))
            
            # Evolution Crewの場合、コールバックを追加
            if crew_name == "evolution_crew":
                from evolution.evolution_callback import evolution_crew_callback, evolution_task_callback
                
                # Evolution設定から自動適用フラグを取得
                evolution_config = self.crew_configs[crew_name].get("evolution_config", {})
                auto_apply = evolution_config.get("auto_apply", False)
                
                # コールバックを設定
                config["task_callback"] = evolution_task_callback
                
                logger.info("Evolution callbacks configured", 
                          auto_apply=auto_apply,
                          crew_name=crew_name)
            
            # すべての設定パラメータでクルーを作成
            logger.info("Crew config used", crew_name=crew_name, config=truncate_dict(config))
            try:
                crew = Crew(**config)
                # 生成後、テスト互換性のためにマネージャーを agents に追加
                if process == Process.hierarchical and _append_manager_after_create and manager_agent:
                    try:
                        crew.agents.append(manager_agent)
                    except Exception:
                        pass
            except Exception as embed_err:
                # 一部の CrewAI バージョンでは provider バリデーションが厳しく失敗する可能性がある
                # フォールバック: embedder を除去して再試行
                if "embedder" in config:
                    faulty_embedder = config.pop("embedder")
                    logger.warning(
                        "Crew creation failed with embedder; retrying without embedder",
                        error=str(embed_err),
                        provider=(faulty_embedder or {}).get("provider")
                    )
                    crew = Crew(**config)
                else:
                    raise
            
            # カスタムメタデータの保存は不要
            
            logger.info(
                f"Crew created",
                name=crew.name,
                agents=len(agents),
                tasks=len(tasks),
                process=process_str,
                knowledge_sources=len(knowledge_sources),

            )
            
            return crew
            
        except Exception as e:
            logger.error(f"Failed to create crew", crew_name=crew_name, error=str(e))
            return None

    def get_crew(self, crew_name: str) -> Optional[Crew]:
        """
        クルーを取得または作成

        Args:
            crew_name: クルー名

        Returns:
            クルーインスタンスまたはNone
        """
        # 既にアクティブかチェック
        if crew_name in self.active_crews:
            return self.active_crews[crew_name]
        
        # 新しいクルーを作成
        crew = self.create_crew(crew_name)
        if crew:
            self.active_crews[crew_name] = crew
        
        return crew

    def get_active_crews(self) -> Dict[str, Crew]:
        """すべてのアクティブなクルーを取得"""
        return self.active_crews.copy()

    def list_crews(self) -> List[str]:
        """利用可能なクルー設定をリスト表示"""
        return list(self.crew_configs.keys())

    def list_agents(self) -> List[str]:
        """利用可能なエージェント設定をリスト表示"""
        return list(self.agent_configs.keys())

    def list_tasks(self) -> List[str]:
        """利用可能なタスク設定をリスト表示"""
        return list(self.task_configs.keys())

    def reload_configs(self) -> None:
        """すべての設定を再読み込み"""
        self.agent_configs = self._load_configs("agents")
        self.task_configs = self._load_configs("tasks")
        self.crew_configs = self._load_configs("crews")
        
        logger.info(
            "Configurations reloaded",
            agents=len(self.agent_configs),
            tasks=len(self.task_configs),
            crews=len(self.crew_configs)
        )

    def shutdown_crew(self, crew_name: str) -> bool:
        """
        クルーをシャットダウンして削除

        Args:
            crew_name: クルー名

        Returns:
            成功ステータス
        """
        if crew_name in self.active_crews:
            # TODO: 適切なクルーシャットダウンを実装
            del self.active_crews[crew_name]
            logger.info(f"Crew shutdown", crew_name=crew_name)
            return True
        
        return False

    def shutdown_all(self) -> None:
        """すべてのアクティブなクルーをシャットダウン"""
        crew_names = list(self.active_crews.keys())
        for crew_name in crew_names:
            self.shutdown_crew(crew_name)
        
        logger.info("すべてのクルーがシャットダウンされました")
