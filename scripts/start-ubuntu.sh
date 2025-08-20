#!/bin/bash

# Ubuntu環境用の起動スクリプト

echo "Starting OKAMI on Ubuntu environment..."
echo "Using lightweight embedding model for better performance on Ubuntu"

# 環境変数ファイルの確認
if [ ! -f .env.production ]; then
    echo "Error: .env.production file not found!"
    echo "Please copy .env.example to .env.production and configure it."
    exit 1
fi

# Ubuntu用の環境変数ファイルの確認
if [ ! -f .env.production.ubuntu ]; then
    echo "Warning: .env.production.ubuntu file not found."
    echo "Using default Ubuntu settings..."
fi

# 既存のコンテナを停止
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yaml down

# Ollamaを先に起動してモデルをプリロード
echo "Starting Ollama service first..."
docker-compose -f docker-compose.prod.yaml up -d ollama

echo "Waiting for Ollama to be ready..."
sleep 30

# 軽量モデルをプリロード
echo "Preloading lightweight embedding model..."
docker exec okami-ollama ollama pull all-minilm:v2 || echo "Model pull failed, but continuing..."

# モデルの初期化（プリロード）
echo "Initializing model..."
docker exec okami-ollama ollama run all-minilm:v2 "test" || echo "Model initialization failed, but continuing..."

# 他のサービスを起動
echo "Starting all services..."
docker-compose -f docker-compose.prod.yaml up -d

# ヘルスチェック
echo "Waiting for services to be healthy..."
sleep 20

# サービスの状態確認
echo "Checking service status..."
docker-compose -f docker-compose.prod.yaml ps

# ログの確認
echo ""
echo "To view logs, run:"
echo "  docker-compose -f docker-compose.prod.yaml logs -f"
echo ""
echo "To check OKAMI health:"
echo "  curl http://localhost:8000/health"
echo ""
echo "OKAMI is starting on Ubuntu with lightweight embedding model (all-minilm:v2)"