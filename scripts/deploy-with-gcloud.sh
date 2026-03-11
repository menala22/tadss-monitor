#!/bin/bash
# Deploy MTF Opportunities using Google Cloud CLI
# No SSH keys needed - uses your Google account authentication

set -e

ZONE="us-central1-a"
INSTANCE="tadss-vm"
PROJECT_PATH="/home/aiagent/tadss-monitor"
CONTAINER_NAME="tadss"

echo "============================================================"
echo "🚀 Deploying MTF Opportunities via gcloud"
echo "============================================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk"
    exit 1
fi

echo "✓ gcloud CLI found"
echo ""

# Check if instance is running
echo "📡 Checking VM instance status..."
INSTANCE_STATUS=$(gcloud compute instances describe $INSTANCE --zone=$ZONE --format="get(status)" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
    echo "❌ VM instance '$INSTANCE' not found in zone '$ZONE'"
    echo "   Available zones: us-central1-a, us-central1-b, us-central1-c, etc."
    exit 1
fi

echo "✓ VM instance found (Status: $INSTANCE_STATUS)"
echo ""

# Files to deploy
FILES=(
    "src/models/mtf_opportunity_model.py"
    "src/services/target_calculator.py"
    "src/services/mtf_opportunity_service.py"
    "src/ui_mtf_opportunities.py"
    "src/ui_mtf_scanner.py"
    "src/scheduler.py"
    "src/migrations/migrate_mtf_opportunities.py"
    "src/migrations/migrate_opportunity_target_columns.py"
)

echo "📦 Copying ${#FILES[@]} files to VM..."
echo ""

# Copy files to VM's /tmp directory
for file in "${FILES[@]}"; do
    echo "  → $file"
    gcloud compute scp "$file" "$INSTANCE:/tmp/$(basename $file)" --zone=$ZONE --quiet
done

echo ""
echo "🔧 Copying files into Docker container..."
# Copy files directly into Docker container
for file in "${FILES[@]}"; do
    FILENAME=$(basename "$file")
    # Determine target directory based on file path
    if [[ "$file" == */models/* ]]; then
        TARGET_DIR="models"
    elif [[ "$file" == */services/* ]]; then
        TARGET_DIR="services"
    elif [[ "$file" == */migrations/* ]]; then
        TARGET_DIR="migrations"
    else
        TARGET_DIR=""
    fi
    
    if [ -n "$TARGET_DIR" ]; then
        gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/$TARGET_DIR/"
    else
        gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/"
    fi
done

# Cleanup temp files
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "rm -f /tmp/*.py"

echo ""
echo "✓ All files copied successfully"
echo ""

# Run migrations inside Docker container
echo "🔧 Running database migrations..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
  docker exec $CONTAINER_NAME python -m src.migrations.migrate_mtf_opportunities run
  docker exec $CONTAINER_NAME python -m src.migrations.migrate_opportunity_target_columns run
"

echo ""
echo "✓ Migration completed"
echo ""

# Restart container
echo "🔄 Restarting Docker container..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker restart $CONTAINER_NAME"

# Wait for container to restart
echo "⏳ Waiting for container to restart (15 seconds)..."
sleep 15

# Check health
echo ""
echo "🏥 Checking API health..."
VM_EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)

if curl -s "http://$VM_EXTERNAL_IP:8000/health" > /dev/null; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed - checking container logs..."
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker logs --tail 30 $CONTAINER_NAME"
fi

echo ""
echo "============================================================"
echo "✅ Deployment Complete!"
echo "============================================================"
echo ""
echo "📊 VM External IP: $VM_EXTERNAL_IP"
echo ""
echo "📊 Next Steps:"
echo "  1. Refresh your dashboard at http://$VM_EXTERNAL_IP:8503"
echo "  2. Navigate to '💼 MTF Opportunities'"
echo "  3. Verify features:"
echo "     ✓ Trading Style column visible"
echo "     ✓ Pullback Quality scores displayed"
echo "     ✓ Alternative Targets table shows"
echo "     ✓ Confidence shows as decimal (0.65)"
echo "     ✓ Best R:R highlighted with 🏆"
echo "     ✓ Highest Confidence highlighted with ⭐"
echo ""
echo "  4. Wait for next hourly scan at :30"
echo "  5. Verify deduplication works (no duplicates)"
echo ""
echo "📝 Files Deployed:"
for file in "${FILES[@]}"; do
    echo "  ✓ $file"
done
echo ""
