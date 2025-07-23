"""
ベクトルストアの統一インターフェース
QdrantとChromaDBの両方をサポート
"""

import os
from typing import List, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
import chromadb
import uuid

logger = structlog.get_logger()


class VectorStore(ABC):
    """ベクトルストアの抽象基底クラス"""
    
    @abstractmethod
    def create_collection(self, name: str, dimension: int) -> None:
        """コレクションを作成"""
        pass
    
    @abstractmethod
    def upsert(self, collection_name: str, embeddings: List[List[float]], 
               documents: List[str], metadatas: List[Dict[str, Any]], 
               ids: Optional[List[str]] = None) -> None:
        """ベクトルとメタデータを挿入/更新"""
        pass
    
    @abstractmethod
    def query(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ベクトル検索を実行"""
        pass
    
    @abstractmethod
    def delete(self, collection_name: str, ids: List[str]) -> None:
        """IDによって削除"""
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """コレクション一覧を取得"""
        pass


class QdrantVectorStore(VectorStore):
    """Qdrantベクトルストアの実装"""
    
    def __init__(self, host: str = None, port: int = None, grpc_port: int = None):
        """
        Qdrantクライアントを初期化
        
        Args:
            host: Qdrantホスト（デフォルト: 環境変数 QDRANT_HOST または localhost）
            port: HTTP APIポート（デフォルト: 環境変数 QDRANT_PORT または 6333）
            grpc_port: gRPCポート（デフォルト: 環境変数 QDRANT_GRPC_PORT または 6334）
        """
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.grpc_port = grpc_port or int(os.getenv("QDRANT_GRPC_PORT", "6334"))
        
        self.client = QdrantClient(
            host=self.host,
            port=self.port,
            prefer_grpc=False  # HTTPを使用
        )
        
        logger.info(
            "Qdrant vector store initialized",
            host=self.host,
            port=self.port
        )
    
    def create_collection(self, name: str, dimension: int) -> None:
        """コレクションを作成"""
        try:
            # コレクションが既に存在するかチェック
            collections = self.client.get_collections().collections
            if any(col.name == name for col in collections):
                logger.info(f"Collection {name} already exists")
                return
            
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection {name} with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise
    
    def upsert(self, collection_name: str, embeddings: List[List[float]], 
               documents: List[str], metadatas: List[Dict[str, Any]], 
               ids: Optional[List[str]] = None) -> None:
        """ベクトルとメタデータを挿入/更新"""
        try:
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in embeddings]
            
            points = []
            for i, (embedding, doc, metadata, point_id) in enumerate(
                zip(embeddings, documents, metadatas, ids)
            ):
                # メタデータにドキュメントテキストを含める
                payload = metadata.copy()
                payload["text"] = doc
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} points to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to upsert to {collection_name}: {e}")
            raise
    
    def query(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ベクトル検索を実行"""
        try:
            # Qdrant用のフィルターを構築
            query_filter = None
            if filter:
                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)
            
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=n_results,
                query_filter=query_filter,
                with_payload=True
            )
            
            # CrewAI互換の形式に変換
            ids = []
            documents = []
            metadatas = []
            distances = []
            
            for result in results:
                ids.append(str(result.id))
                documents.append(result.payload.get("text", ""))
                # textフィールドを除いたメタデータ
                metadata = {k: v for k, v in result.payload.items() if k != "text"}
                metadatas.append(metadata)
                distances.append(1 - result.score)  # cosine距離に変換
            
            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances]
            }
        except Exception as e:
            logger.error(f"Failed to query {collection_name}: {e}")
            raise
    
    def delete(self, collection_name: str, ids: List[str]) -> None:
        """IDによって削除"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} points from {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete from {collection_name}: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """コレクション一覧を取得"""
        try:
            collections = self.client.get_collections().collections
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise


class ChromaVectorStore(VectorStore):
    """ChromaDBベクトルストアの実装（後方互換性のため）"""
    
    def __init__(self, host: str = None, port: int = None):
        """
        ChromaDBクライアントを初期化
        
        Args:
            host: ChromaDBホスト（デフォルト: 環境変数 CHROMA_HOST または localhost）
            port: ポート（デフォルト: 環境変数 CHROMA_PORT または 8000）
        """
        self.host = host or os.getenv("CHROMA_HOST", "localhost")
        self.port = port or int(os.getenv("CHROMA_PORT", "8000"))
        
        self.client = chromadb.HttpClient(
            host=self.host,
            port=self.port
        )
        
        logger.info(
            "ChromaDB vector store initialized",
            host=self.host,
            port=self.port
        )
    
    def create_collection(self, name: str, dimension: int) -> None:
        """コレクションを作成"""
        try:
            self.client.get_or_create_collection(name=name)
            logger.info(f"Created/retrieved collection {name}")
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise
    
    def upsert(self, collection_name: str, embeddings: List[List[float]], 
               documents: List[str], metadatas: List[Dict[str, Any]], 
               ids: Optional[List[str]] = None) -> None:
        """ベクトルとメタデータを挿入/更新"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in embeddings]
            
            collection.upsert(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Upserted {len(embeddings)} items to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to upsert to {collection_name}: {e}")
            raise
    
    def query(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ベクトル検索を実行"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter
            )
            
            return results
        except Exception as e:
            logger.error(f"Failed to query {collection_name}: {e}")
            raise
    
    def delete(self, collection_name: str, ids: List[str]) -> None:
        """IDによって削除"""
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} items from {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete from {collection_name}: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """コレクション一覧を取得"""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise


def get_vector_store(store_type: Optional[str] = None) -> VectorStore:
    """
    設定に基づいてベクトルストアインスタンスを取得
    
    Args:
        store_type: ベクトルストアタイプ（"qdrant" または "chroma"）
                   Noneの場合は環境変数 VECTOR_STORE_TYPE から取得
    
    Returns:
        VectorStoreインスタンス
    """
    if store_type is None:
        store_type = os.getenv("VECTOR_STORE_TYPE", "qdrant").lower()
    
    if store_type == "qdrant":
        return QdrantVectorStore()
    elif store_type == "chroma" or store_type == "chromadb":
        return ChromaVectorStore()
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")