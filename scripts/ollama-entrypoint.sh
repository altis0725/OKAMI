#!/bin/bash

# Ollamaサーバーを起動（エラーがあっても続行）
ollama serve &
server_pid=$!

# サーバーの準備完了を待機（改良版）
echo "Waiting for Ollama server to be ready..."

# 関数: APIの実際のレスポンスをチェック
check_api_health() {
    local endpoint="$1"
    local response
    local exit_code
    
    response=$(curl -s --connect-timeout 3 --max-time 8 "http://localhost:11434${endpoint}" 2>&1)
    exit_code=$?
    
    echo "DEBUG: Endpoint ${endpoint}, Exit code: ${exit_code}, Response: ${response:0:100}..."
    
    # exit codeが0でレスポンスにJSONが含まれていれば成功
    if [[ $exit_code -eq 0 ]] && [[ "$response" =~ ^\{.*\}$ ]]; then
        return 0
    else
        return 1
    fi
}

# ポートの確認
echo "Step 1: Checking if port 11434 is open..."
WAITED=0
while ! ss -tln | grep -q ":11434 "; do
    if [[ $WAITED -ge 30 ]]; then
        echo "Warning: Port 11434 not bound after 30s, but continuing..."
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "Waiting for port binding... ${WAITED}s"
done

# API応答の確認
echo "Step 2: Checking API responses..."
WAITED=0
while true; do
    # /api/version を先にチェック（軽量）
    if check_api_health "/api/version"; then
        echo "✓ Version endpoint is responding"
        
        # 次に /api/tags をチェック
        if check_api_health "/api/tags"; then
            echo "✓ Tags endpoint is responding - Server fully ready!"
            break
        else
            echo "- Version OK, but tags not ready yet..."
        fi
    else
        echo "- API not responding yet..."
    fi
    
    if [[ $WAITED -ge 90 ]]; then
        echo "⚠ API check timeout after 90s - continuing anyway"
        # 最後にもう一度確認
        if check_api_health "/api/version" || check_api_health "/api/tags"; then
            echo "✓ At least one endpoint is working"
        fi
        break
    fi
    
    sleep 5
    WAITED=$((WAITED + 5))
    echo "Waited ${WAITED}s for API..."
done

# モデルが既に存在するか確認してからプル
MODEL="mxbai-embed-large"
# サーバーが完全に起動するまで少し待つ
sleep 5

if ollama list 2>/dev/null | grep -q "${MODEL}"; then
    echo "Model '${MODEL}' already exists, skipping pull"
else
    echo "Pulling model '${MODEL}'..."
    # モデルのプルに失敗してもサーバーは継続
    ollama pull "${MODEL}" || echo "Warning: Failed to pull model, but continuing..."
fi

echo "Ollama service is running on port 11434"

# サーバープロセスを待機
wait $server_pid