#!/bin/bash

# Next.js UIのビルドスクリプト

echo "🚀 Next.js UIのビルドを開始します..."

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Next.jsアプリのディレクトリ
NEXTJS_DIR="$PROJECT_ROOT/webui/nextjs-chat"
STATIC_DIR="$PROJECT_ROOT/webui/static"

# Next.jsディレクトリに移動
cd "$NEXTJS_DIR"

# node_modulesをクリーンアップ
echo "🧹 古い依存関係をクリーンアップ中..."
rm -rf node_modules package-lock.json .next

# Node.js/npm環境確認
echo "🔍 Node.js環境確認中..."
node --version
npm --version

# npmキャッシュクリア（Ubuntu環境での問題対策）
echo "🧽 npmキャッシュをクリア中..."
npm cache clean --force

# 依存関係のインストール（Ubuntu環境向け最適化）
echo "📦 依存関係をインストール中..."
# レガシーピア依存解決オプションを追加
npm install --legacy-peer-deps --verbose || npm install --force --verbose

# TypeScript設定確認
echo "🔧 TypeScript設定確認中..."
if [ -f "tsconfig.json" ]; then
    echo "✅ tsconfig.json が見つかりました"
    # パス解決テスト
    npx tsc --noEmit --skipLibCheck
    if [ $? -ne 0 ]; then
        echo "⚠️  TypeScript型チェックで警告がありますが、ビルドを継続します"
    fi
else
    echo "❌ tsconfig.json が見つかりません"
    exit 1
fi

# ビルド実行（詳細ログ付き）
echo "🔨 Next.jsアプリをビルド中..."
NODE_OPTIONS="--max-old-space-size=4096" npm run build --verbose

# 静的ファイルをコピー
echo "📁 静的ファイルをコピー中..."
mkdir -p "$STATIC_DIR"

# デバッグ情報
echo "  📍 ソース: $NEXTJS_DIR/out/"
echo "  📍 宛先: $STATIC_DIR/"

# 古いファイルを削除
if [ -d "$STATIC_DIR" ]; then
    echo "  🧹 既存ファイルをクリーンアップ中..."
    rm -rf "$STATIC_DIR"/*
fi

# ファイルをコピー
if [ -d "$NEXTJS_DIR/out" ]; then
    echo "  📂 ファイルをコピー中..."
    cp -r "$NEXTJS_DIR/out/"* "$STATIC_DIR/" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✅ コピー成功"
    else
        echo "  ❌ コピー失敗"
        echo "  実行: cp -r $NEXTJS_DIR/out/* $STATIC_DIR/"
    fi
else
    echo "  ❌ エラー: outディレクトリが存在しません"
    exit 1
fi

echo "✅ ビルド完了！"
echo "📍 静的ファイルは $STATIC_DIR に配置されました"
echo ""
echo "🐳 次のステップ:"
echo "  docker-compose up -d"
echo "  ブラウザで http://localhost:8000 を開く"