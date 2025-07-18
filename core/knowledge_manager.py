"""
OKAMIシステム用ナレッジマネージャ
クルー全体・エージェント個別の知識管理（RAG対応）
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage
from crewai.knowledge.knowledge_config import KnowledgeConfig
import chromadb
from crewai.utilities.paths import db_storage_path

logger = structlog.get_logger()


class KnowledgeManager:
    """OKAMIシステムの知識ソースを管理するクラス"""

    def __init__(
        self,
        knowledge_dir: Optional[str] = None,
        embedder_config: Optional[Dict[str, Any]] = None,
    ):
        """
        ナレッジマネージャの初期化

        Args:
            knowledge_dir: 知識ファイルのディレクトリ
            embedder_config: 埋め込みモデルの設定
        """
        self.knowledge_dir = knowledge_dir or os.path.join(os.getcwd(), "knowledge")
        self.embedder_config = embedder_config or {
            "provider": "openai",
            "config": {"model": "text-embedding-3-small"},
        }

        # Ensure knowledge directory exists
        Path(self.knowledge_dir).mkdir(parents=True, exist_ok=True)

        # Knowledge sources registry
        self.crew_sources: List[Any] = []
        self.agent_sources: Dict[str, List[Any]] = {}

        # Initialize ChromaDB client
        self._init_chromadb()

        logger.info(
            "Knowledge Manager initialized",
            knowledge_dir=self.knowledge_dir,
            embedder_provider=self.embedder_config.get("provider"),
        )

    def _init_chromadb(self) -> None:
        """知識ストレージ用ChromaDBクライアント初期化"""
        try:
            storage_path = os.path.join(db_storage_path(), "knowledge")
            self.chroma_client = chromadb.PersistentClient(path=storage_path)
            logger.info("ChromaDB initialized", path=storage_path)
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None

    def add_crew_knowledge(self, source: Any) -> None:
        """
        クルー全体の知識ソースを追加

        Args:
            source: 知識ソース（文字列またはファイル等）
        """
        if isinstance(source, str):
            # Check if it's a file path or content
            if os.path.exists(os.path.join(self.knowledge_dir, source)):
                knowledge_source = TextFileKnowledgeSource(
                    file_paths=[os.path.join(self.knowledge_dir, source)]
                )
            else:
                knowledge_source = StringKnowledgeSource(content=source)
        else:
            knowledge_source = source

        self.crew_sources.append(knowledge_source)
        logger.info("Crew knowledge source added", source_type=type(knowledge_source).__name__)

    def add_agent_knowledge(self, agent_role: str, source: Any) -> None:
        """
        エージェント個別の知識ソースを追加

        Args:
            agent_role: エージェントの役割名
            source: 知識ソース
        """
        if agent_role not in self.agent_sources:
            self.agent_sources[agent_role] = []

        if isinstance(source, str):
            if os.path.exists(os.path.join(self.knowledge_dir, source)):
                knowledge_source = TextFileKnowledgeSource(
                    file_paths=[os.path.join(self.knowledge_dir, source)]
                )
            else:
                knowledge_source = StringKnowledgeSource(content=source)
        else:
            knowledge_source = source

        self.agent_sources[agent_role].append(knowledge_source)
        logger.info(
            "Agent knowledge source added",
            agent_role=agent_role,
            source_type=type(knowledge_source).__name__,
        )

    def get_crew_knowledge_config(self) -> Dict[str, Any]:
        """クルー全体の知識設定を取得"""
        if not self.crew_sources:
            return {}

        return {
            "knowledge_sources": self.crew_sources,
            "embedder": self.embedder_config,
        }

    def get_agent_knowledge_config(
        self, agent_role: str, knowledge_config: Optional[KnowledgeConfig] = None
    ) -> Dict[str, Any]:
        """
        エージェント個別の知識設定を取得

        Args:
            agent_role: エージェントの役割
            knowledge_config: オプションの知識取得設定

        Returns:
            知識設定の辞書
        """
        sources = self.agent_sources.get(agent_role, [])
        if not sources:
            return {}

        config = {
            "knowledge_sources": sources,
            "embedder": self.embedder_config,
        }

        if knowledge_config:
            config["knowledge_config"] = knowledge_config

        return config

    def create_custom_storage(
        self, collection_name: str, embedder_config: Optional[Dict] = None
    ) -> KnowledgeStorage:
        """
        カスタム知識ストレージを作成

        Args:
            collection_name: コレクション名
            embedder_config: 埋め込み設定

        Returns:
            KnowledgeStorageインスタンス
        """
        return KnowledgeStorage(
            embedder=embedder_config or self.embedder_config,
            collection_name=collection_name,
        )

    def list_collections(self) -> List[str]:
        """全知識コレクション名をリストで返す"""
        if self.chroma_client:
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        コレクション情報を取得

        Args:
            collection_name: コレクション名

        Returns:
            コレクション情報
        """
        if self.chroma_client:
            try:
                collection = self.chroma_client.get_collection(collection_name)
                return {
                    "name": collection.name,
                    "count": collection.count(),
                    "metadata": collection.metadata,
                }
            except Exception as e:
                logger.error(f"Failed to get collection info: {e}", collection=collection_name)
        return {}

    def reset_knowledge(self, knowledge_type: str = "all") -> None:
        """
        知識をリセット

        Args:
            knowledge_type: リセット対象（'crew', 'agent', 'all'）
        """
        try:
            if knowledge_type in ["crew", "all"]:
                self.crew_sources.clear()

            if knowledge_type in ["agent", "all"]:
                self.agent_sources.clear()

            logger.info("Knowledge reset completed", knowledge_type=knowledge_type)
        except Exception as e:
            logger.error(f"Failed to reset knowledge: {e}", knowledge_type=knowledge_type)