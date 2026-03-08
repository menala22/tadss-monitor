#!/bin/bash
# Deploy Market Data Feature to Production VM
# This script deploys the new Market Data Status feature to your Google Cloud VM

set -e  # Exit on error

# Configuration
VM_NAME="tadss"
ZONE="us-central1-a"  # Update if your VM is in a different zone
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")

echo "=========================================="
echo "  Market Data Feature Deployment"
echo "=========================================="
echo ""

# Check if gcloud is configured
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if project is configured
if [ -z "$PROJECT_ID" ]; then
    echo "❌ gcloud project not configured. Run:"
    echo "   gcloud init"
    exit 1
fi

echo "✓ gcloud configured (project: $PROJECT_ID)"
echo ""

# Step 1: Get VM external IP
echo "📡 Getting VM external IP..."
VM_IP=$(gcloud compute instances describe $VM_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null)

if [ -z "$VM_IP" ]; then
    echo "❌ Could not get VM IP. Check VM name and zone."
    echo "   VM Name: $VM_NAME"
    echo "   Zone: $ZONE"
    exit 1
fi

echo "✓ VM IP: $VM_IP"
echo ""

# Step 2: Copy new files to VM
echo "📦 Copying new files to VM..."

FILES_TO_COPY=(
    "src/api/routes_market_data.py"
    "src/models/market_data_status_model.py"
    "src/services/market_data_service.py"
    "src/ui_market_data.py"
)

for file in "${FILES_TO_COPY[@]}"; do
    echo "   → $file"
    gcloud compute scp "$file" $VM_NAME:/app/src/ --zone=$ZONE --quiet
done

echo "✓ Files copied"
echo ""

# Step 3: Update main.py to register the new router
echo "🔧 Updating main.py to register market data router..."

gcloud compute ssh $VM_NAME --zone=$ZONE --command "
    cd /app/src &&
    
    # Check if router already exists
    if grep -q 'routes_market_data' main.py; then
        echo 'Router already registered in main.py'
    else
        # Add import after routes_mtf import
        sed -i '/from src.api.routes_mtf import/a from src.api.routes_market_data import router as market_data_router' main.py
        
        # Add router registration after mtf_router
        sed -i '/app.include_router(mtf_router/a app.include_router(market_data_router, prefix=\"/api/v1\")' main.py
        
        echo '✓ main.py updated'
    fi
    
    # Verify the changes
    echo 'Current main.py router imports:'
    grep -n 'router' main.py | head -10
" --quiet

echo ""

# Step 4: Update ui.py to include market data page
echo "🔧 Updating ui.py to include Market Data page..."

gcloud compute ssh $VM_NAME --zone=$ZONE --command "
    cd /app/src &&
    
    # Check if ui_market_data import already exists
    if grep -q 'ui_market_data' ui.py; then
        echo 'Market data page already imported in ui.py'
    else
        # Add import after ui_mtf_scanner import
        sed -i '/from src.ui_mtf_scanner import/a from src.ui_market_data import display_market_data_page' ui.py
        
        echo '✓ ui.py import added'
    fi
    
    # Check if page navigation already exists
    if grep -q 'Market Data' ui.py; then
        echo 'Market Data page already in navigation'
    else
        # Add to navigation menu (after MTF Scanner)
        sed -i 's/\"🔍 MTF Scanner\", \"⚙️ Settings\"/\"🔍 MTF Scanner\", \"📈 Market Data\", \"⚙️ Settings\"/g' ui.py
        
        # Add page rendering logic (after MTF Scanner)
        sed -i '/render_mtf_scanner_page()/a\\    elif page == \"📈 Market Data\":\n        display_market_data_page()' ui.py
        
        echo '✓ ui.py navigation updated'
    fi
" --quiet

echo ""

# Step 5: Copy updated ui_mtf_scanner.py (with data status check)
echo "📦 Copying updated ui_mtf_scanner.py..."
gcloud compute scp src/ui_mtf_scanner.py $VM_NAME:/app/src/ui_mtf_scanner.py --zone=$ZONE --quiet
echo "✓ ui_mtf_scanner.py updated"
echo ""

# Step 6: Restart Docker container
echo "🔄 Restarting Docker container..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command "docker restart tadss" --quiet
echo "✓ Container restarted"
echo ""

# Step 7: Wait for server to start
echo "⏳ Waiting for server to start (10 seconds)..."
sleep 10

# Step 8: Verify deployment
echo "✅ Verifying deployment..."

# Test market-data endpoint
echo "   Testing /api/v1/market-data/status endpoint..."
MARKET_DATA_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/market_data_response.json \
    "http://$VM_IP:8000/api/v1/market-data/status" \
    -H "X-API-Key: $(grep API_SECRET_KEY .env | cut -d'=' -f2)")

MARKET_DATA_STATUS=$(echo "$MARKET_DATA_RESPONSE" | tail -n1)

if [ "$MARKET_DATA_STATUS" = "200" ]; then
    echo "✓ Market data endpoint working (HTTP 200)"
else
    echo "⚠ Market data endpoint returned HTTP $MARKET_DATA_STATUS"
    echo "   Response: $(cat /tmp/market_data_response.json)"
fi

# Test summary endpoint
echo "   Testing /api/v1/market-data/summary endpoint..."
SUMMARY_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/summary_response.json \
    "http://$VM_IP:8000/api/v1/market-data/summary" \
    -H "X-API-Key: $(grep API_SECRET_KEY .env | cut -d'=' -f2)")

SUMMARY_STATUS=$(echo "$SUMMARY_RESPONSE" | tail -n1)

if [ "$SUMMARY_STATUS" = "200" ]; then
    echo "✓ Summary endpoint working (HTTP 200)"
else
    echo "⚠ Summary endpoint returned HTTP $SUMMARY_STATUS"
fi

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "📊 Access the Market Data page:"
echo "   http://$VM_IP:8000/docs  (API documentation)"
echo "   http://$VM_IP:8000/api/v1/market-data/status  (API endpoint)"
echo ""
echo "🖥️  Dashboard URL (update your local .env if needed):"
echo "   API_BASE_URL=http://$VM_IP:8000/api/v1"
echo ""
echo "To view in dashboard, run locally:"
echo "   streamlit run src/ui.py --server.port 8503"
echo ""
echo "=========================================="
