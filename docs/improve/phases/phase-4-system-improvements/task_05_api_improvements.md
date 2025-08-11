# タスク5: API設計改善

## 📋 基本情報

**目標**: 不要なcrew_nameパラメータを削除し、API設計を簡素化  
**優先度**: 高  
**予想作業時間**: 2-3時間  
**担当者**: バックエンド開発者  
**前提条件**: Python/FastAPI経験

## 🔍 現状分析

### 現在の問題点
- **冗長なパラメータ**: crew_nameが常に"main_crew"で固定
- **API設計の複雑性**: 不要なパラメータによる混乱
- **メンテナンス性**: 使用されないコードの存在

### 期待される改善効果
- **API簡素化**: より直感的なAPIインターフェース
- **コード削減**: 不要な条件分岐の削除
- **パフォーマンス向上**: わずかながら処理速度改善

### 関連システムの現状
- **FastAPI**: main.pyでのエンドポイント定義
- **CrewFactory**: クルー生成処理
- **フロントエンド**: API呼び出し処理

## 🛠️ 実装手順

### Step 1: 現状のAPI構造分析

#### 1.1 現在のエンドポイント確認
```python
# main.pyの現在の実装
@app.post("/tasks")
async def create_task(request: TaskRequest):
    crew_name = request.crew_name  # 常に"main_crew"
    task = request.task
    async_execution = request.async_execution
    
    # クルー処理...
```

#### 1.2 影響範囲の調査
```bash
# crew_nameの使用箇所を検索
grep -r "crew_name" --include="*.py" .
grep -r "crew_name" --include="*.js" .
grep -r "crew_name" --include="*.html" .
```

### Step 2: APIモデルの更新

#### 2.1 新しいTaskRequestモデル
```python
# models.py または main.py
from pydantic import BaseModel
from typing import Optional

class TaskRequest(BaseModel):
    """タスク実行リクエストモデル（簡素化版）"""
    task: str
    async_execution: bool = False
    # crew_nameを削除

class LegacyTaskRequest(BaseModel):
    """後方互換性のための旧モデル"""
    task: str
    crew_name: Optional[str] = "main_crew"  # デフォルト値で対応
    async_execution: bool = False
```

#### 2.2 エンドポイントの更新
```python
# main.py
@app.post("/tasks")
async def create_task(request: TaskRequest):
    """
    タスクを実行する（crew_name不要版）
    """
    try:
        # main_crewを直接使用
        crew = crew_factory.create_crew("main_crew")
        
        if request.async_execution:
            task_id = str(uuid.uuid4())
            # 非同期処理
            asyncio.create_task(
                execute_task_async(
                    task_id,
                    crew,
                    request.task
                )
            )
            return {
                "task_id": task_id,
                "status": "processing",
                "message": "Task is being processed"
            }
        else:
            # 同期処理
            result = crew.kickoff({"task": request.task})
            
            # Evolution Crewの起動（必要に応じて）
            if should_run_evolution():
                evolution_crew = crew_factory.create_crew("evolution_crew")
                evolution_result = evolution_crew.kickoff({
                    "task_result": result,
                    "original_task": request.task
                })
            
            return {
                "result": str(result),
                "status": "completed"
            }
            
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 後方互換性のための旧エンドポイント（非推奨）
@app.post("/tasks/legacy", deprecated=True)
async def create_task_legacy(request: LegacyTaskRequest):
    """
    旧APIとの互換性維持用（非推奨）
    """
    # 新しいモデルに変換
    new_request = TaskRequest(
        task=request.task,
        async_execution=request.async_execution
    )
    return await create_task(new_request)
```

### Step 3: フロントエンドの更新

#### 3.1 API呼び出しの簡素化
```javascript
// 現在のコード
async function submitTask(taskText) {
    const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            crew_name: 'main_crew',  // 削除対象
            task: taskText,
            async_execution: false
        })
    });
    return response.json();
}

// 更新後のコード
async function submitTask(taskText, asyncMode = false) {
    const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            task: taskText,
            async_execution: asyncMode
        })
    });
    return response.json();
}
```

### Step 4: テストとドキュメントの更新

#### 4.1 APIテスト
```python
# test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_task_simplified():
    """簡素化されたAPI呼び出しのテスト"""
    response = client.post(
        "/tasks",
        json={
            "task": "テストタスク",
            "async_execution": False
        }
    )
    assert response.status_code == 200
    assert "result" in response.json()

def test_legacy_compatibility():
    """後方互換性のテスト"""
    response = client.post(
        "/tasks/legacy",
        json={
            "crew_name": "main_crew",
            "task": "テストタスク",
            "async_execution": False
        }
    )
    assert response.status_code == 200
```

#### 4.2 OpenAPI仕様の更新
```python
# main.py
app = FastAPI(
    title="OKAMI API",
    description="Simplified API without crew_name parameter",
    version="2.0.0"
)

# Swagger UIで確認
# http://localhost:8000/docs
```

### Step 5: 設定ファイルの整理

#### 5.1 不要な設定の削除
```yaml
# config/api_config.yaml（もし存在すれば）
api:
  # default_crew: "main_crew"  # 削除
  timeout: 30
  max_retries: 3
```

#### 5.2 環境変数の整理
```bash
# .env
# DEFAULT_CREW_NAME=main_crew  # 削除または無効化
```

## ✅ 実装チェックリスト

### 必須項目
- [ ] crew_nameパラメータが新APIから削除されている
- [ ] main_crewがハードコードされている
- [ ] フロントエンドのAPI呼び出しが更新されている
- [ ] APIテストが通過している
- [ ] エラーハンドリングが適切

### 推奨項目
- [ ] 後方互換性エンドポイントが実装されている
- [ ] APIドキュメントが更新されている
- [ ] デプロイメントガイドが更新されている
- [ ] ログ出力が適切に調整されている

## 📊 成功指標

### 定量的指標
- **APIレスポンス時間**: 変更前後で劣化なし
- **エラー率**: 0%（既存機能の破壊なし）
- **コード行数**: 10-20%削減

### 定性的指標
- **API設計の明確性**: パラメータの意図が明確
- **保守性**: 不要なコードの除去
- **開発効率**: 新規開発者の理解速度向上

## 🔒 注意事項

### 重要な制約
- evolution_crewの呼び出しロジックは変更しない
- 既存のタスク実行ロジックを保持
- 非同期実行機能を維持

### リスクと対策
| リスク | 影響度 | 対策 |
|--------|--------|------|
| 既存統合の破壊 | 高 | 後方互換性エンドポイント提供 |
| テスト不足 | 中 | 包括的なテストスイート作成 |
| ドキュメント不整合 | 低 | 同時更新の徹底 |

## 🔄 トラブルシューティング

### 問題1: 既存クライアントからのエラー
**症状**: 422 Unprocessable Entity エラー  
**原因**: crew_nameパラメータを送信している  
**対処法**:
```python
# 一時的な互換性対応
@app.post("/tasks")
async def create_task(request: dict):
    # 辞書として受け取り、必要なフィールドのみ使用
    task = request.get("task")
    async_execution = request.get("async_execution", False)
    # crew_nameは無視
```

### 問題2: Evolution Crewが起動しない
**症状**: 改善提案が生成されない  
**原因**: crew判定ロジックの不具合  
**対処法**: Evolution起動条件を明示的に設定

## 📚 関連リソース

### 内部リンク
- [UI改善タスク](./task_04_ui_improvements.md)
- [README更新タスク](./task_06_readme_update.md)

### 外部リソース
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/best-practices/)
- [API設計ガイド](https://www.oreilly.com/library/view/designing-apis/9781492026921/)

---

**作成日**: 2025-08-02  
**最終更新**: 2025-08-02  
**作成者**: OKAMI Development Team  
**ステータス**: Ready for Implementation  
**次の依存タスク**: README更新タスク