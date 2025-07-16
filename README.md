# 🐺 OKAMI - Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence

自己成長する協調型AIエージェントシステム

## 概要

OKAMIは、CrewAIをベースに構築された自己成長型AIエージェントシステムです。複数のエージェントが協調して作業を行い、経験から学習し、知識を蓄積・共有することで、時間とともにより賢く、効率的になっていきます。

## ✅ 実装済み機能

本システムは以下の機能が実装済みで、すぐに利用可能です：

### 1. 🧠 Memory機能 ✅
- **Basic Provider**: メモリ永続化（実装済み）
- **短期記憶**: 会話コンテキストの保持
- **長期記憶**: 学習結果の永続化

### 2. 📚 Knowledge機能 ✅
- **知識ベース**: ガイドライン、ベストプラクティス、エラーパターン（実装済み）
- **知識ローダー**: エージェントへの自動知識注入（実装済み）
- **知識検索**: キーワードベースの知識検索（実装済み）

### 3. 🛡️ Guardrail機能 ✅
- **品質ガードレール**: 応答品質の自動検証（実装済み）
- **安全性ガードレール**: 機密情報・危険コードの検出（実装済み）
- **正確性ガードレール**: 基本的な事実確認（実装済み）

### 4. 🔧 MCPツール統合 ✅
- **動的ツール発見**: mcp_discover（実装済み）
- **ツール実行**: mcp_execute（実装済み）
- **Docker MCP Gateway連携**: 各種MCPツールへのアクセス（実装済み）

### 5. 👁️ Claude Code監視 ✅
- **品質モニタリング**: 応答時間と品質の監視（実装済み）
- **改善提案**: 自動改善提案生成（実装済み）
- **アラート機能**: 品質低下時の通知（実装済み）

### 6. 🚀 本番環境対応 ✅
- **Docker Compose**: 開発・本番環境構成（実装済み）
- **Nginx**: リバースプロキシ、SSL対応（実装済み）
- **ログ集約**: Logstashによるログ処理（実装済み）
- **バックアップ**: 自動バックアップスクリプト（実装済み）

### 7. 🔄 自己進化システム ✅
- **Evolution Crew**: メインタスク完了後の自動分析（実装済み）
- **改善パーサー**: 分析結果から改善点を抽出（実装済み）
- **自動適用**: 知識・設定ファイルへの自動更新（実装済み）
- **バックアップ**: 変更前の自動バックアップ（実装済み）

## アーキテクチャ

```
OKAMI/
├── config/              # 設定ファイル ✅
│   ├── agents/         # エージェント定義 (6種類)
│   ├── tasks/          # タスク定義 (6種類)
│   └── crews/          # クルー構成 (main_crew)
├── core/               # コア機能 ✅
│   ├── memory_manager.py     # メモリ管理
│   ├── knowledge_manager.py  # 知識管理
│   └── guardrail_manager.py  # ガードレール
├── crews/              # CrewAI実装 ✅
│   └── crew_factory.py # 標準CrewAI利用
├── guardrails/         # カスタムガードレール ✅
├── knowledge/          # 知識ベース ✅
│   ├── general_guidelines.txt
│   ├── best_practices.txt
│   └── error_patterns.txt
├── tools/              # MCPツール ✅
├── monitoring/         # Claude Code監視 ✅
├── evolution/          # 自己進化システム ✅
│   ├── improvement_parser.py   # 改善提案パーサー
│   ├── improvement_applier.py  # 改善適用エンジン
│   └── backups/               # 変更前バックアップ
├── storage/            # データ永続化
├── tests/              # テストコード ✅
└── logs/               # ログファイル
```

## 技術スタック

- **Python**: 3.11+
- **CrewAI**: 0.140.0 (tools付き)
- **FastAPI**: REST API
- **Monica LLM**: GPT-4o互換API
- **ChromaDB**: ベクトルストレージ
- **Docker**: コンテナ化
- **Claude Code**: 外部監視
- **structlog**: 構造化ログ

## セットアップ

### 前提条件
- Docker & Docker Compose
- SEACOR/.envファイル（APIキー用）

### 手順

```bash
# 1. 環境変数の設定（SEACORから）
cp ../SEACOR/.env .env

# 2. Dockerコンテナの起動
docker-compose up -d

# 3. ヘルスチェック
curl http://localhost:8000/health

# 4. 利用可能なクルーの確認
curl http://localhost:8000/crews
```

## 使用方法

### REST APIでの利用

```bash
# タスクの実行
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew",
    "task": "最新のAI技術動向を調査してレポートを作成",
    "async_execution": false
  }'

# タスク履歴の確認
curl http://localhost:8000/tasks

# 非同期タスクの状態確認
curl http://localhost:8000/tasks/{task_id}
```

### Pythonクライアントでの利用

```python
import requests

# OKAMIサーバーに接続
response = requests.post(
    "http://localhost:8000/tasks",
    json={
        "crew_name": "main_crew",
        "task": "Hello Worldプログラムを作成",
        "async_execution": False
    }
)

result = response.json()
print(result["result"])
```

## 開発状況

- [x] システム設計
- [x] ディレクトリ構造
- [x] コア機能実装（メモリ、知識、ガードレール）
- [x] エージェント定義（6種類）
- [x] MCPツール統合
- [x] Claude Code監視システム
- [x] Docker環境構築
- [x] テスト実装
- [x] ドキュメント整備
- [ ] WebUI（必要に応じて）

## テスト

```bash
# ユニットテスト
python tests/test_crew_factory.py
python tests/test_knowledge_loader.py
python tests/test_guardrails.py
python tests/test_mcp_simple.py

# Docker環境テスト
./scripts/test-docker.sh
```

## 本番環境へのデプロイ

```bash
# SSL証明書の準備
mkdir -p nginx/ssl
# cert.pemとkey.pemを配置

# デプロイ実行
./scripts/deploy-prod.sh

# バックアップ
./scripts/backup.sh
```

## トラブルシューティング

### APIキーエラー
```bash
# SEACORの.envファイルを確認
cat ../SEACOR/.env | grep MONICA_API_KEY
```

### MCPツールエラー
```bash
# Docker MCP Gatewayの起動
docker mcp gateway run
```

### メモリエラー
- config/crews/main_crew.yamlで`memory_config.provider: "basic"`を確認

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずイシューを作成して変更内容を議論してください。