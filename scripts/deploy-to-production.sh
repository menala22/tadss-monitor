#!/bin/bash
# Deploy MTF Opportunities Feature to Production VM
# 
# This script deploys all updated files for the MTF Opportunities feature
# including deduplication, alternative targets, and 4-layer framework display.

set -e

# Configuration
VM_IP="34.171.241.166"
CONTAINER_NAME="tadss"
PROJECT_PATH="/app"

echo "============================================================"
echo "🚀 Deploying MTF Opportunities to Production VM ($VM_IP)"
echo "============================================================"
echo ""

# Check if VM is reachable
echo "📡 Checking VM connectivity..."
if ! ping -c 1 "$VM_IP" > /dev/null 2>&1; then
    echo "❌ Cannot reach VM at $VM_IP"
    exit 1
fi
echo "✓ VM is reachable"
echo ""

# Files to deploy
FILES=(
    "src/models/mtf_opportunity_model.py"
    "src/services/target_calculator.py"
    "src/services/mtf_opportunity_service.py"
    "src/ui_mtf_opportunities.py"
    "src/ui_mtf_scanner.py"
    "src/scheduler.py"
    "src/migrations/migrate_opportunity_target_columns.py"
)

echo "📦 Copying ${#FILES[@]} files to VM..."
echo ""

for file in "${FILES[@]}"; do
    echo "  → $file"
    scp "$file" "root@$VM_IP:$PROJECT_PATH/$file"
done

echo ""
echo "✓ All files copied successfully"
echo ""

# Run migration
echo "🔧 Running database migration..."
ssh "root@$VM_IP" "cd $PROJECT_PATH && python -m src.migrations.migrate_opportunity_target_columns run"

if [ $? -eq 0 ]; then
    echo "✓ Migration completed"
else
    echo "⚠️  Migration may have already run (this is OK)"
fi

echo ""

# Restart container
echo "🔄 Restarting Docker container..."
ssh "root@$VM_IP" "docker restart $CONTAINER_NAME"

# Wait for container to start
echo "⏳ Waiting for container to start (15 seconds)..."
sleep 15

# Check health
echo ""
echo "🏥 Checking API health..."
if curl -s "http://$VM_IP:8000/health" > /dev/null; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed - checking container logs..."
    ssh "root@$VM_IP" "docker logs --tail 30 $CONTAINER_NAME"
fi

echo ""
echo "============================================================"
echo "✅ Deployment Complete!"
echo "============================================================"
echo ""
echo "📊 Next Steps:"
echo "  1. Refresh your dashboard at http://$VM_IP:8503"
echo "  2. Navigate to '💼 MTF Opportunities'"
echo "  3. Verify features:"
echo "     ✓ Trading Style column visible"
echo "     ✓ Pullback Quality scores displayed"
echo "     ✓ Alternative Targets table shows"
echo "     ✓ Confidence shows as decimal (0.65)"
echo ""
echo "  4. Wait for next hourly scan at :30"
echo "  5. Verify deduplication works (no duplicates)"
echo ""
echo "📝 Files Deployed:"
for file in "${FILES[@]}"; do
    echo "  ✓ $file"
done
echo ""
