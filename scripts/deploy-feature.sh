#!/bin/bash
# Full Feature Deployment Script
# Usage: ./deploy-feature.sh "Feature Name" file1.py file2.py ...

set -e

if [ -z "$1" ]; then
    echo "❌ Usage: ./deploy-feature.sh \"Feature Name\" file1.py file2.py ..."
    echo "Example: ./deploy-feature.sh \"MTF Opportunities\" src/models/mtf_opportunity_model.py src/services/mtf_opportunity_service.py"
    exit 1
fi

FEATURE_NAME=$1
shift  # Remove first argument, rest are files
FILES=("$@")

ZONE="us-central1-a"
INSTANCE="tadss-vm"
CONTAINER_NAME="tadss"

echo "=================================================="
echo "🚀 Deploying Feature: $FEATURE_NAME"
echo "=================================================="
echo ""

# Verify all files exist
echo "📋 Verifying files..."
for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ File not found: $file"
        exit 1
    fi
    echo "  ✓ $file"
done
echo ""

# Copy files to VM
echo "📦 Copying ${#FILES[@]} files to VM..."
for file in "${FILES[@]}"; do
    echo "  → $file"
    gcloud compute scp "$file" "$INSTANCE:/tmp/$(basename $file)" --zone=$ZONE --quiet
done
echo ""

# Copy into container
echo "🔧 Installing files into container..."
for file in "${FILES[@]}"; do
    FILENAME=$(basename "$file")
    if [[ "$file" == */models/* ]]; then TARGET_DIR="models"
    elif [[ "$file" == */services/* ]]; then TARGET_DIR="services"
    elif [[ "$file" == */api/* ]]; then TARGET_DIR="api"
    elif [[ "$file" == */migrations/* ]]; then TARGET_DIR="migrations"
    else TARGET_DIR=""
    fi
    
    if [ -n "$TARGET_DIR" ]; then
        gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
            docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/$TARGET_DIR/
        "
    else
        gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
            docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/
        "
    fi
done
echo ""

# Clear cache
echo "🧹 Clearing Python cache..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
    docker exec $CONTAINER_NAME find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
"
echo ""

# Run migrations
echo "🔧 Running database migrations..."
MIGRATION_COUNT=0
for file in "${FILES[@]}"; do
    if [[ "$file" == */migrations/* ]]; then
        MIGRATION_NAME=$(basename $file .py)
        echo "  → Running $MIGRATION_NAME"
        gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
            docker exec $CONTAINER_NAME python -m src.$MIGRATION_NAME run
        " || echo "⚠️  Migration $MIGRATION_NAME may have already run"
        MIGRATION_COUNT=$((MIGRATION_COUNT + 1))
    fi
done

if [ $MIGRATION_COUNT -eq 0 ]; then
    echo "  (No migrations to run)"
fi
echo ""

# Restart
echo "🔄 Restarting container..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker restart $CONTAINER_NAME"

echo "⏳ Waiting 20 seconds for restart..."
sleep 20

# Health check
echo ""
echo "🏥 Checking API health..."
VM_IP=$(gcloud compute instances describe $INSTANCE --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

if curl -s "http://$VM_IP:8000/health" > /dev/null; then
    echo "✅ API is healthy!"
else
    echo "⚠️  API health check failed!"
    echo "Checking logs..."
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker logs --tail 50 $CONTAINER_NAME" | tail -30
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Feature: $FEATURE_NAME"
echo "Files deployed: ${#FILES[@]}"
echo "Migrations run: $MIGRATION_COUNT"
echo ""
echo "📊 Dashboard: http://$VM_IP:8503"
echo "📋 API Docs: http://$VM_IP:8000/docs"
echo ""
echo "Next steps:"
echo "1. Refresh dashboard to see new features"
echo "2. Test the deployed functionality"
echo "3. Monitor logs for any errors"
echo ""
