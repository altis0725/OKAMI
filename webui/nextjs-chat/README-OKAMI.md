# OKAMI Next.js Chat UI - 統合ガイド

## 概要

このNext.jsアプリケーションは、OKAMIシステムのためのモダンなチャットインターフェースです。現在、OKAMIバックエンドとの統合が実装されています。

## 統合状況

### ✅ 実装済み機能

- **APIルート統合** (`/api/chat`)
  - OKAMIバックエンドとの通信
  - エラーハンドリング
  - ヘルスチェックエンドポイント

- **チャット機能**
  - メッセージ送信
  - レスポンス表示
  - エラーメッセージ表示（赤色背景）
  - メタデータ保存（task_id、実行時間など）

- **環境設定**
  - `.env.local`でバックエンドURL設定可能
  - デフォルト: `http://localhost:8000`

### ❌ 未実装機能（チャット履歴を除く）

- ストリーミングレスポンス
- ファイルアップロード（UIのみ実装済み）
- 音声入力（UIのみ実装済み）
- チャットのエクスポート/インポート

## セットアップ手順

### 1. OKAMIバックエンドの起動

```bash
# OKAMIのルートディレクトリで
docker-compose up -d
```

### 2. Next.jsアプリケーションのセットアップ

```bash
# このディレクトリ（webui/nextjs-chat）で
npm install
```

### 3. 環境設定（必要に応じて）

`.env.local`ファイルを編集：

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 4. 開発サーバーの起動

```bash
npm run dev
```

### 5. アプリケーションへのアクセス

ブラウザで [http://localhost:3000](http://localhost:3000) を開く

## 使用方法

1. **新しいチャットの開始**
   - サイドバーの「新しいチャット」ボタンをクリック
   - または直接メッセージを入力

2. **メッセージの送信**
   - テキスト入力欄にメッセージを入力
   - Enterキーまたは送信ボタンをクリック

3. **レスポンスの確認**
   - OKAMIシステムからの応答が表示される
   - エラーの場合は赤色の背景で表示

## API仕様

### POST /api/chat

リクエスト:
```json
{
  "message": "ユーザーのメッセージ"
}
```

レスポンス:
```json
{
  "content": "AIの応答内容",
  "metadata": {
    "task_id": "タスクID",
    "status": "completed",
    "created_at": "2025-01-15T12:00:00Z",
    "execution_time": 1.234
  }
}
```

### GET /api/chat

ヘルスチェック用エンドポイント

## トラブルシューティング

### バックエンドに接続できない場合

1. **OKAMIバックエンドの確認**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Docker コンテナの状態確認**
   ```bash
   docker ps | grep okami
   ```

3. **ログの確認**
   ```bash
   docker-compose logs -f okami
   ```

### エラーメッセージが表示される場合

- 「バックエンドサーバーが起動していることを確認してください」
  → OKAMIバックエンドが起動していない可能性があります

- ネットワークエラー
  → `.env.local`のAPI_BASE URLが正しいか確認してください

## 開発のヒント

### バックエンドAPIのテスト

```bash
# 直接APIをテスト
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"crew_name": "main_crew", "task": "テストメッセージ", "async_execution": false}'
```

### Next.jsのログ確認

開発サーバーのコンソールでエラーやAPIコールのログを確認できます。

### ブラウザのデベロッパーツール

- Network タブ: API通信の確認
- Console タブ: JavaScriptエラーの確認

## プロダクション環境での実行

### ビルド

```bash
npm run build
```

### プロダクションサーバーの起動

```bash
npm start
```

### PM2での実行（推奨）

```bash
# PM2のインストール
npm install -g pm2

# アプリケーションの起動
pm2 start npm --name "okami-chat" -- start

# ログの確認
pm2 logs okami-chat
```

## Dockerでの実行

```dockerfile
# Dockerfile
FROM node:20-alpine

WORKDIR /app

# 依存関係のコピーとインストール
COPY package*.json ./
RUN npm ci --only=production

# アプリケーションのコピー
COPY . .

# ビルド
RUN npm run build

# ポート公開
EXPOSE 3000

# 起動
CMD ["npm", "start"]
```

```bash
# Dockerイメージのビルド
docker build -t okami-chat .

# コンテナの実行
docker run -p 3000:3000 --env-file .env.local okami-chat
```

## 今後の改善案

1. **ストリーミングレスポンス**
   - Server-Sent Events (SSE) の実装
   - リアルタイムでの応答表示

2. **ファイルアップロード**
   - 実際のファイル処理実装
   - バックエンドへの送信

3. **パフォーマンス最適化**
   - React.memo の活用
   - 仮想スクロールの実装（大量メッセージ対応）

4. **セキュリティ強化**
   - CSRF対策
   - レート制限
   - 入力検証の強化