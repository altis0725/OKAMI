#!/bin/bash

# Ubuntu環境用の最適化されたOllama起動スクリプト（タイムアウト対策版）

# システムリソースの最適化
echo "Optimizing system resources for Ubuntu environment..."

# ulimitの設定（ファイルディスクリプタとメモリ制限）
ulimit -n 65536
ulimit -v unlimited 2>/dev/null || true

# CPUアフィニティの設定（パフォーマンス向上）
if command -v taskset &> /dev/null; then
    echo "Setting CPU affinity for better performance..."
    export GOMAXPROCS=2  # CPU使用を2コアに制限
fi

# メモリスワップ設定の確認
if [[ -f /proc/sys/vm/swappiness ]]; then
    echo "Current swappiness: $(cat /proc/sys/vm/swappiness)"
fi

# Ollamaサーバーを起動（エラーがあっても続行）
echo "Starting Ollama server with optimized settings..."

# 環境変数の設定（メモリ効率化）
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=5m  # メモリ節約のため短縮
export OLLAMA_HOST=0.0.0.0

# バックグラウンドでOllamaを起動
ollama serve &
server_pid=$!

# サーバーの準備完了を待機（段階的な待機）
echo "Waiting for Ollama server to be ready..."

# 初期待機（Ollamaプロセスの起動を確実にする）
sleep 10

# ヘルスチェック関数
check_ollama_health() {
    curl -s --connect-timeout 10 --max-time 15 http://localhost:11434/api/tags > /dev/null 2>&1
    return $?
}

# 段階的な待機ロジック
STAGE=1
MAX_STAGES=3
TOTAL_WAITED=0

while [[ $STAGE -le $MAX_STAGES ]]; do
    echo "Stage ${STAGE}/${MAX_STAGES}: Checking Ollama server status..."
    
    # 各ステージで異なる待機時間
    case $STAGE in
        1)
            MAX_ATTEMPTS=20  # 20 * 3 = 60秒
            SLEEP_TIME=3
            ;;
        2)
            MAX_ATTEMPTS=20  # 20 * 5 = 100秒
            SLEEP_TIME=5
            ;;
        3)
            MAX_ATTEMPTS=20  # 20 * 10 = 200秒
            SLEEP_TIME=10
            ;;
    esac
    
    ATTEMPT=0
    while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
        if check_ollama_health; then
            echo "✓ Ollama server is ready after ${TOTAL_WAITED}s"
            break 2  # 両方のループを抜ける
        fi
        
        # プロセスが生きているか確認
        if ! kill -0 $server_pid 2>/dev/null; then
            echo "⚠ Ollama server process died, restarting with reduced resources..."
            
            # メモリ制限をさらに厳しくして再起動
            export OLLAMA_NUM_THREADS=2
            export OLLAMA_MAX_QUEUE=1
            
            ollama serve &
            server_pid=$!
            sleep 15  # 再起動後は長めに待機
        fi
        
        sleep $SLEEP_TIME
        TOTAL_WAITED=$((TOTAL_WAITED + SLEEP_TIME))
        ATTEMPT=$((ATTEMPT + 1))
        
        # 進捗表示
        if [[ $((ATTEMPT % 5)) -eq 0 ]]; then
            echo "  Stage ${STAGE}: Attempt ${ATTEMPT}/${MAX_ATTEMPTS} (${TOTAL_WAITED}s elapsed)"
        fi
    done
    
    STAGE=$((STAGE + 1))
    
    if [[ $STAGE -le $MAX_STAGES ]]; then
        echo "Moving to stage ${STAGE} with longer timeouts..."
    fi
done

# 最終確認
if ! check_ollama_health; then
    echo "⚠ WARNING: Ollama server is not responding after ${TOTAL_WAITED}s"
    echo "  The server will continue running in the background."
    echo "  It may become available later."
fi

# モデルのダウンロードと管理
MODEL="${OLLAMA_MODEL:-mxbai-embed-large}"
echo "Managing model '${MODEL}'..."

# モデルサイズの確認とメモリ容量のチェック
check_memory_for_model() {
    if command -v free &> /dev/null; then
        AVAILABLE_MEM=$(free -m | awk 'NR==2 {print $7}')
        echo "Available memory: ${AVAILABLE_MEM}MB"
        
        # mxbai-embed-largeは約640MBなので、最低1GBの空きメモリが必要
        if [[ $AVAILABLE_MEM -lt 1024 ]]; then
            echo "⚠ Low memory detected. Switching to lighter model..."
            MODEL="all-minilm:v2"  # より軽量なモデルに切り替え
            export OLLAMA_MODEL=$MODEL
            return 1
        fi
    fi
    return 0
}

# メモリチェック
if ! check_memory_for_model; then
    echo "Using lightweight model: ${MODEL}"
fi

# モデル取得のリトライロジック（タイムアウト付き）
MODEL_RETRY=0
MODEL_MAX_RETRY=3

while [[ $MODEL_RETRY -lt $MODEL_MAX_RETRY ]]; do
    # 既存モデルのチェック（タイムアウト付き）
    if timeout 10 ollama list 2>/dev/null | grep -q "${MODEL}"; then
        echo "✓ Model '${MODEL}' already exists"
        break
    else
        echo "Pulling model '${MODEL}' (attempt $((MODEL_RETRY + 1))/${MODEL_MAX_RETRY})..."
        
        # モデルのダウンロード（タイムアウト付き）
        if timeout 300 ollama pull "${MODEL}" 2>&1; then
            echo "✓ Model '${MODEL}' pulled successfully"
            break
        else
            echo "Failed to pull model, retrying with cleanup..."
            
            # 失敗時のクリーンアップ
            rm -rf /root/.ollama/models/manifests/${MODEL} 2>/dev/null
            
            MODEL_RETRY=$((MODEL_RETRY + 1))
            
            # 最後の試行では別のモデルを試す
            if [[ $MODEL_RETRY -eq $((MODEL_MAX_RETRY - 1)) ]]; then
                echo "Trying alternative model..."
                MODEL="all-minilm:v2"
            fi
            
            sleep 15
        fi
    fi
done

if [[ $MODEL_RETRY -ge $MODEL_MAX_RETRY ]]; then
    echo "⚠ WARNING: Could not pull model after ${MODEL_MAX_RETRY} attempts"
    echo "  The server will continue without pre-loaded models."
fi

# モデルのプリロード（メモリに常駐させる）
echo "Preloading model to avoid timeout during first use..."
if timeout 60 ollama run "${MODEL}" "test" 2>/dev/null; then
    echo "✓ Model preloaded successfully"
else
    echo "⚠ Model preload failed, but service will continue"
fi

echo "========================================="
echo "Ollama service is running on port 11434"
echo "Model: ${MODEL}"
echo "========================================="

# メモリ使用量の監視（デバッグ用）
if [[ "${OLLAMA_DEBUG}" == "1" ]] || [[ "${OLLAMA_MONITOR}" == "1" ]]; then
    (
        while true; do
            if command -v free &> /dev/null; then
                echo "[Monitor] Memory: $(free -h | grep Mem | awk '{print "Used: "$3" / Total: "$2" / Available: "$7}')"
            fi
            
            # Ollamaプロセスのメモリ使用量
            if command -v ps &> /dev/null; then
                OLLAMA_MEM=$(ps aux | grep "ollama serve" | grep -v grep | awk '{print $6}')
                if [[ -n "$OLLAMA_MEM" ]]; then
                    echo "[Monitor] Ollama RSS: $((OLLAMA_MEM / 1024))MB"
                fi
            fi
            
            sleep 60
        done
    ) &
fi

# シグナルハンドリング
trap "echo 'Shutting down Ollama...'; kill $server_pid 2>/dev/null; exit 0" SIGTERM SIGINT

# サーバープロセスを待機
echo "Ollama server is ready for connections"
wait $server_pid