"""
QdrantベースのカスタムKnowledgeSource
CrewAIのKnowledgeSourceとしてQdrantを使用する実装
"""

from typing import List, Dict, Any, Optional, Union
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
# from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage
from pydantic import Field, ConfigDict
import numpy as np
import structlog
import os
from core.vector_store import get_vector_store
from core.embedding_manager import get_embedding_manager

logger = structlog.get_logger()


class QdrantKnowledgeSource(BaseKnowledgeSource):
    """Qdrantを使用したKnowledgeSource実装"""
    
    content: str = Field(description="Knowledge content to be stored")
    source_name: str = Field(default="qdrant_source", description="Name of the knowledge source")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Qdrantベースのカスタムストレージを初期化
        if not self.storage:
            embedder_config = {
                "provider": "ollama",
                "config": {
                    "model": os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                }
            }
            self.storage = QdrantKnowledgeStorage(
                collection_name=self.collection_name or "okami_knowledge",
                embedder_config=embedder_config
            )
            # 統一されたEmbeddingManagerを取得
            self.embedding_manager = get_embedding_manager(embedder_config)
    
    def validate_content(self) -> str:
        """コンテンツを検証して返す"""
        if not self.content:
            raise ValueError("Content cannot be empty")
        return self.content
    
    def add(self) -> None:
        """コンテンツを処理してQdrantに保存"""
        try:
            # コンテンツを検証
            validated_content = self.validate_content()
            
            # テキストをチャンクに分割
            self.chunks = self._chunk_text(validated_content)
            logger.info(f"Created {len(self.chunks)} chunks from content")
            
            # 各チャンクにメタデータを追加
            metadatas = []
            for i, chunk in enumerate(self.chunks):
                metadata = {
                    "source": self.source_name,
                    "chunk_index": i,
                    "total_chunks": len(self.chunks),
                    **self.metadata  # ユーザー定義のメタデータを追加
                }
                metadatas.append(metadata)
            
            # ストレージに保存（エンベディングはストレージ側で生成）
            if self.storage:
                self.storage.save(self.chunks, metadata=metadatas)
                logger.info(f"Successfully saved {len(self.chunks)} chunks to Qdrant")
            else:
                raise ValueError("Storage not initialized")
                
        except Exception as e:
            logger.error(f"Failed to add knowledge to Qdrant: {e}")
            raise


class QdrantKnowledgeStorage:
    """Qdrantを使用したKnowledgeStorage実装"""
    
    def __init__(self, collection_name: str = "okami_knowledge", 
                 embedder_config: Optional[Dict[str, Any]] = None):
        # Qdrantベクトルストアを初期化
        self.vector_store = get_vector_store()
        self.collection_name = collection_name
        self.embedder_config = embedder_config or {
            "provider": "ollama",
            "config": {
                "model": os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            }
        }
        
        # コレクションを作成
        try:
            self.vector_store.create_collection(
                name=self.collection_name,
                dimension=1024  # mxbai-embed-largeの次元
            )
        except Exception as e:
            logger.debug(f"Collection may already exist: {e}")
        
        # 統一されたEmbeddingManagerを使用
        self.embedding_manager = get_embedding_manager(self.embedder_config)
        
        # 親クラスの初期化は行わない（ChromaDBを避けるため）
        # super().__init__(
        #     embedder=self.embedder_config,
        #     collection_name=self.collection_name
        # )
    
    def save(self, chunks: List[str], metadata: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None) -> None:
        """チャンクをエンベディングしてQdrantに保存"""
        try:
            # 統一されたEmbeddingManagerでエンベディングを生成
            embeddings = self.embedding_manager.generate_embeddings(chunks)
            
            # メタデータの処理
            if metadata is None:
                metadatas = [{} for _ in chunks]
            elif isinstance(metadata, dict):
                metadatas = [metadata for _ in chunks]
            else:
                metadatas = metadata
            
            # Qdrantに保存
            self.vector_store.upsert(
                collection_name=self.collection_name,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            logger.info(f"Saved {len(chunks)} chunks to Qdrant collection '{self.collection_name}'")
            
        except Exception as e:
            logger.error(f"Failed to save to Qdrant: {e}")
            raise
    
    def query(self, queries: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """クエリに基づいて関連ドキュメントを検索"""
        try:
            all_results = []
            
            for query in queries:
                # 統一されたEmbeddingManagerでクエリをエンベディング
                query_embedding = self.embedding_manager.generate_single_embedding(query)
                
                # Qdrantで検索
                results = self.vector_store.query(
                    collection_name=self.collection_name,
                    query_embedding=query_embedding,
                    n_results=top_k
                )
                
                # 結果を整形
                if results.get("documents") and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        result = {
                            "content": doc,
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "score": 1 - results["distances"][0][i] if results.get("distances") else 0.0
                        }
                        all_results.append(result)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Failed to query Qdrant: {e}")
            return []