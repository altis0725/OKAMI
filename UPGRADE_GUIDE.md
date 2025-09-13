# OKAMIシステム最新版アップグレードガイド

## 概要

OllamaとChromaDBの最新版への段階的移行手順を説明します。

## ⚠️ 重要な注意点

1. **ChromaDB 1.0.x系への移行は不可逆的です**
2. **データベースの完全なバックアップが必須です**
3. **本番環境では事前にテスト環境での十分な検証が必要です**

## 🚨 **依存関係の競合問題**

### **問題の発見**
調査の結果、以下の競合が判明しました：

- **ChromaDBサーバー**: Docker `latest` = 1.0.x系
- **CrewAI 0.165.1**: `chromadb>=0.5.23`を要求
- **crewai-tools**: `chromadb==0.5.23`を厳密に要求
- **結果**: Pythonクライアントが1.0.xをインストールできない

### **現在の解決策**
サーバーとクライアントを**0.5.23で統一**：
```yaml
# docker-compose.yaml
chromadb:
  image: chromadb/chroma:0.5.23
```

```txt
# requirements.txt  
chromadb==0.5.23
```

## アップグレード戦略

### 段階1: 保守的アップグレード（推奨）

現在のシステムの安定性を保ちながら、安全な範囲でのアップデート。

```bash
# 現在のバージョンを確認
docker-compose ps
pip list | grep -E "(chromadb|ollama|crewai)"

# バックアップ作成
./scripts/backup.sh

# 段階的アップグレード（現在のrequirements.txt使用）
pip install -r requirements.txt --upgrade
docker-compose up -d --build
```

**変更内容:**
- ChromaDB: 0.5.23 → 0.5.x系最新（<0.6.0）
- Ollama: 0.3.3 → 0.4.x系最新（<0.5.0）

### 段階2: 最新版移行（要慎重なテスト）

十分なテストとバックアップ後の最新版への移行。

#### 2-1. テスト環境での検証

```bash
# テスト環境の準備
cp -r storage/ storage_backup_$(date +%Y%m%d)
cp -r knowledge/ knowledge_backup_$(date +%Y%m%d)
cp .env .env.backup

# テスト用仮想環境
python -m venv test_upgrade_env
source test_upgrade_env/bin/activate

# 最新版での依存関係チェック
pip install -r requirements-latest.txt

# Docker環境テスト
docker-compose -f docker-compose.latest.yaml up -d
```

#### 2-2. 互換性テスト

```bash
# APIテスト
curl http://localhost:8000/health
curl http://localhost:11434/api/version
curl http://localhost:8001/api/v1/heartbeat

# エンベッディング機能テスト
python -c "
import ollama
response = ollama.embed(model='mxbai-embed-large', input='test')
print(f'Embedding dimensions: {len(response.embeddings[0])}')
"

# ChromaDBコレクション確認
python -c "
import chromadb
client = chromadb.Client()
collections = client.list_collections()
print(f'Collections: {[c.name for c in collections]}')
"
```

#### 2-3. 本番環境移行

```bash
# 本番環境の完全停止
docker-compose down

# データの完全バックアップ
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz storage/ knowledge/ logs/ .env

# 最新版への移行
pip install -r requirements-latest.txt
docker-compose -f docker-compose.latest.yaml up -d

# ヘルスチェック
./scripts/health_check.sh
```

## トラブルシューティング

### エンベッディング次元不整合エラー

```
[ERROR]: Embedding dimension mismatch
```

**解決策:**
```bash
# CrewAIメモリのリセット
crewai reset-memories -a

# ChromaDBコレクションの手動削除
rm -rf ~/.local/share/CrewAI/OKAMI/
rm -rf storage/chroma/

# アプリケーション再起動
docker-compose restart
```

### Ollama接続エラー

```
HTTPConnectionPool(host='ollama', port=11434): Max retries exceeded
```

**解決策:**
```bash
# ネットワーク設定確認
docker network inspect okami_okami-network

# Ollamaサービス確認
docker-compose logs ollama
curl http://localhost:11434/api/version

# 環境変数確認
echo $OLLAMA_BASE_URL
echo $OLLAMA_API_BASE_URL
```

### ChromaDB認証エラー（1.0.x系）

**解決策:**
```bash
# 認証設定ファイル作成（必要な場合）
mkdir -p config/chroma
echo '{"token": "your-secure-token"}' > config/chroma/credentials.json

# 環境変数設定
export CHROMA_SERVER_AUTHN_CREDENTIALS_FILE=/chroma/config/credentials.json
```

## ロールバック手順

### ChromaDB 0.5.x系へのロールバック

ChromaDB 1.0.x系から0.5.x系へのロールバックは**不可能**です。バックアップからの復旧のみ可能。

```bash
# サービス停止
docker-compose down

# バックアップからの復旧
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# 従来の設定で再起動
pip install -r requirements.txt
docker-compose up -d
```

## 監視ポイント

### パフォーマンスメトリクス

```bash
# メモリ使用量監視
docker stats --no-stream

# API応答時間監視
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# エンベッディング処理時間
time curl -X POST http://localhost:11434/api/embed \
  -d '{"model":"mxbai-embed-large","input":"test"}'
```

### ログ監視

```bash
# エラーログの監視
docker-compose logs -f | grep -E "(ERROR|WARN)"

# ChromaDBログ
docker-compose logs chromadb | tail -50

# Ollamaログ
docker-compose logs ollama | tail -50
```

## 参考情報

- ChromaDB 1.0.x Migration Guide: https://docs.trychroma.com/guides/migrations
- Ollama 0.5.x Release Notes: https://github.com/ollama/ollama-python/releases
- CrewAI Compatibility Matrix: https://docs.crewai.com/core-concepts/agents

## アップグレード後のチェックリスト

- [ ] すべてのサービスが正常に起動している
- [ ] APIエンドポイントが応答している
- [ ] エンベッディング機能が動作している
- [ ] 既存の知識ベースにアクセスできる
- [ ] メモリ機能が正常に動作している
- [ ] ログにエラーが出力されていない
- [ ] パフォーマンスが期待通りである