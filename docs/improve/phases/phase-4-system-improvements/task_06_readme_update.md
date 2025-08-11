# タスク6: README最新化

## 📋 基本情報

**目標**: READMEを最新の実装状況に合わせて更新し、不要な記述を削除  
**優先度**: 高  
**予想作業時間**: 2-3時間  
**担当者**: ドキュメント作成者  
**前提条件**: OKAMIシステムの理解、Markdown編集スキル

## 🔍 現状分析

### 現在の問題点
- **古い情報**: 実装が変更されているが反映されていない
- **不要な記述**: 削除された機能の説明が残っている
- **情報の欠如**: 新機能や改善点が記載されていない
- **構造の問題**: 情報が整理されていない

### 期待される改善効果
- **正確性向上**: 現在の実装と一致した情報
- **可読性向上**: 整理された構造で理解しやすい
- **開発効率向上**: 新規開発者のオンボーディング改善

### 確認すべき現状
- 実際の実装状況
- 環境変数の最新リスト
- 利用可能なエンドポイント
- 依存パッケージのバージョン

## 🛠️ 実装手順

### Step 1: 現在のREADME.mdの分析と情報収集

#### 1.1 現在のREADMEの問題箇所特定
```bash
# README.mdのバックアップ作成
cp README.md README.md.backup_$(date +%Y%m%d)

# 現在の構造確認
grep "^#" README.md
```

#### 1.2 実装状況の確認
```bash
# 環境変数の確認
cat .env.example
grep -h "os.environ\|os.getenv" *.py **/*.py | sort -u

# APIエンドポイントの確認
grep "@app\." main.py

# 依存関係の確認
cat requirements.txt
cat pyproject.toml  # Poetryを使用している場合
```

### Step 2: README.mdの構造再設計

#### 2.1 新しい構造テンプレート
```markdown
# OKAMI - Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence

## 🎯 概要
[簡潔で正確なプロジェクト説明]

## ✨ 主な特徴
- 自己成長型AIエージェントシステム
- CrewAIベースの階層的タスク処理
- 知識グラフによる動的学習
- Evolution Systemによる継続的改善

## 🚀 クイックスタート

### 前提条件
- Docker & Docker Compose
- Python 3.10+
- 2GB以上の空きメモリ

### インストール
```bash
# リポジトリのクローン
git clone https://github.com/yourusername/OKAMI.git
cd OKAMI

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して必要な値を設定

# Dockerコンテナの起動
docker-compose up -d
```

### 基本的な使用方法
```bash
# ヘルスチェック
curl http://localhost:8000/health

# タスク実行
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task": "あなたのタスク", "async_execution": false}'
```

## 📁 プロジェクト構造
```
OKAMI/
├── main.py              # FastAPIアプリケーション
├── core/                # コアコンポーネント
│   ├── memory_manager.py
│   ├── knowledge_manager.py
│   └── guardrail_manager.py
├── crews/               # CrewAI関連
├── config/              # 設定ファイル
├── knowledge/           # ナレッジベース
└── evolution/           # 自己進化システム
```

## 🔧 設定

### 必須環境変数
| 変数名 | 説明 | 例 |
|--------|------|-----|
| MONICA_API_KEY | Monica AI APIキー | sk-... |
| MONICA_BASE_URL | Monica APIエンドポイント | https://... |
| OPENAI_API_KEY | OpenAI APIキー（Embeddings用） | sk-... |
| BRAVE_API_KEY | Brave Search APIキー | ... |

### オプション環境変数
[詳細な環境変数リスト]

## 📚 API リファレンス

### エンドポイント

#### POST /tasks
タスクを実行します。

**リクエスト:**
```json
{
  "task": "実行するタスク",
  "async_execution": false
}
```

**レスポンス:**
```json
{
  "result": "タスク実行結果",
  "status": "completed"
}
```

[その他のエンドポイント詳細]

## 🧪 開発

### ローカル開発環境
```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発サーバーの起動
uvicorn main:app --reload
```

### テスト実行
```bash
pytest tests/
```

## 🐛 トラブルシューティング

### よくある問題

#### Monica API接続エラー
```bash
# APIキーとURLの確認
cat .env | grep MONICA

# ログ確認
docker-compose logs okami | grep -i error
```

[その他のトラブルシューティング]

## 📄 ライセンス
[ライセンス情報]

## 🤝 コントリビューション
[コントリビューションガイド]

## 📮 サポート
[サポート情報]
```

### Step 3: 不要な記述の削除

#### 3.1 削除対象の特定
- 未実装機能の説明
- 古いAPIパラメータ（crew_nameなど）
- 使用していない環境変数
- 削除されたファイルへの参照

#### 3.2 実装例
```markdown
<!-- 削除前 -->
## API使用方法
```json
{
  "crew_name": "main_crew",  // ← 削除
  "task": "タスク内容",
  "async_execution": false
}
```

<!-- 削除後 -->
## API使用方法
```json
{
  "task": "タスク内容",
  "async_execution": false
}
```
```

### Step 4: 新機能・改善点の追加

#### 4.1 追加すべき内容
- Evolution Systemの説明
- 知識グラフ機能
- MCP統合
- Docker環境の詳細
- セキュリティ設定

#### 4.2 実装例
```markdown
## 🔄 自己進化システム

OKAMIは実行結果から学習し、自動的に改善提案を生成・適用します。

### Evolution Systemの動作
1. タスク実行完了後、自動的に分析
2. 改善提案の生成
3. 安全な範囲で自動適用
4. バックアップ作成により安全性確保

### 設定
```yaml
# config/crews/evolution_crew.yaml
evolution:
  enabled: true
  auto_apply: false  # 自動適用の有効/無効
  backup: true       # バックアップ作成
```
```

### Step 5: 実例とサンプルコードの更新

#### 5.1 動作確認済みのサンプル追加
```markdown
## 📝 使用例

### 基本的なタスク実行
```python
import requests

# タスク実行
response = requests.post(
    "http://localhost:8000/tasks",
    json={
        "task": "OKAMIシステムの特徴を3つ説明してください",
        "async_execution": False
    }
)

print(response.json()["result"])
```

### 非同期タスク実行
```python
# 長時間かかるタスクの非同期実行
response = requests.post(
    "http://localhost:8000/tasks",
    json={
        "task": "詳細な市場調査レポートを作成",
        "async_execution": True
    }
)

task_id = response.json()["task_id"]

# 結果の確認
result = requests.get(f"http://localhost:8000/tasks/{task_id}")
```
```

## ✅ 実装チェックリスト

### 必須項目
- [ ] 実装と一致した正確な情報
- [ ] crew_nameパラメータの削除
- [ ] 環境変数リストの最新化
- [ ] APIエンドポイントの正確な記述
- [ ] インストール手順の動作確認

### 推奨項目
- [ ] 図表やダイアグラムの追加
- [ ] よくある質問（FAQ）セクション
- [ ] パフォーマンスガイド
- [ ] セキュリティベストプラクティス

## 📊 成功指標

### 定量的指標
- **正確性**: 100%（すべての情報が現実装と一致）
- **完全性**: 主要機能の90%以上をカバー
- **可読性**: Markdownリンターでエラー0

### 定性的指標
- **理解しやすさ**: 初見でも30分以内にセットアップ可能
- **構造の明確性**: 情報が論理的に整理されている
- **実用性**: コピー&ペーストで動作するコード例

## 🔒 注意事項

### 重要な制約
- 機密情報（内部APIキーなど）を含めない
- 実際に動作確認したコードのみ記載
- バージョン情報を明記する

### リスクと対策
| リスク | 影響度 | 対策 |
|--------|--------|------|
| 誤情報の記載 | 高 | 実装確認の徹底 |
| 更新漏れ | 中 | チェックリスト使用 |
| 構造の複雑化 | 低 | シンプルな構成維持 |

## 🔄 トラブルシューティング

### 問題1: 環境変数の不一致
**症状**: READMEと実装で環境変数が異なる  
**原因**: 更新漏れ  
**対処法**: 
```bash
# 実装から環境変数を抽出
grep -r "os.environ" . --include="*.py" | \
  sed -n "s/.*os.environ.*['\"]([A-Z_]+)['\"].*/\1/p" | \
  sort -u
```

### 問題2: サンプルコードが動作しない
**症状**: READMEのコードでエラー  
**原因**: API変更の未反映  
**対処法**: 実際にコードを実行して確認

## 📚 関連リソース

### 内部リンク
- [UI改善タスク](./task_04_ui_improvements.md)
- [API改善タスク](./task_05_api_improvements.md)
- [CLAUDE.md](../../CLAUDE.md)

### 外部リソース
- [Markdown Guide](https://www.markdownguide.org/)
- [README Best Practices](https://www.makeareadme.com/)
- [Documentation Style Guide](https://developers.google.com/style)

---

**作成日**: 2025-08-02  
**最終更新**: 2025-08-02  
**作成者**: OKAMI Development Team  
**ステータス**: Ready for Implementation  
**次の依存タスク**: Phase 5のタスク