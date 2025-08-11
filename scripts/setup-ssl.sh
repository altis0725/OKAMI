#!/bin/bash

# SSL証明書セットアップスクリプト for Let's Encrypt
# Usage: ./setup-ssl.sh [domain] [email]

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# デフォルト値
DOMAIN=${1:-traning.work}
EMAIL=${2:-admin@traning.work}
NGINX_DIR="./nginx"
CERTBOT_DIR="${NGINX_DIR}/certbot"

echo -e "${GREEN}=== SSL Certificate Setup for ${DOMAIN} ===${NC}"

# ディレクトリ作成
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p ${CERTBOT_DIR}/www
mkdir -p ${CERTBOT_DIR}/conf
mkdir -p ${NGINX_DIR}/ssl

# Nginx設定の一時的な変更（HTTPのみで証明書取得）
echo -e "${YELLOW}Creating temporary Nginx configuration for certificate generation...${NC}"
cat > ${NGINX_DIR}/nginx.temp.conf <<EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        listen [::]:80;
        server_name ${DOMAIN} www.${DOMAIN};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$host\$request_uri;
        }
    }
}
EOF

# Docker Composeで一時的なNginxを起動
echo -e "${YELLOW}Starting temporary Nginx container...${NC}"
docker-compose -f - <<EOF
version: '3.8'
services:
  nginx-temp:
    image: nginx:alpine
    container_name: nginx-temp-ssl
    ports:
      - "80:80"
    volumes:
      - ${NGINX_DIR}/nginx.temp.conf:/etc/nginx/nginx.conf:ro
      - ${CERTBOT_DIR}/www:/var/www/certbot:ro
EOF

# 少し待機
sleep 5

# Let's Encrypt証明書の取得
echo -e "${YELLOW}Obtaining SSL certificate from Let's Encrypt...${NC}"
docker run --rm \
    -v "$(pwd)/${CERTBOT_DIR}/www:/var/www/certbot" \
    -v "$(pwd)/${CERTBOT_DIR}/conf:/etc/letsencrypt" \
    certbot/certbot:latest \
    certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d ${DOMAIN} \
    -d www.${DOMAIN}

# 一時Nginxの停止
echo -e "${YELLOW}Stopping temporary Nginx container...${NC}"
docker stop nginx-temp-ssl || true
docker rm nginx-temp-ssl || true

# 証明書の確認
if [ -f "${CERTBOT_DIR}/conf/live/${DOMAIN}/fullchain.pem" ]; then
    echo -e "${GREEN}✓ SSL certificate successfully obtained!${NC}"
    
    # 証明書の情報表示
    echo -e "${YELLOW}Certificate information:${NC}"
    openssl x509 -in ${CERTBOT_DIR}/conf/live/${DOMAIN}/fullchain.pem -noout -dates
else
    echo -e "${RED}✗ Failed to obtain SSL certificate${NC}"
    exit 1
fi

# 自動更新用のcronジョブ設定スクリプト作成
echo -e "${YELLOW}Creating certificate renewal script...${NC}"
cat > ${NGINX_DIR}/renew-cert.sh <<'EOF'
#!/bin/bash

# SSL証明書の自動更新スクリプト

DOMAIN="traning.work"
CERTBOT_DIR="/app/nginx/certbot"

echo "Renewing SSL certificate for ${DOMAIN}..."

# Certbotで証明書を更新
docker run --rm \
    -v "${CERTBOT_DIR}/www:/var/www/certbot" \
    -v "${CERTBOT_DIR}/conf:/etc/letsencrypt" \
    certbot/certbot:latest \
    renew

# Nginxをリロード
docker exec okami-nginx nginx -s reload

echo "Certificate renewal process completed."
EOF

chmod +x ${NGINX_DIR}/renew-cert.sh

# 自動更新用のcronジョブ例を表示
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo -e "${YELLOW}To enable automatic certificate renewal, add this to your crontab:${NC}"
echo "0 0,12 * * * cd /path/to/okami && ./nginx/renew-cert.sh >> /var/log/letsencrypt-renewal.log 2>&1"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Deploy the application using: ./scripts/deploy.sh"
echo "2. The SSL certificate will be automatically configured"
echo ""
echo -e "${YELLOW}Certificate files location:${NC}"
echo "  - Certificate: ${CERTBOT_DIR}/conf/live/${DOMAIN}/fullchain.pem"
echo "  - Private Key: ${CERTBOT_DIR}/conf/live/${DOMAIN}/privkey.pem"

# 一時ファイルのクリーンアップ
rm -f ${NGINX_DIR}/nginx.temp.conf