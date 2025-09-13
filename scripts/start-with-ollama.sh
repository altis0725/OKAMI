#!/usr/bin/env sh
set -e

echo "[entry] Starting OKAMI container (with optional Ollama)"

# Defaults
: "${PORT:=8000}"
: "${ENABLE_OLLAMA:=false}"
: "${OLLAMA_HOST:=0.0.0.0:11434}"
: "${OLLAMA_MODELS:=/app/storage/ollama}"

if [ "$ENABLE_OLLAMA" = "true" ]; then
  echo "[ollama] ENABLE_OLLAMA=true → launching ollama serve on ${OLLAMA_HOST}"
  mkdir -p "$OLLAMA_MODELS"

  # Start ollama in background
  OLLAMA_HOST="$OLLAMA_HOST" OLLAMA_MODELS="$OLLAMA_MODELS" nohup ollama serve >/tmp/ollama.log 2>&1 &

  # Wait for Ollama to be ready (max ~60s)
  echo "[ollama] Waiting for server to become ready..."
  tries=0
  until curl -sf "http://127.0.0.1:${OLLAMA_HOST##*:}/api/tags" >/dev/null 2>&1; do
    tries=$((tries+1))
    if [ $tries -gt 60 ]; then
      echo "[ollama] Timeout waiting for Ollama to start" >&2
      break
    fi
    sleep 1
  done

  # Optionally pre-pull models (comma or space separated) in background
  # 指定がない場合は EMBEDDER_MODEL をプリフェッチ対象にする
  if [ -z "$OLLAMA_PULL_MODELS" ] && [ -n "$EMBEDDER_MODEL" ]; then
    OLLAMA_PULL_MODELS="$EMBEDDER_MODEL"
  fi

  if [ -n "$OLLAMA_PULL_MODELS" ]; then
    echo "[ollama] Pre-pulling models in background: $OLLAMA_PULL_MODELS"
    (
      models=$(echo "$OLLAMA_PULL_MODELS" | tr ',' ' ')
      for m in $models; do
        echo "[ollama] pulling $m ..."
        ollama pull "$m" || true
      done
      echo "[ollama] Pre-pull completed"
    ) >/tmp/ollama-pull.log 2>&1 &
  fi
else
  echo "[ollama] Disabled (set ENABLE_OLLAMA=true to enable)"
fi

echo "[api] Launching Uvicorn on :${PORT}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
