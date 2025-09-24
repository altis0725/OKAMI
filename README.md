# 🐺 OKAMI - Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence

自己成長する協調型AIエージェントシステム

## 概要

OKAMIは、CrewAI 0.193.x をベースに構築された自己成長型AIエージェントシステムです。複数のエージェントが協調して作業を行い、経験から学習し、知識を蓄積・共有することで、時間とともにより賢く、効率的になっていきます。

### 🌟 主な特徴

- **自己進化機能**: メインタスク完了後に自動的にEvolution Crewが分析・改善を実行
- **階層型プロセス**: マネージャーエージェントによるインテリジェントなタスク委譲
- **ChromaDB 知識管理**: ベクトル検索対応の高性能知識ベース
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
- **CrewAI**: 0.193.2 (tools付き)
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

### 運用確認用エンドポイント

```bash
# アプリ全体のヘルス
curl http://localhost:8000/health

# 埋め込み（Embedding）プロバイダのヘルス（Ollama / モデル / healthy）
curl http://localhost:8000/api/embed/health

# Mem0 の接続確認（ENV で USE_MEM0=true, MEM0_API_KEY 設定時）
curl http://localhost:8000/mem0/health
```

### .env / 環境変数での運用設定

- Mem0 を YAML ではなく ENV で有効化
  - `USE_MEM0=true`
  - `MEM0_API_KEY=...`（必須）
  - `MEM0_USER_ID=okami_main_crew`（任意）

- ログ／ナレッジ／Chroma の永続化（単一ボリューム配下に集約）
  - `OKAMI_LOG_DIR=/app/storage/logs`
  - `KNOWLEDGE_DIR=/app/storage/knowledge`
  - `CHROMA_PERSIST_DIRECTORY=/app/storage/chroma`

- Chroma 書き込みタイムアウト緩和（リトライ制御）
  - `CHROMA_ADD_MAX_RETRIES`（既定3）
  - `CHROMA_ADD_RETRY_INITIAL_DELAY`（既定0.2秒）
  - `CHROMA_QUERY_MAX_RETRIES`（既定3）
  - `CHROMA_QUERY_INITIAL_DELAY`（既定0.2秒）

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

### 3. CrewAI バリデーション関連（埋め込み/マネージャー）
**症状A**: `Value error, embedder_config is required`（Crew 作成時）

**原因**: CrewAI 0.18x 系では `Crew(embedder=...)` が必要になるケースがあります。

**対処**:
- 本レポジトリでは `crews/crew_factory.py` が `OkamiConfig.get_embedder_config()` から自動注入します（既定は Ollama `mxbai-embed-large`）。
- それでも失敗する場合は自動で embedder を外して再試行するフォールバックが入っています（ログに警告が出ます）。

**症状B**: `Manager agent should not be included in agents list`（階層型）

**原因**: 階層型プロセスで `manager_agent` を `agents` 配列に含めると CrewAI がバリデーションエラーにします。

**対処**:
- 本レポジトリでは Crew 生成時は `manager_agent` を引数で渡し、生成後に `crew.agents` へ追加する実装で両立（テスト互換）しています。

### 4. Mem0 統合（ExternalMemory）
**症状A**: `Invalid API key` / `401 Unauthorized`

**原因**: `MEM0_API_KEY` が無効。

**対処**:
- `.env` に `MEM0_API_KEY` を設定し直す。org/project を使用する場合は `org_id` / `project_id` も mem0 側で有効化が必要です。

**症状B**: `ExternalMemory.save() got an unexpected keyword argument 'agent'`

**原因**: CrewAI のバージョン差異。`agent` キーワード未対応のバージョンがあります。

**対処**:
- `core/memory_manager.py` は位置引数で保存するように修正済み（バージョン差異を吸収）。

**症状C**: `'NoneType' object has no attribute 'save'`（Mem0 ストレージ未初期化）

**原因**: `ExternalMemory` の内部ストレージが未構築。

**対処**:
- `MemoryManager` 側で遅延初期化（`set_crew(None)`）を行うように修正済み。ログに `Mem0 ExternalMemory initialized successfully` が出るか確認してください。

**補足**:
- 失敗時はエラーハンドラにより `search*` は `[]`、`save*` は `False` を返し、動作継続します。

### 5. Ollama 埋め込みモデルが見つからない
**症状**: `model not found` / 埋め込み呼び出しが失敗

**解決策**:
```bash
docker exec -it okami-ollama ollama pull mxbai-embed-large
curl -f http://localhost:11434/api/tags | jq
```
`EMBEDDER_MODEL` と `OLLAMA_BASE_URL` が `.env` と compose で一致しているか確認してください。

---

## 変更履歴（重要）

この節は CrewAI 0.193 系対応とコード整理の要点です。

- Crew 作成の安定化（`crews/crew_factory.py`）
  - `embedder` を `OkamiConfig` から自動注入（既定は Ollama）。失敗時は embedder を外して再試行。
  - `ShortTermMemory` / `EntityMemory` / `LongTermMemory` に `embedder_config` を明示して作成。
  - 階層型プロセス: `manager_agent` は引数渡し→Crew 生成後に `crew.agents` に追加（テスト互換）。
- Mem0 統合の安定化（`core/memory_manager.py`）
  - `ExternalMemory(embedder_config={"provider": "mem0", ...})` を標準化（バージョン差異を吸収）。
  - ストレージ未初期化時は遅延初期化（`set_crew(None)`）を実施。
  - `get_crew_memory_config()` は後方互換のため `external_memory` と Mem0 形の `memory_config` を両方返却。
  - 失敗時フォールバック: `search` は `[]`、`save` は `False` を返す。
- MCP ツールの初期化互換（`tools/mcp_gateway_tool.py`）
  - Pydantic v2 向けに `BaseTool` 初期化をフィールド引数に統一。
  - `tools/__init__.py` にテストが参照するエクスポートを追加。

### バージョン
- CrewAI: 0.193.2
- Mem0: 0.1.116
- ChromaDB: 0.5.23（HTTPサーバー/永続ボリューム利用）

---

## Mem0 v2 運用ガイド（保存/検索）

本プロジェクトは Mem0 外部メモリを v2 API で運用します（既定）。

### 必須環境変数
- `MEM0_API_KEY`（必須）
- 任意: `MEM0_API_BASE`（既定: `https://api.mem0.ai`）

### クルー（YAML）の mem0 設定例
```yaml
mem0_config:
  user_id: "okami_main_crew"
  # 以下は必要に応じて
  org_id: "your_org_id"
  project_id: "your_project_id"
  run_id: "session_or_run_id"
  includes: "include1"
  excludes: "exclude1"
  infer: true
```

### どのエンドポイントを使うか
- 追加(保存): `POST /v1/memories/`（ヘッダ: `Authorization: Token <API_KEY>`、body に `version: "v2"`）
- 検索(v2): `POST /v2/memories/search/`（ヘッダ: `Authorization: Token <API_KEY>`、body に `filters` 必須。例: `{ "AND": [{"user_id":"..."}] }`）

### メタデータ制限について
- v2 でもメタデータの文字数制限（~2000文字）があるため、内部で過大時は自動的に切り詰めて再試行します。
- 厳密な制御が必要な場合は `includes` / `excludes` / `infer` を活用して、保存対象メタデータを絞り込んでください。

### 無効化/切替
- Mem0 を使わない運用に切り替える場合は、
  - `.env` から `MEM0_API_KEY` を外す、または
  - 各クルー YAML の `mem0_config` を一時的にコメントアウトしてください（basic memory にフォールバック）。



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
