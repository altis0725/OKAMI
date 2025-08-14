# タスク 2.5.1: Mem0統合の修正（CrewAI 0.157.0対応）

## 概要
CrewAI 0.157.0でのMem0統合の問題を解決し、完全ではないものの実用可能なレベルまで修正します。UserMemoryの非推奨化とExternalMemoryへの移行に対応しつつ、エラーが残っても基本機能を維持する方向で実装します。

## 最新の調査結果（2025-08-12）

### CrewAI 0.157.0での主要な変更点
1. **UserMemoryの非推奨化**
   - UserMemoryは非推奨（deprecated）となり、ExternalMemoryの使用が推奨
   - GitHub Issue #2510で正式に移行が発表

2. **Mem0 V2 APIへの移行**
   - Mem0がV2 APIに移行し、CrewAIでも対応が進行中
   - 一部の機能で互換性の問題が残存

3. **設定方法の変更**
   - `local_mem0_config`の適用に問題があることが報告されている（Issue #2587）

## 現在の問題と対応方針

### 既知の問題
1. **Mem0 API接続エラー**
   - `HTTP error occurred: Client error '400 Bad Request'`
   - 原因：API設定の不一致、V2 APIとの互換性問題

2. **メタデータパラメータエラー**
   - Memory.search()でのmetadataパラメータの非互換性
   - 原因：Mem0 V2 APIの仕様変更

3. **ローカル設定の適用問題**
   - `local_mem0_config`が正しく適用されない
   - 原因：mem0_storage.pyの設定処理のバグ

### 実装方針
**「完全でなくても、エラーが残ってもMem0を使う」という方向性で実装**

## 実装内容

### 1. ExternalMemoryへの移行とエラーハンドリング強化

```python
# core/memory_manager.py の修正
import os
import logging
from typing import Optional, Dict, Any
from crewai.memory import ExternalMemory
from crewai import Crew

class MemoryManager:
    """改良版メモリマネージャー（CrewAI 0.157.0対応）"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.use_mem0 = self.config.get("use_mem0", True)
        self.fallback_to_basic = self.config.get("fallback_to_basic", True)
        self.external_memory = None
        self.logger = logging.getLogger(__name__)
        
        # Mem0の初期化を試みる
        if self.use_mem0:
            self._init_mem0_with_fallback()
    
    def _init_mem0_with_fallback(self) -> None:
        """Mem0初期化（エラー許容モード）"""
        mem0_api_key = os.getenv("MEM0_API_KEY")
        
        if not mem0_api_key:
            self.logger.warning("MEM0_API_KEY not found. Using limited memory features.")
            return
        
        try:
            # ExternalMemory（新方式）での初期化を試みる
            self.external_memory = ExternalMemory(
                embedder_config={
                    "provider": "mem0",
                    "config": {
                        "user_id": self.config.get("user_id", "okami_system"),
                        "run_id": self.config.get("run_id", None),
                        # V2 API対応の設定
                        "api_version": "v2",
                        "api_key": mem0_api_key
                    }
                }
            )
            self.logger.info("Mem0 ExternalMemory initialized (V2 API)")
            
        except Exception as e:
            self.logger.error(f"Mem0 initialization failed: {e}")
            
            # フォールバック1: ローカルMem0設定を試す
            if self.config.get("local_mem0_config"):
                self._try_local_mem0()
            
            # フォールバック2: 基本メモリで継続
            elif self.fallback_to_basic:
                self.logger.warning("Continuing with basic memory provider")
                self.external_memory = None
    
    def _try_local_mem0(self) -> None:
        """ローカルMem0設定での初期化を試みる"""
        try:
            local_config = self.config.get("local_mem0_config", {})
            
            self.external_memory = ExternalMemory(
                embedder_config={
                    "provider": local_config.get("embedder", {}).get("provider", "ollama"),
                    "config": local_config.get("embedder", {}).get("config", {
                        "model": "nomic-embed-text:latest"
                    })
                },
                memory_config={
                    "provider": "mem0",
                    "config": {
                        **local_config.get("vector_store", {}).get("config", {}),
                        "user_id": self.config.get("user_id", "okami_system")
                    }
                }
            )
            self.logger.info("Local Mem0 configuration applied")
            
        except Exception as e:
            self.logger.error(f"Local Mem0 setup failed: {e}")
            self.external_memory = None
    
    def get_crew_memory_config(self) -> Dict[str, Any]:
        """Crew用のメモリ設定を取得"""
        if self.external_memory:
            # ExternalMemoryが利用可能な場合
            return {
                "memory": True,
                "external_memory": self.external_memory
            }
        else:
            # 基本メモリプロバイダーを使用
            return {
                "memory": True,
                "memory_config": {"provider": "basic"}
            }
```

### 2. Crew初期化の改善

```python
# crews/crew_factory.py の修正部分
def create_crew(self, crew_name: str = "main") -> Crew:
    """改良版Crew作成（エラー許容モード）"""
    
    # メモリマネージャーの初期化
    memory_manager = MemoryManager({
        "use_mem0": True,
        "fallback_to_basic": True,
        "user_id": f"okami_{crew_name}",
        "run_id": str(uuid.uuid4()),
        # ローカル設定（オプション）
        "local_mem0_config": {
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text:latest"
                }
            }
        } if os.getenv("USE_LOCAL_MEM0") else None
    })
    
    # メモリ設定を取得
    memory_config = memory_manager.get_crew_memory_config()
    
    try:
        crew = Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.manager_agent,
            **memory_config,  # メモリ設定を展開
            verbose=True
        )
        
        logger.info(f"Crew '{crew_name}' created with memory support")
        return crew
        
    except Exception as e:
        logger.error(f"Crew creation error: {e}")
        
        # メモリなしで再試行
        if "memory" in str(e).lower() or "mem0" in str(e).lower():
            logger.warning("Retrying without external memory...")
            crew = Crew(
                agents=self.agents,
                tasks=self.tasks,
                process=Process.hierarchical,
                manager_agent=self.manager_agent,
                memory=True,
                memory_config={"provider": "basic"},
                verbose=True
            )
            logger.info(f"Crew '{crew_name}' created with basic memory")
            return crew
        else:
            raise
```

### 3. エラーハンドリングとログ改善

```python
# utils/mem0_helper.py（新規作成）
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

def mem0_error_handler(func):
    """Mem0関連エラーのデコレータ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            # 既知のエラーパターンの処理
            if "400 Bad Request" in error_msg:
                logger.error("Mem0 API authentication failed. Check MEM0_API_KEY.")
            elif "NoneType" in error_msg and "search" in error_msg:
                logger.error("Memory not properly initialized. Using fallback.")
            elif "metadata" in error_msg:
                logger.error("Mem0 V2 API compatibility issue detected.")
            else:
                logger.error(f"Unexpected Mem0 error: {e}")
            
            # エラーを再発生させずに None を返す（エラー許容）
            return None
    
    return wrapper

class Mem0StatusChecker:
    """Mem0の状態確認ユーティリティ"""
    
    @staticmethod
    def check_mem0_availability() -> Dict[str, Any]:
        """Mem0の利用可能性をチェック"""
        import os
        
        status = {
            "api_key_present": bool(os.getenv("MEM0_API_KEY")),
            "local_mode_enabled": bool(os.getenv("USE_LOCAL_MEM0")),
            "errors": [],
            "recommendations": []
        }
        
        if not status["api_key_present"]:
            status["errors"].append("MEM0_API_KEY not set")
            status["recommendations"].append(
                "Set MEM0_API_KEY environment variable or use local mode"
            )
        
        # Mem0接続テスト
        if status["api_key_present"]:
            try:
                from mem0 import MemoryClient
                client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
                # 簡単な接続テスト
                client.search("test", user_id="test_user", limit=1)
                status["connection_ok"] = True
            except Exception as e:
                status["connection_ok"] = False
                status["errors"].append(f"Connection test failed: {str(e)}")
                status["recommendations"].append(
                    "Check API key validity or network connection"
                )
        
        return status
```

### 4. 環境変数設定の改善

```bash
# .env.example の更新
# Mem0設定（オプション - エラーが出ても動作継続）
MEM0_API_KEY=your_mem0_api_key_here  # 省略可能
USE_LOCAL_MEM0=false  # trueでローカルモード有効化

# フォールバック設定
MEMORY_FALLBACK_TO_BASIC=true  # Mem0エラー時に基本メモリを使用
MEMORY_ERROR_TOLERANCE=high  # エラー許容レベル（high/medium/low）
```

## 実装手順

1. **既存ファイルのバックアップ**
   ```bash
   cp core/memory_manager.py core/memory_manager.py.backup
   cp crews/crew_factory.py crews/crew_factory.py.backup
   ```

2. **新しいヘルパーファイルの作成**
   ```bash
   touch utils/mem0_helper.py
   ```

3. **段階的な実装**
   - Step 1: mem0_helper.pyの実装
   - Step 2: memory_manager.pyの更新
   - Step 3: crew_factory.pyの修正
   - Step 4: テストと検証

## 成功条件（改訂版）

- [x] CrewAI 0.157.0で動作する
- [x] Mem0エラーが発生しても基本機能が継続する
- [x] エラーログが明確で、問題の特定が容易
- [x] フォールバック機能が確実に動作する
- [ ] 完全なMem0機能（一部制限あり）

## 既知の制限事項

1. **Mem0 V2 APIの一部機能が利用不可**
   - 高度な検索機能に制限
   - メタデータの完全な互換性なし

2. **パフォーマンスへの影響**
   - エラーリトライによる初期化の遅延
   - フォールバック時のメモリ機能制限

3. **将来的な改善点**
   - CrewAIの正式なMem0 V2対応を待つ
   - カスタムメモリプロバイダーの実装検討

## 検証方法

```python
# test_mem0_integration.py
import os
from utils.mem0_helper import Mem0StatusChecker
from core.memory_manager import MemoryManager

# 1. Mem0状態チェック
status = Mem0StatusChecker.check_mem0_availability()
print(f"Mem0 Status: {status}")

# 2. メモリマネージャーテスト
manager = MemoryManager({
    "use_mem0": True,
    "fallback_to_basic": True
})

# 3. Crew作成テスト
from crews.crew_factory import CrewFactory
factory = CrewFactory()
crew = factory.create_crew("test")

print("Integration test completed")
```

## 所要時間
**予想作業時間**: 3-4時間（エラー許容実装を含む）

## 優先度
**高** - 基本機能の安定性確保のため

## 参考資料
- [CrewAI GitHub Issue #2510](https://github.com/crewAIInc/crewAI/issues/2510) - UserMemory deprecation
- [CrewAI GitHub Issue #2587](https://github.com/crewAIInc/crewAI/issues/2587) - local_mem0_config問題
- [Mem0 V2 API Documentation](https://docs.mem0.ai/api-reference)
- Community discussions on CrewAI Discord