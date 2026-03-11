#!/bin/bash
# =============================================================================
# Deploy Internal Market Database to Production VM
# =============================================================================
# This script deploys the ohlcv_universal architecture to production:
# 1. Copy new files to VM
# 2. Update main.py to register new router
# 3. Create ohlcv_universal table
# 4. Migrate existing data
# 5. Restart container
# 6. Verify deployment
#
# Usage: ./scripts/deploy-internal-market-db.sh
# =============================================================================

set -e  # Exit on error

# Configuration
VM_NAME="tadss-vm"
ZONE="us-central1-a"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  Deploy Internal Market Database"
echo "=========================================="
echo ""
echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Confirm deployment
read -p "This will restart the production container. Continue? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1: Copying new files to VM home directory..."
echo "-------------------------------------------"

# Copy all files to VM home directory first
echo "  → Copying files to VM home..."
gcloud compute scp \
  "$PROJECT_ROOT/src/models/ohlcv_universal_model.py" \
  "$PROJECT_ROOT/src/services/market_data_orchestrator.py" \
  "$PROJECT_ROOT/src/api/routes_mtf.py" \
  "$PROJECT_ROOT/src/api/routes_market_data_prefetch.py" \
  "$PROJECT_ROOT/src/scheduler.py" \
  "$PROJECT_ROOT/src/main.py" \
  "$PROJECT_ROOT/scripts/migrate_ohlcv_to_universal.py" \
  $VM_NAME:~/ --zone=$ZONE --quiet

echo "✓ All files copied to VM home"
echo ""

echo "Step 2: Copying files into container..."
echo "-------------------------------------------"

gcloud compute ssh $VM_NAME --zone=$ZONE --command "
# Copy files into container
docker cp ~/ohlcv_universal_model.py tadss:/app/src/models/ohlcv_universal_model.py &&
docker cp ~/market_data_orchestrator.py tadss:/app/src/services/market_data_orchestrator.py &&
docker cp ~/routes_mtf.py tadss:/app/src/api/routes_mtf.py &&
docker cp ~/routes_market_data_prefetch.py tadss:/app/src/api/routes_market_data_prefetch.py &&
docker cp ~/scheduler.py tadss:/app/src/scheduler.py &&
docker cp ~/main.py tadss:/app/src/main.py &&
docker cp ~/migrate_ohlcv_to_universal.py tadss:/app/scripts/migrate_ohlcv_to_universal.py &&
echo '✓ All files copied to container'
" --quiet
echo ""

echo "Step 3: Updating main.py on VM..."
echo "-------------------------------------------"
gcloud compute ssh $VM_NAME --zone=$ZONE --command "
docker exec tadss bash -c '
cd /app/src &&
if ! grep -q \"routes_market_data_prefetch\" main.py; then
  sed -i \"/from src.api.routes_mtf import/a from src.api.routes_market_data_prefetch import router as market_data_prefetch_router\" main.py &&
  sed -i \"/app.include_router(market_data_router/a app.include_router(market_data_prefetch_router, prefix=\\\"/api/v1\\\")\" main.py &&
  echo \"✓ main.py updated\"
else
  echo \"✓ main.py already has prefetch router\"
fi
'
" --quiet
echo ""

echo "Step 4: Creating ohlcv_universal table..."
echo "-------------------------------------------"
gcloud compute ssh $VM_NAME --zone=$ZONE --command "
docker exec tadss python -c '
from src.models.ohlcv_universal_model import create_ohlcv_universal_table
from src.database import db_manager
create_ohlcv_universal_table(db_manager.engine)
print(\"✓ ohlcv_universal table created\")
'
" --quiet
echo ""

echo "Step 5: Migrating existing data..."
echo "-------------------------------------------"
gcloud compute ssh $VM_NAME --zone=$ZONE --command "
cd /app && docker exec tadss python scripts/migrate_ohlcv_to_universal.py
" 2>&1 | tail -20
echo ""

echo "Step 6: Restarting container..."
echo "-------------------------------------------"
gcloud compute ssh $VM_NAME --zone=$ZONE --command "docker restart tadss" --quiet
echo "✓ Container restarted"
echo ""

echo "Step 7: Waiting for startup..."
echo "-------------------------------------------"
echo "Waiting 15 seconds for container to start..."
sleep 15
echo "✓ Startup complete"
echo ""

echo "Step 8: Verifying deployment..."
echo "-------------------------------------------"

# Get VM IP
VM_IP=$(gcloud compute instances list --filter="name=$VM_NAME" --format="value(EXTERNAL_IP)" 2>/dev/null || echo "34.171.241.166")
API_KEY="da970a671d81d0d3fe0214eeb6424423da0d214daddde5c58b1dc0a46b2453aa"

# Test new prefetch endpoint
echo "Testing /api/v1/market-data/prefetch/status..."
PREFETCH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://$VM_IP:8000/api/v1/market-data/prefetch/status" \
  -H "X-API-Key: $API_KEY")

if [ "$PREFETCH_STATUS" = "200" ]; then
  echo "✓ Prefetch endpoint working (HTTP 200)"
else
  echo "⚠️  Prefetch endpoint returned HTTP $PREFETCH_STATUS"
fi

# Test MTF scan (should use ohlcv_universal now)
echo "Testing /api/v1/mtf/opportunities..."
MTF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://$VM_IP:8000/api/v1/mtf/opportunities?trading_style=SWING" \
  -H "X-API-Key: $API_KEY")

if [ "$MTF_STATUS" = "200" ]; then
  echo "✓ MTF scan working (HTTP 200)"
else
  echo "⚠️  MTF scan returned HTTP $MTF_STATUS"
fi

# Check ohlcv_universal table
echo "Checking ohlcv_universal table..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command "
docker exec tadss python -c '
from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal
from sqlalchemy import func
with get_db_context() as db:
  count = db.query(func.count(OHLCVUniversal.id)).scalar()
  print(f\"✓ ohlcv_universal has {count:,} candles\")
'
" --quiet
echo ""

echo "=========================================="
echo "  ✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "VM IP: http://$VM_IP:8000"
echo "API Docs: http://$VM_IP:8000/docs"
echo ""
echo "Next steps:"
echo "1. Test MTF scanner in dashboard: http://$VM_IP:8503"
echo "2. Monitor logs: docker logs tadss -f"
echo "3. After 24-48h monitoring, run cleanup:"
echo "   docker exec tadss python scripts/phase5_cleanup_cache.py"
echo ""
echo "=========================================="
