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
APP_DIR="~/OKAMI"
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
    
    # 既存のコンテナを停止
    docker-compose -f docker-compose.prod.yaml down
    
    # サービスを起動
    docker-compose -f docker-compose.prod.yaml up -d
    
    # ヘルスチェック待機
    log "Waiting for services to be healthy..."
    sleep 10
    
    # ヘルスチェック
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
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