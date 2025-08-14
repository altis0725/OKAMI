#!/bin/bash

# Ubuntu Server初期セットアップスクリプト (138.2.45.112用)
# Usage: ssh root@138.2.45.112 'bash -s' < server-setup.sh

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
DOMAIN="traning.work"
APP_USER="okami"
APP_DIR="/opt/okami"
GITHUB_REPO="https://github.com/altis0725/OKAMI.git"  # 実際のリポジトリURLに変更してください

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Ubuntu Server Setup for OKAMI${NC}"
echo -e "${GREEN}   Server: 138.2.45.112${NC}"
echo -e "${GREEN}   Domain: ${DOMAIN}${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# システムアップデート
echo -e "${YELLOW}Updating system packages...${NC}"
apt-get update
apt-get upgrade -y
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    unattended-upgrades

echo -e "${GREEN}✓ System packages updated${NC}"

# Docker インストール
echo -e "${YELLOW}Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Docker Compose インストール
echo -e "${YELLOW}Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed (${COMPOSE_VERSION})${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# アプリケーションユーザー作成
echo -e "${YELLOW}Creating application user...${NC}"
if ! id "${APP_USER}" &>/dev/null; then
    useradd -r -s /bin/bash -d ${APP_DIR} -m ${APP_USER}
    usermod -aG docker ${APP_USER}
    echo -e "${GREEN}✓ Created user: ${APP_USER}${NC}"
else
    echo -e "${GREEN}✓ User ${APP_USER} already exists${NC}"
fi

# SSH設定
echo -e "${YELLOW}Configuring SSH...${NC}"
# SSHポート変更（オプション）
# sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
echo -e "${GREEN}✓ SSH configured${NC}"

# ファイアウォール設定
echo -e "${YELLOW}Configuring firewall...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  # SSH (変更した場合は適切なポートに)
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
ufw reload
echo -e "${GREEN}✓ Firewall configured${NC}"

# Fail2ban設定
echo -e "${YELLOW}Configuring Fail2ban...${NC}"
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo -e "${GREEN}✓ Fail2ban configured${NC}"

# スワップファイル作成（メモリが少ない場合）
echo -e "${YELLOW}Checking swap...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✓ 4GB swap file created${NC}"
else
    echo -e "${GREEN}✓ Swap already configured${NC}"
fi

# システムパラメータ調整
echo -e "${YELLOW}Optimizing system parameters...${NC}"
cat >> /etc/sysctl.conf <<EOF

# OKAMI optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.ip_local_port_range = 10000 65000
fs.file-max = 100000
vm.swappiness = 10
EOF

sysctl -p
echo -e "${GREEN}✓ System parameters optimized${NC}"

# アプリケーションディレクトリ作成
echo -e "${YELLOW}Creating application directory...${NC}"
mkdir -p ${APP_DIR}
chown ${APP_USER}:${APP_USER} ${APP_DIR}
echo -e "${GREEN}✓ Application directory created${NC}"

# Git リポジトリのクローン（GitHubを使用する場合）
# echo -e "${YELLOW}Cloning repository...${NC}"
# su - ${APP_USER} -c "cd ${APP_DIR} && git clone ${GITHUB_REPO} ."
# echo -e "${GREEN}✓ Repository cloned${NC}"

# 自動アップデート設定
echo -e "${YELLOW}Configuring automatic updates...${NC}"
cat > /etc/apt/apt.conf.d/50unattended-upgrades <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

echo -e "${GREEN}✓ Automatic updates configured${NC}"

# モニタリングツールのインストール（オプション）
echo -e "${YELLOW}Installing monitoring tools...${NC}"
# Node Exporter for Prometheus
wget https://github.com/prometheus/node_exporter/releases/latest/download/node_exporter-*.linux-amd64.tar.gz -O /tmp/node_exporter.tar.gz
tar xvf /tmp/node_exporter.tar.gz -C /tmp
mv /tmp/node_exporter-*/node_exporter /usr/local/bin/
rm -rf /tmp/node_exporter*

cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=nobody
Group=nogroup
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
echo -e "${GREEN}✓ Monitoring tools installed${NC}"

# 完了メッセージ
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Server Setup Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Upload OKAMI application files to ${APP_DIR}"
echo "   scp -r ./* ${APP_USER}@138.2.45.112:${APP_DIR}/"
echo ""
echo "2. SSH as application user:"
echo "   ssh ${APP_USER}@138.2.45.112"
echo ""
echo "3. Setup environment:"
echo "   cd ${APP_DIR}"
echo "   ./scripts/setup-env.sh"
echo ""
echo "4. Get SSL certificate:"
echo "   ./scripts/setup-ssl.sh"
echo ""
echo "5. Deploy application:"
echo "   ./scripts/deploy.sh --first-time"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "- Root login is disabled"
echo "- Password authentication is disabled (use SSH keys)"
echo "- Firewall is enabled (ports 22, 80, 443 open)"
echo "- Fail2ban is protecting SSH and Nginx"
echo "- Automatic security updates are enabled"
echo ""
echo -e "${GREEN}Server is ready for OKAMI deployment!${NC}"