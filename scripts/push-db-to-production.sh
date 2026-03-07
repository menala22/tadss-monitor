#!/bin/bash
# =============================================================================
# TA-DSS Database Sync - Push Local to Production
# =============================================================================
# Pushes local SQLite database to Google Cloud VM
#
# Usage: ./scripts/push-db-to-production.sh
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}TA-DSS Database Sync - Local → Production${NC}"
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

# Check if local database exists
if [ ! -f "$LOCAL_DB" ]; then
    echo -e "${RED}❌ Error: Local database not found at ${LOCAL_DB}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Local database found${NC}"

# Show local database stats
echo ""
echo -e "${CYAN}Local Database Stats:${NC}"
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
print(f"  - Positions: {positions}")
print(f"  - Alert History: {alerts}")
print(f"  - Signal Changes: {changes}")
EOF

echo ""
echo -e "${YELLOW}⚠️  WARNING: This will OVERWRITE the production database!${NC}"
echo ""
read -p "Continue? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted${NC}"
    exit 0
fi

echo ""
echo -e "${CYAN}Step 1: Creating database backup on VM...${NC}"

# Create backup of remote database before overwriting
ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  if [ -f ~/tadss-monitor/data/positions.db ]; then
    BACKUP_NAME="~/tadss-monitor/data/positions.db.backup.$(date +%Y%m%d_%H%M%S)"
    cp ~/tadss-monitor/data/positions.db "$BACKUP_NAME"
    echo "✓ Backup created: $BACKUP_NAME"
  else
    echo "⚠️  No existing database found (fresh install)"
  fi
ENDSSH

echo ""
echo -e "${CYAN}Step 2: Stopping remote scheduler (if running)...${NC}"

# Stop the container to release database lock
ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  if docker ps --format '{{.Names}}' | grep -q "tadss"; then
    echo "Stopping tadss container..."
    docker stop tadss
    echo "✓ Container stopped"
  else
    echo "⚠️  No running container found"
  fi
ENDSSH

echo ""
echo -e "${CYAN}Step 3: Copying database to VM...${NC}"

# Copy database file
scp -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no \
    "$LOCAL_DB" \
    "$VM_USER@$VM_EXTERNAL_IP:$REMOTE_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database copied successfully${NC}"
else
    echo -e "${RED}❌ Failed to copy database${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Step 4: Setting permissions...${NC}"

ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  chmod 644 ~/tadss-monitor/data/positions.db
  chown $(whoami):$(whoami) ~/tadss-monitor/data/positions.db
  echo "✓ Permissions set"
ENDSSH

echo ""
echo -e "${CYAN}Step 5: Restarting container...${NC}"

ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  if docker ps -a --format '{{.Names}}' | grep -q "tadss"; then
    echo "Starting tadss container..."
    docker start tadss
    echo "✓ Container started"
  else
    echo "⚠️  No container found - starting fresh"
  fi
ENDSSH

echo ""
echo -e "${CYAN}Step 6: Verifying sync...${NC}"

# Wait a moment for container to start
sleep 3

# Check remote database stats
ssh -i "$VM_SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_EXTERNAL_IP" << 'ENDSSH'
  echo "Production Database Stats:"
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
ENDSSH

echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}✅ Database Sync Complete!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Check your dashboard to verify data is visible"
echo "2. Test API endpoints to ensure they work"
echo "3. Monitor logs for any errors"
echo ""
echo -e "${CYAN}Backup location:${NC}"
echo "  VM: ~/tadss-monitor/data/positions.db.backup.*"
echo ""
