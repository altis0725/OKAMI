# Ubuntu環境でのOllamaタイムアウト問題の解決手順（1GB RAM + 4GB Swap環境）

## 問題の概要
物理メモリ1GB、スワップ4GBの超低スペックUbuntu環境でCrewAIからOllamaを呼び出す際に、エンベディング生成でタイムアウトエラーが発生する問題への対処方法。

## 解決手順

### 1. 超低メモリ環境用スクリプトの適用

Ubuntu端末で以下のコマンドを実行：

```bash
# 現在のスクリプトをバックアップ
cp scripts/ollama-entrypoint-ubuntu.sh scripts/ollama-entrypoint-ubuntu.sh.backup

# 超低メモリ環境用スクリプトを適用
cp scripts/ollama-entrypoint-ubuntu-minimal.sh scripts/ollama-entrypoint-ubuntu.sh

# 実行権限を付与
chmod +x scripts/ollama-entrypoint-ubuntu.sh
chmod +x scripts/ollama-entrypoint-ubuntu-minimal.sh
```

### 2. Ubuntu用環境変数ファイルの設定

```bash
# サンプルファイルをコピー
cp env.production.ubuntu.example .env.production.ubuntu

# 必要に応じて編集
nano .env.production.ubuntu
```

### 3. Docker Composeの更新と再起動

```bash
# 既存のコンテナを停止
docker-compose -f docker-compose.prod.yaml down

# Ollamaのボリュームをクリア（オプション：問題が続く場合）
docker volume rm okami_ollama-data

# コンテナを再構築して起動
docker-compose -f docker-compose.prod.yaml up -d --build ollama

# ログを監視
docker-compose -f docker-compose.prod.yaml logs -f ollama
```

### 4. Ollamaの動作確認

```bash
# Ollamaが起動しているか確認
docker exec okami-ollama curl -s http://localhost:11434/api/tags

# モデルがロードされているか確認
docker exec okami-ollama ollama list

# テストエンベディング生成
docker exec okami-ollama curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "mxbai-embed-large", "prompt": "test"}'
```

### 5. メモリ不足の場合の対処

システムメモリが不足している場合：

```bash
# スワップファイルの作成（4GB）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永続化
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# スワップ使用率の調整
sudo sysctl vm.swappiness=60
echo 'vm.swappiness=60' | sudo tee -a /etc/sysctl.conf
```

### 6. 最軽量モデル（nomic-embed-text）の使用

1GB RAMの環境では、**nomic-embed-text:v1.5**（137MB）を使用します：

```bash
# 既に設定済みですが、確認のため
grep "nomic-embed-text" .env.production.ubuntu

# モデルの手動ダウンロード（オプション）
docker exec -it okami-ollama ollama pull nomic-embed-text:v1.5
```

**重要**: このモデルは最も軽量で高性能なエンベディングモデルです。

### 7. システムリソースの監視

```bash
# リアルタイムモニタリング
watch -n 5 'docker stats okami-ollama --no-stream'

# メモリ使用状況
free -h

# Ollamaコンテナの詳細ログ
docker logs okami-ollama --tail 100 -f
```

## トラブルシューティング

### ケース1: "pulling manifest"が繰り返される

```bash
# Ollamaコンテナに入る
docker exec -it okami-ollama bash

# 手動でモデルをプル
ollama pull mxbai-embed-large

# または軽量モデルを試す
ollama pull all-minilm:v2
```

### ケース2: メモリ不足エラー

```bash
# Docker Composeファイルでメモリ制限を調整
nano docker-compose.prod.yaml

# ollamaサービスのdeploy.resources.limitsを変更:
# memory: 4G → memory: 2G
```

### ケース3: タイムアウトが続く場合

```bash
# タイムアウト値をさらに延長
nano .env.production.ubuntu

# 以下を追加または変更
REQUEST_TIMEOUT=900  # 15分
EMBEDDINGS_TIMEOUT=600  # 10分
```

## 1GB RAM環境向けの最適化内容

1. **超軽量モデル**: nomic-embed-text:v1.5（137MB）を使用
2. **メモリ制限**: 
   - Ollama: 最大512MB、最小256MB
   - CrewAI: 最大512MB、最小256MB
   - ChromaDB: 最大256MB
3. **スワップ最適化**: 4GBスワップを積極的に活用
4. **タイムアウト延長**: 全タイムアウトを30分以上に設定
5. **シングルスレッド動作**: CPU使用を1コアに制限
6. **バッチ処理無効**: メモリ使用を最小化

## スペック要件

### 現在の対応環境（超低スペック）:
- RAM: 1GB（物理メモリ）
- Swap: 4GB（必須）
- CPU: 1コア以上
- ストレージ: 5GB以上の空き容量

### 推奨スペック:
- RAM: 4GB以上
- CPU: 2コア以上
- ストレージ: 10GB以上の空き容量

### 快適動作スペック:
- RAM: 8GB以上
- CPU: 4コア以上
- ストレージ: 20GB以上の空き容量

## 注意事項

- この設定はUbuntu環境専用です
- 本番環境では必ずSSL/TLS設定を行ってください
- 定期的にログを確認し、異常がないか監視してください
- メモリ不足が頻発する場合は、より軽量なモデルの使用を検討してください