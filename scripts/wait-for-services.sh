#!/bin/bash
# Wait for required services to be ready

set -e

echo "Waiting for ChromaDB to be ready..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if python -c "import urllib.request; urllib.request.urlopen('http://chromadb:8000/api/v1')" 2>/dev/null; then
        echo "ChromaDB is ready!"
        break
    fi
    echo "ChromaDB is not ready yet, waiting... ($WAITED/$MAX_WAIT)"
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "Warning: ChromaDB may not be fully ready, but continuing..."
fi

echo "Waiting for Ollama to be ready..."
until curl -s -f http://ollama:11434/api/tags > /dev/null 2>&1; do
    echo "Ollama is not ready yet, waiting..."
    sleep 2
done
echo "Ollama is ready!"

# モデルが存在するか確認
echo "Checking if embedding model is loaded..."
for i in {1..30}; do
    if curl -s http://ollama:11434/api/tags | grep -q "mxbai-embed-large"; then
        echo "Embedding model is loaded!"
        break
    fi
    echo "Waiting for embedding model to load... ($i/30)"
    sleep 2
done

echo "All services are ready, starting OKAMI..."
exec "$@"