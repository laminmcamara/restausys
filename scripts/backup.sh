#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups"

mkdir -p $BACKUP_DIR

echo "Backing up database..."
cp db.sqlite3 $BACKUP_DIR/db_$TIMESTAMP.sqlite3

echo "Backing up media..."
tar -czf $BACKUP_DIR/media_$TIMESTAMP.tar.gz media/

echo "Backup completed."