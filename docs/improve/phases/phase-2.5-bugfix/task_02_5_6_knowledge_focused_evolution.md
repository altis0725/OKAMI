# タスク 2.5.6: Evolution System - 知識管理特化型への改善

## 📋 タスク概要
**ID**: TASK-025-06  
**名称**: Evolution System知識管理特化型への改善  
**フェーズ**: Phase 2.5 - Bugfix  
**優先度**: 高  
**推定工数**: 3-4時間  
**依存関係**: Task 2.5.5完了（Evolution Systemファイル更新バグ修正）

## 🎯 目的
Evolution Systemを知識の新規作成と更新のみに特化させることで、システムの知識管理能力を大幅に向上させ、Phase 3の自動改善サイクルの基盤を強化する。

## 🔍 背景・課題

### 現在の問題点
1. **汎用的すぎる処理**
   - エージェント設定更新と知識更新が同じロジックで処理
   - 知識ファイル特有の構造化要件が考慮されていない

2. **知識管理の非効率性**
   - 知識の重複チェックなし
   - カテゴリ分類の自動化なし
   - 知識間の関連性が管理されていない

3. **モデルとタスク定義の不整合**
   - `models/evolution_output.py`にはUpdateAgentParameterとCreateAgentが定義
   - `config/tasks/evolution_task.yaml`では知識管理のみを想定
   - 実際の運用では知識管理が主要タスク

## 📐 技術設計

### 1. モデル定義の簡素化

#### 更新前: models/evolution_output.py
```python
class UpdateAgentParameter(ChangeBase):
    """エージェントパラメータ更新"""
    type: str = Field(default="update_agent_parameter")
    agent: str = Field(..., description="対象エージェント名")
    parameter: str = Field(..., description="パラメータ名")
    value: Any = Field(..., description="新しい値")

class CreateAgent(ChangeBase):
    """新規エージェント作成"""
    type: str = Field(default="create_agent")
    file: str = Field(..., description="ファイルパス")
    config: dict = Field(..., description="エージェント設定")
```

#### 更新後: models/evolution_output.py
```python
class UpdateKnowledge(ChangeBase):
    """既存知識の更新"""
    type: str = Field(default="update_knowledge")
    file: str = Field(..., description="更新対象ファイルパス")
    section: Optional[str] = Field(None, description="更新対象セクション")
    content: str = Field(..., description="更新内容")
    operation: str = Field("append", description="更新操作: append, replace, insert")

class KnowledgeCategory(str, Enum):
    """知識カテゴリ"""
    AGENT = "agents"
    CREW = "crew"
    SYSTEM = "system"
    DOMAIN = "domain"
    GENERAL = "general"
```

### 2. タスク定義の最適化

#### config/tasks/evolution_task.yaml の更新
```yaml
evolution_task:
  description: |
    Analyze system performance and generate knowledge improvements.
    Focus ONLY on knowledge creation and updates.
    
    User Input: {user_input}
    Main Crew Response: {main_response}
    
    Analyze the interaction and identify:
    1. New knowledge that should be captured
    2. Existing knowledge that needs updating
    3. Knowledge gaps that were revealed
    
    Output improvements in this JSON format:
    ```json
    {
      "changes": [
        {
          "type": "add_knowledge",
          "category": "agents|crew|system|domain|general",
          "file": "knowledge/category/filename.md",
          "title": "Knowledge Title",
          "content": "Structured markdown content",
          "tags": ["tag1", "tag2"],
          "reason": "Why this knowledge is valuable"
        },
        {
          "type": "update_knowledge",
          "file": "knowledge/existing_file.md",
          "section": "## Section Name",
          "content": "Updated content",
          "operation": "append|replace|insert",
          "reason": "Why this update is needed"
        }
      ]
    }
    ```
  
  expected_output: |
    A JSON object containing ONLY knowledge-related changes.
    Each change must include structured metadata for proper categorization.
```

### 3. 知識管理特化型Applierの実装

#### evolution/knowledge_applier.py (新規)
```python
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class KnowledgeApplier:
    """知識管理に特化したEvolution System Applier"""
    
    def __init__(self, knowledge_base_path: Path = Path("knowledge")):
        self.knowledge_base = knowledge_base_path
        self.knowledge_index = self._load_knowledge_index()
        
    def apply_knowledge_changes(self, changes: List[Dict], dry_run: bool = False):
        """知識変更の適用"""
        results = []
        
        for change in changes:
            if change["type"] == "add_knowledge":
                result = self._add_knowledge(change, dry_run)
            elif change["type"] == "update_knowledge":
                result = self._update_knowledge(change, dry_run)
            else:
                result = {"status": "skipped", "reason": f"Unknown type: {change['type']}"}
            
            results.append(result)
            
        # インデックスの更新
        if not dry_run:
            self._update_knowledge_index()
            
        return results
    
    def _add_knowledge(self, change: Dict, dry_run: bool) -> Dict:
        """新規知識の追加"""
        try:
            # カテゴリディレクトリの確保
            category = change.get("category", "general")
            category_path = self.knowledge_base / category
            
            if not dry_run:
                category_path.mkdir(parents=True, exist_ok=True)
            
            # 知識ファイルの作成
            file_path = Path(change["file"])
            
            # 構造化されたマークダウンの生成
            content = self._format_knowledge_content(
                title=change.get("title", "Untitled"),
                content=change["content"],
                tags=change.get("tags", []),
                created_at=datetime.now()
            )
            
            if not dry_run:
                # 重複チェック
                if self._is_duplicate_knowledge(content, category):
                    return {
                        "status": "skipped",
                        "reason": "Duplicate knowledge detected"
                    }
                
                # ファイル書き込み
                file_path.write_text(content, encoding="utf-8")
                
                # インデックスに追加
                self._add_to_index(file_path, change)
            
            return {
                "status": "success",
                "file": str(file_path),
                "category": category
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def _update_knowledge(self, change: Dict, dry_run: bool) -> Dict:
        """既存知識の更新"""
        try:
            file_path = Path(change["file"])
            
            if not file_path.exists():
                return {
                    "status": "error",
                    "reason": f"File not found: {file_path}"
                }
            
            current_content = file_path.read_text(encoding="utf-8")
            
            # 更新操作の実行
            operation = change.get("operation", "append")
            section = change.get("section")
            new_content = change["content"]
            
            if operation == "append":
                updated_content = self._append_to_section(
                    current_content, section, new_content
                )
            elif operation == "replace":
                updated_content = self._replace_section(
                    current_content, section, new_content
                )
            elif operation == "insert":
                updated_content = self._insert_at_section(
                    current_content, section, new_content
                )
            else:
                return {
                    "status": "error",
                    "reason": f"Unknown operation: {operation}"
                }
            
            if not dry_run:
                # バックアップ作成
                backup_path = file_path.with_suffix(
                    f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                file_path.rename(backup_path)
                
                # 更新内容の書き込み
                file_path.write_text(updated_content, encoding="utf-8")
                
                # インデックスの更新
                self._update_in_index(file_path, change)
            
            return {
                "status": "success",
                "file": str(file_path),
                "operation": operation
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def _format_knowledge_content(
        self, 
        title: str, 
        content: str, 
        tags: List[str], 
        created_at: datetime
    ) -> str:
        """知識コンテンツのフォーマット"""
        formatted = f"""# {title}

**Created**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}  
**Tags**: {', '.join(tags) if tags else 'None'}  
**Category**: Knowledge Base

---

{content}

---

## Metadata

- **Source**: Evolution System
- **Version**: 1.0
- **Last Updated**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}

## Related Knowledge

<!-- Automatically populated by Knowledge Manager -->

## Usage Examples

<!-- To be added as the knowledge is applied -->
"""
        return formatted
    
    def _is_duplicate_knowledge(self, content: str, category: str) -> bool:
        """重複知識のチェック"""
        # シンプルな類似度チェック（実装は簡略化）
        # 本番環境ではベクトル類似度などを使用
        category_path = self.knowledge_base / category
        
        if not category_path.exists():
            return False
        
        for file in category_path.glob("*.md"):
            existing_content = file.read_text(encoding="utf-8")
            # 簡易的な重複チェック（最初の100文字で判定）
            if content[:100] in existing_content:
                return True
        
        return False
    
    def _load_knowledge_index(self) -> Dict:
        """知識インデックスの読み込み"""
        index_path = self.knowledge_base / "index.json"
        
        if index_path.exists():
            return json.loads(index_path.read_text(encoding="utf-8"))
        
        return {
            "files": {},
            "tags": {},
            "categories": {}
        }
    
    def _update_knowledge_index(self):
        """知識インデックスの更新"""
        index_path = self.knowledge_base / "index.json"
        index_path.write_text(
            json.dumps(self.knowledge_index, indent=2),
            encoding="utf-8"
        )
    
    def _add_to_index(self, file_path: Path, change: Dict):
        """インデックスへの追加"""
        self.knowledge_index["files"][str(file_path)] = {
            "title": change.get("title", "Untitled"),
            "category": change.get("category", "general"),
            "tags": change.get("tags", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def _update_in_index(self, file_path: Path, change: Dict):
        """インデックスの更新"""
        if str(file_path) in self.knowledge_index["files"]:
            self.knowledge_index["files"][str(file_path)]["updated_at"] = \
                datetime.now().isoformat()
    
    def _append_to_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションへの追記"""
        if section:
            lines = content.split('\n')
            section_index = -1
            
            for i, line in enumerate(lines):
                if section in line:
                    section_index = i
                    break
            
            if section_index >= 0:
                # セクションの終わりを見つける
                next_section_index = len(lines)
                for i in range(section_index + 1, len(lines)):
                    if lines[i].startswith('#') and not lines[i].startswith('###'):
                        next_section_index = i
                        break
                
                # セクションの最後に追加
                lines.insert(next_section_index, new_text)
                return '\n'.join(lines)
        
        # セクションが見つからない場合は末尾に追加
        return content + '\n\n' + new_text
    
    def _replace_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションの置換"""
        if not section:
            return new_text
        
        lines = content.split('\n')
        section_start = -1
        section_end = len(lines)
        
        for i, line in enumerate(lines):
            if section in line:
                section_start = i
                # 次のセクションを探す
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('#') and not lines[j].startswith('###'):
                        section_end = j
                        break
                break
        
        if section_start >= 0:
            # セクション全体を置換
            new_lines = lines[:section_start + 1] + [new_text] + lines[section_end:]
            return '\n'.join(new_lines)
        
        return content
    
    def _insert_at_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションへの挿入"""
        if section:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if section in line:
                    lines.insert(i + 1, new_text)
                    return '\n'.join(lines)
        
        # セクションが見つからない場合は先頭に挿入
        return new_text + '\n\n' + content
```

## 🚀 実装手順

### Step 1: モデル定義の更新（15分）
1. `models/evolution_output.py`のバックアップ作成
2. 不要なクラス（UpdateAgentParameter, CreateAgent）を削除
3. UpdateKnowledgeクラスとKnowledgeCategoryを追加
4. EvolutionChangesクラスのUnion型を更新

### Step 2: タスク定義の更新（15分）
1. `config/tasks/evolution_task.yaml`のバックアップ作成
2. descriptionとexpected_outputを知識管理に特化した内容に更新
3. JSON出力フォーマットを新しい構造に変更

### Step 3: Knowledge Applierの実装（1.5時間）
1. `evolution/knowledge_applier.py`を新規作成
2. 基本的な知識管理機能の実装
3. 重複チェックとカテゴリ管理の追加
4. インデックス管理機能の実装

### Step 4: 既存システムとの統合（30分）
1. `evolution/improvement_applier.py`からKnowledgeApplierを呼び出すように変更
2. エージェント設定更新のロジックを分離
3. 知識管理専用のパスを確立

### Step 5: テストの実装（1時間）
1. `tests/test_knowledge_applier.py`を作成
2. 新規知識作成のテスト
3. 既存知識更新のテスト
4. 重複検出のテスト
5. インデックス管理のテスト

### Step 6: 動作確認（30分）
1. Evolution Crewでのテスト実行
2. 知識ファイルの生成確認
3. インデックスの更新確認
4. ログ出力の確認

## ✅ 完了条件

### 機能要件
- [ ] 知識の新規作成が正しく動作する
- [ ] 既存知識の更新が構造化されて実行される
- [ ] 知識カテゴリが自動的に管理される
- [ ] 重複知識が検出される
- [ ] インデックスが自動更新される

### 品質要件
- [ ] すべてのテストが成功する
- [ ] エラーハンドリングが適切に実装されている
- [ ] バックアップが自動作成される
- [ ] ログが適切に出力される

### ドキュメント要件
- [ ] 実装内容がCLAUDE.mdに記載される
- [ ] 使用方法がREADMEに追加される
- [ ] テスト手順が文書化される

## 🎯 期待される効果

### 短期的効果
- Evolution Systemの安定性向上
- 知識管理の効率化
- 知識の構造化と検索性の向上

### 長期的効果
- Phase 3の自動改善サイクルの基盤確立
- 知識ベースの継続的な成長
- システム全体の学習能力向上

## ⚠️ リスクと対策

### リスク1: 既存システムとの互換性
**対策**: 段階的な移行と後方互換性の維持

### リスク2: パフォーマンスの低下
**対策**: インデックスによる高速化とキャッシュの活用

### リスク3: 知識の断片化
**対策**: カテゴリ管理と自動リンク生成

## 📊 成功指標

| 指標 | 現在値 | 目標値 | 測定方法 |
|------|--------|--------|----------|
| 知識作成成功率 | 60% | 95%以上 | Evolution実行ログ |
| 重複知識の割合 | 不明 | 5%以下 | インデックス分析 |
| カテゴリ適合率 | なし | 90%以上 | 手動レビュー |
| 処理時間 | 不明 | 1件あたり1秒以内 | パフォーマンステスト |

## 🔗 関連タスク
- Task 2.5.5: Evolution Systemファイル更新バグ修正（前提条件）
- Phase 3: 自動化改善フェーズ（この修正が基盤となる）

## 📝 実装者向けメモ

### 注意事項
1. **バックアップを必ず作成**してから実装を開始
2. **段階的にテスト**しながら進める
3. **既存の知識ファイルへの影響**を最小限に抑える

### 推奨される開発環境
```bash
# テスト環境の準備
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# テストの実行
python -m pytest tests/test_knowledge_applier.py -v

# Evolution Crewでの動作確認
python main.py --crew evolution --input "Test knowledge creation"
```

### トラブルシューティング
1. **インデックスが更新されない場合**
   - `knowledge/index.json`の権限を確認
   - ログファイルでエラーを確認

2. **重複チェックが機能しない場合**
   - カテゴリディレクトリの存在を確認
   - 類似度閾値の調整を検討

3. **知識ファイルが作成されない場合**
   - ディレクトリの書き込み権限を確認
   - Evolution outputのJSON形式を検証

---

**作成日**: 2025-08-13  
**作成者**: Claude Code Assistant  
**バージョン**: 1.0  
**ステータス**: 実装待ち