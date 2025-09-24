"""
Mem0統合のヘルパーユーティリティ
CrewAI 0.157.0対応のエラーハンドリングとステータスチェック機能を提供
"""

import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

def mem0_error_handler(func):
    """
    Mem0関連エラーのデコレータ
    エラーを許容し、システムの継続動作を保証する
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            # 既知のエラーパターンの処理
            if "400 Bad Request" in error_msg:
                logger.error("Mem0 API authentication failed. Check MEM0_API_KEY.")
            elif "401 Unauthorized" in error_msg:
                logger.error("Mem0 API key is invalid or expired.")
            elif "NoneType" in error_msg and "search" in error_msg:
                logger.error("Memory not properly initialized. Using fallback.")
            elif "metadata" in error_msg:
                logger.error("Mem0 V2 API compatibility issue detected.")
            elif "Connection" in error_msg or "Network" in error_msg:
                logger.error("Network connection issue with Mem0 service.")
            else:
                logger.error(f"Unexpected Mem0 error: {e}")
            
            # エラーを再発生させずに型に応じたフォールバック値を返す
            name = getattr(func, "__name__", "")
            if name.startswith("search"):
                return []
            if name.startswith("save"):
                return False
            return None
    
    return wrapper


class Mem0StatusChecker:
    """Mem0の状態確認ユーティリティ"""
    
    @staticmethod
    def check_mem0_availability() -> Dict[str, Any]:
        """
        Mem0の利用可能性をチェック
        
        Returns:
            Dict: ステータス情報と推奨事項
        """
        import os
        
        status = {
            "api_key_present": bool(os.getenv("MEM0_API_KEY")),
            "local_mode_enabled": bool(os.getenv("USE_LOCAL_MEM0")),
            "fallback_enabled": os.getenv("MEMORY_FALLBACK_TO_BASIC", "true").lower() == "true",
            "error_tolerance": os.getenv("MEMORY_ERROR_TOLERANCE", "high"),
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "connection_ok": False
        }
        
        # API キーの確認
        if not status["api_key_present"]:
            status["warnings"].append("MEM0_API_KEY not set")
            status["recommendations"].append(
                "Set MEM0_API_KEY environment variable or enable local mode (USE_LOCAL_MEM0=true)"
            )
        
        # Mem0接続テスト（API キーがある場合のみ）
        if status["api_key_present"]:
            try:
                from mem0 import MemoryClient
                client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
                
                # 簡単な接続テスト（V2 API対応）
                try:
                    # V2 APIでの検索テスト
                    result = client.search(
                        query="test",
                        user_id="test_user",
                        limit=1
                    )
                    status["connection_ok"] = True
                    status["api_version"] = "v2"
                except Exception as v2_error:
                    # V1 APIフォールバックを試みる
                    try:
                        result = client.search(
                            "test",
                            user_id="test_user",
                            limit=1
                        )
                        status["connection_ok"] = True
                        status["api_version"] = "v1"
                        status["warnings"].append("Using Mem0 V1 API (V2 not available)")
                    except Exception as v1_error:
                        raise v1_error
                        
            except ImportError:
                status["errors"].append("mem0 package not installed")
                status["recommendations"].append(
                    "Install mem0 package: pip install mem0ai"
                )
            except Exception as e:
                status["connection_ok"] = False
                status["errors"].append(f"Connection test failed: {str(e)}")
                
                # エラーに基づく推奨事項
                if "401" in str(e) or "Unauthorized" in str(e):
                    status["recommendations"].append(
                        "Verify your Mem0 API key is valid and active"
                    )
                elif "Connection" in str(e) or "Network" in str(e):
                    status["recommendations"].append(
                        "Check network connection and Mem0 service availability"
                    )
                else:
                    status["recommendations"].append(
                        "Consider using local mode or basic memory provider as fallback"
                    )
        
        # ローカルモードの確認
        if status["local_mode_enabled"]:
            # Ollamaの利用可能性チェック
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    status["ollama_available"] = True
                    models = response.json().get("models", [])
                    nomic_available = any("nomic-embed-text" in m.get("name", "") for m in models)
                    if not nomic_available:
                        status["warnings"].append("nomic-embed-text model not found in Ollama")
                        status["recommendations"].append(
                            "Pull the model: ollama pull nomic-embed-text:latest"
                        )
                else:
                    status["ollama_available"] = False
            except Exception:
                status["ollama_available"] = False
                if status["local_mode_enabled"]:
                    status["warnings"].append("Ollama not accessible for local mode")
                    status["recommendations"].append(
                        "Ensure Ollama is running: ollama serve"
                    )
        
        # 全体的な準備状態の評価
        if status["connection_ok"]:
            status["ready"] = True
            status["mode"] = "cloud"
        elif status["local_mode_enabled"] and status.get("ollama_available"):
            status["ready"] = True
            status["mode"] = "local"
        elif status["fallback_enabled"]:
            status["ready"] = True
            status["mode"] = "basic"
            status["warnings"].append("Using basic memory provider (limited functionality)")
        else:
            status["ready"] = False
            status["mode"] = "none"
            status["errors"].append("No memory provider available")
        
        return status
    
    @staticmethod
    def print_status_report(status: Dict[str, Any]) -> None:
        """
        ステータスレポートを表示
        
        Args:
            status: check_mem0_availability()の結果
        """
        print("\n" + "="*60)
        print("Mem0 Integration Status Report")
        print("="*60)
        
        # 基本情報
        print(f"\n✅ Ready: {status.get('ready', False)}")
        print(f"📡 Mode: {status.get('mode', 'unknown').upper()}")
        
        if status.get('api_version'):
            print(f"🔧 API Version: {status['api_version']}")
        
        # 設定状態
        print("\n📋 Configuration:")
        print(f"  - MEM0_API_KEY: {'✓ Set' if status['api_key_present'] else '✗ Not set'}")
        print(f"  - Local Mode: {'✓ Enabled' if status['local_mode_enabled'] else '✗ Disabled'}")
        print(f"  - Fallback to Basic: {'✓ Enabled' if status['fallback_enabled'] else '✗ Disabled'}")
        print(f"  - Error Tolerance: {status['error_tolerance']}")
        
        # 接続状態
        if status['api_key_present']:
            print(f"\n🌐 Connection Status:")
            print(f"  - Mem0 Cloud: {'✓ Connected' if status['connection_ok'] else '✗ Failed'}")
        
        if status.get('ollama_available') is not None:
            print(f"  - Ollama Local: {'✓ Available' if status['ollama_available'] else '✗ Not available'}")
        
        # エラー
        if status['errors']:
            print("\n❌ Errors:")
            for error in status['errors']:
                print(f"  - {error}")
        
        # 警告
        if status['warnings']:
            print("\n⚠️  Warnings:")
            for warning in status['warnings']:
                print(f"  - {warning}")
        
        # 推奨事項
        if status['recommendations']:
            print("\n💡 Recommendations:")
            for rec in status['recommendations']:
                print(f"  - {rec}")
        
        print("\n" + "="*60)


def get_memory_config_for_crew(
    use_mem0: bool = True,
    fallback_to_basic: bool = True,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    local_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Crew用のメモリ設定を生成するヘルパー関数
    
    Args:
        use_mem0: Mem0を使用するか
        fallback_to_basic: エラー時に基本メモリにフォールバックするか
        user_id: ユーザーID
        run_id: 実行ID
        local_config: ローカルMem0設定
    
    Returns:
        Dict: Crew初期化用のメモリ設定
    """
    import os
    
    config = {
        "use_mem0": use_mem0,
        "fallback_to_basic": fallback_to_basic,
        "user_id": user_id or "okami_system",
        "run_id": run_id
    }
    
    # 環境変数から設定を読み込み
    if os.getenv("USE_LOCAL_MEM0", "false").lower() == "true":
        config["local_mem0_config"] = local_config or {
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text:latest",
                    "base_url": "http://localhost:11434"
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "okami_memories",
                    "embedding_model_dims": 768,
                    "on_disk": True
                }
            }
        }
    
    return config


# エクスポート
__all__ = [
    'mem0_error_handler',
    'Mem0StatusChecker',
    'get_memory_config_for_crew'
]
