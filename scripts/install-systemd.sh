#!/bin/bash

# systemdサービスインストールスクリプト
# Usage: sudo ./install-systemd.sh

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
SERVICE_NAME="okami"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
APP_DIR="/opt/okami"
SERVICE_USER="okami"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   OKAMI systemd Service Installation${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# rootチェック
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# ユーザー作成
echo -e "${YELLOW}Setting up service user...${NC}"
if ! id "${SERVICE_USER}" &>/dev/null; then
    useradd -r -s /bin/bash -d ${APP_DIR} -m ${SERVICE_USER}
    echo -e "${GREEN}✓ Created user: ${SERVICE_USER}${NC}"
else
    echo -e "${GREEN}✓ User ${SERVICE_USER} already exists${NC}"
fi

# Dockerグループに追加
usermod -aG docker ${SERVICE_USER}
echo -e "${GREEN}✓ Added ${SERVICE_USER} to docker group${NC}"

# アプリケーションディレクトリの準備
echo -e "${YELLOW}Preparing application directory...${NC}"
if [ ! -d "${APP_DIR}" ]; then
    mkdir -p ${APP_DIR}
    echo -e "${GREEN}✓ Created directory: ${APP_DIR}${NC}"
fi

# 現在のディレクトリからファイルをコピー（開発環境から本番環境へ）
if [ -d "./config" ] && [ -d "./scripts" ]; then
    echo -e "${YELLOW}Copying application files...${NC}"
    cp -r ./* ${APP_DIR}/
    echo -e "${GREEN}✓ Application files copied${NC}"
fi

# 所有権の設定
chown -R ${SERVICE_USER}:${SERVICE_USER} ${APP_DIR}
echo -e "${GREEN}✓ Set ownership to ${SERVICE_USER}${NC}"

# systemdサービスファイルのコピー
echo -e "${YELLOW}Installing systemd service...${NC}"
if [ -f "./systemd/${SERVICE_NAME}.service" ]; then
    cp ./systemd/${SERVICE_NAME}.service ${SERVICE_FILE}
elif [ -f "${APP_DIR}/systemd/${SERVICE_NAME}.service" ]; then
    cp ${APP_DIR}/systemd/${SERVICE_NAME}.service ${SERVICE_FILE}
else
    echo -e "${RED}Error: Service file not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Service file installed to ${SERVICE_FILE}${NC}"

# systemdのリロード
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd daemon reloaded${NC}"

# サービスの有効化
echo -e "${YELLOW}Enabling ${SERVICE_NAME} service...${NC}"
systemctl enable ${SERVICE_NAME}.service
echo -e "${GREEN}✓ Service enabled (will start on boot)${NC}"

# ログディレクトリの作成
echo -e "${YELLOW}Setting up log directories...${NC}"
mkdir -p /var/log/${SERVICE_NAME}
chown ${SERVICE_USER}:${SERVICE_USER} /var/log/${SERVICE_NAME}
echo -e "${GREEN}✓ Log directory created${NC}"

# 環境ファイルのチェック
echo -e "${YELLOW}Checking environment configuration...${NC}"
if [ ! -f "${APP_DIR}/.env.production" ]; then
    echo -e "${YELLOW}Warning: .env.production not found${NC}"
    echo -e "${YELLOW}Please run: cd ${APP_DIR} && ./scripts/setup-env.sh${NC}"
else
    echo -e "${GREEN}✓ Environment configuration found${NC}"
fi

# サービス管理コマンドの説明
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${BLUE}Service Management Commands:${NC}"
echo ""
echo "  Start service:    sudo systemctl start ${SERVICE_NAME}"
echo "  Stop service:     sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart service:  sudo systemctl restart ${SERVICE_NAME}"
echo "  Check status:     sudo systemctl status ${SERVICE_NAME}"
echo "  View logs:        sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Disable service:  sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure environment: cd ${APP_DIR} && ./scripts/setup-env.sh"
echo "2. Setup SSL: cd ${APP_DIR} && ./scripts/setup-ssl.sh"
echo "3. Start service: sudo systemctl start ${SERVICE_NAME}"
echo "4. Check status: sudo systemctl status ${SERVICE_NAME}"
echo ""
echo -e "${GREEN}Service will automatically start on system boot${NC}"