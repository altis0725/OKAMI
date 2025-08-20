#!/bin/bash

# OKAMI Production Deployment Script
# Usage: ./deploy.sh [options]
# Options:
#   --local         : ローカル環境でのデプロイ（deploy-prod.shと同等）
#   --remote        : リモートサーバーへのデプロイ（138.2.45.112）
#   --first-time    : 初回デプロイ（SSL証明書取得を含む）
#   --update        : アプリケーションの更新のみ
#   --restart       : サービスの再起動のみ
#   --backup        : バックアップを実行してからデプロイ

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
DOMAIN="traning.work"
SERVER_IP="138.2.45.112"
APP_DIR="/home/ubuntu/OKAMI"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deploy.log"

# ログ関数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a ${LOG_FILE}
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a ${LOG_FILE}
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a ${LOG_FILE}
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a ${LOG_FILE}
}

# 引数処理
ACTION=${1:-"--update"}
DEPLOY_MODE="remote"  # デフォルトはリモートデプロイ

# --localオプションの処理
if [ "${ACTION}" = "--local" ]; then
    DEPLOY_MODE="local"
    ACTION="--update"
    APP_DIR="."
    DOMAIN="localhost"
    SERVER_IP="localhost"
fi

# ヘッダー表示
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   OKAMI Production Deployment${NC}"
echo -e "${GREEN}   Server: ${SERVER_IP} (${DOMAIN})${NC}"
echo -e "${GREEN}   Action: ${ACTION}${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# 前提条件チェック
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Docker確認
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    # Docker Compose確認
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Git確認
    if ! command -v git &> /dev/null; then
        error "Git is not installed"
    fi
    
    log "✓ All prerequisites met"
}

# バックアップ実行
perform_backup() {
    log "Creating backup..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
    
    mkdir -p ${BACKUP_PATH}
    
    # データベースとストレージのバックアップ
    if [ -d "${APP_DIR}/storage" ]; then
        tar -czf ${BACKUP_PATH}/storage.tar.gz -C ${APP_DIR} storage/
        log "✓ Storage backed up"
    fi
    
    if [ -d "${APP_DIR}/knowledge" ]; then
        tar -czf ${BACKUP_PATH}/knowledge.tar.gz -C ${APP_DIR} knowledge/
        log "✓ Knowledge base backed up"
    fi
    
    if [ -d "${APP_DIR}/evolution" ]; then
        tar -czf ${BACKUP_PATH}/evolution.tar.gz -C ${APP_DIR} evolution/
        log "✓ Evolution data backed up"
    fi
    
    # Docker volumes のバックアップ
    docker run --rm \
        -v okami_chroma-data:/data \
        -v ${BACKUP_PATH}:/backup \
        alpine tar -czf /backup/chroma-data.tar.gz -C /data .
    
    log "✓ Backup completed: ${BACKUP_PATH}"
}

# Gitリポジトリの更新
update_repository() {
    log "Updating repository..."
    
    cd ${APP_DIR}
    
    # 現在のブランチとコミットを記録
    CURRENT_BRANCH=$(git branch --show-current)
    CURRENT_COMMIT=$(git rev-parse HEAD)
    
    log "Current branch: ${CURRENT_BRANCH}"
    log "Current commit: ${CURRENT_COMMIT}"
    
    # 変更を取得
    git fetch origin
    
    # ローカル変更がある場合は stash
    if ! git diff-index --quiet HEAD --; then
        warning "Local changes detected, stashing..."
        git stash push -m "Deploy stash $(date +%Y%m%d_%H%M%S)"
    fi
    
    # 最新版にアップデート
    git pull origin main
    
    NEW_COMMIT=$(git rev-parse HEAD)
    log "Updated to commit: ${NEW_COMMIT}"
}

# 環境変数の設定
setup_environment() {
    log "Setting up environment variables..."
    
    # .env.production が存在しない場合、.env.example からコピー
    if [ ! -f "${APP_DIR}/.env.production" ]; then
        if [ -f "${APP_DIR}/.env.example" ]; then
            cp ${APP_DIR}/.env.example ${APP_DIR}/.env.production
            warning "Created .env.production from .env.example - Please configure it!"
            warning "Edit ${APP_DIR}/.env.production and set your API keys"
            exit 1
        else
            error ".env.production not found and .env.example is missing"
        fi
    fi
    
    # Ubuntu環境の場合、メモリサイズに応じた環境変数ファイルを設定
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "ubuntu" ]; then
            # メモリサイズの確認
            TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
            TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
            
            log "Detected Ubuntu with ${TOTAL_MEM_GB}GB RAM"
            
            if [ ! -f "${APP_DIR}/.env.production.ubuntu" ]; then
                log "Creating Ubuntu-specific environment file..."
                
                if [ ${TOTAL_MEM_GB} -le 1 ]; then
                    # 1GB以下のメモリ環境（超低スペック）
                    log "Configuring for ultra-low memory environment (1GB RAM)..."
                    cat > ${APP_DIR}/.env.production.ubuntu << 'EOF'
# Ubuntu本番環境専用の環境変数設定（1GB RAM + 4GB Swap環境）
EMBEDDER_MODEL=nomic-embed-text:v1.5
OLLAMA_MODEL=nomic-embed-text:v1.5
CREWAI__EMBEDDINGS__MODEL=nomic-embed-text:v1.5
REQUEST_TIMEOUT=1800
EMBEDDINGS_TIMEOUT=900
TASK_TIMEOUT=3600
OLLAMA_RETRY_COUNT=20
OLLAMA_RETRY_DELAY=60
MAX_WORKERS=1
OLLAMA_NUM_THREADS=1
OLLAMA_KEEP_ALIVE=30s
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NOPREALLOCATE=1
OLLAMA_FLASH_ATTENTION=0
BATCH_SIZE=1
EMBEDDING_BATCH_SIZE=1
OLLAMA_DEBUG=0
OLLAMA_MONITOR=1
GOMAXPROCS=1
GOMEMLIMIT=256MiB
EOF
                elif [ ${TOTAL_MEM_GB} -le 2 ]; then
                    # 2GB以下のメモリ環境（低スペック）
                    log "Configuring for low memory environment (2GB RAM)..."
                    cat > ${APP_DIR}/.env.production.ubuntu << 'EOF'
# Ubuntu本番環境専用の環境変数設定（2GB RAM環境）
EMBEDDER_MODEL=all-minilm:v2
OLLAMA_MODEL=all-minilm:v2
CREWAI__EMBEDDINGS__MODEL=all-minilm:v2
REQUEST_TIMEOUT=900
EMBEDDINGS_TIMEOUT=600
TASK_TIMEOUT=1800
OLLAMA_RETRY_COUNT=15
OLLAMA_RETRY_DELAY=30
MAX_WORKERS=2
OLLAMA_NUM_THREADS=2
OLLAMA_KEEP_ALIVE=5m
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
BATCH_SIZE=5
EMBEDDING_BATCH_SIZE=5
OLLAMA_DEBUG=0
EOF
                else
                    # 通常のメモリ環境
                    log "Configuring for standard memory environment (${TOTAL_MEM_GB}GB RAM)..."
                    cat > ${APP_DIR}/.env.production.ubuntu << 'EOF'
# Ubuntu本番環境専用の環境変数設定
EMBEDDER_MODEL=mxbai-embed-large
OLLAMA_MODEL=mxbai-embed-large
CREWAI__EMBEDDINGS__MODEL=mxbai-embed-large
REQUEST_TIMEOUT=600
EMBEDDINGS_TIMEOUT=300
TASK_TIMEOUT=1200
OLLAMA_RETRY_COUNT=10
OLLAMA_RETRY_DELAY=20
MAX_WORKERS=4
OLLAMA_NUM_THREADS=4
OLLAMA_KEEP_ALIVE=10m
OLLAMA_DEBUG=0
EOF
                fi
                
                log "✓ Ubuntu environment file created for ${TOTAL_MEM_GB}GB RAM"
            fi
            
            # スワップファイルの確認と設定（1GB環境の場合）
            if [ ${TOTAL_MEM_GB} -le 1 ]; then
                SWAP_TOTAL_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
                SWAP_TOTAL_GB=$((SWAP_TOTAL_KB / 1024 / 1024))
                
                if [ ${SWAP_TOTAL_GB} -lt 4 ]; then
                    warning "Low swap space detected (${SWAP_TOTAL_GB}GB). Recommended: 4GB+"
                    warning "To add swap: sudo fallocate -l 4G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
                fi
            fi
        fi
    fi
    
    log "✓ Environment configured"
}

# SSL証明書のセットアップ（初回のみ）
setup_ssl() {
    log "Setting up SSL certificate..."
    
    cd ${APP_DIR}
    
    # setup-ssl.sh スクリプトの実行
    if [ -f "./scripts/setup-ssl.sh" ]; then
        chmod +x ./scripts/setup-ssl.sh
        ./scripts/setup-ssl.sh ${DOMAIN} admin@${DOMAIN}
    else
        warning "SSL setup script not found, skipping SSL setup"
    fi
}

# Next.js UIのビルド
build_ui() {
    log "Building Next.js UI..."
    
    cd ${APP_DIR}
    
    # build-ui.shスクリプトの実行
    if [ -f "./scripts/build-ui.sh" ]; then
        chmod +x ./scripts/build-ui.sh
        ./scripts/build-ui.sh
        if [ $? -eq 0 ]; then
            log "✓ Next.js UI built successfully"
        else
            error "Next.js UI build failed"
        fi
    else
        warning "build-ui.sh script not found, skipping UI build"
    fi
}

# Dockerイメージのビルド
build_images() {
    log "Building Docker images..."
    
    cd ${APP_DIR}
    
    # 古いイメージのクリーンアップ
    docker system prune -f
    
    # ビルド実行
    docker-compose -f docker-compose.prod.yaml build --no-cache
    
    log "✓ Docker images built successfully"
}

# サービスの起動
start_services() {
    log "Starting services..."
    
    cd ${APP_DIR}
    
    # メモリサイズの確認（1GB環境の特別処理）
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "ubuntu" ]; then
            TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
            TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
            
            if [ ${TOTAL_MEM_GB} -le 1 ]; then
                log "Preparing for 1GB RAM deployment..."
                
                # Dockerのメモリ使用を最小化
                docker system prune -af --volumes || true
                
                # スワップをクリア（可能な限りメモリを確保）
                sudo swapoff -a && sudo swapon -a 2>/dev/null || true
                
                # 起動前にスクリプトを確実に配置
                if [ -f ./scripts/ollama-entrypoint-ubuntu-minimal.sh ]; then
                    cp ./scripts/ollama-entrypoint-ubuntu-minimal.sh ./scripts/ollama-entrypoint-ubuntu.sh
                    chmod +x ./scripts/ollama-entrypoint-ubuntu.sh
                    log "✓ Ultra-low memory Ollama script applied"
                fi
            fi
        fi
    fi
    
    # 既存のコンテナを停止
    docker-compose -f docker-compose.prod.yaml down
    
    # サービスを起動
    docker-compose -f docker-compose.prod.yaml up -d
    
    # ヘルスチェック待機
    log "Waiting for services to be healthy..."
    sleep 10
    
    # Ollamaの起動を確認（エンベディングモデルが正常に起動するまで待機）
    log "Waiting for Ollama to be ready..."
    
    # Ubuntu環境の検出とメモリサイズの確認
    IS_UBUNTU=false
    UBUNTU_MODEL="mxbai-embed-large"  # デフォルトモデル
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "ubuntu" ]; then
            IS_UBUNTU=true
            
            # メモリサイズの確認
            TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
            TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
            
            if [ ${TOTAL_MEM_GB} -le 1 ]; then
                log "Ultra-low memory Ubuntu detected (1GB) - using minimal model"
                UBUNTU_MODEL="nomic-embed-text:v1.5"
                MAX_OLLAMA_WAIT=600  # 10分
            elif [ ${TOTAL_MEM_GB} -le 2 ]; then
                log "Low memory Ubuntu detected (2GB) - using lightweight model"
                UBUNTU_MODEL="all-minilm:v2"
                MAX_OLLAMA_WAIT=600  # 10分
            else
                log "Ubuntu environment detected - standard configuration"
                MAX_OLLAMA_WAIT=300  # 5分
            fi
        else
            MAX_OLLAMA_WAIT=60
        fi
    else
        MAX_OLLAMA_WAIT=60
    fi
    
    OLLAMA_WAITED=0
    while ! docker exec okami-ollama curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
        if [ ${OLLAMA_WAITED} -ge ${MAX_OLLAMA_WAIT} ]; then
            warning "Ollama is taking longer to start, continuing anyway..."
            break
        fi
        
        sleep 5
        OLLAMA_WAITED=$((OLLAMA_WAITED + 5))
        
        # 1GB環境では進捗を詳細に表示
        if [ ${TOTAL_MEM_GB} -le 1 ]; then
            if [ $((OLLAMA_WAITED % 60)) -eq 0 ]; then
                info "Still waiting for Ollama (using swap)... ${OLLAMA_WAITED}s / ${MAX_OLLAMA_WAIT}s"
            fi
        else
            info "Waiting for Ollama... ${OLLAMA_WAITED}s"
        fi
    done
    
    if docker exec okami-ollama curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        log "✓ Ollama is ready"
        
        # Ubuntu環境の場合、適切なモデルをプリロード
        if [ "$IS_UBUNTU" = true ]; then
            log "Preloading ${UBUNTU_MODEL} model for Ubuntu..."
            
            # 1GB環境の場合は特別な処理
            if [ ${TOTAL_MEM_GB} -le 1 ]; then
                warning "Model loading will be very slow due to swap usage"
                docker exec okami-ollama timeout 1800 ollama pull ${UBUNTU_MODEL} || warning "Model pull timed out or failed"
            else
                docker exec okami-ollama ollama pull ${UBUNTU_MODEL} || warning "Model pull failed, but continuing..."
            fi
            
            # モデルの初期化テスト（1GB環境ではスキップ可能）
            if [ ${TOTAL_MEM_GB} -gt 1 ]; then
                docker exec okami-ollama ollama run ${UBUNTU_MODEL} "test" || warning "Model initialization failed, but continuing..."
            fi
        fi
    fi
    
    # ヘルスチェック
MAX_RETRIES=30
RETRY_COUNT=0

# デプロイモードに応じてヘルスチェックの対象を決定
if [ "${DEPLOY_MODE}" = "local" ]; then
    HEALTH_CHECK_URL="http://localhost:8000/health"
else
    # リモートデプロイの場合は、サーバー自身のlocalhostを使用
    HEALTH_CHECK_URL="https://traning.work/health"
    info "Using localhost for health check (remote server)"
fi

while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
    if curl -f ${HEALTH_CHECK_URL} > /dev/null 2>&1; then
        log "✓ Health check passed"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    info "Health check attempt ${RETRY_COUNT}/${MAX_RETRIES}..."
    sleep 5
done
    
    if [ ${RETRY_COUNT} -eq ${MAX_RETRIES} ]; then
        error "Health check failed after ${MAX_RETRIES} attempts"
    fi
}

# サービスステータスの表示
show_status() {
    log "Service status:"
    docker-compose -f docker-compose.prod.yaml ps
    
    echo ""
    log "Recent logs:"
    docker-compose -f docker-compose.prod.yaml logs --tail=20
}

# SSL証明書の更新設定
setup_cert_renewal() {
    log "Setting up SSL certificate renewal..."
    
    # Cronジョブの設定
    CRON_JOB="0 0,12 * * * cd ${APP_DIR} && ./nginx/renew-cert.sh >> /var/log/letsencrypt-renewal.log 2>&1"
    
    # 既存のcronジョブをチェック
    if ! crontab -l 2>/dev/null | grep -q "renew-cert.sh"; then
        (crontab -l 2>/dev/null; echo "${CRON_JOB}") | crontab -
        log "✓ SSL renewal cron job added"
    else
        log "✓ SSL renewal cron job already exists"
    fi
}

# ローカルデプロイ処理（deploy-prod.shの機能を統合）
local_deploy() {
    log "Starting local deployment..."
    
    # .env ファイルチェック
    if [ ! -f .env ]; then
        error ".env file not found! Please copy .env.example to .env and configure it"
    fi
    
    # 自己署名SSL証明書の生成（必要な場合）
    if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
        warning "SSL certificates not found, generating self-signed certificates..."
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=OKAMI/CN=localhost"
        log "✓ Self-signed certificates generated"
    fi
    
    # Next.js UIのビルド
    log "Building Next.js UI..."
    if [ -f ./scripts/build-ui.sh ]; then
        chmod +x ./scripts/build-ui.sh
        ./scripts/build-ui.sh
        if [ $? -eq 0 ]; then
            log "✓ Next.js UI built successfully"
        else
            error "Next.js UI build failed"
        fi
    else
        warning "build-ui.sh script not found, skipping UI build"
    fi
    
    # Dockerイメージのビルド
    log "Building Docker images..."
    docker-compose -f docker-compose.prod.yaml build
    
    # 既存コンテナの停止
    log "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yaml down
    
    # サービスの起動
    log "Starting production services..."
    docker-compose -f docker-compose.prod.yaml up -d
    
    # ヘルスチェック
    log "Waiting for services to be ready..."
    sleep 10
    
    if curl -k -f https://localhost/health > /dev/null 2>&1; then
        log "✓ Health check passed"
    else
        error "Health check failed"
    fi
    
    # ステータス表示
    log "Running services:"
    docker-compose -f docker-compose.prod.yaml ps
    
    echo ""
    echo -e "${GREEN}Local deployment completed!${NC}"
    echo -e "Access: https://localhost"
    echo -e "Logs: docker-compose -f docker-compose.prod.yaml logs -f"
}

# メイン処理
main() {
    # ローカルデプロイの場合
    if [ "${DEPLOY_MODE}" = "local" ]; then
        local_deploy
        return
    fi
    
    # リモートデプロイの場合
    check_prerequisites
    
    case ${ACTION} in
        --first-time)
            log "Starting first-time deployment..."
            perform_backup
            update_repository
            setup_environment
            setup_ssl
            build_ui
            build_images
            start_services
            setup_cert_renewal
            show_status
            ;;
            
        --update)
            log "Starting application update..."
            perform_backup
            update_repository
            setup_environment
            build_ui
            build_images
            start_services
            show_status
            ;;
            
        --restart)
            log "Restarting services..."
            cd ${APP_DIR}
            docker-compose -f docker-compose.prod.yaml restart
            show_status
            ;;
            
        --backup)
            log "Performing backup and deployment..."
            perform_backup
            update_repository
            setup_environment
            build_ui
            build_images
            start_services
            show_status
            ;;
            
        *)
            error "Unknown action: ${ACTION}"
            echo "Usage: $0 [--first-time|--update|--restart|--backup]"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}   Deployment completed successfully!${NC}"
    echo -e "${GREEN}   Access: https://${DOMAIN}${NC}"
    echo -e "${GREEN}======================================${NC}"
}

# エラーハンドリング
trap 'error "Deployment failed at line $LINENO"' ERR

# メイン処理実行
main