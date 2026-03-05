#!/bin/bash
# scripts/rollback.sh
# Rollback Production Deployment

set -e

echo "⚠️  WARNING: This will rollback production deployment!"
echo ""

# 1. List recent tags
echo "Recent deployment tags:"
git tag -l "v*" | tail -10
echo ""

# 2. Get target version
read -p "Enter version to rollback to (e.g., v2026.03.04-abc1234): " TARGET_VERSION

if ! git rev-parse "$TARGET_VERSION" >/dev/null 2>&1; then
    echo "❌ Tag '$TARGET_VERSION' not found"
    exit 1
fi

echo ""
echo "Rolling back to: $TARGET_VERSION"
read -p "Continue? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 3. Backup current state
echo "💾 Creating backup before rollback..."
./scripts/backup-database.sh << EOF
n
EOF

# 4. Checkout target version
echo "📦 Checking out $TARGET_VERSION..."
git checkout $TARGET_VERSION

# 5. Deploy to production
echo "🚀 Deploying $TARGET_VERSION to production..."
./scripts/deploy-to-production.sh

# 6. Return to main
echo "🔙 Returning to main branch..."
git checkout main

echo ""
echo "========================================"
echo "✅ Rollback Complete!"
echo "========================================"
echo "Rolled back to: $TARGET_VERSION"
echo "========================================"
