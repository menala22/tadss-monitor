#!/bin/bash
# scripts/deploy-to-production.sh
# Production Deployment Script for TA-DSS

set -e  # Exit on error

echo "========================================"
echo "TA-DSS Production Deployment"
echo "========================================"
echo ""

# 1. Run pre-deployment checks
echo "📋 Running pre-deployment checks..."
./scripts/pre-deploy-check.sh
echo ""

# 2. Get current version
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
echo "📦 Current version: $CURRENT_TAG"
echo ""

# 3. Create deployment tag
DEPLOY_TAG="v$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)"
echo "🏷️  Creating deployment tag: $DEPLOY_TAG"
git tag -a $DEPLOY_TAG -m "Production deployment $(date)"
git push origin $DEPLOY_TAG
echo ""

# 4. Pull latest on VM
echo "📦 Pulling latest code on production VM..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    cd ~/tadss-monitor &&
    git pull origin main
"
echo ""

# 5. Backup database
echo "💾 Backing up database..."
BACKUP_FILE="positions-backup-$(date +%Y%m%d-%H%M%S).db"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    mkdir -p ~/backups &&
    cp ~/tadss-monitor/data/positions.db ~/backups/$BACKUP_FILE &&
    echo 'Backup created: ~/backups/$BACKUP_FILE'
"
echo ""

# 6. Rebuild Docker image
echo "🔨 Rebuilding Docker image..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    cd ~/tadss-monitor &&
    docker build -t tadss-monitor:latest -f docker/Dockerfile .
"
echo ""

# 7. Stop old container
echo "🛑 Stopping old container..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    docker stop tadss 2>/dev/null || true &&
    docker rm tadss 2>/dev/null || true
"
echo ""

# 8. Start new container
echo "🚀 Starting new container..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    docker run -d \
        --name tadss \
        --restart unless-stopped \
        -p 8000:8000 \
        -v \$(pwd)/data:/app/data \
        -v \$(pwd)/logs:/app/logs \
        -v \$(pwd)/.env:/app/.env \
        tadss-monitor:latest
"
echo ""

# 9. Wait for startup
echo "⏳ Waiting for application to start (10 seconds)..."
sleep 10
echo ""

# 10. Health check
echo "🏥 Running health check..."
VM_IP=$(gcloud compute instances list --filter="name=tadss-vm" --format="value(EXTERNAL_IP)")

HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$VM_IP:8000/health)

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "❌ Deployment failed! Health check failed (HTTP $HEALTH_RESPONSE)"
    echo "🔄 Rolling back..."
    echo "Run: ./scripts/rollback.sh"
    exit 1
fi

echo "✅ Health check passed (HTTP $HEALTH_RESPONSE)"
echo ""

# 11. Post-deployment checks
echo "📊 Running post-deployment checks..."
./scripts/post-deploy-check.sh
echo ""

# 12. Summary
echo ""
echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"
echo "Version: $DEPLOY_TAG"
echo "API: http://$VM_IP:8000"
echo "Docs: http://$VM_IP:8000/docs"
echo "Health: http://$VM_IP:8000/health"
echo "Backup: ~/backups/$BACKUP_FILE"
echo "========================================"
echo ""
