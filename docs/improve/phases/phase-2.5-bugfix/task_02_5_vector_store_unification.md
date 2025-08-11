# タスク 2.5.2: ベクトルストアの統一

## 概要
ChromaDBとQdrantの混在を解消し、ベクトルストアを統一することでタイムアウトエラーを解決します。

## 問題の詳細

### エラー内容
- `Error during short_term search: timed out in query.`
- `Error during short_term save: timed out in add.`

### 原因分析
- ChromaDBへの接続設定に問題がある
- ChromaDBがQdrantの代替として使用されているが、適切に初期化されていない
- ベクトルストアの設定ミスマッチ

## 作業内容

### 1. Qdrantコードの完全削除
- **対象ファイル**: 
  - `core/vector_store.py`
  - `core/knowledge_manager.py`
- **作業項目**:
  - Qdrant関連のimport文削除
  - Qdrant設定コードの削除
  - Qdrant初期化コードの削除

### 2. ChromaDBへの完全移行
- **作業項目**:
  - ChromaDBのみを使用するように統一
  - ChromaDB設定の最適化
  - 接続パラメータの調整

### 3. タイムアウト設定の調整
- **作業項目**:
  - デフォルトタイムアウト: 30秒→60秒
  - 操作別タイムアウト設定の実装
  - 接続リトライメカニズムの実装

### 4. 実装例

```python
# core/vector_store.py の修正例
class VectorStore:
    def __init__(self, config: Dict[str, Any]):
        # Qdrant関連コードを削除し、ChromaDBのみに統一
        self.client = chromadb.PersistentClient(
            path=config.get('persist_directory', './storage/chroma_db'),
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # タイムアウト設定の追加
        self.query_timeout = config.get('query_timeout', 60)
        self.add_timeout = config.get('add_timeout', 60)
        self.retry_count = config.get('retry_count', 3)
    
    async def search_with_retry(self, query: str, n_results: int = 5):
        """リトライ機能付きの検索"""
        for attempt in range(self.retry_count):
            try:
                return await asyncio.wait_for(
                    self._search_internal(query, n_results),
                    timeout=self.query_timeout
                )
            except asyncio.TimeoutError:
                if attempt == self.retry_count - 1:
                    raise
                logger.warning(f"Search timeout, retrying ({attempt + 1}/{self.retry_count})")
                await asyncio.sleep(1)
```

## 設定ファイルの更新

### docker-compose.yaml
```yaml
# Qdrant関連の設定を削除
# ChromaDB用のボリュームマウントのみ保持
volumes:
  - ./storage/chroma_db:/app/storage/chroma_db
```

### .env.example
```bash
# Qdrant関連の環境変数を削除
# ChromaDB設定のみ保持
CHROMA_DB_PATH=./storage/chroma_db
CHROMA_QUERY_TIMEOUT=60
CHROMA_ADD_TIMEOUT=60
```

## 成功条件
- [ ] Qdrant関連コードが完全に削除される
- [ ] ChromaDBのタイムアウトエラーが解消される
- [ ] ベクトル検索・追加操作が正常に動作する
- [ ] リトライメカニズムが動作する
- [ ] Docker環境での安定動作

## 所要時間
**予想作業時間**: 3-4時間

## 優先度
**中** - ベクトル検索機能の安定性に影響

## 前提条件
- ChromaDBの動作確認
- 既存データのマイグレーション計画

## 検証方法
1. ベクトル追加操作のテスト
2. ベクトル検索操作のテスト
3. タイムアウト設定のテスト
4. リトライ機能のテスト
5. Docker環境での統合テスト

## 影響範囲
- 知識検索機能
- メモリー検索機能  
- エンベディング保存機能