#!/bin/bash
# Quick Deploy Script for Single File Changes
# Usage: ./quick-deploy.sh src/path/to/file.py

set -e

if [ -z "$1" ]; then
    echo "❌ Usage: ./quick-deploy.sh <file_path>"
    echo "Example: ./quick-deploy.sh src/services/mtf_opportunity_service.py"
    exit 1
fi

FILE=$1
ZONE="us-central1-a"
INSTANCE="tadss-vm"
CONTAINER_NAME="tadss"

if [ ! -f "$FILE" ]; then
    echo "❌ File not found: $FILE"
    exit 1
fi

FILENAME=$(basename $FILE)

echo "=================================================="
echo "🚀 Quick Deploy: $FILE"
echo "=================================================="
echo ""

# Copy to VM
echo "📦 Copying to VM..."
gcloud compute scp "$FILE" "$INSTANCE:/tmp/$FILENAME" --zone=$ZONE --quiet

# Determine target directory
if [[ "$FILE" == */models/* ]]; then DIR="models"
elif [[ "$FILE" == */services/* ]]; then DIR="services"
elif [[ "$FILE" == */api/* ]]; then DIR="api"
elif [[ "$FILE" == */migrations/* ]]; then DIR="migrations"
else DIR=""
fi

# Copy into container
echo "🔧 Installing in container..."
if [ -n "$DIR" ]; then
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
        docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/$DIR/
    "
else
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
        docker cp /tmp/$FILENAME $CONTAINER_NAME:/app/src/
    "
fi

# Clear cache
echo "🧹 Clearing Python cache..."
gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "
    docker exec $CONTAINER_NAME find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
"

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
    gcloud compute ssh "$INSTANCE" --zone=$ZONE --command "docker logs --tail 30 $CONTAINER_NAME" | tail -20
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "📊 Dashboard: http://$VM_IP:8503"
echo "📋 API Docs: http://$VM_IP:8000/docs"
echo ""
