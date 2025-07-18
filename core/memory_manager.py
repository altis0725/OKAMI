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
        self._init_long_term_memory()
        self._init_external_memory()

        logger.info(
            "Memory Manager initialized",
            storage_path=self.storage_path,
            use_mem0=self.use_mem0,
        )

    def _init_long_term_memory(self) -> None:
        """長期メモリストレージ初期化"""
        db_path = os.path.join(self.storage_path, "long_term_memory.db")
        self.long_term_memory = LongTermMemory(
            storage=LTMSQLiteStorage(db_path=db_path)
        )

    def _init_external_memory(self) -> None:
        """外部メモリ（Mem0）初期化"""
        if self.use_mem0 and os.getenv("MEM0_API_KEY"):
            try:
                self.external_memory = ExternalMemory(
                    embedder_config={
                        "provider": "mem0",
                        "config": {
                            "user_id": self.mem0_config.get("user_id", "okami_system"),
                            "api_key": os.getenv("MEM0_API_KEY"),
                            **self.mem0_config,
                        },
                    }
                )
                logger.info("Mem0 external memory initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mem0: {e}")
                self.external_memory = None
        else:
            self.external_memory = None

    def get_memory_config(self) -> Dict[str, Any]:
        """CrewAI用メモリ設定を取得"""
        config = {
            "memory": True,
            "long_term_memory": self.long_term_memory,
        }

        if self.external_memory:
            config["external_memory"] = self.external_memory

        if self.use_mem0:
            config["memory_config"] = {
                "provider": "mem0",
                "config": self.mem0_config,
                "user_memory": {},
            }

        return config

    def save_memory(self, key: str, value: Any, metadata: Optional[Dict] = None) -> None:
        """
        メモリエントリ保存

        Args:
            key: メモリキー
            value: メモリ値
            metadata: 追加メタデータ
        """
        try:
            if self.external_memory:
                self.external_memory.save(value, metadata=metadata)
            logger.info("Memory saved", key=key, has_metadata=bool(metadata))
        except Exception as e:
            logger.error(f"Failed to save memory: {e}", key=key)

    def search_memory(
        self, query: str, limit: int = 10, score_threshold: float = 0.5
    ) -> List[Dict]:
        """
        メモリ検索

        Args:
            query: 検索クエリ
            limit: 最大件数
            score_threshold: 閾値

        Returns:
            検索結果リスト
        """
        try:
            if self.external_memory:
                results = self.external_memory.search(
                    query, limit=limit, score_threshold=score_threshold
                )
                logger.info(f"Memory search completed", query=query, results=len(results))
                return results
            return []
        except Exception as e:
            logger.error(f"Failed to search memory: {e}", query=query)
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