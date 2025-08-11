"""
OKAMIシステム用メモリマネージャ
短期・長期・エンティティメモリ管理（Mem0対応）
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog
from crewai.memory import LongTermMemory
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
from crewai.memory.external.external_memory import ExternalMemory
from crewai.utilities.paths import db_storage_path

from .graph_memory_manager import GraphMemoryManager
from .knowledge_graph_integration import KnowledgeGraphIntegration

logger = structlog.get_logger()


class MemoryManager:
    """OKAMIエージェントの全メモリを管理するクラス"""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_mem0: bool = False,
        mem0_config: Optional[Dict[str, Any]] = None,
        use_graph_memory: bool = True,
    ):
        """
        メモリマネージャの初期化

        Args:
            storage_path: メモリ保存先パス
            use_mem0: Mem0高度メモリ利用有無
            mem0_config: Mem0設定
            use_graph_memory: グラフメモリを使用するか
        """
        self.storage_path = storage_path or db_storage_path()
        self.use_mem0 = use_mem0
        self.mem0_config = mem0_config or {}
        self.use_graph_memory = use_graph_memory

        # Ensure storage directory exists
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize memory components
        self._init_short_term_memory()
        self._init_long_term_memory()
        self._init_external_memory()
        
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
        )

    def _init_short_term_memory(self) -> None:
        """短期メモリ初期化（Qdrantを使わないため無効化）"""
        # Qdrantを使わないため、ShortTermMemoryは初期化しない
        self.short_term_memory = None

    def _init_long_term_memory(self) -> None:
        """長期メモリ初期化（Qdrantを使わないため無効化）"""
        # Qdrantを使わないため、LongTermMemoryは初期化しない
        self.long_term_memory = None

    def _init_external_memory(self) -> None:
        """外部メモリ（Mem0）初期化"""
        if self.use_mem0 and os.getenv("MEM0_API_KEY"):
            try:
                self.external_memory = ExternalMemory(
                    embedder_config={
                        "provider": "huggingface",
                        "config": {
                            "model": "sentence-transformers/all-MiniLM-L6-v2"
                        }
                    },
                    memory_config={
                        "provider": "mem0",
                        "config": {
                            "user_id": self.mem0_config.get("user_id", "okami_system"),
                            "org_id": self.mem0_config.get("org_id"),
                            "project_id": self.mem0_config.get("project_id"),
                            "api_key": os.getenv("MEM0_API_KEY")
                        }
                    }
                )
                logger.info("Mem0 external memory initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mem0: {e}")
                self.external_memory = None
        else:
            self.external_memory = None

    def get_memory_config(self) -> Dict[str, Any]:
        """CrewAI用メモリ設定を取得（Qdrantを使わずにmem0のみ使用）"""
        config = {
            "memory": True,
        }

        if self.use_mem0:
            # ExternalMemoryを使用する設定（embedderはollama、memoryはmem0）
            from crewai.memory.external.external_memory import ExternalMemory
            
            external_memory = ExternalMemory(
                embedder_config={
                    "provider": "huggingface",
                    "config": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                },
                memory_config={
                    "provider": "mem0",
                    "config": {
                        "user_id": self.mem0_config.get("user_id", "okami_system"),
                        "org_id": self.mem0_config.get("org_id"),
                        "project_id": self.mem0_config.get("project_id"),
                        "api_key": os.getenv("MEM0_API_KEY")
                    }
                }
            )
            
            config["memory"] = True
            config["external_memory"] = external_memory
        else:
            # デフォルトのbasic memory設定（Qdrantを使わない）
            config["memory_config"] = {
                "provider": "basic",
                "config": {},
                "user_memory": {}
            }

        return config

    def save_memory(self, key: str, value: str, metadata: Dict[str, Any] = None) -> bool:
        """メモリを保存"""
        try:
            if self.external_memory:
                # mem0のAPI形式に合わせてデータを整形
                # mem0はExternalMemoryItemのリストを期待する
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
        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")
            return False

    def search_memory(self, query: str, limit: int = 10, score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """メモリを検索"""
        try:
            if self.external_memory:
                results = self.external_memory.search(query, limit=limit, score_threshold=score_threshold)
                return results
            return []
        except Exception as e:
            self.logger.error(f"Failed to search memory: {e}")
            return []

    def reset_memory(self, memory_type: str = "all") -> None:
        """
        メモリリセット

        Args:
            memory_type: リセット種別（'short', 'long', 'entity', 'graph', 'all'）
        """
        try:
            if memory_type in ["all", "external"] and self.external_memory:
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
        config = self.get_memory_config()
        
        if self.use_graph_memory and self.graph_memory:
            config["graph_memory"] = {
                "enabled": True,
                "storage_path": str(self.graph_memory.storage_path),
                "statistics": self.graph_memory.get_graph_statistics()
            }
        
        return config