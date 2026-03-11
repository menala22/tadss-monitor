#!/bin/bash
# MTF EMA Update - VM Deployment Script
# Run this on your VM to deploy the latest MTF improvements

set -e  # Exit on error

echo "========================================="
echo "MTF EMA Update - VM Deployment"
echo "========================================="
echo ""

# Navigate to project directory
cd /path/to/trading-order-monitoring-system  # UPDATE THIS PATH

echo "📥 Pulling latest changes from GitHub..."
git pull origin main

echo ""
echo "📦 Installing new dependencies (matplotlib, seaborn)..."
source venv/bin/activate  # UPDATE THIS if your venv path is different
pip install -r requirements.txt

echo ""
echo "🧪 Testing MTF report generation..."
python scripts/generate_mtf_report.py BTC/USDT SWING

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Verify the deployment:"
echo "  1. Check reports: ls -lh docs/reports/"
echo "  2. Check charts: ls -lh docs/reports/charts/"
echo "  3. Test API: curl http://localhost:8000/api/v1/mtf/opportunities"
echo ""
echo "🎯 Changes deployed:"
echo "  - HTF: EMA 20/50 (was SMA 50/200)"
echo "  - MTF: EMA 10/20 (was SMA 20/50)"
echo "  - Data quality dashboard added"
echo "  - Interactive HTML reports added"
echo "  - PNG charts (4 per report) added"
echo ""
echo "⚠️  Note: Signal frequency may increase by ~35%"
echo "⚠️  Data requirements reduced by 75% (50 vs 200 candles)"
