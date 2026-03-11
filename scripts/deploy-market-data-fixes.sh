#!/bin/bash
# =============================================================================
# Market Data Orchestrator Fixes Deployment Script
# =============================================================================
# Deploys BUG-032, dual-cache, and 4h aggregation fixes to production VM
# 
# Fixes deployed:
#   1. BUG-032: Hourly candle corruption (timeframe mapping)
#   2. Dual-cache writes removal (single source of truth)
#   3. 4h aggregation for Twelve Data pairs
#
# Usage:
#   ./scripts/deploy-market-data-fixes.sh
# =============================================================================

set -e

# Configuration
VM_EXTERNAL_IP="34.171.241.166"
VM_USER="aiagent"
PROJECT_NAME="trading-order-monitoring-system"
CONTAINER_NAME="tadss"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Pre-deployment checks
# =============================================================================
echo ""
echo "========================================================================"
echo "  Market Data Orchestrator Fixes Deployment"
echo "========================================================================"
echo ""

log_info "Pre-deployment checks..."

# Check if running from project root
if [ ! -d "src" ] || [ ! -d "scripts" ]; then
    log_error "Must run from project root directory"
    exit 1
fi
log_success "Running from project root"

# Check if .env exists
if [ ! -f ".env" ]; then
    log_error ".env file not found"
    exit 1
fi
log_success ".env file found"

# Check SSH connectivity to VM
log_info "Testing SSH connectivity to VM ($VM_EXTERNAL_IP)..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes $VM_USER@$VM_EXTERNAL_IP "echo 'Connection successful'" > /dev/null 2>&1; then
    log_success "VM is reachable"
else
    log_error "Cannot connect to VM. Check SSH keys and network."
    exit 1
fi

# =============================================================================
# Files to deploy
# =============================================================================
echo ""
log_info "Preparing files for deployment..."

# Create temporary deployment directory
DEPLOY_DIR=$(mktemp -d)
log_info "Created temp deploy directory: $DEPLOY_DIR"

# Copy modified files
cp src/data_fetcher.py "$DEPLOY_DIR/"
cp src/services/market_data_orchestrator.py "$DEPLOY_DIR/"
cp src/services/ohlcv_cache_manager.py "$DEPLOY_DIR/"
cp scripts/test_dual_cache_fix.py "$DEPLOY_DIR/"
cp scripts/test_4h_aggregation.py "$DEPLOY_DIR/"

log_success "Files copied to deploy directory"

# =============================================================================
# Deploy to VM
# =============================================================================
echo ""
log_info "Deploying to VM..."

# SSH into VM and prepare for deployment
ssh $VM_USER@$VM_EXTERNAL_IP << 'ENDSSH'
    cd ~/trading-order-monitoring-system
    
    # Create backup directory with timestamp
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)_market_data_fixes"
    mkdir -p "$BACKUP_DIR"
    
    # Backup current files
    cp src/data_fetcher.py "$BACKUP_DIR/" 2>/dev/null || true
    cp src/services/market_data_orchestrator.py "$BACKUP_DIR/" 2>/dev/null || true
    cp src/services/ohlcv_cache_manager.py "$BACKUP_DIR/" 2>/dev/null || true
    
    echo "Backup created: $BACKUP_DIR"
ENDSSH

log_success "Backup created on VM"

# Upload new files
log_info "Uploading new files to VM..."

scp src/data_fetcher.py $VM_USER@$VM_EXTERNAL_IP:~/trading-order-monitoring-system/src/
scp src/services/market_data_orchestrator.py $VM_USER@$VM_EXTERNAL_IP:~/trading-order-monitoring-system/src/services/
scp src/services/ohlcv_cache_manager.py $VM_USER@$VM_EXTERNAL_IP:~/trading-order-monitoring-system/src/services/
scp scripts/test_dual_cache_fix.py $VM_USER@$VM_EXTERNAL_IP:~/trading-order-monitoring-system/scripts/
scp scripts/test_4h_aggregation.py $VM_USER@$VM_EXTERNAL_IP:~/trading-order-monitoring-system/scripts/

log_success "Files uploaded successfully"

# =============================================================================
# Restart container
# =============================================================================
echo ""
log_info "Restarting Docker container..."

ssh $VM_USER@$VM_EXTERNAL_IP << 'ENDSSH'
    cd ~/trading-order-monitoring-system
    
    # Clear Python cache
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Restart container
    docker restart tadss
    
    # Wait for container to be ready
    echo "Waiting for container to start..."
    sleep 5
    
    # Check container status
    docker ps --filter "name=tadss" --format "table {{.Names}}\t{{.Status}}"
ENDSSH

log_success "Container restarted"

# =============================================================================
# Run verification tests
# =============================================================================
echo ""
log_info "Running verification tests on VM..."

ssh $VM_USER@$VM_EXTERNAL_IP << 'ENDSSH'
    cd ~/trading-order-monitoring-system
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run dual-cache test
    echo "Running dual-cache verification test..."
    python scripts/test_dual_cache_fix.py
    
    # Run 4h aggregation test (function test only, skip API calls)
    echo ""
    echo "Running 4h aggregation function test..."
    python -c "
import sys
sys.path.insert(0, 'src')
from src.data_fetcher import aggregate_1h_to_4h
import pandas as pd

# Quick function test
dates = pd.date_range('2026-03-10', periods=24, freq='1h')
df = pd.DataFrame({'Open': range(24), 'High': range(24), 'Low': range(24), 'Close': range(24), 'Volume': [100]*24}, index=dates)
result = aggregate_1h_to_4h(df)
assert len(result) == 6, f'Expected 6 candles, got {len(result)}'
print('✓ 4h aggregation function test passed')
"
    
    echo ""
    echo "All verification tests completed"
ENDSSH

log_success "Verification tests completed"

# =============================================================================
# Post-deployment summary
# =============================================================================
echo ""
echo "========================================================================"
echo "  Deployment Complete!"
echo "========================================================================"
echo ""
log_info "Deployment Summary:"
echo ""
echo "  Files Deployed:"
echo "    ✓ src/data_fetcher.py"
echo "    ✓ src/services/market_data_orchestrator.py"
echo "    ✓ src/services/ohlcv_cache_manager.py"
echo "    ✓ scripts/test_dual_cache_fix.py"
echo "    ✓ scripts/test_4h_aggregation.py"
echo ""
echo "  Fixes Applied:"
echo "    ✓ BUG-032: Hourly candle corruption (timeframe mapping)"
echo "    ✓ Dual-cache writes removal (single source of truth)"
echo "    ✓ 4h aggregation for Twelve Data pairs"
echo ""
echo "  Next Steps:"
echo "    1. Monitor dashboard for data freshness"
echo "    2. Check Twelve Data API usage dashboard"
echo "    3. Review logs: docker logs tadss --tail 100"
echo ""
echo "  Rollback (if needed):"
echo "    Backup location: ~/trading-order-monitoring-system/backups/"
echo "    Restore: cp backups/YYYYMMDD_HHMMSS/*.py src/ && docker restart tadss"
echo ""
echo "========================================================================"
echo ""

# Cleanup temp directory
rm -rf "$DEPLOY_DIR"

log_success "Deployment script completed successfully!"
