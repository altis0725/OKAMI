# Phase 4 - タスク4: UI改善 最終統合作業

## 実施日
2025-08-15（続き）

## 追加実施内容

### 1. レスポンス表示問題の修正

#### 問題点
- APIからのレスポンスがUIに表示されない
- セッション管理の不具合

#### 修正内容
1. **デバッグログの追加** (`src/app/page.tsx`)
   - セッション更新時の詳細ログ
   - メッセージ数の追跡
   - currentSessionの監視

2. **Stageswiseコンポーネントの無効化**
   - IDEツールバーエラーの解消
   - 不要な開発ツールの削除

### 2. http://localhost:8000での統合

#### 実装方法
**静的ファイル配信方式を採用**

#### 主な変更

##### 1. ビルドスクリプト (`scripts/build-ui.sh`)
```bash
#!/bin/bash
# Next.jsアプリをビルドして静的ファイルを生成
npm install
npm run build
cp -r out/* ../static/
```

##### 2. FastAPI設定 (`main.py`)
```python
# 静的ファイルのマウント
webui_static = Path(__file__).parent / "webui" / "static"
webui_nextjs_out = Path(__file__).parent / "webui" / "nextjs-chat" / "out"

# Next.js静的ファイルの配信
if webui_static.exists():
    app.mount("/_next", StaticFiles(directory=str(nextjs_static)), name="nextjs_static")
    app.mount("/static", StaticFiles(directory=str(webui_static)), name="static_files")

# ルートパスでindex.htmlを提供
@app.get("/", response_class=FileResponse)
async def serve_app():
    if webui_static.exists():
        nextjs_index = webui_static / "index.html"
        if nextjs_index.exists():
            return FileResponse(nextjs_index)
```

##### 3. Next.js設定 (`next.config.ts`)
```typescript
const nextConfig: NextConfig = {
  output: 'export',  // 静的エクスポート
  images: {
    unoptimized: true  // 静的サイト用
  },
  trailingSlash: true
};
```

### 3. 既存ファイルの削除

- ✅ `webui/chat.html` - 削除完了
- Next.js UIに完全移行

## 使用手順

### 開発環境

#### 方法1: 静的ビルド + FastAPI配信
```bash
# 1. Next.jsをビルド
./scripts/build-ui.sh

# 2. OKAMIサーバー起動
docker-compose up -d

# 3. アクセス
# http://localhost:8000
```

#### 方法2: 開発モード（別ポート）
```bash
# 1. Next.js開発サーバー
cd webui/nextjs-chat
npm run dev  # http://localhost:3000

# 2. OKAMIバックエンド
docker-compose up -d  # http://localhost:8000
```

### 本番環境
```bash
# Dockerコンテナ内で自動ビルド
docker-compose -f docker-compose.prod.yaml up -d
```

## トラブルシューティング

### Stageswiseエラー
```
The stagewise toolbar isn't connected to any IDE window
```
**解決方法**: 
- layout.tsxでStagewiseClientコンポーネントをコメントアウト済み
- 必要に応じて`npm uninstall @stagewise-plugins/react`を実行

### レスポンスが表示されない
**確認事項**:
1. ブラウザのコンソールでデバッグログを確認
2. Network タブでAPI通信を確認
3. OKAMIバックエンドが起動しているか確認

### ビルドエラー
```bash
# node_modulesの権限問題
chmod +x node_modules/.bin/*

# 再インストール
rm -rf node_modules package-lock.json
npm install
```

## アーキテクチャの利点

1. **単一ポート構成**
   - http://localhost:8000ですべて完結
   - CORSの問題を回避

2. **段階的移行**
   - 開発時は別ポートで並行開発可能
   - 本番は統合された単一サービス

3. **パフォーマンス**
   - FastAPIによる高速な静的ファイル配信
   - Next.jsの静的最適化

4. **保守性**
   - フロントエンドとバックエンドの明確な分離
   - ビルドプロセスの自動化

## 残作業

### nginx設定（本番環境）
- 現状のnginx設定は変更不要
- FastAPIがすべてのルーティングを処理

## 成果物

### 新規/更新ファイル
- ✅ `scripts/build-ui.sh` - ビルドスクリプト
- ✅ `main.py` - 静的ファイル配信設定
- ✅ `webui/nextjs-chat/src/app/page.tsx` - デバッグログ追加
- ✅ `webui/nextjs-chat/next.config.ts` - 静的エクスポート設定

### 削除ファイル
- ✅ `webui/chat.html` - 旧UI削除

## まとめ

Phase 4 タスク4の追加作業により、Next.js UIはOKAMIバックエンドと完全に統合され、http://localhost:8000で単一サービスとして動作するようになりました。

主な成果：
1. ✅ レスポンス表示のデバッグ機能追加
2. ✅ 単一ポート（8000）での統合完了
3. ✅ 旧UIの削除と完全移行
4. ✅ ビルドプロセスの自動化

これにより、ユーザーは従来通りhttp://localhost:8000にアクセスするだけで、モダンなNext.js UIを利用できます。