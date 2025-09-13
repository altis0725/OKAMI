# Railway デプロイガイド

OKAMI システムをRailwayにデプロイする手順です。

## 前提条件

- [Railway CLI](https://docs.railway.app/develop/cli) がインストール済み
- Railwayアカウントでログイン済み（`railway login`）

## デプロイ手順

### 1. プロジェクトの初期化

```bash
# プロジェクトディレクトリで実行
railway login
railway link  # 既存プロジェクトにリンクする場合
# または
railway init  # 新規プロジェクトを作成する場合
```

### 2. 環境変数の設定

Railwayのダッシュボードまたはコマンドラインで必須環境変数を設定：

```bash
# 必須APIキー
railway variables set MONICA_API_KEY=sk-your-monica-api-key-here
railway variables set OPENAI_API_KEY=sk-your-monica-api-key-here
railway variables set OPENAI_API_BASE=https://openapi.monica.im/v1

# Railway最適化設定（Ollamaを使わない通常運用）
railway variables set EMBEDDER_PROVIDER=ollama
railway variables set EMBEDDER_MODEL=text-embedding-ada-002
railway variables set VECTOR_STORE_TYPE=local
railway variables set USE_MEM0=false
railway variables set OKAMI_LOG_LEVEL=INFO
```

### 3. デプロイ実行

```bash
railway up
```

補足: UI(Next.js)は Dockerfile のマルチステージビルドで自動ビルドされ、`/webui/static` に取り込まれます。Railway では `scripts/build-ui.sh` を実行する必要はありません。

### 4. ログの確認

```bash
# リアルタイムログの監視（終了は Ctrl+C）
railway logs

# デプロイ（起動）直後のログを直近200行だけ確認したい場合（ストリームを自動で切る）
# macOS等で `timeout` が無い場合でも `head` で安全に中断できます
railway logs --deployment | head -n 200
```

### 5. ヘルスチェック

デプロイ後、以下のエンドポイントで動作確認：

```bash
# アプリケーションURLを取得
railway status

# ヘルスチェック（API全体）
curl https://your-app-url.railway.app/health

# 埋め込みプロバイダ（Ollama）ヘルス
curl https://your-app-url.railway.app/api/embed/health

# Mem0 ヘルス（ENVベース）
curl https://your-app-url.railway.app/mem0/health
```

## Railway固有の制約と対策

### 1. 外部サービス依存の回避

**問題**: RailwayではDocker Composeが使えず、Ollama/ChromaDBの同一コンテナ起動は非推奨（モデルサイズ/リソース制約）

**対策**: OpenAI(Monica) Embedding と ChromaDB のローカル永続ストア(ライブラリ内蔵)を使用
- `EMBEDDER_PROVIDER=ollama`
- `VECTOR_STORE_TYPE=local`
- `USE_MEM0=false`

必要であれば、Railway プロジェクト内に「別サービス」として ChromaDB コンテナや Ollama を追加できますが、Ollama はモデルのサイズやディスク容量的に非推奨です。

### 2. ストレージの永続化

**問題**: Railwayの一時ファイルシステムはデプロイごとにリセット

**対策**: 
- 重要なデータは外部ストレージ（S3等）を検討
- 現在の設定では起動時に自動初期化

### 3. ポート設定

**自動対応済み**: 
- Railway の `$PORT` 環境変数を自動使用
- `config.py` と `Dockerfile` で対応完了

## トラブルシューティング

### デプロイが失敗する場合

```bash
# ビルドログの確認
railway logs --deployment | head -n 200

### 追加エンドポイント（運用確認用）
- `/api` … API ルート情報
- `/health` … アプリ全体のヘルス
- `/api/embed/health` … 埋め込み（Embedding）プロバイダのヘルス（Ollama / モデル名 / healthy）
- `/mem0/health` … Mem0 の接続確認（ENVベース有効化時）

# 現在の環境変数を確認
railway variables
```

### アプリケーションが起動しない場合

```bash
# リアルタイムログで原因を調査
railway logs

# よくある問題：
# 1. APIキーが未設定
# 2. 依存パッケージの問題
# 3. ファイルパーミッションエラー
```

### パフォーマンス問題

```bash
# リソース使用状況の確認
railway status

# 必要に応じてプランをアップグレード
railway deploy --help
```

## 本番環境の推奨設定

```bash
# セキュリティ
railway variables set OKAMI_LOG_LEVEL=INFO
railway variables set SERVER_RELOAD=false
railway variables set MONITOR_ENABLED=false

# パフォーマンス
railway variables set EMBEDDING_BATCH_SIZE=5
railway variables set DEFAULT_MAX_ITER=15
railway variables set DEFAULT_MAX_RETRIES=2

### Mem0 を ENV で有効化する場合
```bash
railway variables --set USE_MEM0=true \
  --set MEM0_API_KEY=*** \
  --set MEM0_USER_ID=okami_main_crew   # 任意
```

### ログ／ナレッジ／Chroma 永続化（単一ボリューム配下に集約）
- 既に `/app/storage` にボリュームをアタッチ済み。
- 代表的な環境変数:
  - `OKAMI_LOG_DIR=/app/storage/logs`
  - `KNOWLEDGE_DIR=/app/storage/knowledge`
  - `CHROMA_PERSIST_DIRECTORY=/app/storage/chroma`

### Chroma 書き込みタイムアウト緩和（リトライ制御）
以下の環境変数で retry/待機を調整できます（既定: 3回 / 0.2秒、指数バックオフ）。
```bash
railway variables --set CHROMA_ADD_MAX_RETRIES=5 \
  --set CHROMA_ADD_RETRY_INITIAL_DELAY=0.5 \
  --set CHROMA_QUERY_MAX_RETRIES=5 \
  --set CHROMA_QUERY_INITIAL_DELAY=0.5
```

## Ollama を Railway 上で有効化する（任意）

OKAMI は埋め込み（ベクトル化）に Ollama も利用できます。Railway 上でコンテナ内サイドカーとして `ollama serve` を起動できるよう Dockerfile と起動スクリプトを追加済みです。

注意点:
- モデルは大きくダウンロードに時間とストレージが必要です。Railway のファイルシステムは「デプロイごとにリセット」されるため、再デプロイのたびに再取得が必要です。
- 無料/小さなプランではメモリやCPUが不足する可能性があります。小さめモデルの利用を推奨します。

手順:

1) 環境変数を設定（Ollamaを有効化し、ローカル接続に切り替え）

```bash
railway variables set ENABLE_OLLAMA=true
railway variables set OLLAMA_BASE_URL=http://127.0.0.1:11434

# 埋め込みをOllamaに切替（軽量モデル推奨）
railway variables set EMBEDDER_PROVIDER=ollama
# 例: nomic-embed-text（軽量） or mxbai-embed-large（高品質だがサイズ大）
railway variables set EMBEDDER_MODEL=nomic-embed-text

# 初回起動時に自動pullしたいモデル（カンマ/スペース区切り）
# 例: 埋め込みのみ         → nomic-embed-text
#     LLMも試す（軽量）   → phi3:mini,qwen2.5:1.5b,llama3.2:1b
railway variables set OLLAMA_PULL_MODELS="nomic-embed-text"
```

2) デプロイ

```bash
railway up
railway logs --deployment | head -n 200
```

3) 動作確認

```bash
# Ollamaのタグ一覧（コンテナ内サイドカーに対して）
curl -fsS http://127.0.0.1:11434/api/tags || echo "not running"

# アプリの埋め込みヘルスチェックは以下エンドポイントで確認（簡易）
curl -fsS https://<your-app>.railway.app/api | jq . >/dev/null 2>&1 || true
```

ヒント:
- モデルの事前pullが長時間かかる場合、まずは `nomic-embed-text` のみで運用し、必要なときにLLMモデルを追加でpullしてください。
- モデルは `/app/storage/ollama` に保存され、同一デプロイ中はキャッシュされます（再デプロイで消えます）。
```

## ローカル環境との併用

Railway用の設定を追加しても、ローカル環境は影響を受けません：

- ローカル: `.env` ファイルを使用（Docker Composeでも動作）
- Railway: `railway.toml` と環境変数を使用

## 料金の最適化

- 不要な環境変数を削除
- ログレベルを `INFO` 以上に設定
- モニタリングを無効化（`MONITOR_ENABLED=false`）
- バッチサイズを調整してAPI呼び出し回数を最適化

## 参考リンク

- [Railway Documentation](https://docs.railway.app/)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
- [Monica API Documentation](https://openapi.monica.im/docs)
