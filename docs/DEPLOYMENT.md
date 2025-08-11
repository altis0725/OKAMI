# OKAMI Production Deployment Guide

このガイドでは、OKAMIを本番環境（Ubuntu Server 138.2.45.112）にデプロイする手順を説明します。

## 📋 前提条件

- Ubuntu Server 20.04 LTS以上
- ドメイン名（例：traning.work）がサーバーIPに解決されること
- root権限またはsudo権限
- 最低4GB RAM、20GB ストレージ

## 🚀 デプロイ手順

### 1. サーバーの初期設定

初回のみ、サーバーの基本設定を行います：

```bash
# ローカルマシンから実行
ssh root@138.2.45.112 'bash -s' < scripts/server-setup.sh
```

このスクリプトは以下を自動的に設定します：
- システムパッケージの更新
- Docker & Docker Composeのインストール
- セキュリティ設定（ファイアウォール、Fail2ban）
- アプリケーションユーザーの作成
- システム最適化

### 2. アプリケーションファイルのアップロード

```bash
# ローカルマシンから実行
rsync -avz --exclude='.git' --exclude='storage/*' --exclude='*.pyc' \
  ./ okami@138.2.45.112:/opt/okami/
```

### 3. サーバーにSSH接続

```bash
ssh okami@138.2.45.112
cd /opt/okami
```

### 4. 環境変数の設定

```bash
# インタラクティブな設定ウィザードを実行
./scripts/setup-env.sh
```

必要な情報：
- Monica API Key
- OpenAI API Key
- その他の設定（対話形式で入力）

### 5. SSL証明書の取得

Let's Encryptから無料のSSL証明書を取得：

```bash
./scripts/setup-ssl.sh traning.work admin@traning.work
```

### 6. アプリケーションのデプロイ

#### 初回デプロイ

```bash
./scripts/deploy.sh --first-time
```

#### 通常のアップデート

```bash
./scripts/deploy.sh --update
```

#### サービスの再起動のみ

```bash
./scripts/deploy.sh --restart
```

## 🔧 systemdサービスとして登録

システム起動時に自動起動するように設定：

```bash
sudo ./scripts/install-systemd.sh
```

サービス管理コマンド：
```bash
# サービスの開始
sudo systemctl start okami

# サービスの停止
sudo systemctl stop okami

# サービスの再起動
sudo systemctl restart okami

# ステータス確認
sudo systemctl status okami

# ログの確認
sudo journalctl -u okami -f
```

## 📝 設定ファイル一覧

### 本番環境用ファイル

| ファイル | 説明 |
|---------|------|
| `docker-compose.prod.yaml` | 本番環境用Docker Compose設定 |
| `nginx/nginx.prod.conf` | Nginx設定（SSL、リバースプロキシ） |
| `.env.production` | 本番環境用環境変数 |
| `systemd/okami.service` | systemdサービス定義 |

### デプロイスクリプト

| スクリプト | 用途 |
|-----------|------|
| `scripts/server-setup.sh` | サーバー初期設定 |
| `scripts/setup-env.sh` | 環境変数設定 |
| `scripts/setup-ssl.sh` | SSL証明書取得 |
| `scripts/deploy.sh` | デプロイ実行 |
| `scripts/install-systemd.sh` | systemdサービス登録 |

## 🔐 セキュリティ設定

### ファイアウォール

開放ポート：
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)

### Fail2ban

以下の攻撃から保護：
- SSH総当たり攻撃
- Nginx認証失敗
- レート制限違反

### SSL/TLS

- Let's Encryptによる自動証明書管理
- TLS 1.2/1.3のみサポート
- 強力な暗号スイートのみ使用
- HSTSヘッダー有効

## 📊 モニタリング

### ヘルスチェック

```bash
# ローカルから
curl https://traning.work/health

# サーバー内から
curl http://localhost:8000/health
```

### ログ確認

```bash
# Dockerログ
docker-compose -f docker-compose.prod.yaml logs -f

# systemdログ
sudo journalctl -u okami -f

# Nginxアクセスログ
docker exec okami-nginx tail -f /var/log/nginx/access.log

# アプリケーションログ
tail -f /opt/okami/logs/okami.log
```

### メトリクス

Node Exporterが自動的にインストールされ、以下でアクセス可能：
```
http://138.2.45.112:9100/metrics
```

## 🔄 アップデート手順

1. コードの更新
```bash
cd /opt/okami
git pull origin main
```

2. デプロイ実行
```bash
./scripts/deploy.sh --update
```

## 🆘 トラブルシューティング

### サービスが起動しない

```bash
# ログを確認
docker-compose -f docker-compose.prod.yaml logs okami

# 環境変数を確認
cat .env.production

# Dockerの状態確認
docker ps -a
```

### SSL証明書の問題

```bash
# 証明書の再取得
./scripts/setup-ssl.sh traning.work admin@traning.work

# 証明書の有効期限確認
openssl x509 -in nginx/certbot/conf/live/traning.work/fullchain.pem -noout -dates
```

### メモリ不足

```bash
# スワップ追加
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 🔄 バックアップとリストア

### バックアップ

```bash
# 自動バックアップ（デプロイ時に実行）
./scripts/deploy.sh --backup

# 手動バックアップ
tar -czf backup-$(date +%Y%m%d).tar.gz storage/ knowledge/ evolution/
```

### リストア

```bash
# バックアップからリストア
tar -xzf backup-20240101.tar.gz
docker-compose -f docker-compose.prod.yaml restart
```

## 📞 サポート

問題が発生した場合は、以下の情報を含めて報告してください：

1. エラーログ（`docker-compose logs`の出力）
2. 環境情報（`docker version`, `docker-compose version`）
3. 実行したコマンドと手順
4. `.env.production`の内容（APIキーは除く）