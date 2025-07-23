"""
Qdrantベースの知識検索ツール
エージェントが知識ベースを検索するためのツール
"""

from typing import List, Dict, Any, Optional
from crewai.tools import tool
from core.vector_store import get_vector_store
import structlog
import os

logger = structlog.get_logger()


class KnowledgeSearcher:
    """Qdrantを使用した知識検索エンジン"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.collection_name = "okami_knowledge"
        self.embedding_dimension = 1024  # mxbai-embed-largeの次元
        
        # コレクションを作成
        try:
            self.vector_store.create_collection(
                name=self.collection_name,
                dimension=self.embedding_dimension
            )
        except Exception as e:
            logger.debug(f"Collection may already exist: {e}")
    
    def search(self, query: str, n_results: int = 5, 
               filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        知識ベースを検索
        
        Args:
            query: 検索クエリ
            n_results: 返す結果の数
            filter: メタデータフィルター
            
        Returns:
            検索結果のリスト
        """
        try:
            # Ollamaを使用してクエリをエンベディング
            import ollama
            
            client = ollama.Client(
                host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
            
            response = client.embeddings(
                model=os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
                prompt=query
            )
            query_embedding = response["embedding"]
            
            # ベクトル検索を実行
            results = self.vector_store.query(
                collection_name=self.collection_name,
                query_embedding=query_embedding,
                n_results=n_results,
                filter=filter
            )
            
            # 結果を整形
            formatted_results = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "score": 1 - results["distances"][0][i] if results.get("distances") else 0.0
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []
    
    def add_knowledge(self, documents: List[str], 
                     metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        知識を追加
        
        Args:
            documents: ドキュメントのリスト
            metadatas: メタデータのリスト
            
        Returns:
            成功したかどうか
        """
        try:
            # 統一されたEmbeddingManagerでドキュメントをエンベディング
            embeddings = self.embedding_manager.generate_embeddings(documents)
            
            if metadatas is None:
                metadatas = [{} for _ in documents]
            
            # ベクトルストアに追加
            self.vector_store.upsert(
                collection_name=self.collection_name,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} documents to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            return False


# グローバルインスタンス
_knowledge_searcher = None


def get_knowledge_searcher() -> KnowledgeSearcher:
    """知識検索エンジンのシングルトンインスタンスを取得"""
    global _knowledge_searcher
    if _knowledge_searcher is None:
        _knowledge_searcher = KnowledgeSearcher()
    return _knowledge_searcher


@tool("knowledge_search")
def search_knowledge(query: str, n_results: int = 5) -> str:
    """
    Search the knowledge base for relevant information.
    
    Args:
        query: The search query
        n_results: Number of results to return (default: 5)
        
    Returns:
        Formatted search results
    """
    searcher = get_knowledge_searcher()
    results = searcher.search(query, n_results)
    
    if not results:
        return "No relevant knowledge found."
    
    # 結果を整形
    output = []
    for i, result in enumerate(results, 1):
        output.append(f"Result {i} (Score: {result['score']:.3f}):")
        output.append(result['content'])
        if result.get('metadata'):
            output.append(f"Source: {result['metadata']}")
        output.append("")
    
    return "\n".join(output)


@tool("add_knowledge")
def add_knowledge_to_base(content: str, source: Optional[str] = None) -> str:
    """
    Add new knowledge to the knowledge base.
    
    Args:
        content: The knowledge content to add
        source: Optional source information
        
    Returns:
        Success or error message
    """
    searcher = get_knowledge_searcher()
    
    metadata = {}
    if source:
        metadata["source"] = source
    
    success = searcher.add_knowledge(
        documents=[content],
        metadatas=[metadata]
    )
    
    if success:
        return "Knowledge successfully added to the base."
    else:
        return "Failed to add knowledge to the base."