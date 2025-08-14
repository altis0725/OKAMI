# Evolution System - Knowledge Directory Only Restriction

## 概要

2025年8月14日より、OKAMI Evolution Systemの自動改善適用範囲を`knowledge/`ディレクトリのみに制限しました。これにより、システムの自己進化機能は知識ベースの更新のみを自動的に行い、設定ファイル（YAML）への直接的な変更は行わなくなります。

## 変更理由

1. **安全性の向上**: システム設定の自動変更によるリスクを排除
2. **予測可能性**: 設定変更は人間のレビューと承認を必要とする
3. **知識中心の進化**: 知識の蓄積と改善に焦点を当てる

## 技術的実装

### 変更されたコンポーネント

#### 1. ImprovementParser (`evolution/improvement_parser.py`)

`extract_actionable_changes`メソッドを修正：
- config/agents/*.yaml への変更を知識ファイルへの提案として変換
- config/tasks/*.yaml への変更を知識ファイルへの提案として変換
- config/crews/*.yaml への変更を知識ファイルへの提案として変換

変換マッピング：
- エージェント設定 → `knowledge/agents/{agent}.md`
- タスク設定 → `knowledge/crew/task_improvements.md`
- システム設定 → `knowledge/system/config_suggestions.md`

#### 2. ImprovementApplier (`evolution/improvement_applier.py`)

`apply_changes`メソッドを修正：
- knowledge/以外のファイルへの変更をブロック
- ブロックされた変更を`blocked_config_changes`として記録
- 提案されたconfig変更を`evolution/proposed_changes/config_proposals.json`に保存

### 新機能

#### 提案されたConfig変更の記録

ブロックされたconfig変更は自動的に以下に保存されます：
```
evolution/proposed_changes/
└── config_proposals.json
```

フォーマット：
```json
[
  {
    "file_path": "config/agents/research_agent.yaml",
    "action": "update_field",
    "changes": {
      "field": "max_iter",
      "value": 50
    },
    "timestamp": "2025-08-14T01:08:59"
  }
]
```

## 使用方法

### 1. 通常の自動進化プロセス

Evolution Crewは引き続き改善提案を生成しますが、実際に適用されるのは知識ファイルのみです：

```python
# Evolution Crewの実行
result = evolution_crew.kickoff({"task": "analyze_performance"})

# ImprovementApplierが自動的に知識ファイルのみを更新
applier = ImprovementApplier()
results = applier.apply_changes(changes)
```

### 2. 提案されたConfig変更のレビュー

```python
import json

# 提案されたconfig変更を読み込み
with open("evolution/proposed_changes/config_proposals.json", "r") as f:
    proposals = json.load(f)

# レビューして手動で適用
for proposal in proposals:
    print(f"File: {proposal['file_path']}")
    print(f"Changes: {proposal['changes']}")
    # 手動で適用するかどうかを決定
```

### 3. Config変更を知識として活用

Config変更の提案は、対応する知識ファイルに記録されます：

- `knowledge/agents/{agent}.md`: エージェント固有の改善提案
- `knowledge/crew/task_improvements.md`: タスク改善の提案
- `knowledge/system/config_suggestions.md`: システム設定の提案

エージェントはこれらの知識を参照して、動的に動作を調整できます。

## 影響と注意点

### ポジティブな影響

1. **安全性**: 予期しない設定変更によるシステムダウンのリスクなし
2. **透明性**: すべての設定変更提案が記録され、レビュー可能
3. **柔軟性**: 知識ベースの進化は継続

### 制限事項

1. **自動最適化の制限**: パラメータの自動調整は行われない
2. **手動介入の必要性**: 設定変更には人間の判断が必要
3. **進化速度の低下**: 完全自動進化と比較して遅い

## テスト

変更の動作確認：
```bash
python tests/test_knowledge_only_applier.py
```

## 移行ガイド

### 既存のシステムからの移行

1. 最新のコードを取得
2. 既存の`evolution/backups/`を確認（変更前のバックアップ）
3. `evolution/proposed_changes/`ディレクトリを作成
4. テストを実行して動作確認

### ロールバック

以前の動作に戻す場合：
1. `evolution/improvement_parser.py`の`extract_actionable_changes`を元に戻す
2. `evolution/improvement_applier.py`の`apply_changes`を元に戻す

## 今後の改善案

1. **スマートレビューシステム**: 提案されたconfig変更の自動分析とリスク評価
2. **条件付き適用**: 特定の条件下でのみconfig変更を許可
3. **サンドボックステスト**: 提案された変更を隔離環境でテスト
4. **知識ベースの設定オーバーライド**: 知識ファイルから設定を動的に調整

## 関連ファイル

- `evolution/improvement_parser.py`: 改善提案の解析
- `evolution/improvement_applier.py`: 改善の適用
- `evolution/knowledge_applier.py`: 知識ファイル専用の適用器
- `tests/test_knowledge_only_applier.py`: テストスクリプト
- `evolution/proposed_changes/config_proposals.json`: 提案されたconfig変更の記録