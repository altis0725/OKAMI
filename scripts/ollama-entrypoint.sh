#!/bin/bash

# Ollamaサーバーを起動（エラーがあっても続行）
ollama serve &
server_pid=$!

# サーバーの準備完了を待機
echo "Waiting for Ollama server to be ready..."
MAX_WAIT=60
WAITED=0
while ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        echo "Warning: Ollama server might take longer to start, continuing anyway..."
        # exit 1を削除し、警告のみ表示
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    echo "Waiting... ${WAITED}s"
done

# サーバーがレスポンスを返すか最終確認
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama server is ready"
else
    echo "Ollama server is still starting up, but continuing..."
fi

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