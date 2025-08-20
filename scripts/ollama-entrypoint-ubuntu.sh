#!/bin/bash

# Ubuntu環境用の最適化されたOllama起動スクリプト

# CPUアフィニティの設定（パフォーマンス向上）
if command -v taskset &> /dev/null; then
    echo "Setting CPU affinity for better performance..."
    export GOMAXPROCS=4
fi

# Ollamaサーバーを起動（エラーがあっても続行）
echo "Starting Ollama server..."
ollama serve &
server_pid=$!

# サーバーの準備完了を待機（Ubuntu環境用に長めの待機時間）
echo "Waiting for Ollama server to be ready (this may take several minutes on Ubuntu)..."
MAX_WAIT=600  # 10分に延長
WAITED=0
RETRY_COUNT=0
MAX_RETRIES=120  # 120回リトライ（10分）

while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
    if curl -s --connect-timeout 5 http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama server is ready after ${WAITED}s"
        break
    fi
    
    # プロセスが生きているか確認
    if ! kill -0 $server_pid 2>/dev/null; then
        echo "Ollama server process died, restarting..."
        ollama serve &
        server_pid=$!
        sleep 10
    fi
    
    sleep 5
    WAITED=$((WAITED + 5))
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    # 進捗表示
    if [[ $((RETRY_COUNT % 12)) -eq 0 ]]; then
        echo "Still waiting... ${WAITED}s elapsed ($(($MAX_WAIT - $WAITED))s remaining)"
    fi
done

if [[ $RETRY_COUNT -ge $MAX_RETRIES ]]; then
    echo "Warning: Ollama server is taking longer than expected, but continuing..."
fi

# モデルが既に存在するか確認してからプル
# Ubuntu環境では軽量モデルを使用
MODEL="${OLLAMA_MODEL:-all-minilm:v2}"
echo "Checking for model '${MODEL}'..."

# モデル取得のリトライロジック
MODEL_RETRY=0
MODEL_MAX_RETRY=3

while [[ $MODEL_RETRY -lt $MODEL_MAX_RETRY ]]; do
    if ollama list 2>/dev/null | grep -q "${MODEL}"; then
        echo "Model '${MODEL}' already exists, skipping pull"
        break
    else
        echo "Pulling model '${MODEL}' (attempt $((MODEL_RETRY + 1))/${MODEL_MAX_RETRY})..."
        if ollama pull "${MODEL}" 2>&1; then
            echo "Model '${MODEL}' pulled successfully"
            break
        else
            echo "Failed to pull model, retrying..."
            MODEL_RETRY=$((MODEL_RETRY + 1))
            sleep 10
        fi
    fi
done

if [[ $MODEL_RETRY -ge $MODEL_MAX_RETRY ]]; then
    echo "Warning: Could not pull model after ${MODEL_MAX_RETRY} attempts, but server will continue"
fi

echo "Ollama service is running on port 11434"

# メモリ使用量の監視（デバッグ用）
if [[ "$OLLAMA_DEBUG" == "1" ]]; then
    while true; do
        if command -v free &> /dev/null; then
            echo "Memory status: $(free -h | grep Mem | awk '{print "Used: "$3" / Total: "$2}')"
        fi
        sleep 60
    done &
fi

# サーバープロセスを待機
wait $server_pid