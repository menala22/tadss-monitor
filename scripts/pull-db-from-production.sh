#!/bin/bash
# =============================================================================
# TA-DSS Database Sync - Pull Production to Local
# =============================================================================
# Downloads production SQLite database from Google Cloud VM to local
#
# Usage: ./scripts/pull-db-from-production.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}TA-DSS Database Sync - Production → Local${NC}"
echo -e "${CYAN}==============================================${NC}"
echo ""

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from .env file..."
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Get VM details
VM_EXTERNAL_IP="${VM_EXTERNAL_IP:-}"
VM_USER="${VM_USER:-$USER}"
VM_SSH_KEY="${VM_SSH_KEY:-~/.ssh/google_compute_engine}"
REMOTE_PATH="~/tadss-monitor/data/positions.db"

# Check if VM IP is configured
if [ -z "$VM_EXTERNAL_IP" ]; then
    echo -e "${RED}❌ Error: VM_EXTERNAL_IP not set in .env file${NC}"
    echo "Please add your VM IP to .env:"
    echo "  VM_EXTERNAL_IP=your_vm_ip_here"
    exit 1
fi

echo -e "${GREEN}✓ VM IP loaded: ${VM_EXTERNAL_IP}${NC}"
echo ""

# Local database path
LOCAL_DB="$PROJECT_ROOT/data/positions.db"
LOCAL_BACKUP_DIR="$PROJECT_ROOT/data/backups"

# Create backup directory if it doesn't exist
mkdir -p "$LOCAL_BACKUP_DIR"

echo -e "${CYAN}Step 1: Checking production database...${NC}"

# Check remote database stats
ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  if [ -f ~/tadss-monitor/data/positions.db ]; then
    echo "✓ Production database found"
    cd ~/tadss-monitor
    docker exec tadss python3 -c "
import sqlite3
conn = sqlite3.connect('data/positions.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM positions')
positions = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM alert_history')
alerts = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM signal_changes')
changes = cursor.fetchone()[0]
conn.close()
print(f'  - Positions: {positions}')
print(f'  - Alert History: {alerts}')
print(f'  - Signal Changes: {changes}')
"
  else
    echo "❌ Production database not found!"
    exit 1
  fi
ENDSSH

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to read production database${NC}"
    exit 1
fi

echo ""

# Check if local database exists and create backup
if [ -f "$LOCAL_DB" ]; then
    echo -e "${CYAN}Step 2: Creating local backup...${NC}"
    
    BACKUP_NAME="positions.db.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$LOCAL_DB" "$LOCAL_BACKUP_DIR/$BACKUP_NAME"
    
    echo -e "${GREEN}✓ Local backup created: ${BACKUP_NAME}${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  No local database found (fresh download)${NC}"
    echo ""
fi

echo -e "${CYAN}Step 3: Downloading database from production...${NC}"

# Copy database file from VM to local
scp -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no \
    "$VM_USER@$VM_EXTERNAL_IP:$REMOTE_PATH" \
    "$LOCAL_DB"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database downloaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to download database${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Step 4: Verifying local database...${NC}"

# Show local database stats
python3 << EOF
import sqlite3
conn = sqlite3.connect('${LOCAL_DB}')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM positions')
positions = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM alert_history')
alerts = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM signal_changes')
changes = cursor.fetchone()[0]
conn.close()
print(f"Local Database Stats:")
print(f"  - Positions: {positions}")
print(f"  - Alert History: {alerts}")
print(f"  - Signal Changes: {changes}")
EOF

echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}✅ Database Sync Complete!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  Production → Local database copied successfully"
echo ""
echo -e "${YELLOW}Backup location:${NC}"
echo "  Local: ${LOCAL_BACKUP_DIR}/positions.db.backup.*"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart your local API server if running"
echo "2. Refresh your local dashboard to see updated data"
echo "3. Verify positions match production"
echo ""
