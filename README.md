# 🐺 OKAMI - Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence

自己成長する協調型AIエージェントシステム

## 概要

OKAMIは、CrewAI 0.140.0をベースに構築された自己成長型AIエージェントシステムです。複数のエージェントが協調して作業を行い、経験から学習し、知識を蓄積・共有することで、時間とともにより賢く、効率的になっていきます。

### 🌟 主な特徴

- **自己進化機能**: メインタスク完了後に自動的にEvolution Crewが分析・改善を実行
- **階層型プロセス**: マネージャーエージェントによるインテリジェントなタスク委譲
- **Qdrant知識管理**: ベクトル検索対応の高性能知識ベース
- **リアルタイム監視**: Claude Code品質モニタリング統合
- **マルチLLMサポート**: Monica LLM（GPT-4o互換）+ Ollama埋め込み

## ✅ 実装済み機能

本システムは以下の機能が実装済みで、すぐに利用可能です：

### 1. 🧠 Memory機能 ✅
- **Basic Provider**: メモリ永続化（実装済み）
- **Mem0統合**: 永続的なメモリ管理（実装済み）
- **短期記憶**: 会話コンテキストの保持
- **長期記憶**: 学習結果の永続化
- **エンティティ記憶**: エンティティの追跡
- **セマンティック検索**: 関連情報の高度な検索

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

### 7. 🔄 自己進化システム ✅ ⚠️
- **Evolution Crew**: メインタスク完了後の自動分析（実装済み）
- **改善パーサー**: 分析結果から改善点を抽出（実装済み）
- **自動適用**: 知識・設定ファイルへの自動更新（実装済み）
- **バックアップ**: 変更前の自動バックアップ（実装済み）
- **制約**: 現在Qdrant接続問題により、知識管理を含む高度な機能のテストが必要

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
- **CrewAI**: 0.159.0 (tools付き)
- **FastAPI**: REST API
- **Monica LLM**: GPT-4o互換API
- **ChromaDB**: ベクトルストレージ
- **Ollama**: ローカル埋め込みモデル（mxbai-embed-large）
- **Mem0**: 永続的メモリ管理（クラウド・ローカル対応）
- **Docker**: コンテナ化
- **Claude Code**: 外部監視
- **structlog**: 構造化ログ
- **NetworkX**: 知識グラフ
- **SQLAlchemy**: データベースORM

## セットアップ

### 前提条件
- Docker & Docker Compose
- Monica LLM API キー

### 手順

```bash
# 1. 環境変数の設定
cp .env.example .env
# MONICA_API_KEY と MONICA_BASE_URL を設定

# 2. Dockerコンテナの起動（Ollamaも自動起動）
docker-compose up -d
# ※初回起動時はOllamaがmxbai-embed-largeモデルを自動ダウンロード

# 3. ヘルスチェック
curl http://localhost:8000/health

# 4. 利用可能なクルーの確認
curl http://localhost:8000/crews

# 5. ChromaDB接続確認
curl http://localhost:8001/api/v1/heartbeat
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
        "crew_name": "simple_crew",
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

## 🚨 既知の問題と解決策

### 1. Ollama関連エラー
**症状**: 起動時に「pulling manifest」が繰り返し表示される

**原因**: Docker起動時に毎回モデルをダウンロードしようとしている

**解決策**: 
- 最新版では修正済み（モデルが既に存在する場合はスキップ）
- 手動確認：`docker exec okami-ollama ollama list`

### 2. ChromaDB接続エラー
**症状**: ベクトル検索でエラー

**解決策**:
```bash
# ChromaDBの状態確認
docker-compose logs chromadb
curl http://localhost:8001/api/v1/heartbeat

# Ollamaの起動確認
curl http://localhost:11434/api/tags
```

### 2. Evolution履歴が見つからない
**症状**: `{"detail":"Not Found"}`

**説明**: evolution_crewは正常にタスク完了後にトリガーされるため、まずmain_crewでタスクを正常実行する必要があります。

### 3. APIキーエラー
```bash
# Monica APIキーの確認
cat .env | grep MONICA_API_KEY
```

### 4. メモリエラー
- config/crews/main_crew.yamlで`memory_config.provider: "mem0"`を確認
- Mem0 APIキーが必要な場合があります

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずイシューを作成して変更内容を議論してください。