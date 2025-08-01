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

logger = structlog.get_logger()


class MemoryManager:
    """OKAMIエージェントの全メモリを管理するクラス"""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_mem0: bool = False,
        mem0_config: Optional[Dict[str, Any]] = None,
    ):
        """
        メモリマネージャの初期化

        Args:
            storage_path: メモリ保存先パス
            use_mem0: Mem0高度メモリ利用有無
            mem0_config: Mem0設定
        """
        self.storage_path = storage_path or db_storage_path()
        self.use_mem0 = use_mem0
        self.mem0_config = mem0_config or {}

        # Ensure storage directory exists
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

        # Initialize memory components
        self._init_short_term_memory()
        self._init_long_term_memory()
        self._init_external_memory()

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
            memory_type: リセット種別（'short', 'long', 'entity', 'all'）
        """
        try:
            if memory_type in ["all", "external"] and self.external_memory:
                self.external_memory.reset()
            logger.info(f"Memory reset completed", memory_type=memory_type)
        except Exception as e:
            logger.error(f"Failed to reset memory: {e}", memory_type=memory_type)