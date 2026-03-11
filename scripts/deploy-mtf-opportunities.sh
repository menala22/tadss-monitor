#!/bin/bash
# Deploy MTF Opportunities feature to production VM
# 
# This script copies the new files to the VM and restarts the Docker container.

set -e

# Configuration
VM_IP="34.171.241.166"
CONTAINER_NAME="tadss"
PROJECT_PATH="/app"

echo "🚀 Deploying MTF Opportunities to production VM ($VM_IP)"
echo "=" * 60

# Check if VM is reachable
echo "📡 Checking VM connectivity..."
if ! ping -c 1 "$VM_IP" > /dev/null 2>&1; then
    echo "❌ Cannot reach VM at $VM_IP"
    exit 1
fi
echo "✓ VM is reachable"

# Files to deploy
FILES=(
    "src/models/mtf_opportunity_model.py"
    "src/migrations/migrate_mtf_opportunities.py"
    "src/migrations/migrate_watchlist_trading_styles.py"
    "src/services/mtf_opportunity_service.py"
    "src/api/routes_mtf_opportunities.py"
    "src/ui_mtf_opportunities.py"
    "src/scheduler.py"
    "src/services/mtf_notifier.py"
    "src/main.py"
    "src/models/mtf_watchlist_model.py"
    "src/ui.py"
)

echo ""
echo "📦 Copying files to VM..."
for file in "${FILES[@]}"; do
    echo "  → $file"
    scp "$file" "root@$VM_IP:$PROJECT_PATH/$file"
done

# Run migration on VM
echo ""
echo "🔧 Running database migrations on VM..."
ssh "root@$VM_IP" "cd $PROJECT_PATH && python -m src.migrations.migrate_mtf_opportunities run"
ssh "root@$VM_IP" "cd $PROJECT_PATH && python -m src.migrations.migrate_watchlist_trading_styles run"

# Restart container
echo ""
echo "🔄 Restarting Docker container..."
ssh "root@$VM_IP" "docker restart $CONTAINER_NAME"

# Wait for container to start
echo "⏳ Waiting for container to start (10 seconds)..."
sleep 10

# Check health
echo ""
echo "🏥 Checking API health..."
if curl -s "http://$VM_IP:8000/health" > /dev/null; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed - check container logs"
    ssh "root@$VM_IP" "docker logs --tail 50 $CONTAINER_NAME"
fi

echo ""
echo "=" * 60
echo "✅ Deployment complete!"
echo ""
echo "📊 Next steps:"
echo "  1. Refresh your dashboard: http://localhost:8503"
echo "  2. Navigate to '💼 MTF Opportunities'"
echo "  3. Run manual scan to test: python scripts/manual_mtf_scan.py"
echo ""
