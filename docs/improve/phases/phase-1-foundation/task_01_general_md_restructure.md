# タスク1: general.md構造化と内容充実

## タスク概要

**目標**: knowledge/general.mdを体系的なナレッジベースとして再構築する  
**優先度**: 高  
**予想作業時間**: 2-3時間  
**担当者**: AI Assistant  

## 現状分析

### 現在のgeneral.mdの問題
```
現在の内容:
- Evolution Update の履歴のみ
- 構造化されていない
- OKAMIの基本知識が含まれていない
- 断片的な情報のみ
```

### 期待される新しい構造
```markdown
# OKAMI System Knowledge Base

## 1. システム概要
## 2. アーキテクチャ
## 3. コアコンポーネント
## 4. 設定と使用方法
## 5. トラブルシューティング
## 6. 関連リソース
```

## 実装手順

### Step 1: 現状バックアップと分析
```bash
# 現在のgeneral.mdをバックアップ
cp knowledge/general.md knowledge/general.md.backup

# 既存の進化履歴を別ファイルに移動準備
mkdir -p knowledge/system
```

### Step 2: 新しいgeneral.md構造の作成

#### 必要な情報収集元
- `CLAUDE.md` - プロジェクト概要とアーキテクチャ
- `config/` ディレクトリ - エージェント・タスク・クルー設定
- `core/` ディレクトリ - マネージャークラスの機能
- `crews/` ディレクトリ - クルーファクトリーの仕組み
- `evolution/` ディレクトリ - 自己進化システム

#### 作成すべき内容

**1. システム概要セクション**
```markdown
## システム概要

### OKAMIとは
- Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence
- CrewAIベースの自己成長型AIエージェントシステム
- 複数エージェントの協調作業による問題解決

### 主要特徴
- 階層型プロセス管理
- 自己進化機能
- ナレッジベース統合
- MCP（Model Context Protocol）対応
```

**2. アーキテクチャセクション**
```markdown
## システムアーキテクチャ

### コンポーネント関係図
[テキストベースの図表]

### データフロー
1. ユーザー入力 → FastAPI
2. CrewFactory → Crew実行
3. タスク完了 → Evolution分析
4. 改善適用 → システム更新
```

**3. コアコンポーネント詳細**
- MemoryManager: 短期・長期記憶管理
- KnowledgeManager: RAG対応知識管理  
- GuardrailManager: 品質保証
- EvolutionTracker: 進化追跡

**4. 実用的な使用方法**
- 基本的なタスク実行方法
- エージェント設定のカスタマイズ
- ナレッジ追加方法

### Step 3: 進化履歴の分離

新しいファイル作成: `knowledge/system/evolution_history.md`
```markdown
# OKAMI Evolution History

## 概要
OKAMIシステムの自動進化履歴を時系列で記録

## 履歴
[既存の進化履歴をここに移動]
```

### Step 4: クロスリファレンスの追加

他のナレッジファイルへの参照:
```markdown
## 関連ナレッジ
- [AI技術動向](./AI_advancements.md)
- [エラーパターン](./error_patterns.md)
- [ベストプラクティス](./best_practices.md)
- [システム改善履歴](./system/evolution_history.md)
```

## 実装テンプレート

### ファイル構造
```
knowledge/
├── general.md (新バージョン)
├── general.md.backup
├── system/
│   └── evolution_history.md
└── [既存ファイル]
```

### 新general.mdのテンプレート
```markdown
# OKAMI System Knowledge Base

> **更新日**: [作成日]
> **バージョン**: 2.0
> **前バージョン**: general.md.backup

## 目次
1. [システム概要](#システム概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [コアコンポーネント](#コアコンポーネント)
4. [設定と使用方法](#設定と使用方法)
5. [トラブルシューティング](#トラブルシューティング)
6. [関連リソース](#関連リソース)

[各セクションの詳細内容]

## 関連ナレッジファイル
- [AI技術動向](./AI_advancements.md) - 最新AI技術情報
- [エラーパターン](./error_patterns.md) - 一般的なエラーと対処法
- [ベストプラクティス](./best_practices.md) - 推奨される使用方法
- [システム改善履歴](./system/evolution_history.md) - 進化履歴

---
*このファイルはOKAMIシステムの中核ナレッジベースです*
```

## 品質チェックリスト

### 必須項目
- [ ] システム概要が明確に記述されている
- [ ] アーキテクチャが理解しやすく説明されている
- [ ] 各コンポーネントの役割が明記されている
- [ ] 実用的な使用方法が含まれている
- [ ] 他のナレッジファイルへの参照がある
- [ ] 進化履歴が適切に分離されている

### 技術的要件
- [ ] Markdown形式が正しい
- [ ] 目次リンクが機能する
- [ ] ファイル内リンクが正しい
- [ ] 既存バックアップが保持されている

## 検証方法

### 機能テスト
```bash
# 1. OKAMIシステムを起動
docker-compose up -d

# 2. ナレッジを使用したテストタスク実行
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew", 
    "task": "OKAMIシステムの基本的な使い方を説明してください",
    "async_execution": false
  }'

# 3. 回答にgeneral.mdの内容が反映されているか確認
```

### 内容検証
- main crewでの質問応答品質
- ナレッジ検索での適切なヒット
- 新規ユーザーにとっての理解しやすさ

## 注意事項

### 重要な制約
- 既存のKnowledgeManagerとの互換性維持
- バックアップは必ず作成
- 段階的な実装（一度にすべて変更しない）

### 推奨事項
- 作業前に現状のナレッジ検索結果を記録
- 実装後に同様のテストで改善を確認
- 問題が発生した場合のロールバック準備

## 成功指標

### 定量的指標
- ナレッジ検索ヒット率の向上
- 回答品質の向上（主観評価）
- システム説明タスクの完了精度

### 定性的指標
- 構造化された読みやすさ
- 他AIによる理解しやすさ
- 保守性の向上

---

**作成日**: 2025-08-02  
**ステータス**: Ready for Implementation  
**次の依存タスク**: タスク2（ナレッジファイル連携強化）