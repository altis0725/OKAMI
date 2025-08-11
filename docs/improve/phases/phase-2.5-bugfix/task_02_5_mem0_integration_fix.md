# タスク 2.5.1: Mem0統合の修正

## 概要
Mem0 APIの接続エラーを解決し、外部メモリーシステムの安定性を向上させます。

## 問題の詳細

### エラー内容
- `HTTP error occurred: Client error '400 Bad Request' for url 'https://api.mem0.ai/v1/memories/'`
- Mem0のAPIエンドポイントへの接続で認証エラーが発生

### 原因分析
- Mem0 APIキーが無効または未設定
- Mem0のエンドポイント設定が不適切
- API呼び出しのペイロード形式が不正

## 作業内容

### 1. Mem0 API設定の修正
- **ファイル**: `core/memory_manager.py`
- **作業項目**:
  - MEM0_API_KEYの有効性確認メカニズムの追加
  - Mem0接続失敗時のフォールバック処理の実装
  - エラーログの改善（具体的なエラー内容の記録）

### 2. 設定ファイルの改善
- **ファイル**: `utils/config.py`
- **作業項目**:
  - Mem0設定の検証機能追加
  - 設定値のバリデーション強化

### 3. フォールバック戦略の実装

```python
# core/memory_manager.py の修正例
def _init_external_memory(self) -> None:
    """外部メモリ（Mem0）初期化"""
    if self.use_mem0 and os.getenv("MEM0_API_KEY"):
        try:
            # APIキーの検証を追加
            self._validate_mem0_api_key()
            
            self.external_memory = ExternalMemory(
                embedder_config={
                    "provider": "huggingface",  # OpenAIからHuggingFaceへ変更
                    "config": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                },
                memory_config={
                    "provider": "mem0",
                    "config": {
                        "user_id": self.mem0_config.get("user_id", "okami_system"),
                        "api_key": os.getenv("MEM0_API_KEY"),
                        "timeout": 30,  # タイムアウト設定追加
                        "retry_count": 3  # リトライ設定追加
                    }
                }
            )
            logger.info("Mem0 external memory initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Mem0, falling back to basic memory: {e}")
            self.external_memory = None
            self.use_mem0 = False  # フラグを更新
    else:
        self.external_memory = None
```

## 成功条件
- [ ] Mem0 APIエラーが発生しない
- [ ] 接続失敗時に適切にフォールバックする
- [ ] エラーログが改善され、デバッグが容易になる
- [ ] APIキーの検証機能が動作する

## 所要時間
**予想作業時間**: 2-3時間

## 優先度
**緊急** - メモリーシステムの基本機能に影響

## 前提条件
- MEM0_API_KEYの取得または代替手段の検討
- HuggingFace Transformersライブラリの利用可能性確認

## 検証方法
1. 無効なAPIキーでの起動テスト
2. 有効なAPIキーでのMem0接続テスト
3. フォールバック機能のテスト
4. エラーログの確認