# Repository Guidelines

## Project Structure & Module Organization
- `config/`: YAML for `agents/`, `tasks/`, `crews/` (runtime behavior).
- `core/`: core managers (memory, knowledge, guardrails).
- `crews/`: CrewAI integration (`crew_factory.py`).
- `evolution/`: auto-improvement parser/applier + `backups/`.
- `monitoring/`: Claude Code quality monitor.
- `knowledge/`, `storage/`, `logs/`: data, persistence, and logs.
- `tests/`: pytest suite; see many `test_*` files.
- Entry: `main.py` (FastAPI), Docker: `docker-compose.yaml`.

## Build, Test, and Development Commands
- Install (Poetry): `poetry install` (Python 3.11).
- Run API: `poetry run uvicorn main:app --reload` (http://localhost:8000/health).
- Tests: `poetry run pytest -q` or `pytest tests/test_evolution_flow.py -q`.
- Coverage: `poetry run pytest --cov=okami --cov-report=term-missing`.
- Lint/format: `poetry run black . && poetry run isort . && poetry run flake8 && poetry run mypy .`.
- Docker (full stack): `docker-compose up -d` (API on 8000, ChromaDB on 8001, Ollama on 11434). Validate: `curl :8000/health`.

## Coding Style & Naming Conventions
- Formatting: Black (line length 88) + isort (profile=black).
- Linting: flake8; typing via mypy (disallow untyped defs).
- Indentation: 4 spaces; Python 3.11 features allowed.
- Naming: modules/files `lower_snake_case.py`; functions/vars `snake_case`; classes `PascalCase`.
- Config: place crew/agent/task YAML in `config/{crews,agents,tasks}/` with descriptive names (e.g., `main_crew.yaml`).

## Testing Guidelines
- Framework: pytest (+ pytest-asyncio, pytest-cov). Tests live in `tests/`, named `test_*.py`.
- Run subset: `pytest tests/test_json_evolution_parser.py -q`.
- Aim for meaningful coverage of core flows (crews, evolution, knowledge). Target ≥80% where practical.
- Keep tests deterministic; use fixtures and avoid network I/O.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits (e.g., `feat: ...`, `fix: ...`, `refactor: ...`).
- PRs: clear description, linked issue, reproduction steps, and impact. Include screenshots/log snippets for UI/monitoring changes.
- Requirements: passing tests and linters; update docs (`README.md`, `knowledge/`) when behavior or APIs change.

## Security & Configuration Tips
- Never commit secrets. Copy `.env.example` to `.env` and set keys (e.g., `MONICA_API_KEY`).
- Default vector store: ChromaDB; embeddings: Ollama `mxbai-embed-large` (see `docker-compose.yaml`).
- Persistent data lives in `storage/` and `logs/`; review before sharing.

## CrewAI + LLM/Embedder 設計方針（重要）
- 既定の LLM は Monica（OpenAI 互換）を使用します。コード側（`crews/crew_factory.py`）の LLM 設定を安易に変更しないでください。
- 埋め込み（Embeddings）は CrewAI の `embedder` 設定で明示的に上書きして使用します（RAG/Knowledge 用）。
- CrewAI 公式ドキュメントでは `provider: "ollama"` もサポートされています（例：`{"provider":"ollama","config":{"model":"mxbai-embed-large","url":"http://localhost:11434/api/embeddings"}}`）。
- ただし、CrewAI のバージョンや ExternalMemory（mem0）初期化の差異により、`Crew(**config)` 時に `embedder` の厳格バリデーションで失敗するケースがあります。その場合は以下を徹底：
  - Crew 構築時の `embedder` は一旦外し（未設定）、KnowledgeManager/Storage 側で embedding を行う。
  - ExternalMemory（mem0）は CrewAI のバージョン差異に対応（新仕様：`memory_config`、旧仕様：`embedder_config.provider="mem0"`）。
- Railway では、Ollama は別サービスとしてデプロイし、OKAMI からは内部ネットワークで到達させます。外部公開は不要です。

### Railway での埋め込み（Ollama）設定
- Ollama サービス（テンプレート推奨）を同一プロジェクト・同一環境に追加し、内部ホスト名 `ollama.railway.internal` を使用します。
- OKAMI 側の環境変数例（Crew に直接 `embedder` を渡さない運用でも、下記は内部の埋め込み呼び出し用に参照されます）:
  - `EMBEDDER_PROVIDER=ollama`
  - `EMBEDDER_MODEL=mxbai-embed-large`
  - `OLLAMA_BASE_URL=http://ollama.railway.internal:11434`
  - `ENABLE_OLLAMA=false`（OKAMI コンテナ内で Ollama を起動しない）
- 任意: `/api/embed/health` で埋め込みの簡易ヘルスを確認できます。

### Ollama（別サービス側）でのモデル準備
- 例: `gemma3:1b`（LLM）, `mxbai-embed-large`（埋め込み）
- テンプレの環境変数や起動時スクリプトでプリフェッチ設定、またはシェルで `ollama pull gemma3:1b` / `ollama pull mxbai-embed-large` を実行。
- 外部公開は避け、Railway 内部ルーティングのみ（`*.railway.internal`）。

## 使用可能な MCP サーバ（ツール）
- Context7 Docs（ライブラリドキュメント取得）
  - `resolve-library-id` → `get-library-docs`（CrewAI の LLM/Knowledge の公式ドキュメント参照に使用）
- Brave 検索系
  - `brave_web_search`（一般検索） / `brave_summarizer`（要約） / `brave_image_search`（画像） / `brave_news_search` / `brave_video_search`
- GitHub/デプロイ補助（docker-mcp-toolkit）
  - `railway` 関連コマンドはローカル CLI 経由で実行。ログは `| head -n N` 等でトリミング（無限ストリームを避ける）。
  - GitHub 操作、ファイル操作、CI 取得などは `docker-mcp-toolkit__*` を参照。

## 変更方針（守ってほしいこと）
- LLM（Monica）の既定を崩さない。必要な場合は PR で合意を得てから。
- Embeddings のみを Ollama に寄せる場合、CrewAI の推奨に従い `embedder` 設定で上書きする（参照: CrewAI docs “Customize CrewAI Knowledge Embeddings with Local Ollama”）。
- 重大な挙動変更・依存追加は AGENTS.md と README に必ず追記。

## 調査/参照ポリシー（MCPの活用）
- コマンドや挙動が不明な場合、または詰まった場合は、以下のMCPを使って必ず一次情報を確認してください（必須）。
  - Context7: `resolve-library-id` → `get-library-docs`（CrewAI, 依存ライブラリの公式ドキュメント）
  - Brave: `brave_web_search` / `brave_summarizer`（最新の手順・テンプレ確認）
- 参照結果に基づき、推測で設定変更せず、根拠（URL）と差分の意図をPRに明記してください。
