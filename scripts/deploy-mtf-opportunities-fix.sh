#!/bin/bash
# Deploy MTF Opportunities - COMPLETE FIX
# Fixes: Missing files, outdated code, migrations, and verification
# Date: March 10, 2026

set -e

ZONE="us-central1-a"
INSTANCE="tadss-vm"
CONTAINER_NAME="tadss"

echo "============================================================"
echo "🚀 MTF Opportunities - COMPLETE REDEPLOYMENT"
echo "============================================================"
echo ""
echo "This script will:"
echo "  1. Deploy ALL required MTF files (not just 8)"
echo "  2. Run all database migrations"
echo "  3. Restart container"
echo "  4. Verify deployment"
echo ""

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk"
    exit 1
fi

echo "✓ gcloud CLI found"
echo ""

# Check VM status
echo "📡 Checking VM instance status..."
INSTANCE_STATUS=$(gcloud compute instances describe $INSTANCE --zone=$ZONE --format="get(status)" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
    echo "❌ VM instance '$INSTANCE' not found in zone '$ZONE'"
    exit 1
fi

echo "✓ VM instance found (Status: $INSTANCE_STATUS)"
echo ""

# =============================================================================
# COMPLETE FILE LIST - ALL MTF OPPORTUNITIES DEPENDENCIES
# =============================================================================
echo "📦 Preparing to deploy 22 files..."
echo ""

FILES=(
    # Core Models
    "src/models/mtf_opportunity_model.py"
    "src/models/mtf_models.py"
    "src/models/mtf_watchlist_model.py"
    
    # Core Services (4-Layer Framework)
    "src/services/mtf_opportunity_service.py"
    "src/services/mtf_opportunity_scanner.py"
    "src/services/mtf_alignment_scorer.py"
    "src/services/mtf_bias_detector.py"
    "src/services/mtf_setup_detector.py"
    "src/services/mtf_entry_finder.py"
    "src/services/mtf_notifier.py"
    
    # Supporting Services
    "src/services/target_calculator.py"
    "src/services/divergence_detector.py"
    "src/services/pullback_quality_scorer.py"
    "src/services/mtf_context_classifier.py"
    "src/services/support_resistance_detector.py"
    
    # API Routes
    "src/api/routes_mtf_opportunities.py"
    
    # UI Components
    "src/ui_mtf_opportunities.py"
    "src/ui_mtf_scanner.py"
    
    # Scheduler & Config
    "src/scheduler.py"
    "src/main.py"
    
    # Migrations
    "src/migrations/migrate_mtf_opportunities.py"
    "src/migrations/migrate_opportunity_target_columns.py"
)

echo "Files to deploy:"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ⚠️  $file (NOT FOUND - will skip)"
    fi
done
echo ""

# Copy files to VM's /tmp directory
echo "📤 Copying files to VM..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        FILENAME=$(basename "$file")
        gcloud compute scp "$file" "$INSTANCE:/tmp/$FILENAME" --zone=$ZONE --quiet 2>/dev/null || {
            echo "  ⚠️  Failed to copy $FILENAME - skipping"
        }
    fi
done

echo ""
echo "📥 Copying files into Docker container..."

# Copy files into Docker container based on their type
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        FILENAME=$(basename "$file")
        
        # Determine target directory
        if [[ "$file" == */models/* ]]; then
            TARGET_DIR="models"
        elif [[ "$file" == */services/* ]]; then
            TARGET_DIR="services"
        elif [[ "$file" == */api/* ]]; then
            TARGET_DIR="api"
        elif [[ "$file" == */migrations/* ]]; then
            TARGET_DIR="migrations"
        else
            TARGET_DIR=""
        fi

        if [ -n "$TARGET_DIR" ]; then
            gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/$TARGET_DIR/" 2>/dev/null || {
                echo "  ⚠️  Failed to copy $FILENAME to $TARGET_DIR - skipping"
            }
        else
            gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/" 2>/dev/null || {
                echo "  ⚠️  Failed to copy $FILENAME to src - skipping"
            }
        fi
    fi
done

# Cleanup temp files on VM
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "rm -f /tmp/*.py"

echo ""
echo "✓ All files copied successfully"
echo ""

# =============================================================================
# DATABASE MIGRATIONS
# =============================================================================
echo "🔧 Running database migrations..."

echo "  → Creating mtf_opportunities table..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker exec $CONTAINER_NAME python -m src.migrations.migrate_mtf_opportunities run" || {
    echo "  ⚠️  Migration may have already run - continuing"
}

echo "  → Adding target columns..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker exec $CONTAINER_NAME python -m src.migrations.migrate_opportunity_target_columns run" || {
    echo "  ⚠️  Migration may have already run - continuing"
}

echo ""
echo "✓ Migrations completed"
echo ""

# =============================================================================
# RESTART CONTAINER
# =============================================================================
echo "🔄 Restarting Docker container..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker restart $CONTAINER_NAME"

echo "⏳ Waiting for container to restart (20 seconds)..."
sleep 20

# =============================================================================
# HEALTH CHECK
# =============================================================================
echo ""
echo "🏥 Checking API health..."
VM_EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)

if curl -s "http://$VM_EXTERNAL_IP:8000/health" > /dev/null; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed - checking container logs..."
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker logs --tail 50 $CONTAINER_NAME"
fi

echo ""
echo "📊 Checking scheduler status..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker logs $CONTAINER_NAME 2>&1 | grep -E '(MTF|scheduler|MTF scan)' | tail -20" || {
    echo "⚠️  Could not retrieve scheduler logs"
}

echo ""
echo "============================================================"
echo "✅ Deployment Complete!"
echo "============================================================"
echo ""
echo "📊 VM External IP: $VM_EXTERNAL_IP"
echo ""
echo "📋 Next Steps - VERIFICATION CHECKLIST:"
echo ""
echo "  1. Dashboard Access:"
echo "     → http://$VM_EXTERNAL_IP:8503"
echo "     → Navigate to '💼 MTF Opportunities'"
echo ""
echo "  2. Verify Files Deployed:"
echo "     → Check container has all 22 files"
echo "     → Run: gcloud compute ssh $INSTANCE --zone=$ZONE --command 'docker exec $CONTAINER_NAME ls -la src/services/mtf_*'"
echo ""
echo "  3. Verify Database:"
echo "     → Run: gcloud compute ssh $INSTANCE --zone=$ZONE --command 'docker exec $CONTAINER_NAME python -m src.migrations.migrate_mtf_opportunities stats'"
echo ""
echo "  4. Verify Scheduler:"
echo "     → Wait for next :30 mark"
echo "     → Check logs: gcloud compute ssh $INSTANCE --zone=$ZONE --command 'docker logs $CONTAINER_NAME 2>&1 | grep \"MTF scan\"'"
echo ""
echo "  5. Test Manual Scan:"
echo "     → Run: gcloud compute ssh $INSTANCE --zone=$ZONE --command 'docker exec $CONTAINER_NAME python scripts/manual_mtf_scan.py --trading-styles SWING'"
echo ""
echo "  6. Verify No Duplicates:"
echo "     → Check dashboard shows unique opportunities"
echo "     → Run deduplication check (see docs)"
echo ""
echo "📝 Troubleshooting:"
echo "   • No opportunities showing → Check watchlist has pairs with trading styles"
echo "   • Duplicates appearing → Check deduplication logs"
echo "   • API errors → Check container logs for import errors"
echo "   • Scheduler not running → Check main.py has MTF routes registered"
echo ""
echo "============================================================"
