"""
OKAMI設定管理
システム設定・環境変数の管理を担当
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import yaml
from pydantic_settings import BaseSettings
import logging
from pydantic import Field, field_validator
from dotenv import load_dotenv


class OkamiConfig(BaseSettings):
    """OKAMIシステムの設定クラス"""

    # API Keys
    monica_api_key: Optional[str] = Field(None, env="MONICA_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_api_base: str = Field(
        default="https://openapi.monica.im/v1",
        env="OPENAI_API_BASE"
    )
    mem0_api_key: Optional[str] = Field(None, env="MEM0_API_KEY")
    huggingface_api_key: Optional[str] = Field(None, env="HUGGINGFACE_API_KEY")

    # System Settings
    okami_log_level: str = Field(default="INFO", env="OKAMI_LOG_LEVEL")
    okami_log_json: bool = Field(default=True, env="OKAMI_LOG_JSON")
    crewai_storage_dir: str = Field(default="./storage", env="CREWAI_STORAGE_DIR")

    # Server Settings
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    # Prefer Railway/Heroku style PORT if present; fallback to 8000
    server_port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000")),
        env="SERVER_PORT",
    )
    server_reload: bool = Field(default=False, env="SERVER_RELOAD")

    # Monitoring Settings
    monitor_enabled: bool = Field(default=True, env="MONITOR_ENABLED")
    monitor_interval: int = Field(default=60, env="MONITOR_INTERVAL")
    claude_monitor_webhook_url: Optional[str] = Field(None, env="CLAUDE_MONITOR_WEBHOOK_URL")

    # Database Settings
    chroma_host: str = Field(default="chromadb", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    chroma_persist_directory: str = Field(default="./storage/chroma", env="CHROMA_PERSIST_DIRECTORY")
    
    # Vector Store Settings
    vector_store_type: str = Field(default="chroma", env="VECTOR_STORE_TYPE")
    # qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    # qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    # qdrant_grpc_port: int = Field(default=6334, env="QDRANT_GRPC_PORT")

    # Prometheus Settings
    prometheus_host: str = Field(default="localhost", env="PROMETHEUS_HOST")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")

    # Memory Settings
    use_mem0: bool = Field(default=False, env="USE_MEM0")
    memory_cooldown: int = Field(default=300, env="MEMORY_COOLDOWN")

    # Knowledge Settings
    knowledge_dir: str = Field(default="./knowledge", env="KNOWLEDGE_DIR")
    embedder_provider: str = Field(default="ollama", env="EMBEDDER_PROVIDER")
    embedder_model: str = Field(default="mxbai-embed-large", env="EMBEDDER_MODEL")
    
    # Embedding Settings (EmbeddingManager用)
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    embedding_batch_size: int = Field(default=10, env="EMBEDDING_BATCH_SIZE")
    embedding_max_retries: int = Field(default=1, env="EMBEDDING_MAX_RETRIES")
    embedding_retry_delay: float = Field(default=1.0, env="EMBEDDING_RETRY_DELAY")

    # Guardrail Settings
    guardrail_llm_model: str = Field(default="gpt-4o-mini", env="GUARDRAIL_LLM_MODEL")
    hallucination_threshold: float = Field(default=7.0, env="HALLUCINATION_THRESHOLD")

    # Evolution Settings
    evolution_enabled: bool = Field(default=True, env="EVOLUTION_ENABLED")
    learning_threshold: float = Field(default=0.5, env="LEARNING_THRESHOLD")

    # Agent Settings
    default_max_iter: int = Field(default=20, env="DEFAULT_MAX_ITER")
    default_max_retries: int = Field(default=3, env="DEFAULT_MAX_RETRIES")
    enable_reasoning: bool = Field(default=True, env="ENABLE_REASONING")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }

    @field_validator("okami_log_level")
    @classmethod
    def validate_log_level(cls, v):
        """
        ログレベルを検証
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("embedder_provider")
    @classmethod
    def validate_embedder_provider(cls, v):
        """
        埋め込みプロバイダを検証
        """
        valid_providers = [
            "openai", "google", "cohere", "huggingface", "ollama",
            "vertexai", "bedrock", "voyageai", "watson"
        ]
        if v.lower() not in valid_providers:
            raise ValueError(f"Invalid embedder provider: {v}")
        return v.lower()

    def is_railway_environment(self) -> bool:
        """Railway環境かどうかを判定"""
        return os.getenv("RAILWAY_ENVIRONMENT") is not None

    def get_api_key(self) -> str:
        """APIキーを取得（Railway環境を考慮）"""
        if self.is_railway_environment():
            # Railway環境ではMONICA_API_KEYまたはOPENAI_API_KEYを使用
            return self.monica_api_key or self.openai_api_key
        else:
            # ローカル環境ではMONICA_API_KEYを優先
            return self.monica_api_key or self.openai_api_key

    def get_embedder_config(self) -> Dict[str, Any]:
        """
        埋め込みモデルの設定を取得
        - 通常: .env / 環境変数の `EMBEDDER_PROVIDER` と `EMBEDDER_MODEL`
        - Railway: `ENABLE_OLLAMA=true` の場合は Ollama を優先（サイドカー起動前提）
                   それ以外は OpenAI を使用
        """
        # 明示指定があれば最優先（REMOTE Ollamaなどのケースに対応）
        explicit_provider = os.getenv("EMBEDDER_PROVIDER")
        explicit_model = os.getenv("EMBEDDER_MODEL")

        if explicit_provider:
            provider = explicit_provider.lower()
            model = explicit_model or self.embedder_model
        elif self.is_railway_environment():
            if os.getenv("ENABLE_OLLAMA", "false").lower() == "true":
                provider = "ollama"
                model = explicit_model or "mxbai-embed-large"
            else:
                provider = "openai"
                model = "text-embedding-ada-002"
        else:
            provider = self.embedder_provider
            model = self.embedder_model

        config = {
            "provider": provider,
            "config": {
                "model": model
            }
        }

        # Add provider-specific configurations
        if provider == "openai":
            api_key = self.get_api_key()
            if not api_key:
                raise ValueError("OpenAI API key is required for embeddings")
            config["config"]["api_key"] = api_key
            config["config"]["base_url"] = self.openai_api_base
            config["config"]["batch_size"] = self.embedding_batch_size
            config["config"]["max_retries"] = self.embedding_max_retries
            config["config"]["retry_delay"] = self.embedding_retry_delay
        elif self.embedder_provider == "google" and os.getenv("GOOGLE_API_KEY"):
            config["config"]["api_key"] = os.getenv("GOOGLE_API_KEY")
        elif self.embedder_provider == "cohere" and os.getenv("COHERE_API_KEY"):
            config["config"]["api_key"] = os.getenv("COHERE_API_KEY")
        elif provider == "huggingface" and self.huggingface_api_key:
            config["config"]["api_key"] = self.huggingface_api_key
            config["config"]["api_url"] = "https://api-inference.huggingface.co"
        elif provider == "ollama":
            # EmbeddingConfigurator は `url` キーを参照するため、こちらを優先
            base = self.ollama_base_url.rstrip("/")

            # コンテナ内から `localhost` を叩かないように自動補正（Mac/Docker Desktop想定）
            try:
                in_docker = os.path.exists("/.dockerenv") or os.getenv("IN_DOCKER") == "1"
                if in_docker and ("localhost" in base or "127.0.0.1" in base):
                    base = base.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            except Exception:
                pass

            cfg = {
                "url": f"{base}/api/embeddings",
                # 参考情報（ツール側で使わないが記録として残す）
                "base_url": base,
                "batch_size": self.embedding_batch_size,
                "max_retries": self.embedding_max_retries,
                "retry_delay": self.embedding_retry_delay,
                "truncate": True,
                "keep_alive": "5m",
                "verbose": True,
                "debug": True,
            }
            # ログ（DEBUG）
            try:
                logging.getLogger(__name__).debug(
                    "Resolved Ollama embedder URL",
                    extra={"url": cfg["url"], "base_url": cfg["base_url"]},
                )
            except Exception:
                pass
            config["config"].update(cfg)

        return config

    def get_llm_config(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        LLM（大規模言語モデル）の設定を取得（Monica/OpenAI互換）
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError("API key is required for LLM")
        return {
            "model": model or "gpt-4o-mini",
            "api_key": api_key,
            "base_url": self.openai_api_base,
        }

    def get_mem0_config(self) -> Dict[str, Any]:
        """
        Mem0用の設定を取得
        """
        if not self.mem0_api_key:
            return {}

        return {
            "user_id": "okami_system",
            "api_key": self.mem0_api_key,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        設定を辞書型に変換
        """
        return self.model_dump(exclude_unset=True, exclude_none=True)

    def save_to_file(self, filepath: str, format: str = "json") -> None:
        """
        設定をファイルに保存

        Args:
            filepath: ファイルパス
            format: ファイル形式（jsonまたはyaml）
        """
        config_data = self.to_dict()
        
        # Remove sensitive data
        sensitive_keys = ["monica_api_key", "mem0_api_key", "claude_monitor_webhook_url"]
        for key in sensitive_keys:
            if key in config_data:
                config_data[key] = "***"

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(filepath, "w") as f:
                json.dump(config_data, f, indent=2)
        elif format == "yaml":
            with open(filepath, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def load_from_file(cls, filepath: str) -> "OkamiConfig":
        """
        ファイルから設定を読み込む

        Args:
            filepath: ファイルパス

        Returns:
            設定インスタンス
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, "r") as f:
            if filepath.suffix == ".json":
                config_data = json.load(f)
            elif filepath.suffix in [".yaml", ".yml"]:
                config_data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported file format: {filepath.suffix}")

        # Set as environment variables
        for key, value in config_data.items():
            if value != "***":  # Skip masked values
                os.environ[key.upper()] = str(value)

        return cls()


# Global config instance
_config_instance: Optional[OkamiConfig] = None


def get_config() -> OkamiConfig:
    """
    グローバル設定インスタンスを取得
    """
    global _config_instance
    
    if _config_instance is None:
        # Load .env file if exists
        if Path(".env").exists():
            load_dotenv()
        
        _config_instance = OkamiConfig()
    
    return _config_instance


def reload_config() -> OkamiConfig:
    """
    設定を再読み込み
    """
    global _config_instance
    
    # Reload .env file
    if Path(".env").exists():
        load_dotenv(override=True)
    
    _config_instance = OkamiConfig()
    return _config_instance
