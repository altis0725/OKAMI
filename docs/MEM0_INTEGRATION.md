# OKAMIシステムでのMem0統合

## 概要

OKAMIシステムでは、CrewAIのbasic memoryシステムとmem0を統合して、永続的なメモリ機能を提供しています。

## 設定方法

### 1. 環境変数の設定

```bash
# mem0のAPIキーを設定
export MEM0_API_KEY="your-mem0-api-key"
```

### 2. クルー設定でのmem0使用

#### 基本設定

```yaml
# config/crews/main_crew.yaml
main_crew:
  memory: true
  memory_config:
    provider: "mem0"  # mem0を使用
    config:
      user_id: "okami_main_crew"  # ユーザーID
      # org_id: "your_org_id"  # オプション
      # project_id: "your_project_id"  # オプション
```

#### ローカルmem0設定

```yaml
# config/crews/main_crew.yaml
main_crew:
  memory: true
  memory_config:
    provider: "mem0"
    config:
      user_id: "okami_main_crew"
      local_mem0_config:
        vector_store:
          provider: "qdrant"
          config: {"host": "localhost", "port": 6333}
        llm:
          provider: "openai"
          config: {"api_key": "your-api-key", "model": "gpt-4"}
        embedder:
          provider: "openai"
          config: {"api_key": "your-api-key", "model": "text-embedding-3-small"}
```

### 3. プログラムでの使用

#### MemoryManagerを使用

```python
from core.memory_manager import MemoryManager

# mem0を使用するメモリマネージャーを作成
memory_manager = MemoryManager(
    use_mem0=True,
    mem0_config={
        "user_id": "okami_system",
        "org_id": "your_org_id",  # オプション
        "project_id": "your_project_id"  # オプション
    }
)

# CrewAI用の設定を取得
memory_config = memory_manager.get_memory_config()

# クルー作成時に使用
crew = Crew(
    agents=[...],
    tasks=[...],
    **memory_config
)
```

#### 直接設定

```python
from crewai import Crew

crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,
    memory_config={
        "provider": "mem0",
        "config": {
            "user_id": "okami_system",
            "api_key": "your-mem0-api-key"
        },
        "user_memory": {}  # 必須
    }
)
```

## 機能

### 1. Basic Memory統合

- **短期メモリ**: エージェント間の最近の対話を保持
- **長期メモリ**: 過去の実行からの洞察を保存
- **エンティティメモリ**: エンティティの追跡
- **mem0バックエンド**: 上記すべてがmem0で永続化

### 2. 検索機能

```python
# メモリ検索
results = memory_manager.search_memory(
    query="過去のAI開発に関する議論",
    limit=10,
    score_threshold=0.5
)
```

### 3. メモリ保存

```python
# メモリ保存
memory_manager.save_memory(
    key="ai_discussion",
    value="AI開発に関する重要な洞察",
    metadata={"agent": "research_agent", "timestamp": "2024-01-01"}
)
```

## 設定オプション

### 1. クラウドmem0

```yaml
memory_config:
  provider: "mem0"
  config:
    user_id: "your_user_id"
    org_id: "your_org_id"  # オプション
    project_id: "your_project_id"  # オプション
    api_key: "your-api-key"  # 環境変数を上書き
```

### 2. ローカルmem0

```yaml
memory_config:
  provider: "mem0"
  config:
    user_id: "your_user_id"
    local_mem0_config:
      vector_store:
        provider: "qdrant"
        config: {"host": "localhost", "port": 6333}
      llm:
        provider: "openai"
        config: {"api_key": "your-api-key", "model": "gpt-4"}
      embedder:
        provider: "openai"
        config: {"api_key": "your-api-key", "model": "text-embedding-3-small"}
```

## トラブルシューティング

### 1. APIキーが設定されていない場合

```
WARNING: Mem0 configured but MEM0_API_KEY not found, using basic memory
```

**解決方法**: 環境変数`MEM0_API_KEY`を設定してください。

### 2. mem0初期化エラー

```
ERROR: Failed to configure mem0 basic memory: [エラー詳細]
```

**解決方法**: 
- APIキーが正しく設定されているか確認
- ネットワーク接続を確認
- mem0サービスのステータスを確認

### 3. メモリ検索が動作しない

**確認項目**:
- mem0の設定が正しいか
- 検索クエリが適切か
- スコア閾値が適切か

## パフォーマンス最適化

### 1. ローカルmem0の使用

プライバシーとコスト削減のため、ローカルmem0インスタンスの使用を推奨します。

### 2. 適切なスコア閾値の設定

```python
# 高精度検索
results = memory_manager.search_memory(query, score_threshold=0.8)

# 幅広い検索
results = memory_manager.search_memory(query, score_threshold=0.3)
```

### 3. メモリリセット

```python
# 特定のメモリタイプをリセット
memory_manager.reset_memory("short")  # 短期メモリ
memory_manager.reset_memory("long")   # 長期メモリ
memory_manager.reset_memory("all")    # すべて
```

## 監視とログ

### 1. メモリ操作のログ

```python
import structlog

logger = structlog.get_logger()
logger.info("Memory operation completed", operation="save", key="example")
```

### 2. パフォーマンス監視

```python
# メモリ操作の時間を測定
import time

start_time = time.time()
results = memory_manager.search_memory(query)
execution_time = time.time() - start_time

logger.info("Memory search completed", 
           query=query, 
           results=len(results), 
           execution_time=execution_time)
```

## セキュリティ

### 1. APIキーの管理

- 環境変数を使用してAPIキーを管理
- コード内にハードコーディングしない
- 定期的にAPIキーをローテーション

### 2. データプライバシー

- ローカルmem0インスタンスの使用を推奨
- 機密データの適切な処理
- データ保持期間の設定

## 今後の拡張

### 1. カスタムストレージ

```python
from crewai.memory.storage.interface import Storage

class CustomStorage(Storage):
    def save(self, value, metadata=None, agent=None):
        # カスタム保存ロジック
        pass
    
    def search(self, query, limit=10, score_threshold=0.5):
        # カスタム検索ロジック
        pass
```

### 2. イベントリスナー

```python
from crewai.utilities.events import MemorySaveCompletedEvent

@crewai_event_bus.on(MemorySaveCompletedEvent)
def on_memory_save_completed(source, event):
    # メモリ保存完了時の処理
    pass
```

## まとめ

OKAMIシステムでは、CrewAIのbasic memoryシステムとmem0を統合することで、以下の利点を提供しています：

1. **永続的なメモリ**: セッション間での情報保持
2. **高度な検索**: セマンティック検索による関連情報の取得
3. **スケーラビリティ**: クラウドまたはローカルでの運用
4. **柔軟性**: カスタム設定とローカルインスタンスのサポート

この統合により、OKAMIシステムはより洗練されたメモリ機能を提供し、複雑なタスクでの継続的な学習と改善が可能になります。 