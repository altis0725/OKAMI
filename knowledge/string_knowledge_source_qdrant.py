"""
QdrantベースのStringKnowledgeSource
CrewAIのStringKnowledgeSourceと互換性のあるQdrant実装
"""

from typing import Dict, Any, Optional
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from knowledge.qdrant_knowledge_source import QdrantKnowledgeStorage
from core.embedding_manager import get_embedding_manager
import structlog

logger = structlog.get_logger()


class StringKnowledgeSourceQdrant(StringKnowledgeSource):
    """Qdrantを使用するStringKnowledgeSource"""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None, 
                 collection_name: str = "okami_knowledge", **kwargs):
        # 親クラスの初期化
        super().__init__(content=content, metadata=metadata or {}, **kwargs)
        
        # QdrantベースのストレージをセットUp
        import os
        embedder_config = {
            "provider": "ollama",
            "config": {
                "model": os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
            }
        }
        self.storage = QdrantKnowledgeStorage(
            collection_name=collection_name,
            embedder_config=embedder_config
        )
        self.collection_name = collection_name
        
        # 統一されたEmbeddingManagerを取得
        self.embedding_manager = get_embedding_manager(embedder_config)
        
        logger.info(f"Initialized StringKnowledgeSourceQdrant with collection: {collection_name}")
    
    def add(self) -> None:
        """コンテンツを処理してQdrantに保存（親クラスのaddメソッドをオーバーライド）"""
        try:
            # テキストをチャンクに分割
            self.chunks = self._chunk_text(self.content)
            
            # メタデータを各チャンクに追加
            metadatas = []
            for i, chunk in enumerate(self.chunks):
                chunk_metadata = {
                    "source": "string_knowledge",
                    "chunk_index": i,
                    "total_chunks": len(self.chunks),
                    **self.metadata  # ユーザー定義のメタデータを含める
                }
                metadatas.append(chunk_metadata)
            
            # Qdrantストレージに保存
            self.storage.save(self.chunks, metadata=metadatas)
            
            logger.info(f"Successfully added {len(self.chunks)} chunks to Qdrant")
            
        except Exception as e:
            logger.error(f"Failed to add string knowledge to Qdrant: {e}")
            raise


def create_qdrant_string_source(content: str, metadata: Optional[Dict[str, Any]] = None,
                               collection_name: str = "okami_knowledge") -> StringKnowledgeSourceQdrant:
    """Qdrantベースの文字列知識ソースを作成するヘルパー関数"""
    return StringKnowledgeSourceQdrant(
        content=content,
        metadata=metadata,
        collection_name=collection_name
    )