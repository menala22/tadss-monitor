#!/bin/bash
# scripts/backup-database.sh
# Database Backup Script

set -e

echo "💾 Backing up production database..."
echo ""

# Create backup directory on VM
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    mkdir -p ~/backups
"

# Create backup
BACKUP_FILE="positions-backup-$(date +%Y%m%d-%H%M%S).db"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    cp ~/tadss-monitor/data/positions.db ~/backups/$BACKUP_FILE &&
    echo '✅ Backup created: ~/backups/$BACKUP_FILE'
"

# Download backup locally (optional)
echo ""
read -p "Download backup locally? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    LOCAL_BACKUP="backups/$BACKUP_FILE"
    mkdir -p backups
    gcloud compute scp tadss-vm:~/backups/$BACKUP_FILE $LOCAL_BACKUP --zone us-central1-a
    echo "✅ Backup downloaded to: $LOCAL_BACKUP"
fi

# List recent backups
echo ""
echo "Recent backups on VM:"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    ls -lht ~/backups/*.db | head -10
"

echo ""
echo "✅ Backup complete!"
