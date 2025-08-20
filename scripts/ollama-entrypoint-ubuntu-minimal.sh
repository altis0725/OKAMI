#!/bin/bash

# ================================================================
# Ubuntu超低メモリ環境用Ollama起動スクリプト
# 対象環境: 物理メモリ1GB + スワップ4GB
# ================================================================

echo "========================================"
echo "Starting Ollama for Minimal Memory Environment"
echo "Target: 1GB RAM + 4GB Swap"
echo "========================================"

# スワップの確認と最適化
if [[ -f /proc/sys/vm/swappiness ]]; then
    echo "Checking swap configuration..."
    free -h
fi

# システムリソースの超最適化
echo "Applying extreme memory optimizations..."

# ファイルディスクリプタを最小限に
ulimit -n 1024

# コアダンプを無効化（メモリ節約）
ulimit -c 0

# スタックサイズを制限
ulimit -s 8192

# 環境変数の設定（超省メモリモード）
export GOGC=10  # ガベージコレクションを頻繁に実行
export GOMEMLIMIT=256MiB  # Goのメモリ使用量を256MBに制限
export GOMAXPROCS=1  # CPUコアを1つのみ使用

# Ollama用の最小限設定
export OLLAMA_HOST=0.0.0.0
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=30s  # 30秒でアンロード
export OLLAMA_NOPREALLOCATE=1
export OLLAMA_NUM_THREADS=1

# 最軽量モデルの設定
MODEL="${OLLAMA_MODEL:-nomic-embed-text:v1.5}"  # 137MBの最軽量モデル
echo "Using minimal model: ${MODEL}"

# Ollamaサーバーの起動（超低優先度で）
echo "Starting Ollama server with minimal resources..."
nice -n 19 ollama serve &
server_pid=$!

# 初期待機（スワップ使用を考慮して長めに）
echo "Waiting for initial startup (this will be slow due to swap usage)..."
sleep 30

# ヘルスチェック関数（長めのタイムアウト）
check_ollama_health() {
    timeout 30 curl -s --connect-timeout 20 --max-time 30 \
        http://localhost:11434/api/tags > /dev/null 2>&1
    return $?
}

# 起動確認（超寛容な待機）
MAX_WAIT=1800  # 30分
WAITED=0
CHECK_INTERVAL=15  # 15秒ごとにチェック

echo "Checking server status (may take up to 30 minutes)..."
while [[ $WAITED -lt $MAX_WAIT ]]; do
    if check_ollama_health; then
        echo "✓ Ollama server is responding after ${WAITED}s"
        break
    fi
    
    # プロセス確認
    if ! kill -0 $server_pid 2>/dev/null; then
        echo "Server process died. Restarting with even lower resources..."
        
        # さらにメモリ制限を強化
        export GOMEMLIMIT=128MiB
        
        nice -n 19 ollama serve &
        server_pid=$!
        sleep 30
    fi
    
    sleep $CHECK_INTERVAL
    WAITED=$((WAITED + CHECK_INTERVAL))
    
    # 進捗表示（5分ごと）
    if [[ $((WAITED % 300)) -eq 0 ]]; then
        echo "Still waiting... ${WAITED}s elapsed"
        
        # メモリ状況の確認
        if command -v free &> /dev/null; then
            echo "Memory status:"
            free -h | head -3
        fi
    fi
done

# モデルの管理（超慎重モード）
echo "========================================="
echo "Model Management"
echo "========================================="

# 既存モデルのクリーンアップ（メモリ確保）
echo "Cleaning up old models to save memory..."
if ollama list 2>/dev/null | grep -v "${MODEL}" | grep -v "NAME"; then
    echo "Removing unused models..."
    for old_model in $(ollama list 2>/dev/null | grep -v "${MODEL}" | grep -v "NAME" | awk '{print $1}'); do
        echo "Removing: $old_model"
        ollama rm "$old_model" 2>/dev/null || true
    done
fi

# モデルのダウンロード（必要な場合のみ）
MODEL_EXISTS=false
if timeout 30 ollama list 2>/dev/null | grep -q "${MODEL}"; then
    echo "✓ Model '${MODEL}' already exists"
    MODEL_EXISTS=true
else
    echo "Model '${MODEL}' not found. Will download on first use."
    echo "WARNING: First embedding request will be very slow!"
fi

# モデルのダウンロード（スワップ使用を前提）
if [[ "$MODEL_EXISTS" == "false" ]]; then
    echo "Attempting to download model (this will use swap heavily)..."
    
    # メモリをクリア
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    
    # ダウンロード試行（超長時間タイムアウト）
    if timeout 1800 ollama pull "${MODEL}" 2>&1; then
        echo "✓ Model downloaded successfully"
    else
        echo "⚠ Model download failed or timed out"
        echo "  The model will be downloaded on first use"
        echo "  First request will be VERY slow!"
    fi
fi

# 最小限のプリロード試行（オプション）
if [[ "$MODEL_EXISTS" == "true" ]] || [[ "$OLLAMA_PRELOAD" == "true" ]]; then
    echo "Attempting minimal model preload..."
    if timeout 120 ollama run "${MODEL}" "test" 2>/dev/null; then
        echo "✓ Model preloaded"
    else
        echo "⚠ Preload skipped to save memory"
    fi
fi

echo "========================================="
echo "Ollama Status"
echo "========================================="
echo "Server: Running on port 11434"
echo "Model: ${MODEL} (137MB minimal embeddings)"
echo "Memory: 1GB physical + 4GB swap"
echo "Mode: Ultra-low memory consumption"
echo "========================================="

# メモリモニタリング（軽量版）
if [[ "${OLLAMA_MONITOR}" == "1" ]]; then
    (
        while true; do
            # 簡易メモリチェック
            if command -v free &> /dev/null; then
                MEM_INFO=$(free -m | awk 'NR==2 {printf "RAM: %dMB/%dMB ", $3, $2}')
                SWAP_INFO=$(free -m | awk 'NR==3 {printf "Swap: %dMB/%dMB", $3, $2}')
                echo "[$(date +%H:%M:%S)] ${MEM_INFO} | ${SWAP_INFO}"
            fi
            sleep 300  # 5分ごと
        done
    ) &
fi

# クリーンシャットダウン
trap "echo 'Shutting down...'; kill $server_pid 2>/dev/null; exit 0" SIGTERM SIGINT

# プロセス待機
echo "Ready for embedding requests (expect slow performance)"
wait $server_pid