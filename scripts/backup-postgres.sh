#!/bin/bash
# 💾 PostgreSQL backup script for Budget Bot
# This script creates compressed backups with rotation

set -e

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
MAX_BACKUPS=10

# Database connection
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_USER=${POSTGRES_USER:-budget_user}
POSTGRES_DB=${POSTGRES_DB:-budget_bot}

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/budget_bot_backup_$DATE.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"

log "Starting backup of database: $POSTGRES_DB"

# Create database backup
if pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --verbose > "$BACKUP_FILE" 2>/dev/null; then
    log "✅ Database dump created: $BACKUP_FILE"
    
    # Compress backup
    if gzip "$BACKUP_FILE"; then
        log "✅ Backup compressed: $COMPRESSED_FILE"
        
        # Get file size
        BACKUP_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        log "📊 Backup size: $BACKUP_SIZE"
        
        # Verify backup integrity
        if gunzip -t "$COMPRESSED_FILE" 2>/dev/null; then
            log "✅ Backup integrity verified"
        else
            log "❌ Backup integrity check failed!"
            exit 1
        fi
    else
        log "❌ Failed to compress backup"
        exit 1
    fi
else
    log "❌ Failed to create database dump"
    exit 1
fi

# Remove old backups (by date)
log "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "budget_bot_backup_*.sql.gz" -mtime +$RETENTION_DAYS -print | wc -l)
find "$BACKUP_DIR" -name "budget_bot_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

if [ "$DELETED_COUNT" -gt 0 ]; then
    log "🗑️ Deleted $DELETED_COUNT old backup(s)"
fi

# Keep only latest N backups (safety measure)
CURRENT_COUNT=$(find "$BACKUP_DIR" -name "budget_bot_backup_*.sql.gz" | wc -l)
if [ "$CURRENT_COUNT" -gt "$MAX_BACKUPS" ]; then
    log "🧹 Too many backups ($CURRENT_COUNT), keeping only latest $MAX_BACKUPS"
    find "$BACKUP_DIR" -name "budget_bot_backup_*.sql.gz" -printf '%T@ %p\n' | \
        sort -n | \
        head -n -$MAX_BACKUPS | \
        cut -d' ' -f2- | \
        xargs rm -f
fi

# List current backups
log "📋 Current backups:"
ls -lah "$BACKUP_DIR"/budget_bot_backup_*.sql.gz 2>/dev/null | while read -r line; do
    log "   $line"
done

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "💾 Total backup size: $TOTAL_SIZE"

log "✅ Backup completed successfully: $COMPRESSED_FILE"

# Optional: Send notification (if webhook URL is set)
if [ -n "$BACKUP_WEBHOOK_URL" ]; then
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"✅ Budget Bot backup completed\",
            \"attachments\": [{
                \"color\": \"good\",
                \"fields\": [
                    {\"title\": \"Database\", \"value\": \"$POSTGRES_DB\", \"short\": true},
                    {\"title\": \"Size\", \"value\": \"$BACKUP_SIZE\", \"short\": true},
                    {\"title\": \"File\", \"value\": \"$(basename $COMPRESSED_FILE)\", \"short\": false}
                ]
            }]
        }" \
        "$BACKUP_WEBHOOK_URL" 2>/dev/null || log "⚠️ Failed to send backup notification"
fi