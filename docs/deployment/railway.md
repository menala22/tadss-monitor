# Railway.app Deployment Guide

**Project:** TA-DSS - Trading Order Monitoring System
**Version:** 1.0
**Date:** March 4, 2026
**Status:** 🟢 Recommended for Easiest 24/7 Deployment
**Estimated Time:** 10-15 minutes
**Monthly Cost:** ~$0.21/month (covered by $5/month trial credit)

---

## ⚠️ Important Notice

**Why Railway Over Other Free Options?**

| Issue | Oracle Cloud Free | GitHub Actions | Hugging Face | Google Cloud e2-micro | **Railway** |
|-------|-------------------|----------------|--------------|----------------------|-------------|
| **Capacity Issues** | ⚠️ Frequent outages | ✅ None | ✅ None | ✅ None | ✅ None |
| **Data Privacy** | ✅ Private | ❌ No DB access | 🔴 Public code | ✅ Private | ✅ Private |
| **24/7 Uptime** | ✅ Yes | ❌ Scheduled only | ✅ Yes | ✅ Yes | ✅ Yes |
| **Setup Complexity** | ⚠️ 30-60 min | ✅ 10 min | ✅ 15 min | ⚠️ 15-20 min | ✅ 10 min |
| **Monthly Cost** | $0 | $0 | $0 | $0 | **~$0.21** |
| **Credit Required** | ✅ Yes | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Auto-Deploy** | ❌ Manual | ❌ Manual | ⚠️ Git-based | ❌ Manual | ✅ Yes |
| **SSL/HTTPS** | ⚠️ Manual | N/A | ✅ Auto | ⚠️ Manual | ✅ Auto |

**Railway Advantages:**
- ✅ **Easiest deployment** (10 minutes, no SSH/firewall config)
- ✅ **Automatic HTTPS/SSL** (free domain included)
- ✅ **Auto-deploy from GitHub** (push code → auto-deploy)
- ✅ **No capacity issues** (unlike Oracle Cloud)
- ✅ **Full privacy** (your code + data not exposed)
- ✅ **$5/month trial credit** (renews monthly, covers ~23 months of TA-DSS)

**Trade-offs:**
- ⚠️ **Not completely free** (~$0.21/month, but covered by $5 credit)
- ⚠️ **No SSH access** (managed platform)
- ⚠️ **Less control** than VM (can't customize OS)

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Overview](#1-overview) | What is Railway? |
| [Prerequisites](#2-prerequisites) | What you need before starting |
| [Step 1: Create Railway Account](#3-step-1-create-railway-account-3-min) | Account setup |
| [Step 2: Install Railway CLI](#4-step-2-install-railway-cli-2-min) | CLI installation |
| [Step 3: Create Project](#5-step-3-create-project-3-min) | Project initialization |
| [Step 4: Configure Environment](#6-step-4-configure-environment-2-min) | Set secrets |
| [Step 5: Deploy](#7-step-5-deploy-5-min) | Deploy application |
| [Step 6: Test & Verify](#8-step-6-test--verify-3-min) | Final testing |
| [Cost Analysis](#9-cost-analysis) | Pricing breakdown |
| [Troubleshooting](#10-troubleshooting) | Common issues |
| [Security Best Practices](#11-security-best-practices) | Hardening your deployment |
| [Monitoring & Maintenance](#12-monitoring--maintenance) | Ongoing operations |

---

## 1. Overview

### 1.1 What is Railway?

**Railway** is a **Platform-as-a-Service (PaaS)** that automatically builds, deploys, and scales your applications. It's like "Heroku but better" with generous free credits.

**Key Features:**
- 🚀 **Git-based deployment** (push to GitHub → auto-deploy)
- 🔒 **Built-in secrets management** (encrypted environment variables)
- 🌐 **Free SSL/HTTPS** (automatic certificates)
- 💾 **Persistent volumes** (for SQLite database)
- 📊 **Usage dashboard** (real-time cost tracking)
- 🔄 **Auto-deploy on push** (CI/CD built-in)

### 1.2 Architecture on Railway

```
┌─────────────────────────────────────────────────────────────┐
│ Railway Platform                                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Your Service (TA-DSS)                                 │ │
│  │                                                       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │ FastAPI     │  │ APScheduler │  │ SQLite      │   │ │
│  │  │ :8000       │  │ Every hour  │  │ /data       │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  │                                                       │ │
│  │  Resources: ~0.5 vCPU, 512 MB RAM                    │ │
│  │  Cost: ~$0.21/month                                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Persistent Volume: /data (2 GB for SQLite database)       │
│  Public URL: https://tadss-monitor.up.railway.app         │
│  Environment Variables: Encrypted in Railway Dashboard    │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Why This Works for TA-DSS

**Resource Requirements vs Railway Usage:**

| Resource | TA-DSS Needs | Railway Provides | Headroom |
|----------|--------------|------------------|----------|
| CPU | ~10% of 1 core | Scalable (pay per use) | ✅ 90% free |
| RAM | ~500 MB | 512 MB - 1 GB | ✅ 50% free |
| Storage | ~2 GB | 2 GB volume | ✅ Sufficient |
| Network | ~50 MB/month | Unlimited | ✅ 99% free |
| Uptime | 24/7 | 24/7 | ✅ Perfect |

**Conclusion:** TA-DSS runs comfortably within Railway's free trial credit.

---

## 2. Prerequisites

### 2.1 Required Accounts

| Account | Purpose | Link |
|---------|---------|------|
| **GitHub** | Code repository + auth | https://github.com |
| **Railway** | Deployment platform | https://railway.app |
| **Telegram Bot** | For alerts (already have) | @BotFather |

### 2.2 Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Node.js** | v18+ | Railway CLI |
| **npm** | v9+ | Package manager |
| **Git** | Any | Version control |

### 2.3 Required Information

| Item | Example | Where to Find |
|------|---------|---------------|
| **GitHub Repo** | `menala22/tadss-monitor` | Already created |
| **Telegram Bot Token** | `8726527766:AAF8F9P3ES6t...` | Your `.env` file |
| **Telegram Chat ID** | `652745650` | Your `.env` file |
| **Credit/Debit Card** | For verification | Your wallet |

### 2.4 What You DON'T Need

- ❌ Docker knowledge (Railway handles it)
- ❌ SSH configuration (no SSH needed)
- ❌ Firewall rules (managed by Railway)
- ❌ SSL certificates (automatic)
- ❌ Domain name (free `*.up.railway.app` domain)
- ❌ Database migration (SQLite works as-is)

---

## 3. Step 1: Create Railway Account (3 min)

### 3.1 Sign Up for Railway

1. **Go to:** https://railway.app
2. Click **"Start a New Project"**
3. **Choose Login Method:**
   - ✅ **GitHub** (recommended - easiest)
   - Or Google
   - Or Email

### 3.2 Authorize Railway (GitHub Login)

If using GitHub:

1. Click **"Login with GitHub"**
2. Authorize Railway to access your GitHub account
3. Select which repositories Railway can access:
   - ✅ **All repositories** (easiest)
   - Or **Only select repositories** → choose `tadss-monitor`

### 3.3 Add Payment Method

**Important:** This is for **verification only**. You won't be charged if you stay within limits.

1. Click your profile icon (top right)
2. Click **"Billing"**
3. Click **"Add Payment Method"**
4. Enter credit/debit card details
5. Click **"Save"**

**You Get:**
- ✅ $5 trial credit (renews monthly)
- ✅ Access to all Railway features
- ✅ No automatic charges beyond credit

### 3.4 Verify Account

1. Check your email for verification link
2. Click verification link
3. Account is now active

---

## 4. Step 2: Install Railway CLI (2 min)

### 4.1 Install Node.js (If Not Installed)

**Check if installed:**
```bash
node --version
# Should show: v18.x.x or higher
```

**If not installed:**

**macOS:**
```bash
brew install node@18
```

**Windows:**
- Download from https://nodejs.org
- Run installer
- Follow prompts

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 4.2 Install Railway CLI

```bash
# Install globally
npm install -g @railway/cli

# Verify installation
railway --version
# Should show version number
```

### 4.3 Login to CLI

```bash
# Login to Railway
railway login

# This opens browser for authentication
# Click "Authorize" in browser
# Return to terminal - should show "Logged in as [your-email]"
```

---

## 5. Step 3: Create Project (3 min)

### 5.1 Navigate to Your Project

```bash
# Navigate to TA-DSS project
cd "/Users/aiagent/Documents/No.3 - Qwen - Trading Order Monitoring system/trading-order-monitoring-system"
```

### 5.2 Initialize Railway Project

```bash
# Initialize new Railway project
railway init
```

**You'll be prompted:**

1. **Select a project:**
   - Choose **"Create a new project"**
   - Or select existing if you have one

2. **Project Name:**
   - Enter: `tadss-monitor`
   - Press Enter

3. **Select a region:**
   - Choose closest to you:
     - `us-east-1` (US East - Virginia)
     - `us-west-1` (US West - Oregon)
     - `eu-west-1` (Europe - London)
     - `ap-southeast-1` (Asia - Singapore)
   - **Recommendation:** Choose closest to your location for lower latency

### 5.3 Link to GitHub (Optional but Recommended)

```bash
# Link to GitHub repository
railway link
```

**You'll be prompted:**

1. **Select a repository:**
   - Choose `menala22/tadss-monitor`

2. **Link type:**
   - Choose **"GitHub"** (for auto-deploy)

**Benefits of GitHub linking:**
- ✅ Auto-deploy on every push
- ✅ Version control
- ✅ Easy rollback

---

## 6. Step 4: Configure Environment (2 min)

### 6.1 Set Environment Variables

Railway uses encrypted environment variables (like GitHub Secrets).

**Set via CLI:**

```bash
# Telegram credentials
railway variables set TELEGRAM_BOT_TOKEN=8726527766:AAF8F9P3ES6tRUHEpVcxSZv_qffUUNCp58Y
railway variables set TELEGRAM_CHAT_ID=652745650

# Database configuration
railway variables set DATABASE_URL=sqlite:///./data/positions.db

# Application settings
railway variables set APP_ENV=production
railway variables set LOG_LEVEL=INFO

# Security (generate new secret)
railway variables set SECRET_KEY=$(openssl rand -hex 32)

# Timezone
railway variables set TIMEZONE=UTC
```

**Verify variables:**
```bash
railway variables list
# Should show all variables (values hidden)
```

### 6.2 Alternative: Set via Dashboard

If you prefer GUI:

1. Go to https://railway.app
2. Click your project (`tadss-monitor`)
3. Click **"Variables"** tab
4. Click **"New Variable"**
5. Add each variable manually

---

## 7. Step 5: Deploy (5 min)

### 7.1 Add Persistent Volume (For Database)

Railway containers are ephemeral - you need a persistent volume for the SQLite database.

```bash
# Add persistent volume for /data directory
railway volume add --mount /data --size 2GB
```

**Verify volume:**
```bash
railway volume list
# Should show: /data (2 GB)
```

### 7.2 Deploy Application

**Option A: Deploy from Local (Quick)**

```bash
# Deploy current directory
railway up
```

**What happens:**
1. Railway packages your code
2. Uploads to Railway servers
3. Builds Docker image (using your Dockerfile)
4. Deploys container
5. Assigns public URL

**Wait 2-3 minutes** for deployment to complete.

---

**Option B: Deploy from GitHub (Auto-Deploy)**

If you linked GitHub in Step 5.3:

1. Go to https://railway.app
2. Click your project
3. Click **"New"** → **"GitHub Repo"**
4. Select `menala22/tadss-monitor`
5. Click **"Deploy"**

**Benefits:**
- ✅ Auto-deploy on every `git push`
- ✅ No manual deployment needed
- ✅ Version history in Railway dashboard

---

### 7.3 Configure Docker Build (If Needed)

Railway auto-detects Dockerfile. If you have multiple Dockerfiles:

1. Go to https://railway.app
2. Click your project
3. Click **"Settings"** tab
4. Under **"Build"**, set:
   - **Dockerfile Path:** `docker/Dockerfile`

---

### 7.4 Set Start Command

Railway auto-detects from Dockerfile. To override:

1. Go to project settings
2. Under **"Deploy"**, set:
   - **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port 8000`

---

### 7.5 Check Deployment Status

```bash
# View deployment logs
railway logs

# Check service status
railway status

# Get public URL
railway domain
# Returns: https://tadss-monitor-production.up.railway.app
```

---

## 8. Step 6: Test & Verify (3 min)

### 8.1 Get Your Public URL

```bash
# Get your Railway URL
railway domain
```

**Expected output:**
```
https://tadss-monitor-production.up.railway.app
```

**Save this URL** - you'll need it for API calls.

---

### 8.2 Test Health Endpoint

```bash
# Replace with your actual Railway URL
curl https://tadss-monitor-production.up.railway.app/health

# Expected response:
# {"status":"healthy","timestamp":"2026-03-04T..."}
```

---

### 8.3 Test Telegram Alerts

```bash
# Send test alert
curl -X POST https://tadss-monitor-production.up.railway.app/api/v1/positions/scheduler/test-alert

# Check your Telegram for test message
```

---

### 8.4 Verify Scheduler is Running

```bash
# View logs for scheduler messages
railway logs | grep -i "scheduler"

# Expected:
# "Background scheduler started"
# "Scheduled 'position_monitoring' job (runs every hour at :10 minutes)"
```

---

### 8.5 Create Test Position

```bash
# Create test position via API
curl -X POST https://tadss-monitor-production.up.railway.app/api/v1/positions/open \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTCUSD",
    "entry_price": 50000,
    "position_type": "LONG",
    "timeframe": "h4"
  }'

# Expected: Position created with ID
```

---

### 8.6 Verify Database Persistence

```bash
# Wait 1 hour for scheduled check
# Then check logs
railway logs | grep -i "monitoring check completed"

# Should show successful check with database access
```

---

## 9. Cost Analysis

### 9.1 Railway Pricing Model

Railway charges based on **actual usage**:

| Resource | Rate | TA-DSS Usage | Monthly Cost |
|----------|------|--------------|--------------|
| **Compute** | $0.0000071667/second | ~0.5 vCPU average | ~$0.19 |
| **Memory** | Included (no extra charge) | 512 MB | $0.00 |
| **Storage** | $1.00/GB/month | 2 GB volume | ~$0.02 |
| **Bandwidth** | Unlimited | ~50 MB | $0.00 |
| **Total** | | | **~$0.21/month** |

---

### 9.2 Free Trial Credit

| Credit Type | Amount | Renewal | TA-DSS Coverage |
|-------------|--------|---------|-----------------|
| **Trial Credit** | $5/month | ✅ Monthly | ~23 months |

**Your $5 credit renews every month** for trial users, covering TA-DSS costs indefinitely.

---

### 9.3 Cost Comparison

| Provider | Monthly Cost | 1-Year Cost | Setup Time |
|----------|--------------|-------------|------------|
| **Railway** | ~$0.21 | ~$2.52 | 10 min |
| **Google Cloud e2-micro** | $0 | $0 | 15-20 min |
| **Oracle Cloud VM** | $0 | $0 | 30-60 min |
| **Hugging Face** | $0 | $0 | 15 min |
| **GitHub Actions** | $0 | $0 | 10 min (but no 24/7) |

**Railway trade-off:** Pay ~$0.21/month for easiest deployment and no capacity issues.

---

### 9.4 Potential Overage Scenarios

| Scenario | Cause | Monthly Cost | Prevention |
|----------|-------|--------------|------------|
| **Normal TA-DSS usage** | Expected usage | ~$0.21 | N/A |
| **High traffic** | 10x normal API calls | ~$0.30 | Monitor usage |
| **Large database** | 10 GB instead of 2 GB | ~$0.29 | Clean old data |
| **Accidental scale-up** | Increase resources | ~$5-10 | Don't change settings |

**Monitor your usage:**
```bash
railway usage
# Shows current month spending
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue 1: Deployment Fails

**Symptoms:**
```bash
railway up
# Error: Build failed
```

**Solutions:**

1. **Check Dockerfile exists:**
   ```bash
   ls -la docker/Dockerfile
   ```

2. **View build logs:**
   ```bash
   railway logs --build
   ```

3. **Common causes:**
   - ❌ Missing `requirements.txt`
   - ❌ Wrong Dockerfile path
   - ❌ Build errors in Dockerfile

**Fix:**
```bash
# Test Docker build locally
docker build -t tadss-test -f docker/Dockerfile .

# If local build fails, Railway will too
```

---

#### Issue 2: Container Crashes on Start

**Symptoms:**
- Container starts then immediately stops
- Logs show errors

**Solutions:**

```bash
# View logs
railway logs

# Common causes:
# 1. Missing environment variables
railway variables list

# 2. Database path incorrect
# Ensure DATABASE_URL=sqlite:///./data/positions.db

# 3. Port not exposed
# Ensure Dockerfile has: EXPOSE 8000
```

---

#### Issue 3: Database Not Persisting

**Symptoms:**
- Positions disappear after restart
- "No such table: positions" error

**Solutions:**

1. **Verify volume exists:**
   ```bash
   railway volume list
   # Should show: /data (2 GB)
   ```

2. **Check mount path:**
   - Go to Railway dashboard
   - Click your service
   - Click **"Volumes"** tab
   - Ensure mount path is `/data`

3. **Verify DATABASE_URL:**
   ```bash
   railway variables get DATABASE_URL
   # Should be: sqlite:///./data/positions.db
   ```

---

#### Issue 4: Telegram Alerts Not Working

**Symptoms:**
- No alerts received
- Logs show "Telegram not configured"

**Solutions:**

```bash
# Verify environment variables
railway variables list | grep TELEGRAM

# Re-set if needed
railway variables set TELEGRAM_BOT_TOKEN=8726527766:AAF8F9P3ES6t...
railway variables set TELEGRAM_CHAT_ID=652745650

# Restart service
railway restart
```

---

#### Issue 5: High Memory Usage

**Symptoms:**
- Service restarts frequently
- Logs show OOM (Out Of Memory)

**Solutions:**

1. **Check memory usage:**
   ```bash
   railway status
   ```

2. **Reduce log verbosity:**
   ```bash
   railway variables set LOG_LEVEL=WARNING
   ```

3. **Restart service:**
   ```bash
   railway restart
   ```

---

### 10.2 Useful Commands

```bash
# Deployment
railway up              # Deploy
railway logs            # View logs
railway restart         # Restart service

# Environment
railway variables list  # List variables
railway variables set   # Set variable
railway variables get   # Get variable

# Resources
railway status          # Service status
railway usage           # Cost usage
railway volume list     # List volumes

# Network
railway domain          # Get public URL
railway open            # Open dashboard
```

---

## 11. Security Best Practices

### 11.1 Environment Variables

**Never commit `.env` to Git:**

```bash
# Verify .gitignore includes .env
cat .gitignore | grep env
# Should show: .env

# Railway variables are encrypted and never exposed
```

---

### 11.2 Access Control

**Limit Railway Account Access:**

1. Enable 2FA on Railway account:
   - Go to Account Settings
   - Enable Two-Factor Authentication

2. Use GitHub for authentication (more secure than email)

3. Don't share Railway dashboard access

---

### 11.3 Network Security

**Railway handles network security:**
- ✅ Automatic DDoS protection
- ✅ Container isolation
- ✅ Encrypted HTTPS

**Optional: Restrict API Access**

If you want to limit API access to your IP only:

1. Go to Railway dashboard
2. Click your project
3. Click **"Settings"**
4. Under **"Networking"**, enable **Private Network**
5. Use Railway's internal networking for API calls

---

### 11.4 Regular Updates

**Keep Application Updated:**

```bash
# Pull latest changes
git pull

# Deploy update
railway up

# Or auto-deploy if GitHub linked
git push  # Railway auto-deploys
```

---

## 12. Monitoring & Maintenance

### 12.1 Railway Dashboard Monitoring

**View Real-time Metrics:**

1. Go to https://railway.app
2. Click your project
3. View dashboard:
   - **CPU Usage** (real-time graph)
   - **Memory Usage** (real-time graph)
   - **Network I/O** (real-time graph)
   - **Cost** (current month spending)

---

### 12.2 Set Up Alerts

**Get Notified on Issues:**

1. Go to project settings
2. Click **"Alerts"** tab
3. Enable alerts for:
   - ✅ High CPU usage (>80%)
   - ✅ High memory usage (>90%)
   - ✅ Service crashes
   - ✅ Deployment failures

**Notification methods:**
- Email (default)
- Slack (optional)
- Discord (optional)

---

### 12.3 Application Logs

**View Logs:**

```bash
# Real-time logs
railway logs --follow

# Last 100 lines
railway logs --lines 100

# Filter by keyword
railway logs | grep -i "error"
```

**Log Locations (in container):**
- `/app/logs/monitor.log` - Monitoring logs
- `/app/logs/telegram.log` - Telegram logs

---

### 12.4 Backup Strategy

**Database Backup (Monthly):**

Railway volumes are persistent but not backed up automatically.

**Option 1: Manual Backup**

```bash
# SSH into container (via Railway shell)
railway run bash

# Copy database
cp /data/positions.db /tmp/positions-backup-$(date +%Y%m%d).db

# Download backup
railway run cat /tmp/positions-backup-*.db > backup.db
```

**Option 2: Automated Backup (Advanced)**

Create a backup script in your repository that:
1. Runs daily via scheduler
2. Uploads backup to cloud storage (S3, Google Drive)
3. Deletes old backups (>30 days)

---

### 12.5 Cost Monitoring

**Check Monthly Spending:**

```bash
# View current usage
railway usage
```

**Or via Dashboard:**
1. Go to https://railway.app
2. Click your profile icon
3. Click **"Usage"**
4. View current month spending

**Set Budget Alert:**
1. Go to Billing settings
2. Set budget alert at $2 (well under $5 credit)
3. Get email notification when approaching limit

---

## Appendix A: Quick Reference

### A.1 Essential Commands

```bash
# Login
railway login

# Deploy
railway up

# View logs
railway logs --follow

# Get URL
railway domain

# Set variable
railway variables set KEY=value

# Restart
railway restart

# Check usage
railway usage
```

---

### A.2 File Locations

| File | Path | Purpose |
|------|------|---------|
| **Dockerfile** | `docker/Dockerfile` | Docker config |
| **Environment** | Railway Dashboard | Encrypted variables |
| **Database** | `/data/positions.db` | Persistent storage |
| **Logs** | `/app/logs/` | Application logs |

---

### A.3 Important URLs

| Resource | URL |
|----------|-----|
| **Railway Dashboard** | https://railway.app |
| **Your Project** | https://railway.app/project/[project-id] |
| **Public API** | https://tadss-monitor.up.railway.app |
| **API Docs** | https://tadss-monitor.up.railway.app/docs |
| **Usage Dashboard** | https://railway.app/usage |

---

## Appendix B: Cost Calculator

### B.1 Monthly Cost Estimate

```
Compute (0.5 vCPU average, 24/7):
  - $0.0000071667 × 2,592,000 seconds × 0.5 vCPU
  - = ~$0.19/month

Storage (2 GB volume):
  - $1.00 × 2 GB
  - = ~$0.02/month

Bandwidth (<1 GB):
  - Free
  - = $0.00

Total Monthly Cost: ~$0.21
```

### B.2 Trial Credit Coverage

```
Monthly credit: $5.00
TA-DSS cost:    $0.21
Leftover:       $4.79

Coverage: ~23 months of TA-DSS usage per $5 credit
```

---

## Appendix C: Comparison with Other Providers

### C.1 Feature Comparison

| Feature | Railway | Google Cloud e2-micro | Oracle Cloud Free | Hugging Face |
|---------|---------|----------------------|-------------------|--------------|
| **Monthly Cost** | ~$0.21 | $0 | $0 | $0 |
| **Setup Time** | 10 min | 15-20 min | 30-60 min | 15 min |
| **24/7 Uptime** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Capacity Issues** | ✅ None | ✅ None | ⚠️ Frequent | ✅ None |
| **Code Privacy** | ✅ Private | ✅ Private | ✅ Private | 🔴 Public |
| **Data Privacy** | ✅ Private | ✅ Private | ✅ Private | 🟡 HF access |
| **Auto-Deploy** | ✅ Yes | ❌ No | ❌ No | ⚠️ Git-based |
| **SSL/HTTPS** | ✅ Auto | ⚠️ Manual | ⚠️ Manual | ✅ Auto |
| **SSH Access** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Credit Card** | ✅ Required | ✅ Required | ✅ Required | ❌ Not required |

---

### C.2 When to Choose Each

| Choose This | When... |
|-------------|---------|
| **Railway** | You want easiest deployment, don't mind ~$0.21/month |
| **Google Cloud e2-micro** | You want $0 cost, okay with 15-20 min setup |
| **Oracle Cloud VM** | You need more resources (4 OCPU, 24 GB) |
| **Hugging Face** | You're okay with public code for testing |

---

## Appendix D: Deployment Checklist

### Pre-Deployment

- [ ] GitHub account created
- [ ] Railway account created
- [ ] Payment method added (for verification)
- [ ] Railway CLI installed
- [ ] Logged in to Railway CLI

### Deployment

- [ ] Project initialized (`railway init`)
- [ ] Environment variables set
- [ ] Persistent volume added (`railway volume add`)
- [ ] Deployment successful (`railway up`)
- [ ] Public URL obtained (`railway domain`)

### Post-Deployment Testing

- [ ] Health endpoint responds
- [ ] Telegram test alert received
- [ ] Scheduler running (check logs)
- [ ] Database persisting (verify volume)
- [ ] Usage monitoring enabled

---

**Document Version:** 1.0
**Last Updated:** March 4, 2026
**Status:** 🟢 Ready for Deployment
