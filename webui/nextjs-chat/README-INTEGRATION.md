# OKAMI Next.js UI 統合ガイド

Next.jsアプリをOKAMI FastAPIサーバー（http://localhost:8000）と統合する手順です。

## アーキテクチャ概要

```
ユーザー → http://localhost:8000 → FastAPI
                                    ├── / → Next.js UI (静的ファイル)
                                    ├── /api/* → OKAMI API
                                    ├── /_next/* → Next.js静的リソース
                                    └── /health → ヘルスチェック
```

## セットアップ手順

### 1. 開発環境でのビルドとテスト

```bash
# Next.jsアプリのディレクトリに移動
cd webui/nextjs-chat

# 依存関係のインストール
npm install

# 開発サーバーで動作確認
npm run dev
# → http://localhost:3000 で確認

# 本番ビルド
npm run build

# OKAMIディレクトリに静的ファイルをコピー
npm run copy-to-okami
```

### 2. 自動ビルドスクリプトの使用

```bash
# プロジェクトルートから実行
./scripts/build-ui.sh
```

### 3. FastAPIサーバーで動作確認

```bash
# OKAMIサーバーを起動
python main.py

# ブラウザで確認
# http://localhost:8000 → Next.js UI
# http://localhost:8000/api → API情報
# http://localhost:8000/health → ヘルスチェック
```

## Docker環境での利用

### 開発環境

```bash
# 通常通りDocker Composeで起動
docker-compose up -d

# UIは自動的にビルドされてhttp://localhost:8000で利用可能
```

### 本番環境

```bash
# 本番環境でのデプロイ
docker-compose -f docker-compose.prod.yaml up -d

# Nginx経由でhttps://traning.workでアクセス
```

## 設定ファイル

### `next.config.ts`
- `output: 'export'`: 静的エクスポートを有効化
- `images.unoptimized: true`: 画像最適化を無効化（静的エクスポート用）

### `main.py`
- Next.js静的ファイルのマウント
- SPAルーティング対応（catch-all route）
- APIとUIの適切な分離

### `Dockerfile`
- Node.js 20のインストール
- Next.jsの自動ビルド
- 静的ファイルの配置

## API統合

Next.jsアプリは以下のAPI構造でOKAMIバックエンドと通信します：

```typescript
// src/app/api/chat/route.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

// POSTリクエスト: チャット処理
fetch(`${API_BASE}/tasks`, {
  method: 'POST',
  body: JSON.stringify({
    crew_name: 'main_crew',
    task: message,
    async_execution: false
  })
});

// GETリクエスト: ヘルスチェック
fetch(`${API_BASE}/health`);
```

## トラブルシューティング

### UIが表示されない場合

1. ビルドが完了しているか確認：
   ```bash
   ls -la webui/dist/
   ```

2. FastAPIのログを確認：
   ```bash
   docker-compose logs okami
   ```

3. 手動ビルドを実行：
   ```bash
   ./scripts/build-ui.sh
   ```

### API接続エラーの場合

1. バックエンドのヘルスチェック：
   ```bash
   curl http://localhost:8000/health
   ```

2. CORSエラーの場合、`main.py`のCORS設定を確認

3. ネットワーク設定を確認：
   ```bash
   docker network ls
   docker network inspect okami_okami-network
   ```

## パフォーマンス最適化

### 静的ファイルキャッシュ
- FastAPIの`StaticFiles`により自動的にキャッシュヘッダーが設定
- Nginxによる追加キャッシュ（本番環境）

### Bundle Size最適化
- Next.js 15の最新機能を活用
- TurbopackとReact 19による高速化
- 不要な依存関係の削除

## セキュリティ考慮事項

### CORS設定
- 開発環境: `allow_origins=["*"]`
- 本番環境: 特定ドメインのみ許可を推奨

### CSP (Content Security Policy)
- Nginx設定で基本的なCSPを実装済み
- 追加カスタマイズが必要な場合は`nginx.prod.conf`を編集

## 今後の拡張案

### リアルタイム機能
- WebSocketサポートの追加
- Server-Sent Events (SSE) の実装

### PWA対応
- Service Workerの追加
- オフライン機能の実装

### 多言語対応
- i18nサポートの追加
- 動的言語切り替え

---

## 関連ファイル

- `/Users/altis/Documents/crewAI/OKAMI/main.py` - FastAPIサーバー設定
- `/Users/altis/Documents/crewAI/OKAMI/webui/nextjs-chat/next.config.ts` - Next.js設定
- `/Users/altis/Documents/crewAI/OKAMI/Dockerfile` - Docker設定
- `/Users/altis/Documents/crewAI/OKAMI/scripts/build-ui.sh` - ビルドスクリプト