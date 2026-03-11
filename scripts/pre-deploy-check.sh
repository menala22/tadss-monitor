#!/bin/bash
# scripts/pre-deploy-check.sh
# Pre-Deployment Checklist - Run before EVERY deployment

set -e

echo "========================================"
echo "Pre-Deployment Checklist"
echo "========================================"
echo ""

# 1. Check git status
echo "1. Git Status:"
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Uncommitted changes"
    git status
    exit 1
fi
echo "✅ No uncommitted changes"
echo ""

# 2. Check branch
echo "2. Current Branch:"
if [ "$(git branch --show-current)" != "main" ]; then
    echo "❌ Error: Not on main branch"
    echo "   Please checkout main branch before deploying"
    exit 1
fi
echo "✅ On main branch"
echo ""

# 3. Check for local files
echo "3. Local Files Check:"
LOCAL_FILES=$(git ls-files --others --exclude-standard | grep -v ".env" | grep -v "data/" | grep -v ".gitignore" || true)
if [ -n "$LOCAL_FILES" ]; then
    echo "⚠️  Warning: Untracked files:"
    echo "$LOCAL_FILES"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo "✅ No problematic local files"
echo ""

# 4. Run tests
echo "4. Running Tests:"
pytest tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Error: Tests failed"
    exit 1
fi
echo "✅ All tests passed"
echo ""

# 5. Check .env not in git
echo "5. Checking .env:"
if git ls-files | grep -q "^\.env$"; then
    echo "❌ Error: .env is in git!"
    echo "   Run: git rm --cached .env"
    exit 1
fi
echo "✅ .env not in git"
echo ""

# 6. Check requirements.txt
echo "6. Checking requirements.txt:"
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    exit 1
fi
echo "✅ requirements.txt exists"
echo ""

echo "========================================"
echo "✅ Pre-deployment checks passed!"
echo "========================================"
echo ""
echo "Ready to deploy. Run:"
echo "  ./scripts/deploy-to-production.sh"
echo ""
