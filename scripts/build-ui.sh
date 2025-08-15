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
rm -rf node_modules package-lock.json

# 依存関係のインストール
echo "📦 依存関係をインストール中..."
npm install

# ビルド実行
echo "🔨 Next.jsアプリをビルド中..."
npm run build

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