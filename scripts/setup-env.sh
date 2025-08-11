#!/bin/bash

# 環境変数セットアップスクリプト
# Usage: ./setup-env.sh

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 環境ファイル
ENV_FILE=".env.production"
ENV_EXAMPLE=".env.example"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   OKAMI Environment Setup${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# .env.example の存在確認
if [ ! -f "${ENV_EXAMPLE}" ]; then
    echo -e "${RED}Error: ${ENV_EXAMPLE} not found${NC}"
    exit 1
fi

# 既存の.env.productionのバックアップ
if [ -f "${ENV_FILE}" ]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp ${ENV_FILE} ${BACKUP_FILE}
    echo -e "${YELLOW}Existing ${ENV_FILE} backed up to ${BACKUP_FILE}${NC}"
fi

# インタラクティブな設定収集
echo -e "${CYAN}Please provide the following configuration values:${NC}"
echo ""

# Monica API設定
echo -e "${BLUE}1. Monica API Configuration${NC}"
read -p "   Monica API Key (required): " MONICA_API_KEY
while [ -z "${MONICA_API_KEY}" ]; do
    echo -e "${RED}   Monica API Key is required!${NC}"
    read -p "   Monica API Key: " MONICA_API_KEY
done

read -p "   Monica Base URL [https://monica.im/v1]: " MONICA_BASE_URL
MONICA_BASE_URL=${MONICA_BASE_URL:-"https://monica.im/v1"}

# OpenAI API設定
echo ""
echo -e "${BLUE}2. OpenAI Configuration (for embeddings)${NC}"
read -p "   OpenAI API Key (required for embeddings): " OPENAI_API_KEY
while [ -z "${OPENAI_API_KEY}" ]; do
    echo -e "${RED}   OpenAI API Key is required for embeddings!${NC}"
    read -p "   OpenAI API Key: " OPENAI_API_KEY
done

# ChromaDB設定
echo ""
echo -e "${BLUE}3. ChromaDB Configuration${NC}"
read -p "   ChromaDB Auth Token [auto-generated]: " CHROMA_AUTH_TOKEN
if [ -z "${CHROMA_AUTH_TOKEN}" ]; then
    CHROMA_AUTH_TOKEN=$(openssl rand -base64 32)
    echo -e "${GREEN}   Generated ChromaDB auth token: ${CHROMA_AUTH_TOKEN}${NC}"
fi

# サーバー設定
echo ""
echo -e "${BLUE}4. Server Configuration${NC}"
read -p "   Server Port [8000]: " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-8000}

read -p "   Log Level [INFO]: " LOG_LEVEL
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Ollama設定（オプション）
echo ""
echo -e "${BLUE}5. Ollama Configuration (optional)${NC}"
read -p "   Enable Ollama support? (y/n) [n]: " ENABLE_OLLAMA
if [ "${ENABLE_OLLAMA}" = "y" ] || [ "${ENABLE_OLLAMA}" = "Y" ]; then
    read -p "   Ollama Base URL [http://localhost:11434]: " OLLAMA_BASE_URL
    OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-"http://localhost:11434"}
    
    read -p "   Ollama Model [llama2]: " OLLAMA_MODEL
    OLLAMA_MODEL=${OLLAMA_MODEL:-"llama2"}
else
    OLLAMA_BASE_URL=""
    OLLAMA_MODEL=""
fi

# MCP Gateway設定（オプション）
echo ""
echo -e "${BLUE}6. MCP Gateway Configuration (optional)${NC}"
read -p "   Enable MCP Gateway? (y/n) [n]: " ENABLE_MCP
if [ "${ENABLE_MCP}" = "y" ] || [ "${ENABLE_MCP}" = "Y" ]; then
    read -p "   MCP Gateway URL [http://localhost:5173]: " MCP_GATEWAY_URL
    MCP_GATEWAY_URL=${MCP_GATEWAY_URL:-"http://localhost:5173"}
else
    MCP_GATEWAY_URL=""
fi

# 環境ファイルの生成
echo ""
echo -e "${YELLOW}Generating ${ENV_FILE}...${NC}"

cat > ${ENV_FILE} <<EOF
# OKAMI Production Environment Configuration
# Generated on $(date)

# === Monica API Configuration ===
MONICA_API_KEY="${MONICA_API_KEY}"
MONICA_BASE_URL="${MONICA_BASE_URL}"

# === OpenAI Configuration ===
OPENAI_API_KEY="${OPENAI_API_KEY}"

# === ChromaDB Configuration ===
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_AUTH_TOKEN="${CHROMA_AUTH_TOKEN}"
CHROMA_PERSIST_DIRECTORY=/app/storage/chroma

# === Server Configuration ===
SERVER_HOST=0.0.0.0
SERVER_PORT=${SERVER_PORT}
LOG_LEVEL=${LOG_LEVEL}
PRODUCTION=true
ALLOWED_HOSTS=traning.work,www.traning.work,138.2.45.112,localhost

# === CrewAI Configuration ===
CREWAI_STORAGE_DIR=/app/storage
CREWAI_LOG_LEVEL=${LOG_LEVEL}

# === Storage Paths ===
STORAGE_BASE_PATH=/app/storage
KNOWLEDGE_BASE_PATH=/app/knowledge
EVOLUTION_BASE_PATH=/app/evolution

# === Memory Configuration ===
MEMORY_PROVIDER=basic
MEMORY_DB_PATH=/app/storage/memory.db

# === Security ===
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# === Performance ===
MAX_WORKERS=4
REQUEST_TIMEOUT=300
TASK_TIMEOUT=600

# === Monitoring ===
ENABLE_METRICS=true
METRICS_PORT=9090
EOF

# Ollama設定の追加（有効な場合）
if [ -n "${OLLAMA_BASE_URL}" ]; then
    cat >> ${ENV_FILE} <<EOF

# === Ollama Configuration ===
OLLAMA_BASE_URL="${OLLAMA_BASE_URL}"
OLLAMA_MODEL="${OLLAMA_MODEL}"
EOF
fi

# MCP Gateway設定の追加（有効な場合）
if [ -n "${MCP_GATEWAY_URL}" ]; then
    cat >> ${ENV_FILE} <<EOF

# === MCP Gateway Configuration ===
MCP_GATEWAY_URL="${MCP_GATEWAY_URL}"
MCP_ENABLED=true
EOF
fi

echo -e "${GREEN}✓ Environment file created successfully!${NC}"

# 権限設定
chmod 600 ${ENV_FILE}
echo -e "${GREEN}✓ File permissions set (600)${NC}"

# 設定の検証
echo ""
echo -e "${CYAN}Validating configuration...${NC}"

# 必須変数のチェック
ERRORS=0

if [ -z "${MONICA_API_KEY}" ]; then
    echo -e "${RED}✗ Monica API Key is missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "${OPENAI_API_KEY}" ]; then
    echo -e "${RED}✗ OpenAI API Key is missing${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ ${ERRORS} -eq 0 ]; then
    echo -e "${GREEN}✓ All required configurations are set${NC}"
else
    echo -e "${RED}✗ ${ERRORS} configuration error(s) found${NC}"
    echo -e "${YELLOW}Please edit ${ENV_FILE} to fix the errors${NC}"
fi

# サマリー表示
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Configuration Summary${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${CYAN}Monica API:${NC} Configured"
echo -e "${CYAN}OpenAI API:${NC} Configured"
echo -e "${CYAN}ChromaDB:${NC} Auth token set"
echo -e "${CYAN}Server Port:${NC} ${SERVER_PORT}"
echo -e "${CYAN}Log Level:${NC} ${LOG_LEVEL}"

if [ -n "${OLLAMA_BASE_URL}" ]; then
    echo -e "${CYAN}Ollama:${NC} Enabled (${OLLAMA_MODEL})"
fi

if [ -n "${MCP_GATEWAY_URL}" ]; then
    echo -e "${CYAN}MCP Gateway:${NC} Enabled"
fi

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review the configuration in ${ENV_FILE}"
echo "2. Run the deployment script: ./scripts/deploy.sh"
echo ""
echo -e "${YELLOW}Note: Keep your API keys secure and never commit them to version control!${NC}"