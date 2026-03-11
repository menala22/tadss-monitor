#!/bin/bash
# scripts/post-deploy-check.sh
# Post-Deployment Verification Checks

set -e

echo "========================================"
echo "Post-Deployment Checks"
echo "========================================"
echo ""

# Get VM IP
VM_IP=$(gcloud compute instances list --filter="name=tadss-vm" --format="value(EXTERNAL_IP)")

# 1. Health check
echo "1. Health Check:"
HEALTH=$(curl -s http://$VM_IP:8000/health)
echo "$HEALTH" | jq . 2>/dev/null || echo "$HEALTH"
echo ""

# 2. API endpoints
echo "2. API Endpoints:"
echo "   - Positions count: $(curl -s http://$VM_IP:8000/api/v1/positions/open | jq '. | length' 2>/dev/null || echo 'N/A')"
echo "   - Scheduler status: $(curl -s http://$VM_IP:8000/api/v1/positions/scheduler/status | jq '.running' 2>/dev/null || echo 'N/A')"
echo ""

# 3. Check logs for errors
echo "3. Recent Errors:"
ERRORS=$(gcloud compute ssh tadss-vm --zone us-central1-a --command "docker logs tadss --tail 200 | grep -i error" 2>/dev/null || true)
if [ -n "$ERRORS" ]; then
    echo "⚠️  Errors found:"
    echo "$ERRORS"
else
    echo "✅ No errors in logs"
fi
echo ""

# 4. Check scheduler
echo "4. Scheduler Status:"
SCHEDULER=$(gcloud compute ssh tadss-vm --zone us-central1-a --command "docker logs tadss | grep -i 'scheduler'" | tail -3 2>/dev/null || true)
echo "$SCHEDULER"
echo ""

# 5. Test Telegram
echo "5. Testing Telegram Alert:"
curl -X POST http://$VM_IP:8000/api/v1/positions/scheduler/test-alert
echo ""
echo "   Check your Telegram for test message"
echo ""

# 6. Check container status
echo "6. Container Status:"
CONTAINER_STATUS=$(gcloud compute ssh tadss-vm --zone us-central1-a --command "docker ps --filter 'name=tadss' --format '{{.Status}}'" 2>/dev/null || true)
if [ -n "$CONTAINER_STATUS" ]; then
    echo "✅ Container running: $CONTAINER_STATUS"
else
    echo "❌ Container not running!"
    exit 1
fi
echo ""

echo "========================================"
echo "✅ Post-Deployment Checks Complete"
echo "========================================"
