#!/bin/bash
#
# PostgreSQL Restore from Mega Cloud Script
#
# Restores a PostgreSQL database backup from Mega cloud storage.
#
# Usage:
#   ./restore-from-mega.sh [options]
#
# Options:
#   -f, --file FILENAME       Backup filename to restore (required)
#   -h, --host HOST          Database host (default: localhost)
#   -p, --port PORT          Database port (default: 5432)
#   -u, --user USER          Database user (default: goalixa)
#   -d, --database DB        Database name (default: goalixa)
#   --dry-run                Show what would be done without executing
#   --help                   Show this help message
#
# Environment Variables:
#   POSTGRES_PASSWORD        Database password (required if not interactive)
#   MEGA_EMAIL              Mega account email (required)
#   MEGA_PASSWORD           Mega account password (required)
#   MEGA_BACKUP_PATH        Remote Mega path for backups (default: /goalixa-backups)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_FILE=""
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-goalixa}"
DB_NAME="${DB_NAME:-goalixa}"
DRY_RUN=false
MEGA_BACKUP_PATH="${MEGA_BACKUP_PATH:-/goalixa-backups}"
TEMP_DIR=$(mktemp -d)

# Cleanup on exit
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
    # Always logout from Mega
    mega-logout 2>/dev/null || true
}
trap cleanup EXIT

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

# Show usage
usage() {
    cat << EOF
PostgreSQL Restore from Mega Cloud

Usage: $0 [options]

Options:
    -f, --file FILENAME       Backup filename to restore (required)
    -h, --host HOST          Database host (default: localhost)
    -p, --port PORT          Database port (default: 5432)
    -u, --user USER          Database user (default: goalixa)
    -d, --database DB        Database name (default: goalixa)
    --dry-run                Show what would be done without executing
    --help                   Show this help message

Environment Variables:
    POSTGRES_PASSWORD        Database password (required if not interactive)
    MEGA_EMAIL              Mega account email (required)
    MEGA_PASSWORD           Mega account password (required)
    MEGA_BACKUP_PATH        Remote Mega path for backups (default: /goalixa-backups)

Examples:
    # Restore latest backup
    ./restore-from-mega.sh -f goalixa_20260501_140000.sql.gz

    # Restore to specific host
    ./restore-from-mega.sh -f goalixa_20260501_140000.sql.gz -h prod-db.example.com

    # Dry run (preview without restoring)
    ./restore-from-mega.sh -f goalixa_20260501_140000.sql.gz --dry-run

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                BACKUP_FILE="$2"
                shift 2
                ;;
            -h|--host)
                DB_HOST="$2"
                shift 2
                ;;
            -p|--port)
                DB_PORT="$2"
                shift 2
                ;;
            -u|--user)
                DB_USER="$2"
                shift 2
                ;;
            -d|--database)
                DB_NAME="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Validate configuration
validate_config() {
    if [[ -z "$BACKUP_FILE" ]]; then
        error "Backup filename is required (-f option)"
        usage
        exit 1
    fi

    if [[ -z "${MEGA_EMAIL:-}" ]]; then
        error "MEGA_EMAIL environment variable is required"
        exit 1
    fi

    if [[ -z "${MEGA_PASSWORD:-}" ]]; then
        error "MEGA_PASSWORD environment variable is required"
        exit 1
    fi

    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        warning "POSTGRES_PASSWORD not set in environment"
        read -sp "Enter PostgreSQL password: " POSTGRES_PASSWORD
        echo
        export POSTGRES_PASSWORD
    fi
}

# List available backups
list_backups() {
    log "Listing available backups in Mega..."

    if ! mega-login "$MEGA_EMAIL" "$MEGA_PASSWORD" >/dev/null 2>&1; then
        error "Failed to login to Mega"
        exit 1
    fi

    local backups=$(mega-ls -l "$MEGA_BACKUP_PATH" 2>/dev/null | grep 'goalixa_.*\.sql\.gz' | awk '{print $NF}')

    if [[ -z "$backups" ]]; then
        error "No backups found in $MEGA_BACKUP_PATH"
        return 1
    fi

    echo
    echo "Available backups:"
    echo "$backups" | nl
    echo

    mega-logout >/dev/null 2>&1
    return 0
}

# Download backup from Mega
download_backup() {
    local backup_file=$1
    local local_path="$TEMP_DIR/$backup_file"

    log "Logging in to Mega..."
    if ! mega-login "$MEGA_EMAIL" "$MEGA_PASSWORD" >/dev/null 2>&1; then
        error "Failed to login to Mega"
        return 1
    fi

    log "Downloading backup: $backup_file"
    if ! mega-get "$MEGA_BACKUP_PATH/$backup_file" "$local_path" >/dev/null 2>&1; then
        error "Failed to download backup from Mega"
        return 1
    fi

    if [[ ! -f "$local_path" ]]; then
        error "Downloaded file not found: $local_path"
        return 1
    fi

    success "Downloaded backup: $(du -h "$local_path" | cut -f1)"
    echo "$local_path"
}

# Decompress backup
decompress_backup() {
    local compressed_file=$1
    local decompressed_file="${compressed_file%.gz}"

    log "Decompressing backup..."

    if ! gunzip -c "$compressed_file" > "$decompressed_file"; then
        error "Failed to decompress backup"
        return 1
    fi

    if [[ ! -f "$decompressed_file" ]]; then
        error "Decompressed file not found: $decompressed_file"
        return 1
    fi

    local decompressed_size=$(du -h "$decompressed_file" | cut -f1)
    success "Decompressed backup: $decompressed_size"
    echo "$decompressed_file"
}

# Get row counts before restore
get_table_counts() {
    local db=$1
    log "Getting pre-restore table counts from $db..."

    export PGPASSWORD="$POSTGRES_PASSWORD"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT
            tablename,
            (pg_total_relation_size(schemaname||'.'||tablename) / 1024 / 1024)::int as size_mb
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    " 2>/dev/null || true
}

# Restore database
restore_database() {
    local sql_file=$1

    log "Starting restore to database: $DB_NAME at $DB_HOST:$DB_PORT"

    if [[ "$DRY_RUN" == true ]]; then
        log "(DRY RUN) Would restore: $sql_file"
        log "(DRY RUN) File size: $(du -h "$sql_file" | cut -f1)"
        return 0
    fi

    # Confirmation prompt
    echo
    warning "This will restore the database: $DB_NAME"
    warning "Any existing data in $DB_NAME will be replaced"
    read -p "Do you want to continue? (yes/no): " confirmation

    if [[ "$confirmation" != "yes" ]]; then
        log "Restore cancelled"
        return 1
    fi

    echo

    export PGPASSWORD="$POSTGRES_PASSWORD"

    log "Restoring from: $sql_file"
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$sql_file"; then
        error "Database restore failed"
        return 1
    fi

    success "Database restored successfully"
    return 0
}

# Verify restoration
verify_restoration() {
    local db=$1

    log "Verifying restoration..."

    export PGPASSWORD="$POSTGRES_PASSWORD"

    # Get table counts
    local table_counts=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT count(*)::int as table_count
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
    " 2>/dev/null)

    if [[ -z "$table_counts" || "$table_counts" -eq 0 ]]; then
        error "No tables found in database - restoration may have failed"
        return 1
    fi

    success "Found $table_counts tables in restored database"

    # Sample row counts
    log "Sample table row counts:"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$db" -t -c "
        SELECT
            tablename,
            (SELECT count(*) FROM (SELECT 1 FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND c.relname = tablename LIMIT 1000000) t)::int as row_count
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY row_count DESC LIMIT 10;
    " 2>/dev/null || true

    return 0
}

# Main execution
main() {
    log "PostgreSQL Restore from Mega Cloud"

    parse_args "$@"
    validate_config

    log "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    log "Backup file: $BACKUP_FILE"

    if [[ "$DRY_RUN" == true ]]; then
        log "DRY RUN mode enabled"
    fi

    echo

    # Download backup
    local backup_path=$(download_backup "$BACKUP_FILE")
    if [[ -z "$backup_path" ]]; then
        error "Failed to download backup"
        exit 1
    fi

    # Decompress
    local sql_file=$(decompress_backup "$backup_path")
    if [[ -z "$sql_file" ]]; then
        error "Failed to decompress backup"
        exit 1
    fi

    # Restore
    if ! restore_database "$sql_file"; then
        if [[ "$DRY_RUN" != true ]]; then
            exit 1
        fi
    fi

    # Verify (skip in dry run)
    if [[ "$DRY_RUN" != true ]]; then
        echo
        if ! verify_restoration "$DB_NAME"; then
            warning "Verification found issues - please check the database"
        fi
    fi

    echo
    success "Restore process completed"
}

main "$@"
