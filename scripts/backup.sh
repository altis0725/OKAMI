#!/bin/bash
# Backup script for OKAMI data

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
echo "🗂️  Creating backup in $BACKUP_DIR..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup ChromaDB data
echo "💾 Backing up ChromaDB..."
docker run --rm \
  -v okami_chroma-data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf /backup/chromadb_backup.tar.gz -C /data .

# Backup storage directory
echo "📦 Backing up storage..."
tar czf "$BACKUP_DIR/storage_backup.tar.gz" storage/

# Backup knowledge base
echo "📚 Backing up knowledge base..."
tar czf "$BACKUP_DIR/knowledge_backup.tar.gz" knowledge/

# Backup configurations
echo "⚙️  Backing up configurations..."
tar czf "$BACKUP_DIR/config_backup.tar.gz" config/

# Create backup metadata
echo "📝 Creating backup metadata..."
cat > "$BACKUP_DIR/backup_info.txt" << EOF
OKAMI Backup
Date: $(date)
Version: $(git describe --tags --always 2>/dev/null || echo "unknown")
Containers: $(docker-compose -f docker-compose.prod.yaml ps -q | wc -l)
EOF

# List backup contents
echo ""
echo "✅ Backup completed!"
echo "📁 Backup location: $BACKUP_DIR"
echo "📊 Backup contents:"
ls -lh "$BACKUP_DIR"

# Cleanup old backups (keep last 7 days)
echo ""
echo "🧹 Cleaning up old backups..."
find backups -type d -name "20*" -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo "✅ Backup process completed!"