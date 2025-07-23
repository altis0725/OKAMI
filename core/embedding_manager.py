"""
埋め込み生成を統一管理するEmbeddingManager
OKAMIシステム全体で使用されるエンベディング処理を統一
"""

import os
import time
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import structlog
import ollama
from openai import OpenAI

logger = structlog.get_logger()


class EmbeddingManager:
    """
    エンベディング生成を統一管理するクラス
    
    複数のプロバイダー（Ollama、OpenAI）をサポートし、
    バッチ処理、エラーハンドリング、リトライ機能を提供
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        EmbeddingManagerの初期化
        
        Args:
            config: エンベディング設定辞書
        """
        self.config = config or self._load_default_config()
        self.provider = self.config.get("provider", "ollama").lower()
        self.provider_config = self.config.get("config", {})
        
        # プロバイダー固有の初期化
        self._init_provider()
        
        # パフォーマンス追跡
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0
        }
        
        logger.info(
            "EmbeddingManager initialized",
            provider=self.provider,
            model=self.provider_config.get("model", "unknown")
        )
    
    def _load_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を読み込む（統一設定を使用）"""
        try:
            from utils.config import get_config
            okami_config = get_config()
            return okami_config.get_embedder_config()
        except ImportError:
            # フォールバック：環境変数から直接読み込み
            return {
                "provider": os.getenv("EMBEDDER_PROVIDER", "ollama"),
                "config": {
                    "model": os.getenv("EMBEDDER_MODEL", "mxbai-embed-large"),
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "batch_size": int(os.getenv("EMBEDDING_BATCH_SIZE", "10")),
                    "max_retries": int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
                    "retry_delay": float(os.getenv("EMBEDDING_RETRY_DELAY", "1.0"))
                }
            }
    
    def _init_provider(self):
        """プロバイダー固有の初期化"""
        if self.provider == "ollama":
            self.client = ollama.Client(
                host=self.provider_config.get("base_url", "http://localhost:11434")
            )
            self.model = self.provider_config.get("model", "mxbai-embed-large")
        elif self.provider == "openai":
            api_key = self.provider_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")
            self.client = OpenAI(api_key=api_key)
            self.model = self.provider_config.get("model", "text-embedding-3-small")
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        テキストリストからエンベディングを生成
        
        Args:
            texts: エンベディングを生成するテキストのリスト
            
        Returns:
            エンベディングベクトルのリスト
        """
        if not texts:
            return []
        
        start_time = time.time()
        all_embeddings = []
        
        try:
            # バッチ処理で効率化
            batch_size = self.provider_config.get("batch_size", 10)
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self._generate_batch(batch)
                all_embeddings.extend(batch_embeddings)
            
            # 統計更新
            processing_time = time.time() - start_time
            self._update_stats(len(texts), True, processing_time)
            
            logger.info(
                "Embeddings generated successfully",
                text_count=len(texts),
                processing_time=processing_time,
                provider=self.provider
            )
            
            return all_embeddings
            
        except Exception as e:
            self._update_stats(len(texts), False, time.time() - start_time)
            logger.error(f"Failed to generate embeddings: {e}", provider=self.provider)
            raise
    
    def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        テキストバッチのエンベディング生成（リトライ機能付き）
        
        Args:
            texts: テキストのバッチ
            
        Returns:
            エンベディングベクトルのリスト
        """
        max_retries = self.provider_config.get("max_retries", 3)
        retry_delay = self.provider_config.get("retry_delay", 1.0)
        
        for attempt in range(max_retries + 1):
            try:
                if self.provider == "ollama":
                    return self._generate_ollama_batch(texts)
                elif self.provider == "openai":
                    return self._generate_openai_batch(texts)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Embedding generation attempt {attempt + 1} failed, retrying",
                        error=str(e),
                        retry_delay=retry_delay
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数バックオフ
                else:
                    raise e
    
    def _generate_ollama_batch(self, texts: List[str]) -> List[List[float]]:
        """Ollaraを使用したバッチエンベディング生成"""
        embeddings = []
        
        for text in texts:
            if not text.strip():
                # 空のテキストの場合は零ベクトルを返す
                embeddings.append([0.0] * 1024)  # mxbai-embed-largeの次元数
                continue
                
            response = self.client.embeddings(
                model=self.model,
                prompt=text
            )
            embeddings.append(response["embedding"])
        
        return embeddings
    
    def _generate_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """OpenAIを使用したバッチエンベディング生成"""
        # OpenAIは効率的なバッチAPIを提供
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        
        return [data.embedding for data in response.data]
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        単一テキストのエンベディング生成
        
        Args:
            text: エンベディングを生成するテキスト
            
        Returns:
            エンベディングベクトル
        """
        embeddings = self.generate_embeddings([text])
        return embeddings[0] if embeddings else []
    
    def _update_stats(self, text_count: int, success: bool, processing_time: float):
        """統計情報を更新"""
        self.stats["total_requests"] += 1
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        self.stats["total_processing_time"] += processing_time
        self.stats["average_processing_time"] = (
            self.stats["total_processing_time"] / self.stats["total_requests"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_requests"] / max(self.stats["total_requests"], 1)
            ) * 100,
            "provider": self.provider,
            "model": self.model
        }
    
    def reset_stats(self):
        """統計情報をリセット"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0
        }
        logger.info("EmbeddingManager stats reset")
    
    def health_check(self) -> Tuple[bool, str]:
        """
        エンベディングサービスのヘルスチェック
        
        Returns:
            (is_healthy, status_message)
        """
        try:
            test_embedding = self.generate_single_embedding("health check test")
            if test_embedding and len(test_embedding) > 0:
                return True, f"Healthy - {self.provider} provider working correctly"
            else:
                return False, f"Unhealthy - {self.provider} returned empty embedding"
                
        except Exception as e:
            return False, f"Unhealthy - {self.provider} error: {str(e)}"


# シングルトンインスタンス（プロジェクト全体で共有）
_embedding_manager_instance: Optional[EmbeddingManager] = None


def get_embedding_manager(config: Optional[Dict[str, Any]] = None) -> EmbeddingManager:
    """
    EmbeddingManagerのシングルトンインスタンスを取得
    
    Args:
        config: エンベディング設定（初回のみ使用）
        
    Returns:
        EmbeddingManagerインスタンス
    """
    global _embedding_manager_instance
    
    if _embedding_manager_instance is None:
        _embedding_manager_instance = EmbeddingManager(config)
    
    return _embedding_manager_instance


def reset_embedding_manager():
    """EmbeddingManagerインスタンスをリセット（テスト用）"""
    global _embedding_manager_instance
    _embedding_manager_instance = None