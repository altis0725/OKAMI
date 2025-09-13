"""
ベクトルストアの統一インターフェース
QdrantとChromaDBの両方をサポート
"""

import os
from typing import List, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod
import structlog
# from qdrant_client import QdrantClient
# from qdrant_client.models import (
#     Distance, 
#     VectorParams, 
#     PointStruct,
#     Filter,
#     FieldCondition,
#     MatchValue
# )
import chromadb
try:
    from chromadb.config import Settings as ChromaSettings  # 0.5.x
except Exception:  # pragma: no cover
    ChromaSettings = None
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


# class QdrantVectorStore(VectorStore):
#     """Qdrantベクトルストアの実装（無効化中）"""
#     def __init__(self, host: str = None, port: int = None, grpc_port: int = None):
#         raise NotImplementedError("Qdrantは無効化されています")
    
#     def create_collection(self, name: str, dimension: int) -> None:
#         """コレクションを作成"""
#         try:
#             # コレクションが既に存在するかチェック
#             collections = self.client.get_collections().collections
#             if any(col.name == name for col in collections):
#                 logger.info(f"Collection {name} already exists")
#                 return
            
#             self.client.create_collection(
#                 collection_name=name,
#                 vectors_config=VectorParams(
#                     size=dimension,
#                     distance=Distance.COSINE
#                 )
#             )
#             logger.info(f"Created collection {name} with dimension {dimension}")
#         except Exception as e:
#             logger.error(f"Failed to create collection {name}: {e}")
#             raise
    
#     def upsert(self, collection_name: str, embeddings: List[List[float]], 
#                documents: List[str], metadatas: List[Dict[str, Any]], 
#                ids: Optional[List[str]] = None) -> None:
#         """ベクトルとメタデータを挿入/更新"""
#         try:
#             if ids is None:
#                 ids = [str(uuid.uuid4()) for _ in embeddings]
            
#             points = []
#             for i, (embedding, doc, metadata, point_id) in enumerate(
#                 zip(embeddings, documents, metadatas, ids)
#             ):
#                 # メタデータにドキュメントテキストを含める
#                 payload = metadata.copy()
#                 payload["text"] = doc
                
#                 points.append(
#                     PointStruct(
#                         id=point_id,
#                         vector=embedding,
#                         payload=payload
#                     )
#                 )
            
#             self.client.upsert(
#                 collection_name=collection_name,
#                 points=points
#             )
#             logger.info(f"Upserted {len(points)} points to {collection_name}")
#         except Exception as e:
#             logger.error(f"Failed to upsert to {collection_name}: {e}")
#             raise
    
#     def query(self, collection_name: str, query_embedding: List[float], 
#               n_results: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#         """ベクトル検索を実行"""
#         try:
#             # Qdrant用のフィルターを構築
#             query_filter = None
#             if filter:
#                 conditions = []
#                 for key, value in filter.items():
#                     conditions.append(
#                         FieldCondition(
#                             key=key,
#                             match=MatchValue(value=value)
#                         )
#                     )
#                 if conditions:
#                     query_filter = Filter(must=conditions)
            
#             results = self.client.search(
#                 collection_name=collection_name,
#                 query_vector=query_embedding,
#                 limit=n_results,
#                 query_filter=query_filter,
#                 with_payload=True
#             )
            
#             # CrewAI互換の形式に変換
#             ids = []
#             documents = []
#             metadatas = []
#             distances = []
            
#             for result in results:
#                 ids.append(str(result.id))
#                 documents.append(result.payload.get("text", ""))
#                 # textフィールドを除いたメタデータ
#                 metadata = {k: v for k, v in result.payload.items() if k != "text"}
#                 metadatas.append(metadata)
#                 distances.append(1 - result.score)  # cosine距離に変換
            
#             return {
#                 "ids": [ids],
#                 "documents": [documents],
#                 "metadatas": [metadatas],
#                 "distances": [distances]
#             }
#         except Exception as e:
#             logger.error(f"Failed to query {collection_name}: {e}")
#             raise
    
#     def delete(self, collection_name: str, ids: List[str]) -> None:
#         """IDによって削除"""
#         try:
#             self.client.delete(
#                 collection_name=collection_name,
#                 points_selector=ids
#             )
#             logger.info(f"Deleted {len(ids)} points from {collection_name}")
#         except Exception as e:
#             logger.error(f"Failed to delete from {collection_name}: {e}")
#             raise
    
#     def list_collections(self) -> List[str]:
#         """コレクション一覧を取得"""
#         try:
#             collections = self.client.get_collections().collections
#             return [col.name for col in collections]
#         except Exception as e:
#             logger.error(f"Failed to list collections: {e}")
#             raise


class ChromaVectorStore(VectorStore):
    """ChromaDBベクトルストアの実装（後方互換性のため）"""
    
    def __init__(self, host: str = None, port: int = None, persist_directory: str = None):
        """
        ChromaDBクライアントを初期化
        
        Args:
            host: ChromaDBホスト（デフォルト: 環境変数 CHROMA_HOST または localhost）
            port: ポート（デフォルト: 環境変数 CHROMA_PORT または 8000）
            persist_directory: 永続化ディレクトリ（デフォルト: 環境変数 CHROMA_PERSIST_DIRECTORY または ./storage/chroma）
        """
        self.host = host or os.getenv("CHROMA_HOST", "localhost")
        self.port = port or int(os.getenv("CHROMA_PORT", "8000"))
        self.persist_directory = persist_directory or os.getenv("CHROMA_PERSIST_DIRECTORY", "./storage/chroma")
        
        # 永続化ディレクトリが指定されている場合はPersistentClientを使用
        if self.persist_directory and self.persist_directory != "":
            # ディレクトリが存在しない場合は作成
            os.makedirs(self.persist_directory, exist_ok=True)
            # テレメトリ無効化などの設定（ネットワーク依存を避ける）
            if ChromaSettings is not None:
                settings = ChromaSettings(anonymized_telemetry=False)
                self.client = chromadb.PersistentClient(path=self.persist_directory, settings=settings)
            else:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
        else:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port
            )
        # タイムアウト/リトライ設定（環境変数で調整可）
        self.add_max_retries = int(os.getenv("CHROMA_ADD_MAX_RETRIES", "3"))
        self.add_retry_initial_delay = float(os.getenv("CHROMA_ADD_RETRY_INITIAL_DELAY", "0.2"))
        self.query_max_retries = int(os.getenv("CHROMA_QUERY_MAX_RETRIES", "3"))
        self.query_retry_initial_delay = float(os.getenv("CHROMA_QUERY_INITIAL_DELAY", "0.2"))

        logger.info(
            "ChromaDB vector store initialized",
            host=self.host,
            port=self.port,
            persist_directory=self.persist_directory
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
            
            # リトライ付きでupsert（NFS上のロック競合・I/O遅延に対応）
            attempt = 0
            delay = self.add_retry_initial_delay
            while True:
                try:
                    collection.upsert(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > self.add_max_retries:
                        raise
                    logger.warning(
                        "Chroma upsert timed out/failed, retrying",
                        attempt=attempt,
                        max_retries=self.add_max_retries,
                        error=str(e)
                    )
                    import time
                    time.sleep(delay)
                    delay = min(delay * 2, 3.0)  # 指数バックオフ（上限3秒）
            logger.info(f"Upserted {len(embeddings)} items to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to upsert to {collection_name}: {e}")
            raise
    
    def query(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10, filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ベクトル検索を実行"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            # リトライ付きでquery
            attempt = 0
            delay = self.query_retry_initial_delay
            while True:
                try:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        where=filter
                    )
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > self.query_max_retries:
                        raise
                    logger.warning(
                        "Chroma query timed out/failed, retrying",
                        attempt=attempt,
                        max_retries=self.query_max_retries,
                        error=str(e)
                    )
                    import time
                    time.sleep(delay)
                    delay = min(delay * 2, 3.0)
            
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
    """
    if store_type is None:
        store_type = os.getenv("VECTOR_STORE_TYPE", "chroma").lower()

    # Accept aliases commonly used in PaaS configs
    if store_type in ("chroma", "chromadb", "local", "filesystem"):
        # For 'local'/'filesystem' we rely on CHROMA_PERSIST_DIRECTORY to persist data
        return ChromaVectorStore()

    raise ValueError(f"Unknown or disabled vector store type: {store_type}")
