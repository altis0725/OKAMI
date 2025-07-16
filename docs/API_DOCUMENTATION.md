# OKAMI API ドキュメント

## ベースURL
- 開発環境: `http://localhost:8000`
- 本番環境: `https://your-domain.com`

## 認証
現在、APIは認証を必要としません。本番環境では、適切なセキュリティ対策を実装してください。

## エンドポイント

### システムエンドポイント

#### ヘルスチェック
```http
GET /health
```
システムのヘルス状態を返します。

**レスポンス:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:30:00Z",
  "components": {
    "api": "healthy",
    "crews": "healthy",
    "monitoring": "healthy"
  }
}
```

#### システムステータス
```http
GET /status
```
アクティブなクルーと品質メトリクスを含む詳細なシステムステータスを返します。

**レスポンス:**
```json
{
  "status": "healthy",
  "active_crews": 2,
  "total_tasks": 42,
  "recent_quality_score": 0.85,
  "pending_improvements": 3
}
```

### タスクエンドポイント

#### タスク実行
```http
POST /tasks
```
指定されたクルーを使用してタスクを実行します。

**リクエストボディ:**
```json
{
  "crew_name": "main_crew",
  "task": "最新のAIトレンドを分析し、洞察を提供してください",
  "context": {
    "focus_area": "LLMの開発"
  },
  "inputs": {
    "additional_param": "value"
  },
  "async_execution": false
}
```

**レスポンス:**
```json
{
  "task_id": "task_1737031234567",
  "status": "completed",
  "result": "分析結果...",
  "execution_time": 12.5
}
```

#### 最近のタスク取得
```http
GET /tasks/recent?limit=10
```
最近のタスク実行を取得します。

**レスポンス:**
```json
[
  {
    "task_id": "task_1737031234567",
    "status": "completed",
    "execution_time": 12.5,
    "task_description": "最新のAIトレンドを分析",
    "result": "分析結果...",
    "timestamp": "2025-01-16T10:30:00Z",
    "quality_score": 0.85
  }
]
```

#### タスク詳細取得
```http
GET /tasks/{task_id}
```
特定のタスク実行の詳細を取得します。

### クルーエンドポイント

#### クルー一覧
```http
GET /crews
```
利用可能なすべてのクルーを一覧表示します。

**レスポンス:**
```json
{
  "crews": ["main_crew", "evolution_crew"]
}
```

#### クルー情報取得
```http
GET /crews/{crew_name}
```
特定のクルーの詳細情報を取得します。

**レスポンス:**
```json
{
  "name": "main_crew",
  "agents": ["manager_agent", "research_agent", "analysis_agent"],
  "tasks": ["main_task"],
  "process": "hierarchical",
  "memory_enabled": true,
  "knowledge_enabled": true
}
```

### エージェントエンドポイント

#### エージェント一覧
```http
GET /agents
```
設定とともにすべての利用可能なエージェントを一覧表示します。

**レスポンス:**
```json
{
  "agents": [
    {
      "name": "research_agent",
      "role": "研究専門家",
      "goal": "徹底的な調査を実施し、包括的な情報を提供する",
      "backstory": "あなたは経験豊富な研究者です...",
      "tools": ["mcp"],
      "memory": true,
      "max_iter": 15
    }
  ]
}
```

### 改善エンドポイント（進化システム）

#### 改善取得
```http
GET /improvements
```
まだ適用されていない保留中の改善を取得します。

**レスポンス:**
```json
{
  "total_improvements": 15,
  "pending_improvements": 3,
  "improvements": [
    {
      "timestamp": "2025-01-16T10:30:00Z",
      "improvements": "分析により、Dockerネットワーキングの知識を追加することが提案されています...",
      "applied": false
    }
  ]
}
```

#### 改善適用
```http
POST /improvements/apply/{improvement_id}
```
特定の改善を手動で適用します。

**レスポンス:**
```json
{
  "status": "applied",
  "results": {
    "applied": [
      {
        "file": "knowledge/general.md",
        "action": "add",
        "status": "applied",
        "content_added": 256
      }
    ],
    "failed": [],
    "skipped": []
  }
}
```

#### 改善履歴取得
```http
GET /improvements/history?limit=50
```
適用された改善の履歴を表示します。

**レスポンス:**
```json
{
  "total": 12,
  "history": [
    {
      "id": 5,
      "timestamp": "2025-01-16T10:30:00Z",
      "applied": true,
      "summary": {
        "applied": 3,
        "failed": 0,
        "skipped": 1
      },
      "details": {
        "applied": [...],
        "failed": [],
        "skipped": [...]
      }
    }
  ]
}
```

#### 改善受信（内部用）
```http
POST /improvements
```
Claude Monitorが改善指示を送信するために使用します。

**リクエストボディ:**
```json
{
  "target": "crew_optimization",
  "improvements": [
    {
      "issue": "レスポンスタイムが遅い",
      "suggestions": ["キャッシュを有効にする", "タスクを並列化する"]
    }
  ],
  "priority": "high"
}
```

### モニタリングエンドポイント

#### モニタリングデータ取得
```http
GET /monitoring
```
システムモニタリングメトリクスを取得します。

**レスポンス:**
```json
{
  "total_tasks": 100,
  "completed_tasks": 85,
  "failed_tasks": 5,
  "success_rate": 85.0,
  "avg_execution_time": 15.3,
  "pending_improvements": 3
}
```

## エラーレスポンス

すべてのエンドポイントは一貫したエラーレスポンス形式に従います：

```json
{
  "error": "エラータイプ",
  "detail": "詳細なエラーメッセージ"
}
```

### 一般的なHTTPステータスコード
- `200 OK`: リクエスト成功
- `404 Not Found`: リソースが見つかりません
- `500 Internal Server Error`: サーバーエラー

## WebSocketサポート

現在実装されていません。将来のバージョンでは、リアルタイムタスク更新のためのWebSocketサポートが含まれる可能性があります。

## レート制限

現在レート制限は実装されていません。本番環境では、要件に基づいて適切なレート制限を実装してください。

## CORS

開発環境ではすべてのオリジンに対してCORSが有効になっています。本番環境では適切に設定してください。

## 使用例

### Python
```python
import requests

# タスクを実行
response = requests.post(
    "http://localhost:8000/tasks",
    json={
        "crew_name": "main_crew",
        "task": "量子コンピューティングの最新の開発について調査してください",
        "async_execution": False
    }
)

task_result = response.json()
print(f"タスクID: {task_result['task_id']}")
print(f"結果: {task_result['result']}")
```

### JavaScript
```javascript
// タスクを実行
const response = await fetch('http://localhost:8000/tasks', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        crew_name: 'main_crew',
        task: '量子コンピューティングの最新の開発について調査してください',
        async_execution: false
    })
});

const taskResult = await response.json();
console.log(`タスクID: ${taskResult.task_id}`);
console.log(`結果: ${taskResult.result}`);
```

### cURL
```bash
# タスクを実行
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew",
    "task": "量子コンピューティングの最新の開発について調査してください",
    "async_execution": false
  }'
```