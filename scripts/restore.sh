#!/bin/bash
# Daily Headlines - Database Restore Script
# Usage: ./scripts/restore.sh <backup_file.sql.gz>

set -euo pipefail

COMPOSE_FILE="docker-compose.yml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[restore]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/db_*.sql.gz 2>/dev/null || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

# Get MySQL credentials from .env
if [ -f .env ]; then
    source .env
fi

MYSQL_USER="${MYSQL_USER:-dailyhead}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-dailyhead123}"
MYSQL_DATABASE="${MYSQL_DATABASE:-daily_headlines}"

# Check if docker compose is running
if ! docker compose -f "$COMPOSE_FILE" ps mysql | grep -q "running"; then
    error "MySQL container is not running. Start services first: docker compose up -d"
fi

# Confirm
warn "This will DROP and recreate the database '$MYSQL_DATABASE'."
read -p "Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Restore cancelled."
    exit 0
fi

# Restore
log "Restoring database from $BACKUP_FILE..."

gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T mysql \
    mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"

log "Database restored successfully! ✅"
echo ""
log "You may want to restart the API service:"
echo "  docker compose restart api"
