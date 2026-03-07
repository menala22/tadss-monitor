#!/bin/bash
# =============================================================================
# TA-DSS Dashboard - Production Mode
# =============================================================================
# Connects to Google Cloud production API
# 
# Usage: ./scripts/run-dashboard-production.sh
# =============================================================================

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from .env file..."
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Google Cloud VM External IP (from .env or default)
VM_EXTERNAL_IP="${VM_EXTERNAL_IP:-35.188.118.182}"

# API Base URL
export API_BASE_URL="http://${VM_EXTERNAL_IP}:8000/api/v1"

echo "=============================================="
echo "TA-DSS Dashboard - Production Mode"
echo "=============================================="
echo "VM External IP: ${VM_EXTERNAL_IP}"
echo "API URL: ${API_BASE_URL}"
echo "Dashboard: http://localhost:8503"
echo "=============================================="
echo ""

echo "Testing API connection..."
if curl -s --connect-timeout 5 "${API_BASE_URL}/health" > /dev/null 2>&1; then
    echo "✅ API connection successful!"
    # Show API status
    curl -s --connect-timeout 5 "${API_BASE_URL}/health"
    echo ""
else
    echo "⚠️  API connection test timed out (may still work)"
    echo "   If dashboard doesn't work, check:"
    echo "   1. VM is running: ${VM_EXTERNAL_IP}"
    echo "   2. Firewall allows port 8000"
    echo "   3. Docker container is running"
    echo ""
fi

echo ""

# Run Streamlit dashboard
streamlit run src/ui.py --server.port 8503
