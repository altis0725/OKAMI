"""
OKAMIシステム用メモリマネージャ
短期・長期・エンティティメモリ管理（Mem0対応）
CrewAI 0.157.0対応版 - ExternalMemoryへの移行とエラー許容モード実装
"""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog
from crewai.memory.external.external_memory import ExternalMemory
import crewai as _crewai_pkg
from crewai.utilities.paths import db_storage_path

from .graph_memory_manager import GraphMemoryManager
from .knowledge_graph_integration import KnowledgeGraphIntegration
from utils.mem0_helper import mem0_error_handler, Mem0StatusChecker

logger = structlog.get_logger()


class MemoryManager:
    """OKAMIエージェントの全メモリを管理するクラス（CrewAI 0.157.0対応）"""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_mem0: bool = False,
        mem0_config: Optional[Dict[str, Any]] = None,
        use_graph_memory: bool = True,
        fallback_to_basic: bool = True,
    ):
        """
        メモリマネージャの初期化

        Args:
            storage_path: メモリ保存先パス
            use_mem0: Mem0高度メモリ利用有無
            mem0_config: Mem0設定
            use_graph_memory: グラフメモリを使用するか
            fallback_to_basic: Mem0エラー時に基本メモリにフォールバックするか
        """
        self.storage_path = storage_path or db_storage_path()
        self.use_mem0 = use_mem0
        self.mem0_config = mem0_config or {}
        self.use_graph_memory = use_graph_memory
        self.fallback_to_basic = fallback_to_basic
        self.external_memory = None
        self.mem0_initialized = False

        # Ensure storage directory exists
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize external memory only if mem0 is enabled
        if self.use_mem0:
            self._init_external_memory_with_fallback()
        
        # Initialize graph memory if enabled
        if self.use_graph_memory:
            self.graph_memory = GraphMemoryManager()
            # KnowledgeManagerは別途CrewFactoryで管理されるため、ここではNoneを渡す
            self.kg_integration = KnowledgeGraphIntegration(
                knowledge_manager=None,
                graph_memory=self.graph_memory
            )
        else:
            self.graph_memory = None
            self.kg_integration = None

        logger.info(
            "Memory Manager initialized",
            storage_path=self.storage_path,
            use_mem0=self.use_mem0,
            mem0_initialized=self.mem0_initialized,
            fallback_mode=not self.mem0_initialized and self.fallback_to_basic
        )

    def _init_external_memory_with_fallback(self) -> None:
        """外部メモリ（Mem0）初期化（エラー許容モード）"""
        if not self.use_mem0:
            logger.info("Mem0 disabled by configuration")
            return
            
        mem0_api_key = os.getenv("MEM0_API_KEY")
        
        if not mem0_api_key:
            logger.warning("MEM0_API_KEY not found. Using limited memory features.")
            return
        
        try:
            # crewai バージョン差異に対応
            def _parse_ver(v: str):
                try:
                    parts = [int(p) for p in v.split(".")[:3]]
                    while len(parts) < 3:
                        parts.append(0)
                    return tuple(parts)
                except Exception:
                    return (0, 0, 0)

            _ver = _parse_ver(getattr(_crewai_pkg, "__version__", "0.0.0"))

            if _ver < (0, 160, 0):
                # crewai 0.159 系: embedder_config.provider に mem0 を指定
                self.external_memory = ExternalMemory(
                    embedder_config={
                        "provider": "mem0",
                        "config": {
                            "user_id": self.mem0_config.get("user_id", "okami_system"),
                            "run_id": self.mem0_config.get("run_id"),
                            "org_id": self.mem0_config.get("org_id"),
                            "project_id": self.mem0_config.get("project_id"),
                            "api_key": mem0_api_key,
                            "api_version": "v2"
                        }
                    }
                )
            else:
                # crewai 0.160+ 系: embedder_config は埋め込み、memory_config で mem0
                self.external_memory = ExternalMemory(
                    embedder_config={
                        "provider": "ollama",
                        "config": {
                            "model": "nomic-embed-text:latest",
                            "base_url": "http://localhost:11434"
                        }
                    },
                    memory_config={
                        "provider": "mem0",
                        "config": {
                            "user_id": self.mem0_config.get("user_id", "okami_system"),
                            "run_id": self.mem0_config.get("run_id"),
                            "org_id": self.mem0_config.get("org_id"),
                            "project_id": self.mem0_config.get("project_id"),
                            "api_key": mem0_api_key,
                            "api_version": "v2"
                        }
                    }
                )
            self.mem0_initialized = True
            logger.info("Mem0 ExternalMemory initialized successfully (V2 API)")
            
        except Exception as e:
            logger.error(f"Mem0 initialization failed: {e}")
            
            # フォールバック1: ローカルMem0設定を試す
            if self.mem0_config.get("local_mem0_config"):
                self._try_local_mem0()
            
            # フォールバック2: 基本メモリで継続
            elif self.fallback_to_basic:
                logger.warning("Continuing with basic memory provider")
                self.external_memory = None
                self.mem0_initialized = False
    
    def _try_local_mem0(self) -> None:
        """ローカルMem0設定での初期化を試みる"""
        try:
            local_config = self.mem0_config.get("local_mem0_config", {})
            
            # Ollamaベースのローカル設定
            self.external_memory = ExternalMemory(
                embedder_config={
                    "provider": local_config.get("embedder", {}).get("provider", "ollama"),
                    "config": local_config.get("embedder", {}).get("config", {
                        "model": "nomic-embed-text:latest",
                        "base_url": "http://localhost:11434"
                    })
                },
                memory_config={
                    "provider": "mem0",
                    "config": {
                        **local_config.get("vector_store", {}).get("config", {}),
                        "user_id": self.mem0_config.get("user_id", "okami_system"),
                        "local_mode": True  # ローカルモードフラグ
                    }
                }
            )
            self.mem0_initialized = True
            logger.info("Local Mem0 configuration applied successfully")
            
        except Exception as e:
            logger.error(f"Local Mem0 setup failed: {e}")
            self.external_memory = None
            self.mem0_initialized = False

    def get_crew_memory_config(self) -> Dict[str, Any]:
        """Crew用のメモリ設定を取得（エラー許容モード対応）"""
        if self.external_memory and self.mem0_initialized:
            # ExternalMemoryが利用可能な場合
            return {
                "memory": True,
                "external_memory": self.external_memory
            }
        else:
            # 基本メモリプロバイダーを使用（フォールバック）
            return {
                "memory": True,
                "memory_config": {"provider": "basic"}
            }

    def get_memory_config(self) -> Dict[str, Any]:
        """CrewAI用メモリ設定を取得（後方互換性のため維持）"""
        return self.get_crew_memory_config()

    @mem0_error_handler
    def save_memory(self, key: str, value: str, metadata: Dict[str, Any] = None) -> bool:
        """メモリを保存（エラー許容）"""
        if self.external_memory and self.mem0_initialized:
            # mem0のAPI形式に合わせてデータを整形
            from crewai.memory.external.external_memory_item import ExternalMemoryItem
            
            memory_item = ExternalMemoryItem(
                content=value,
                metadata=metadata or {},
                key=key
            )
            
            # リスト形式で保存
            self.external_memory.save([memory_item])
            return True
        return False

    @mem0_error_handler
    def search_memory(self, query: str, limit: int = 10, score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """メモリを検索（エラー許容）"""
        if self.external_memory and self.mem0_initialized:
            # V2 API対応のパラメータ調整
            try:
                results = self.external_memory.search(
                    query, 
                    limit=limit, 
                    score_threshold=score_threshold
                )
                return results
            except TypeError as e:
                # metadataパラメータエラーの場合、パラメータを調整して再試行
                if "metadata" in str(e):
                    logger.warning("Adjusting search parameters for V2 API compatibility")
                    results = self.external_memory.search(
                        query,
                        limit=limit
                    )
                    return results
                raise
        return []

    def reset_memory(self, memory_type: str = "all") -> None:
        """
        メモリリセット

        Args:
            memory_type: リセット種別（'short', 'long', 'entity', 'graph', 'all'）
        """
        try:
            if memory_type in ["all", "external"] and self.external_memory:
                if hasattr(self.external_memory, 'reset'):
                    self.external_memory.reset()
            if memory_type in ["all", "graph"] and self.graph_memory:
                # グラフメモリをリセット（新しいグラフで初期化）
                import networkx as nx
                self.graph_memory.memory_graph = nx.DiGraph()
                self.graph_memory.save_memory_graph()
            logger.info(f"Memory reset completed", memory_type=memory_type)
        except Exception as e:
            logger.error(f"Failed to reset memory: {e}", memory_type=memory_type)
    
    def record_task_in_graph(
        self,
        task_id: str,
        agent_name: str,
        task_description: str,
        result: str,
        success: bool = True
    ) -> None:
        """
        タスク実行をグラフメモリに記録
        
        Args:
            task_id: タスクID
            agent_name: エージェント名
            task_description: タスク説明
            result: 実行結果
            success: 成功フラグ
        """
        if self.graph_memory:
            self.graph_memory.record_task_execution(
                task_id=task_id,
                agent_name=agent_name,
                task_description=task_description,
                result=result,
                success=success
            )
    
    def search_graph_memory(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        グラフメモリを検索
        
        Args:
            query: 検索クエリ
            node_types: フィルタするノードタイプ
            limit: 結果の最大数
            
        Returns:
            検索結果のリスト
        """
        if self.graph_memory:
            return self.graph_memory.search_memories(
                query=query,
                node_types=node_types,
                limit=limit
            )
        return []
    
    def get_enhanced_memory_config(self) -> Dict[str, Any]:
        """
        グラフメモリを含む拡張メモリ設定を取得
        
        Returns:
            拡張メモリ設定
        """
        config = self.get_crew_memory_config()
        
        # Mem0ステータス情報を追加
        config["mem0_status"] = {
            "initialized": self.mem0_initialized,
            "fallback_mode": not self.mem0_initialized and self.fallback_to_basic,
            "api_key_present": bool(os.getenv("MEM0_API_KEY")),
            "local_mode": bool(self.mem0_config.get("local_mem0_config"))
        }
        
        if self.use_graph_memory and self.graph_memory:
            config["graph_memory"] = {
                "enabled": True,
                "storage_path": str(self.graph_memory.storage_path),
                "statistics": self.graph_memory.get_graph_statistics()
            }
        
        return config
    
    def check_mem0_status(self) -> Dict[str, Any]:
        """
        Mem0の現在の状態を確認
        
        Returns:
            ステータス情報
        """
        status = Mem0StatusChecker.check_mem0_availability()
        status["memory_manager_state"] = {
            "initialized": self.mem0_initialized,
            "external_memory_active": self.external_memory is not None,
            "fallback_active": not self.mem0_initialized and self.fallback_to_basic
        }
        return status
