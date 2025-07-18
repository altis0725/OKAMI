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
from core.memory_manager import MemoryManager
from core.knowledge_manager import KnowledgeManager
from core.guardrail_manager import GuardrailManager
from crewai import Process
from crewai.project import CrewBase
from utils.config import get_config
from tools import get_mcp_tools_for_agent
from tools.mcp_docker_tool import get_docker_tools
from knowledge.knowledge_loader import get_knowledge_for_crew
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
        
        # Monica LLMの初期化
        self.monica_llm = LLM(
            model="gpt-4o",
            api_key=os.environ.get("MONICA_API_KEY"),
            base_url="https://openapi.monica.im/v1"
        )
        
        # 設定の読み込み
        self.agent_configs = self._load_configs("agents")
        self.task_configs = self._load_configs("tasks")
        self.crew_configs = self._load_configs("crews")
        
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
            
            # 知識コンテキストを取得
            knowledge_context = get_knowledge_for_crew()
            
            # 利用可能な場合、知識をバックストーリーに追加
            backstory = config.get("backstory", "")
            if knowledge_context:
                backstory = f"{backstory}\n\n{knowledge_context}"
            
            # Update config with processed values
            config["backstory"] = backstory
            config["tools"] = agent_tools
            config["llm"] = self.monica_llm
            
            # 指定されていない場合、デフォルト値を設定
            config.setdefault("verbose", True)
            config.setdefault("memory", True)
            config.setdefault("max_iter", self.config.default_max_iter)
            config.setdefault("allow_delegation", True)
            
            # すべての設定パラメータでエージェントを作成
            logger.info("Agent config used", agent_name=agent_name, config=truncate_dict(config))
            agent = Agent(**config)
            
            logger.info(f"Agent created", role=agent.role)
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
            
            # デフォルトでツールを設定
            config.setdefault("tools", [])
            
            # すべての設定パラメータでタスクを作成
            logger.info("Task config used", task_name=task_name, config=truncate_dict(config))
            task = Task(**config)
            
            # 後で解決するためにコンテキスト名を保存
            if context_names:
                task._context_names = context_names
            
            logger.info(f"Task created", description=task.description[:50])
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
            
            if process == Process.hierarchical:
                # 指定されている場合はmanager_llmを設定（CrewAIが独自のマネージャーを作成するため）
                if config.get("manager_llm"):
                    manager_llm = self.monica_llm
                
                # または指定されている場合はカスタムマネージャーエージェントを使用
                if config.get("manager_agent"):
                    manager_agent_name = config.get("manager_agent")
                    # マネージャーエージェントを作成（まだエージェントリストに含まれていない場合）
                    manager_agent = self.create_agent(manager_agent_name)
                    if manager_agent and manager_agent not in agents:
                        # マネージャーエージェントは階層プロセスでは別扱いなので追加しない
                        pass
            
            # エンベッダー設定の取得
            embedder_config = config.get("embedder", self.config.get_embedder_config())
            
            # 処理された値で設定を更新
            config["agents"] = agents
            config["tasks"] = tasks
            config["process"] = process
            
            # 指定されていない場合、デフォルト値を設定
            config.setdefault("name", crew_name)
            config.setdefault("memory", True)
            config.setdefault("cache", True)
            config.setdefault("verbose", True)
            
            # マネージャー設定の処理
            if manager_llm:
                config["manager_llm"] = manager_llm
            elif manager_agent:
                config["manager_agent"] = manager_agent
            
            # プランニングLLMの処理
            if config.get("planning") and config.get("planning_llm"):
                config["planning_llm"] = self.monica_llm
            
            # エンベッダー設定の処理
            if config.get("memory_config", {}).get("provider") != "basic":
                config["embedder"] = embedder_config
            
            # すべての設定パラメータでクルーを作成
            logger.info("Crew config used", crew_name=crew_name, config=truncate_dict(config))
            crew = Crew(**config)
            
            # カスタムメタデータの保存は不要
            
            logger.info(
                f"Crew created",
                name=crew.name,
                agents=len(agents),
                tasks=len(tasks),
                process=process_str
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