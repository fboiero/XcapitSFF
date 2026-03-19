#!/usr/bin/env bash
# =============================================================================
# backup.sh — PostgreSQL backup script for XcapitSFF
#
# Usage:
#   ./scripts/backup.sh                    # Backup with defaults
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh   # Custom backup directory
#   KEEP_DAYS=14 ./scripts/backup.sh       # Keep 14 days of backups
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# Configuration (override via environment)
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
CONTAINER_NAME="${CONTAINER_NAME:-xcapitsff-postgres}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# =============================================================================
# Load environment
# =============================================================================
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
fi

POSTGRES_USER="${POSTGRES_USER:-xcapit}"
POSTGRES_DB="${POSTGRES_DB:-xcapitsff}"

# =============================================================================
# Create backup directory
# =============================================================================
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

# =============================================================================
# Check that the postgres container is running
# =============================================================================
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "PostgreSQL container '$CONTAINER_NAME' is not running."
    log_error "Start it with: docker compose -f docker-compose.prod.yml up -d postgres"
    exit 1
fi

# =============================================================================
# Dump and compress
# =============================================================================
log_info "Starting backup of database '$POSTGRES_DB'..."

docker exec "$CONTAINER_NAME" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# =============================================================================
# Verify backup is not empty
# =============================================================================
if [[ ! -s "$BACKUP_FILE" ]]; then
    log_error "Backup file is empty. Something went wrong."
    rm -f "$BACKUP_FILE"
    exit 1
fi

# =============================================================================
# Rotate old backups (keep last N days)
# =============================================================================
log_info "Rotating backups older than $KEEP_DAYS days..."

DELETED_COUNT=0
while IFS= read -r old_backup; do
    rm -f "$old_backup"
    DELETED_COUNT=$((DELETED_COUNT + 1))
    log_info "  Deleted: $(basename "$old_backup")"
done < <(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f -mtime +"$KEEP_DAYS" 2>/dev/null)

if [[ $DELETED_COUNT -eq 0 ]]; then
    log_info "No old backups to rotate."
else
    log_info "Deleted $DELETED_COUNT old backup(s)."
fi

# =============================================================================
# Summary
# =============================================================================
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "============================================="
echo "  Backup Summary"
echo "============================================="
echo "  File:           $(basename "$BACKUP_FILE")"
echo "  Size:           $BACKUP_SIZE"
echo "  Location:       $BACKUP_DIR"
echo "  Total backups:  $TOTAL_BACKUPS"
echo "  Total size:     $TOTAL_SIZE"
echo "  Retention:      $KEEP_DAYS days"
echo "============================================="
