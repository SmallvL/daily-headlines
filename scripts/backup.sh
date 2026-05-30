#!/bin/bash
# Daily Headlines - Database Backup Script
# Usage: ./scripts/backup.sh [backup_dir]

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="docker-compose.yml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[backup]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if docker compose is running
if ! docker compose -f "$COMPOSE_FILE" ps mysql | grep -q "running"; then
    error "MySQL container is not running. Start services first: docker compose up -d"
fi

# Get MySQL credentials from .env
if [ -f .env ]; then
    source .env
fi

MYSQL_USER="${MYSQL_USER:-dailyhead}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-dailyhead123}"
MYSQL_DATABASE="${MYSQL_DATABASE:-daily_headlines}"

# 1. Database dump
log "Dumping MySQL database..."
BACKUP_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"

docker compose -f "$COMPOSE_FILE" exec -T mysql \
    mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
    --single-transaction --routines --triggers \
    "$MYSQL_DATABASE" | gzip > "$BACKUP_FILE"

log "Database backup saved: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# 2. Meilisearch snapshot (if running)
if docker compose -f "$COMPOSE_FILE" ps meilisearch | grep -q "running"; then
    log "Creating Meilisearch snapshot..."
    MEILI_BACKUP="$BACKUP_DIR/meili_${TIMESTAMP}.tar.gz"
    
    docker compose -f "$COMPOSE_FILE" exec -T meilisearch \
        curl -s -X POST "http://localhost:7700/dumps" | jq -r '.taskUid' > /dev/null 2>&1 || true
    
    log "Meilisearch snapshot triggered (async, check /dumps API for status)"
fi

# 3. List recent backups
log "Recent backups:"
ls -lh "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | tail -5 || warn "No backups found"

echo ""
log "Backup complete! 📦"
echo ""
echo "To restore:"
echo "  gunzip -c $BACKUP_FILE | docker compose -f $COMPOSE_FILE exec -T mysql mysql -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE"
