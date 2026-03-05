# Development & Deployment Workflow Guide

**Version:** 1.0
**Date:** March 5, 2026
**Purpose:** Prevent discrepancies between local and production code

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Environment Setup](#environment-setup)
3. [Git Branch Strategy](#git-branch-strategy)
4. [Local Development Workflow](#local-development-workflow)
5. [Testing Workflow](#testing-workflow)
6. [Production Deployment](#production-deployment)
7. [Database Management](#database-management)
8. [Monitoring & Rollback](#monitoring--rollback)
9. [Quick Reference](#quick-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### The Problem

| Issue | Consequence |
|-------|-------------|
| Developing directly on `main` | Production breaks |
| No testing before deploy | Bugs in production |
| Manual deployment | Human error, forgotten steps |
| No backups | Data loss on migration failures |
| Same database local/prod | Accidental production data modification |

### The Solution

**Automated, documented workflow with:**
- ✅ Separate environments (local ≠ production)
- ✅ Feature branches (never develop on main)
- ✅ Automated deployment scripts
- ✅ Pre-deployment checks
- ✅ Database backups
- ✅ Post-deployment verification
- ✅ Easy rollback procedure

---

## Environment Setup

### Production Environment (Google Cloud VM)

| Component | Value |
|-----------|-------|
| **Platform** | Google Cloud e2-micro VM |
| **Region** | us-central1 (Iowa) |
| **Container** | Docker (tadss-monitor:latest) |
| **Database** | `/home/tadss-monitor/data/positions.db` |
| **Port** | 8000 |
| **Environment** | Production |
| **Telegram Bot** | Main bot (real alerts) |

### Local Development Environment (Your Laptop)

| Component | Value |
|-----------|-------|
| **Platform** | Your laptop (macOS) |
| **Container** | None (run directly) |
| **Database** | `data/positions-local.db` |
| **Port** | 8001 (API), 8503 (Dashboard) |
| **Environment** | Development |
| **Telegram Bot** | Test bot from @BotFather |

### Create Local Environment File

```bash
# Copy template
cp .env.example .env.local

# Edit .env.local (NEVER commit this file!)
nano .env.local
```

**`.env.local` content:**
```bash
# Local Development Configuration
# DO NOT COMMIT THIS FILE!

# Telegram (TEST BOT - create new bot via @BotFather)
TELEGRAM_BOT_TOKEN=your_test_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id

# Database (LOCAL ONLY)
DATABASE_URL=sqlite:///./data/positions-local.db

# Application
APP_ENV=development
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8001

# Scheduler (disabled in local dev)
MONITOR_INTERVAL=0

# Security
SECRET_KEY=dev-secret-key-change-in-production

# Leave these empty
CCXT_API_KEY=
CCXT_SECRET=
YFINANCE_API_KEY=
```

### Add to `.gitignore`

```bash
# Local environment files
.env
.env.local
.env.*.local

# Local databases
data/positions-local.db
data/positions-local.db-shm
data/positions-local.db-wal

# Local logs
logs/local-*.log
logs/development-*.log

# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
```

---

## Git Branch Strategy

### Branch Structure

```
main (production)
  ↑
  └── develop (staging - optional)
        ↑
        └── feature/your-feature (local development)
```

### Branch Rules

| Branch | Purpose | Protected | Deploy To |
|--------|---------|-----------|-----------|
| **`main`** | Production code | ✅ Yes | Google Cloud VM |
| **`develop`** | Integration testing | Optional | Local testing |
| **`feature/*`** | New features | ❌ No | Never deploy directly |

### Branch Naming Conventions

```bash
# Features
feature/add-new-indicator
feature/telegram-alert-improvements

# Bug fixes
fix/telegram-async-bug
fix/database-lock-issue

# Documentation
docs/update-readme
docs/add-deployment-guide

# Hotfixes (urgent production fixes)
hotfix/critical-security-patch
```

---

## Local Development Workflow

### Step 1: Start Fresh

```bash
# Always start from updated main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name

# Verify branch
git branch
# Should show: * feature/your-feature-name
```

### Step 2: Develop Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Run API locally (port 8001)
uvicorn src.main:app --reload --port 8001

# In another terminal, run dashboard
streamlit run src/ui.py --server.port 8503

# Test in browser:
# API: http://localhost:8001
# Docs: http://localhost:8001/docs
# Dashboard: http://localhost:8503
```

### Step 3: Commit Frequently

```bash
# Check what changed
git status
git diff

# Stage changes
git add src/services/your-feature.py
git add tests/test-your-feature.py

# Commit with clear message
git commit -m "feat: add new RSI indicator calculation

- Implement RSI calculation in technical_analyzer.py
- Add unit tests for RSI signals
- Update documentation"

# Push to GitHub (backup)
git push origin feature/your-feature-name
```

### Step 4: End of Day

```bash
# Commit all changes
git add .
git commit -m "WIP: progress on feature"

# Push to GitHub
git push origin feature/your-feature-name

# Next day: continue
git checkout feature/your-feature-name
git pull origin feature/your-feature-name
```

---

## Testing Workflow

### Pre-Commit Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_signal_engine.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Check code style (if you have linters)
flake8 src/
black --check src/
```

### Manual Testing Checklist

Before deploying ANY feature:

```bash
# 1. API endpoints work
curl http://localhost:8001/health
curl http://localhost:8001/api/v1/positions/open

# 2. Dashboard loads
# Open http://localhost:8503 in browser

# 3. Create test position
curl -X POST http://localhost:8001/api/v1/positions/open \
  -H "Content-Type: application/json" \
  -d '{"pair":"TEST","entry_price":100,"position_type":"LONG","timeframe":"h4"}'

# 4. Check database
sqlite3 data/positions-local.db "SELECT * FROM positions;"

# 5. Test Telegram (test bot)
curl -X POST http://localhost:8001/api/v1/positions/scheduler/test-alert
```

### Test Data Script

Create `scripts/create-test-data.py`:

```python
#!/usr/bin/env python3
"""Create test data for local development"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_context
from src.models.position_model import Position, PositionType, PositionStatus
from datetime import datetime

def create_test_data():
    with get_db_context() as db:
        # Create test positions
        test_positions = [
            Position(
                pair="BTCUSD",
                entry_price=50000,
                position_type=PositionType.LONG,
                timeframe="h4",
                status=PositionStatus.OPEN,
                last_signal_status="BULLISH",
            ),
            Position(
                pair="ETHUSD",
                entry_price=3000,
                position_type=PositionType.SHORT,
                timeframe="h1",
                status=PositionStatus.OPEN,
                last_signal_status="BEARISH",
            ),
        ]
        
        db.add_all(test_positions)
        db.commit()
        print(f"✅ Created {len(test_positions)} test positions")

if __name__ == "__main__":
    create_test_data()
```

**Run:**
```bash
python scripts/create-test-data.py
```

---

## Production Deployment

### Pre-Deployment Checklist

**Run before EVERY deployment:**

```bash
# scripts/pre-deploy-check.sh
#!/bin/bash

echo "========================================"
echo "Pre-Deployment Checklist"
echo "========================================"

# 1. Check git status
echo "1. Git Status:"
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Uncommitted changes"
    git status
    exit 1
fi
echo "✅ No uncommitted changes"

# 2. Check branch
echo "2. Current Branch:"
if [ "$(git branch --show-current)" != "main" ]; then
    echo "❌ Error: Not on main branch"
    exit 1
fi
echo "✅ On main branch"

# 3. Check for local files
echo "3. Local Files Check:"
LOCAL_FILES=$(git ls-files --others --exclude-standard | grep -v ".env" | grep -v "data/" || true)
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

# 4. Run tests
echo "4. Running Tests:"
pytest tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Error: Tests failed"
    exit 1
fi
echo "✅ All tests passed"

# 5. Check .env not in git
echo "5. Checking .env:"
if git ls-files | grep -q "^\.env$"; then
    echo "❌ Error: .env is in git!"
    exit 1
fi
echo "✅ .env not in git"

echo "========================================"
echo "✅ Pre-deployment checks passed!"
echo "========================================"
```

**Make executable:**
```bash
chmod +x scripts/pre-deploy-check.sh
```

---

### Deployment Script

**The main deployment script:**

```bash
#!/bin/bash
# scripts/deploy-to-production.sh

set -e  # Exit on error

echo "========================================"
echo "TA-DSS Production Deployment"
echo "========================================"
echo ""

# 1. Run pre-deployment checks
echo "📋 Running pre-deployment checks..."
./scripts/pre-deploy-check.sh

# 2. Get current version
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
echo "📦 Current version: $CURRENT_TAG"

# 3. Create deployment tag
DEPLOY_TAG="v$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)"
echo "🏷️  Creating deployment tag: $DEPLOY_TAG"
git tag -a $DEPLOY_TAG -m "Production deployment $(date)"
git push origin $DEPLOY_TAG

# 4. Pull latest on VM
echo "📦 Pulling latest code on production VM..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    cd ~/tadss-monitor &&
    git pull origin main
"

# 5. Backup database
echo "💾 Backing up database..."
BACKUP_FILE="positions-backup-$(date +%Y%m%d-%H%M%S).db"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    mkdir -p ~/backups &&
    cp ~/tadss-monitor/data/positions.db ~/backups/$BACKUP_FILE &&
    echo 'Backup created: ~/backups/$BACKUP_FILE'
"

# 6. Rebuild Docker image
echo "🔨 Rebuilding Docker image..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    cd ~/tadss-monitor &&
    docker build -t tadss-monitor:latest -f docker/Dockerfile .
"

# 7. Stop old container
echo "🛑 Stopping old container..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    docker stop tadss 2>/dev/null || true &&
    docker rm tadss 2>/dev/null || true
"

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

# 9. Wait for startup
echo "⏳ Waiting for application to start (10 seconds)..."
sleep 10

# 10. Health check
echo "🏥 Running health check..."
VM_IP=$(gcloud compute instances list --filter="name=tadss-vm" --format="value(EXTERNAL_IP)")

HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$VM_IP:8000/health)

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "❌ Deployment failed! Health check failed (HTTP $HEALTH_RESPONSE)"
    echo "🔄 Rolling back..."
    # Add rollback logic here or run ./scripts/rollback.sh
    exit 1
fi

echo "✅ Health check passed (HTTP $HEALTH_RESPONSE)"

# 11. Post-deployment checks
echo "📊 Running post-deployment checks..."
./scripts/post-deploy-check.sh

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
```

**Make executable:**
```bash
chmod +x scripts/deploy-to-production.sh
```

---

## Database Management

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup-database.sh

echo "💾 Backing up production database..."

# Create backup directory on VM
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    mkdir -p ~/backups
"

# Create backup
BACKUP_FILE="positions-backup-$(date +%Y%m%d-%H%M%S).db"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    cp ~/tadss-monitor/data/positions.db ~/backups/$BACKUP_FILE &&
    echo '✅ Backup created: ~/backups/$BACKUP_FILE'
"

# Download backup locally (optional)
read -p "Download backup locally? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    LOCAL_BACKUP="backups/$BACKUP_FILE"
    mkdir -p backups
    gcloud compute scp tadss-vm:~/backups/$BACKUP_FILE $LOCAL_BACKUP --zone us-central1-a
    echo "✅ Backup downloaded to: $LOCAL_BACKUP"
fi

# List recent backups
echo ""
echo "Recent backups on VM:"
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    ls -lht ~/backups/*.db | head -10
"
```

**Make executable:**
```bash
chmod +x scripts/backup-database.sh
```

### Database Migration Script

```bash
#!/bin/bash
# scripts/run-migration.sh

if [ -z "$1" ]; then
    echo "Usage: ./scripts/run-migration.sh <migration_script.py>"
    exit 1
fi

MIGRATION_SCRIPT=$1

echo "========================================"
echo "Database Migration"
echo "========================================"
echo ""

# 1. Backup first
echo "1. Creating backup..."
./scripts/backup-database.sh

# 2. Run migration locally
echo "2. Testing migration locally..."
python $MIGRATION_SCRIPT --test
if [ $? -ne 0 ]; then
    echo "❌ Local migration test failed"
    exit 1
fi
echo "✅ Local migration test passed"

# 3. Run on production
echo "3. Running migration on production..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    set -e
    cd ~/tadss-monitor &&
    python $MIGRATION_SCRIPT
"

# 4. Verify
echo "4. Verifying migration..."
gcloud compute ssh tadss-vm --zone us-central1-a --command "
    sqlite3 ~/tadss-monitor/data/positions.db '.schema'
"

echo ""
echo "========================================"
echo "✅ Migration Complete!"
echo "========================================"
```

---

## Monitoring & Rollback

### Post-Deployment Checks

```bash
#!/bin/bash
# scripts/post-deploy-check.sh

echo "========================================"
echo "Post-Deployment Checks"
echo "========================================"

# Get VM IP
VM_IP=$(gcloud compute instances list --filter="name=tadss-vm" --format="value(EXTERNAL_IP)")

# 1. Health check
echo "1. Health Check:"
HEALTH=$(curl -s http://$VM_IP:8000/health)
echo "$HEALTH" | jq . || echo "$HEALTH"
echo ""

# 2. API endpoints
echo "2. API Endpoints:"
echo "   - Positions count: $(curl -s http://$VM_IP:8000/api/v1/positions/open | jq '. | length')"
echo "   - Scheduler status: $(curl -s http://$VM_IP:8000/api/v1/positions/scheduler/status | jq '.running')"
echo ""

# 3. Check logs for errors
echo "3. Recent Errors:"
ERRORS=$(gcloud compute ssh tadss-vm --zone us-central1-a --command "docker logs tadss --tail 200 | grep -i error" || true)
if [ -n "$ERRORS" ]; then
    echo "⚠️  Errors found:"
    echo "$ERRORS"
else
    echo "✅ No errors in logs"
fi
echo ""

# 4. Check scheduler
echo "4. Scheduler Status:"
SCHEDULER=$(gcloud compute ssh tadss-vm --zone us-central1-a --command "docker logs tadss | grep -i 'scheduler'" | tail -3)
echo "$SCHEDULER"
echo ""

# 5. Test Telegram
echo "5. Testing Telegram Alert:"
curl -X POST http://$VM_IP:8000/api/v1/positions/scheduler/test-alert
echo ""
echo "   Check your Telegram for test message"
echo ""

echo "========================================"
echo "✅ Post-Deployment Checks Complete"
echo "========================================"
```

**Make executable:**
```bash
chmod +x scripts/post-deploy-check.sh
```

---

### Rollback Procedure

```bash
#!/bin/bash
# scripts/rollback.sh

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
./scripts/backup-database.sh

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
```

**Make executable:**
```bash
chmod +x scripts/rollback.sh
```

---

## Quick Reference

### Daily Development

```bash
# Start development
git checkout main
git pull origin main
git checkout -b feature/my-feature

# Work, test, commit
git add .
git commit -m "feat: my new feature"
git push origin feature/my-feature

# End of day
git push origin feature/my-feature
```

### Deploy to Production

```bash
# 1. Merge to main
git checkout main
git merge feature/my-feature
git push origin main

# 2. Deploy
./scripts/deploy-to-production.sh

# 3. Verify
./scripts/post-deploy-check.sh
```

### Useful Commands

```bash
# Check production status
gcloud compute instances list --filter="name=tadss-vm"

# SSH to VM
gcloud compute ssh tadss-vm --zone us-central1-a

# View production logs
gcloud compute ssh tadss-vm --command "docker logs tadss --tail 100"

# Restart production
gcloud compute ssh tadss-vm --command "docker restart tadss"

# Backup database
./scripts/backup-database.sh

# Check local vs remote
git diff main origin/main
```

---

## Troubleshooting

### Issue: Local code different from production

**Symptoms:**
- Feature works locally but not on production
- Different behavior between environments

**Solution:**
```bash
# Check what's different
git diff main origin/main

# Check production version
gcloud compute ssh tadss-vm --command "git log -1 --oneline"

# Check local version
git log -1 --oneline

# If different, redeploy
./scripts/deploy-to-production.sh
```

---

### Issue: Accidentally committed .env

**Solution:**
```bash
# Remove from git history
git rm --cached .env
git commit -m "Remove .env from git"
git push origin main

# Add to .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
git push origin main

# Rotate secrets (IMPORTANT!)
# 1. Create new Telegram bot token
# 2. Update .env on production
# 3. Update .env.local locally
```

---

### Issue: Database migration failed

**Solution:**
```bash
# 1. Check backup exists
gcloud compute ssh tadss-vm --command "ls -l ~/backups/"

# 2. Restore backup
gcloud compute ssh tadss-vm --command "
    cp ~/backups/positions-backup-YYYYMMDD-HHMMSS.db ~/tadss-monitor/data/positions.db
"

# 3. Restart container
gcloud compute ssh tadss-vm --command "docker restart tadss"

# 4. Verify
curl http://YOUR_VM_IP:8000/health
```

---

### Issue: Production down after deploy

**Solution:**
```bash
# 1. Check logs
gcloud compute ssh tadss-vm --command "docker logs tadss --tail 200"

# 2. If container crashed, restart
gcloud compute ssh tadss-vm --command "docker restart tadss"

# 3. If still broken, rollback
./scripts/rollback.sh

# 4. Test locally first
git checkout main
uvicorn src.main:app --reload --port 8001
# Fix the issue
# Test again
# Redeploy
```

---

## Summary: Golden Rules

1. ✅ **Never develop on `main`** - Always use feature branches
2. ✅ **Never commit `.env`** - Use `.env.example` template
3. ✅ **Never deploy untested code** - Run tests first
4. ✅ **Always backup before deploy** - Database backup script
5. ✅ **Always health check after deploy** - Automated verification
6. ✅ **Use separate environments** - Local dev ≠ Production
7. ✅ **Tag production deployments** - Easy rollback
8. ✅ **Document everything** - Scripts, checklists, procedures

---

**Document Version:** 1.0
**Last Updated:** March 5, 2026
**Maintained By:** Development Team
