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


class QdrantKnowledgeSource:
    """Qdrantを使用したKnowledgeSource実装"""
    
    content: str = Field(description="Knowledge content to be stored")
    source_name: str = Field(default="qdrant_source", description="Name of the knowledge source")
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Qdrantは無効化されています")
    
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
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Qdrantは無効化されています")
    
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