# Google Cloud Platform Free Tier Deployment Guide

**Project:** TA-DSS - Trading Order Monitoring System
**Version:** 1.1
**Date:** March 4, 2026
**Status:** ✅ Successfully Deployed & Verified
**Estimated Time:** 30-45 minutes (first-time setup)
**Monthly Cost:** $0 (within free tier limits)

---

## ⚠️ Important Notice

### **Critical Free Tier Requirements**

| Requirement | Value | Why It Matters |
|-------------|-------|----------------|
| **Region** | `us-central1` (Iowa) | **ONLY US regions are free tier eligible** |
| **Machine Type** | `e2-micro` | Only this type is free |
| **Disk Type** | `Standard persistent disk` | SSD costs extra |
| **Disk Size** | ≤ 30 GB | Free tier limit |

**If you see pricing like "$7.31/month":**
- ❌ You're in a non-US region → Change to `us-central1`
- ❌ Wrong machine type → Select `e2-micro`
- ❌ SSD selected → Change to `Standard persistent disk`

**Google Cloud may show the regular price** but will apply **Free Tier Credit** at end of month. Your $300 trial credit also covers any accidental charges.

---

### **Known Issues & Fixes (From Real Deployment)**

| Issue | Error Message | Solution |
|-------|---------------|----------|
| **Wrong Architecture** | `exec format error` | Use x86_64 Dockerfile (VM is Intel, not ARM) |
| **CORS Format** | `error parsing cors_origins` | Use comma-separated, not JSON array |
| **Free Tier Pricing** | Shows $7.31/month | Change region to `us-central1` |

---

### **Why Google Cloud Over Other Free Options?**

| Issue | Oracle Cloud Free | GitHub Actions | Hugging Face | **Google Cloud e2-micro** |
|-------|-------------------|----------------|--------------|---------------------------|
| **Capacity Issues** | ⚠️ Frequent outages | ✅ None | ✅ None | ✅ None |
| **Data Privacy** | ✅ Private | ❌ No DB access | 🔴 Public code | ✅ Private |
| **24/7 Uptime** | ✅ Yes | ❌ Scheduled only | ✅ Yes | ✅ Yes |
| **Free Tier Limits** | ✅ Generous | ✅ 2K min/mo | ✅ 16 GB RAM | ✅ Always free |
| **Setup Complexity** | ⚠️ Medium | ✅ Easy | ✅ Easy | ⚠️ Medium |

**Google Cloud e2-micro Advantages:**
- ✅ **Truly free** in US regions (no capacity issues like Oracle)
- ✅ **Full privacy** (your code + data not exposed)
- ✅ **24/7 uptime** (VM runs continuously)
- ✅ **SQLite support** (no database migration needed)
- ✅ **$300 free credit** for 90 days (for testing paid features)
- ✅ **No laptop required** after deployment

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Overview](#1-overview) | What is Google Cloud e2-micro? |
| [Prerequisites](#2-prerequisites) | What you need before starting |
| [Step 1: Create Google Cloud Account](#3-step-1-create-google-cloud-account-5-min) | Account setup |
| [Step 2: Create VM Instance](#4-step-2-create-vm-instance-10-min) | VM configuration |
| [Step 3: Connect & Install Docker](#5-step-3-connect--install-docker-5-min) | Server setup |
| [Step 4: Deploy TA-DSS](#6-step-4-deploy-tadss-10-min) | Application deployment |
| [Step 5: Configure & Test](#7-step-5-configure--test-5-min) | Final setup |
| [Cost Analysis](#8-cost-analysis) | Free tier limits & costs |
| [Troubleshooting](#9-troubleshooting) | Common issues |
| [Security Best Practices](#10-security-best-practices) | Hardening your VM |
| [Monitoring & Maintenance](#11-monitoring--maintenance) | Ongoing operations |

---

## 1. Overview

### 1.1 What is Google Cloud e2-micro?

**Google Cloud e2-micro** is a **free tier VM instance** that provides:

| Resource | Specification | TA-DSS Usage |
|----------|---------------|--------------|
| **vCPU** | 2 vCPU (shared) | ~0.2 vCPU average |
| **RAM** | 1 GB | ~500 MB used |
| **Storage** | 30 GB HDD | ~2 GB used |
| **Network** | 1 GB egress/month | ~50 MB used |
| **Uptime** | 24/7 | 24/7 |
| **SLA** | 99.5% | Production-ready |

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│ Google Cloud Platform (us-central1)                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ e2-micro VM Instance                                  │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │ Docker Container (TA-DSS)                       │ │ │
│  │  │                                                  │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │ │ │
│  │  │  │ FastAPI     │  │ APScheduler │  │ SQLite  │ │ │ │
│  │  │  │ :8000       │  │ Every hour  │  │ DB      │ │ │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────┘ │ │ │
│  │  │                                                  │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐               │ │ │
│  │  │  │ Telegram    │  │ CCXT/       │               │ │ │
│  │  │  │ Bot         │  │ yfinance    │               │ │ │
│  │  │  └─────────────┘  └─────────────┘               │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  Firewall: Only port 22 (SSH) + 8000 (API) open     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Access: SSH from your laptop, API from anywhere           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Why This Works for TA-DSS

**Resource Requirements vs Free Tier:**

| Resource | TA-DSS Needs | e2-micro Provides | Headroom |
|----------|--------------|-------------------|----------|
| CPU | ~10% of 1 core | 2 vCPU (shared) | ✅ 80% free |
| RAM | ~500 MB | 1 GB | ✅ 50% free |
| Storage | ~2 GB | 30 GB | ✅ 93% free |
| Network | ~50 MB/month | 1 GB/month | ✅ 95% free |

**Conclusion:** TA-DSS runs comfortably within free tier limits.

---

## 2. Prerequisites

### 2.1 Required Accounts

| Account | Purpose | Link |
|---------|---------|------|
| **Google Account** | Gmail/Google Workspace | https://accounts.google.com |
| **Google Cloud** | Auto-created with billing | https://console.cloud.google.com |
| **Telegram Bot** | For alerts (already have) | @BotFather |

### 2.2 Required Information

| Item | Example | Where to Find |
|------|---------|---------------|
| **Project Name** | `tadss-monitor` | You choose |
| **VM Name** | `tadss-vm` | You choose |
| **Region** | `us-central1` (Iowa) | Free tier eligible |
| **Telegram Bot Token** | `8726527766:AAF8F9P3ES6t...` | Your `.env` file |
| **Telegram Chat ID** | `652745650` | Your `.env` file |

### 2.3 What You DON'T Need

- ❌ Credit card for billing (only for verification, not charged)
- ❌ Domain name (use VM's external IP)
- ❌ SSL certificate (internal API only)
- ❌ Database migration (SQLite works as-is)
- ❌ Docker knowledge (commands provided)

---

## 3. Step 1: Create Google Cloud Account (5 min)

### 3.1 Sign Up for Google Cloud

1. **Go to:** https://console.cloud.google.com/getting-started
2. **Sign in** with your Google account
3. **Accept Terms of Service**

### 3.2 Create Billing Account

**Important:** This is for **verification only**. You won't be charged if you stay within free tier.

1. Click **"Create Billing Account"**
2. Fill in:
   - **Account Type:** Individual (or Business)
   - **Name:** Your name
   - **Address:** Your address
3. **Add Payment Method:**
   - Credit/Debit card (verified, not charged)
   - Or bank account (some regions)
4. Click **"Start My Free Trial"**

**You Get:**
- ✅ $300 free credit (90 days)
- ✅ Always Free tier (unlimited time)
- ✅ No automatic charges after trial

### 3.3 Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Click **"Select a Project"** → **"New Project"**
3. Fill in:
   - **Project Name:** `tadss-monitor`
   - **Organization:** (none)
   - **Location:** No organization
4. Click **"Create"**
5. Wait 30 seconds for project creation

### 3.4 Enable Required APIs

1. Go to **APIs & Services** → **Library**
2. Search and enable:
   - **Compute Engine API** (for VM)
   - **Cloud Build API** (optional, for Docker builds)

---

## 4. Step 2: Create VM Instance (10 min)

### 4.1 Navigate to Compute Engine

1. Go to **Compute Engine** → **VM Instances**
2. Click **"Create Instance"**

### 4.2 Configure VM Settings

**Basic Configuration:**

| Setting | Value | Notes |
|---------|-------|-------|
| **Name** | `tadss-vm` | Your choice |
| **Region** | `us-central1 (Iowa)` | **Must be US region for free tier** |
| **Zone** | `us-central1-a` | Any in us-central1 |
| **Machine Family** | E2 | Free tier eligible |
| **Machine Type** | `e2-micro` | 2 vCPU, 1 GB RAM |

**Boot Disk Configuration:**

| Setting | Value |
|---------|-------|
| **Operating System** | Ubuntu |
| **Version** | `Ubuntu 22.04 LTS` |
| **Boot Disk Type** | Standard persistent disk |
| **Size** | `30 GB` (free tier limit) |

**Firewall Configuration:**

| Setting | Value | Purpose |
|---------|-------|---------|
| **Allow HTTP traffic** | ❌ Uncheck | Not needed |
| **Allow HTTPS traffic** | ❌ Uncheck | Not needed |

**Advanced Options:**

1. Click **"Management, Security, DNS, Networking, Sole Tenancy"**
2. **Management Tab:**
   - ✅ Enable "Install automatic updates"
   - ✅ Enable "Use Compute Engine serial port output"
3. **Security Tab:**
   - Leave defaults (SSH key will be generated)
4. **Networking Tab:**
   - **Network Interfaces:** Keep default (default network)
   - **Firewall:** We'll configure manually later

### 4.3 Review & Create

1. Review configuration summary:
   ```
   Machine type: e2-micro (2 vCPU, 1 GB memory)
   Boot disk: 30 GB Standard Persistent Disk
   Region: us-central1
   Zone: us-central1-a
   ```
2. Click **"Create"**
3. Wait 2-3 minutes for VM provisioning

### 4.4 Note External IP Address

Once VM is created:

1. Go to **Compute Engine** → **VM Instances**
2. Find your VM (`tadss-vm`)
3. Copy the **External IP** (e.g., `34.123.45.67`)
4. **Save this IP** - you'll need it for SSH and API access

---

## 5. Step 3: Connect & Install Docker (5 min)

### 5.1 Connect via SSH

**Option A: Browser-based SSH (Easiest)**

1. Go to **Compute Engine** → **VM Instances**
2. Click **"SSH"** button next to your VM
3. Wait for SSH terminal to open in browser

**Option B: Terminal SSH (Advanced)**

```bash
# Download your SSH key (first time only)
gcloud compute config-ssh

# Connect to VM
gcloud compute ssh tadss-vm --zone us-central1-a
```

### 5.2 Update System Packages

In SSH terminal:

```bash
# Update package list
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install required tools
sudo apt install -y git curl wget
```

### 5.3 Install Docker

```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Verify Docker installation
docker --version
# Expected: Docker version 24.x.x
```

**Important:** After adding user to docker group, you need to **reconnect SSH**:

```bash
# Exit SSH
exit

# Reconnect (use SSH button or gcloud command again)
```

### 5.4 Install Docker Compose (Optional)

```bash
# Docker Compose v2 is included with Docker Desktop
# For Linux, install separately:
sudo apt install -y docker-compose-plugin

# Verify
docker compose version
```

---

## 6. Step 4: Deploy TA-DSS (10 min)

### 6.1 Clone Your Repository

In SSH terminal:

```bash
# Navigate to home directory
cd ~

# Clone your GitHub repository
git clone https://github.com/menala22/tadss-monitor.git

# Navigate to project
cd tadss-monitor

# Verify files
ls -la
# Should see: src/, requirements.txt, docker/, etc.
```

### 6.2 Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Update these values in `.env`:**

```bash
# Telegram (REQUIRED)
TELEGRAM_BOT_TOKEN=8726527766:AAF8F9P3ES6tRUHEpVcxSZv_qffUUNCp58Y
TELEGRAM_CHAT_ID=652745650

# Database (keep as-is for SQLite)
DATABASE_URL=sqlite:///./data/positions.db

# Application
APP_ENV=production
LOG_LEVEL=INFO

# Scheduler (1 hour interval)
MONITOR_INTERVAL=3600
TIMEZONE=UTC

# Security (generate new secret)
SECRET_KEY=$(openssl rand -hex 32)

# CORS Origins - IMPORTANT: Use JSON array format with double quotes
CORS_ORIGINS=["http://localhost:8501","http://localhost:8000"]

# Leave these empty/defaults
CCXT_API_KEY=
CCXT_SECRET=
YFINANCE_API_KEY=
```

**⚠️ CRITICAL: CORS_ORIGINS Format**

**✅ Correct (JSON array with double quotes):**
```bash
CORS_ORIGINS=["http://localhost:8501","http://localhost:8000"]
```

**❌ Wrong (causes startup error):**
```bash
CORS_ORIGINS=http://localhost:8501,http://localhost:8000
```

**Why:** Pydantic Settings expects JSON array format for list fields.

**To generate SECRET_KEY:**

```bash
# Generate random secret
openssl rand -hex 32
# Copy output to SECRET_KEY in .env
```

**Save and exit nano:**
- `Ctrl + O` → Enter (save)
- `Ctrl + X` (exit)

**Verify .env was saved correctly:**
```bash
cat .env | grep -E "TELEGRAM|CORS"
```

### 6.3 Create Dockerfile (x86_64 Simplified Version)

**Important:** Your VM is **x86_64 (Intel)**, NOT ARM. Use this simplified Dockerfile:

```bash
# Check if Dockerfile exists
ls -la docker/Dockerfile
```

If exists, backup and create new:

```bash
# Backup old Dockerfile
mv docker/Dockerfile docker/Dockerfile.bak

# Create new simplified Dockerfile
nano docker/Dockerfile
```

**Paste this content (x86_64 compatible):**

```dockerfile
# TA-DSS Production Dockerfile (x86_64)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install basic dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create directories
RUN mkdir -p logs data

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Save and exit:** `Ctrl + O` → `Enter` → `Ctrl + X`

**Why this Dockerfile works:**
- ✅ Uses `python:3.12-slim` (x86_64 compatible)
- ✅ Minimal dependencies (gcc only)
- ✅ No ARM-specific packages
- ✅ Simple and reliable

### 6.4 Build Docker Image

```bash
# Navigate to project root
cd ~/tadss-monitor

# Build Docker image
docker build -t tadss-monitor:latest -f docker/Dockerfile .

# Wait 3-5 minutes for build
# Expected output: Successfully tagged tadss-monitor:latest
```

### 6.5 Run Docker Container

```bash
# Create necessary directories
mkdir -p data logs

# Run container
docker run -d \
  --name tadss \
  --restart unless-stopped \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env \
  tadss-monitor:latest

# Check container status
docker ps
# Should show: tadss-monitor with STATUS: Up
```

---

## 7. Step 5: Configure & Test (5 min)

### 7.1 Configure Firewall Rules

Allow incoming traffic to your VM:

1. Go to **VPC Network** → **Firewall**
2. Click **"Create Firewall Rule"**
3. Configure:
   - **Name:** `allow-tadss-api`
   - **Network:** default
   - **Priority:** 1000
   - **Direction:** Ingress
   - **Action on match:** Allow
   - **Targets:** All instances in network
   - **Source IP ranges:** `0.0.0.0/0` (or your IP for security)
   - **Protocols and ports:** `tcp:8000`
4. Click **"Create"**

### 7.2 Test API Endpoint

**Get your VM's external IP** (from VM Instances page):

```bash
# Test health endpoint
curl http://YOUR_VM_IP:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-03-04T..."}
```

**Test with your actual IP:**

```bash
# Replace with your VM's external IP
curl http://34.123.45.67:8000/health
```

### 7.3 Test Telegram Alerts

```bash
# Send test alert via API
curl -X POST http://YOUR_VM_IP:8000/api/v1/positions/scheduler/test-alert

# Check your Telegram for test message
```

### 7.4 Verify Scheduler is Running

```bash
# Check container logs
docker logs tadss | grep -i "scheduler"

# Expected: "Background scheduler started"
# Expected: "Scheduled 'position_monitoring' job (runs every hour at :10 minutes)"
```

### 7.5 Create Test Position (Optional)

```bash
# Create a test position via API
curl -X POST http://YOUR_VM_IP:8000/api/v1/positions/open \
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

## 8. Cost Analysis

### 8.1 Free Tier Limits (Monthly)

| Resource | Free Tier Limit | TA-DSS Usage | % Used | Cost |
|----------|-----------------|--------------|--------|------|
| **Compute (e2-micro)** | 1 instance (US regions) | 1 instance | 100% | $0 |
| **Storage (HDD)** | 30 GB | 2 GB | 7% | $0 |
| **Network Egress** | 1 GB to internet | ~50 MB | 5% | $0 |
| **IP Address** | 1 external IPv4 | 1 IP | 100% | $0 |
| **Total** | | | | **$0/month** |

### 8.2 Potential Overage Costs

| Scenario | Cause | Cost | Prevention |
|----------|-------|------|------------|
| **Network overage** | >1 GB egress/month | $0.12/GB | Monitor usage |
| **Storage overage** | >30 GB disk | $0.04/GB/month | Delete old logs |
| **VM upgrade** | Change to larger instance | ~$15-30/month | Stay with e2-micro |
| **Premium features** | Snapshots, backups | Varies | Use free tier only |

### 8.3 $300 Free Credit Usage

**Your $300 credit is for:**
- Testing paid features (don't need for TA-DSS)
- Accidental overages (won't happen with this setup)
- Future expansion (ML models, bigger DB, etc.)

**TA-DSS won't use any credit** - it stays within Always Free limits.

---

## 9. Troubleshooting

### 9.1 Real Deployment Issues (From Production)**

#### Issue 1: Docker Build Fails - Architecture Mismatch

**Symptoms:**
```bash
ERROR: docker: 'docker buildx build' requires 1 argument
# OR
exec /bin/sh: exec format error
```

**Root Cause:**
- VM is **x86_64 (Intel)**, not ARM
- Dockerfile was configured for ARM64 (Apple Silicon)

**Solution:**
```bash
# Use simplified x86_64 Dockerfile
mv docker/Dockerfile docker/Dockerfile.bak

cat > docker/Dockerfile << 'EOF'
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY scripts/ ./scripts/
RUN mkdir -p logs data
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Rebuild
docker build -t tadss-monitor:latest -f docker/Dockerfile .
```

---

#### Issue 2: CORS Configuration Error

**Symptoms:**
```bash
pydantic_settings.sources.SettingsError: error parsing value for field "cors_origins"
```

**Root Cause:**
- `.env` has `CORS_ORIGINS` in wrong format
- Pydantic expects JSON array format with double quotes

**Solution:**
```bash
# Fix CORS_ORIGINS format
nano .env

# Use JSON array format (with double quotes):
CORS_ORIGINS=["http://localhost:8501","http://localhost:8000"]

# NOT comma-separated (this causes error):
# CORS_ORIGINS=http://localhost:8501,http://localhost:8000  ❌

# Restart container
docker restart tadss
```

**Correct Format Example:**
```bash
# ✅ Correct - JSON array with double quotes
CORS_ORIGINS=["http://localhost:8501","http://localhost:8000"]

# ✅ Also correct - single origin
CORS_ORIGINS=["http://localhost:8501"]

# ❌ Wrong - comma-separated (causes parsing error)
CORS_ORIGINS=http://localhost:8501,http://localhost:8000
```

---

#### Issue 3: Free Tier Pricing Shows $7.31/month

**Symptoms:**
- Google Cloud Console shows "$7.31/month" during VM creation
- Worried about being charged

**Root Cause:**
- Not in free tier region (`us-central1`, `us-east1`, or `us-west1`)
- Or wrong machine type selected

**Solution:**
1. **Change region to:** `us-central1 (Iowa)`
2. **Verify machine type:** `e2-micro`
3. **Verify disk type:** `Standard persistent disk`

Google will apply **Free Tier Credit** at end of month. Your $300 trial credit also covers any accidental charges.

---

### 9.2 Common Issues

#### Issue 1: VM Won't Start

**Symptoms:**
- VM status shows "Terminated" or "Stopped"
- SSH connection fails

**Solutions:**
```bash
# Check VM status in Console
# Compute Engine → VM Instances

# If stopped, click "Start"

# If terminated, check:
# - Billing account active?
# - Free tier eligibility?
```

---

#### Issue 2: Docker Container Exits Immediately

**Symptoms:**
```bash
docker ps
# Container not listed

docker ps -a
# Container shows "Exited"
```

**Solutions:**
```bash
# Check container logs
docker logs tadss

# Common causes:
# 1. .env file missing → Create .env
# 2. Port 8000 in use → Change port
# 3. Database error → Check permissions

# Fix and restart
docker rm tadss
docker run -d --name tadss --restart unless-stopped -p 8000:8000 tadss-monitor:latest
```

---

#### Issue 3: Cannot Access API

**Symptoms:**
```bash
curl http://YOUR_VM_IP:8000/health
# Connection timeout
```

**Solutions:**

1. **Check firewall rule:**
   - VPC Network → Firewall
   - Verify `allow-tadss-api` rule exists
   - Port 8000 allowed

2. **Check container is running:**
   ```bash
   docker ps
   # Should show tadss container
   ```

3. **Check container logs:**
   ```bash
   docker logs tadss
   # Look for errors
   ```

4. **Test locally on VM:**
   ```bash
   # SSH into VM
   curl http://localhost:8000/health
   # If this works but external doesn't → Firewall issue
   ```

---

#### Issue 4: Telegram Alerts Not Working

**Symptoms:**
- No alerts received
- Logs show "Telegram not configured"

**Solutions:**

```bash
# Check .env file
cat .env | grep TELEGRAM

# Verify values are correct
TELEGRAM_BOT_TOKEN=8726527766:AAF8F9P3ES6tRUHEpVcxSZv_qffUUNCp58Y
TELEGRAM_CHAT_ID=652745650

# Restart container with updated .env
docker restart tadss

# Check logs
docker logs tadss | grep -i telegram
```

---

#### Issue 5: High Memory Usage

**Symptoms:**
- VM slow or unresponsive
- Container restarts

**Solutions:**

```bash
# Check memory usage
free -h

# If >90% used:
# 1. Reduce log verbosity
nano .env
# Change: LOG_LEVEL=WARNING

# 2. Clear old logs
rm logs/*.log.*

# 3. Restart container
docker restart tadss
```

---

### 9.2 Useful Commands

```bash
# Container management
docker ps                    # List running containers
docker logs tadss            # View logs
docker restart tadss         # Restart container
docker stop tadss            # Stop container
docker start tadss           # Start container

# Resource monitoring
docker stats tadss           # Real-time resource usage
free -h                      # Memory usage
df -h                        # Disk usage

# Logs
tail -f logs/monitor.log     # Live monitoring logs
tail -f logs/telegram.log    # Live Telegram logs
```

---

## 10. Security Best Practices

### 10.1 Firewall Configuration

**Minimum Required Ports:**

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP only | SSH access |
| 8000 | TCP | Your IP only | API access |

**Restrict SSH to Your IP:**

1. Go to **VPC Network** → **Firewall**
2. Edit existing SSH rule or create new:
   - **Source IP ranges:** `YOUR_IP/32` (not `0.0.0.0/0`)
3. Delete default `default-allow-ssh` rule (optional)

---

### 10.2 SSH Key Security

**Use SSH Keys Instead of Passwords:**

```bash
# On your laptop, generate SSH key (if not exists)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy public key to VM
gcloud compute ssh tadss-vm --zone us-central1-a --command="mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys" < ~/.ssh/id_ed25519.pub
```

---

### 10.3 Environment Variables

**Never commit `.env` to Git:**

```bash
# Verify .gitignore includes .env
cat .gitignore | grep env
# Should show: .env

# Never run:
# git add .env  ❌
```

---

### 10.4 Regular Updates

**Monthly Security Updates:**

```bash
# SSH into VM
gcloud compute ssh tadss-vm --zone us-central1-a

# Update system
sudo apt update && sudo apt upgrade -y

# Update Docker image
docker pull tadss-monitor:latest
docker restart tadss
```

---

## 11. Monitoring & Maintenance

### 11.1 Verify 24/7 Operation (Post-Deployment Checklist)

After deployment, verify everything is working:

**1. Check Container Auto-Restart:**
```bash
# Verify restart policy
docker inspect tadss --format='{{.HostConfig.RestartPolicy.Name}}'
# Expected: unless-stopped
```

**2. Test VM Reboot Resilience:**
```bash
# Check current uptime
uptime

# Note container status
docker ps | grep tadss
# Expected: STATUS: Up X minutes
```

**3. Enable Google Cloud Monitoring:**
1. Go to: https://console.cloud.google.com/monitoring
2. Click "Get Started" (if first time)
3. View Dashboard:
   - CPU Utilization
   - Memory Usage
   - Disk I/O
   - Network Traffic

**4. Create Health Check Script:**
```bash
cat > ~/health-check.sh << 'EOF'
#!/bin/bash
EXTERNAL_IP=$(gcloud compute instances list --format='value(EXTERNAL_IP)' --filter='NAME=tadss-vm')
echo "Checking TA-DSS Health..."
echo "VM External IP: $EXTERNAL_IP"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://$EXTERNAL_IP:8000/health)
if [ "$RESPONSE" == "200" ]; then
    echo "✅ Health Check: PASSED (HTTP $RESPONSE)"
else
    echo "❌ Health Check: FAILED (HTTP $RESPONSE)"
fi
CONTAINER_STATUS=$(docker ps --filter "name=tadss" --format "{{.Status}}")
if [ ! -z "$CONTAINER_STATUS" ]; then
    echo "✅ Container: $CONTAINER_STATUS"
else
    echo "❌ Container: Not running"
fi
EOF
chmod +x ~/health-check.sh
~/health-check.sh
```

**Expected output:**
```
Checking TA-DSS Health...
VM External IP: 34.x.x.x
✅ Health Check: PASSED (HTTP 200)
✅ Container: Up X minutes
```

---

### 11.2 Log Rotation (Prevent Disk Full)

**Google Cloud Monitoring (Free):**

1. Go to **Monitoring** → **Dashboards**
2. Click **"Create Dashboard"**
3. Add widgets:
   - CPU Utilization
   - Memory Usage
   - Disk Usage
   - Network Traffic

**Set Up Alerts (Free Tier):**

1. Go to **Monitoring** → **Alerting**
2. Click **"Create Policy"**
3. Configure:
   - **Metric:** VM Instance → CPU utilization
   - **Threshold:** > 80% for 5 minutes
   - **Notification:** Email

---

### 11.2 Application Logs

**View Logs:**

```bash
# Real-time monitoring logs
docker exec tadss tail -f logs/monitor.log

# Real-time Telegram logs
docker exec tadss tail -f logs/telegram.log

# Last 100 lines
docker exec tadss tail -n 100 logs/monitor.log
```

**Log Rotation (Prevent Disk Full):**

Create logrotate config:

```bash
sudo nano /etc/logrotate.d/tadss
```

**Paste:**

```
/app/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

### 11.3 Backup Strategy

**Database Backup (Weekly):**

```bash
# Create backup script
nano ~/backup-db.sh
```

**Paste:**

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR

# Copy database
cp ~/tadss-monitor/data/positions.db $BACKUP_DIR/positions-$DATE.db

# Keep only last 7 backups
find $BACKUP_DIR -name "positions-*.db" -mtime +7 -delete

echo "Backup completed: positions-$DATE.db"
```

**Make executable and schedule:**

```bash
chmod +x ~/backup-db.sh

# Add to crontab (every Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 ~/backup-db.sh") | crontab -
```

---

### 11.4 Cost Monitoring

**Check Monthly Costs:**

1. Go to **Billing** → **Reports**
2. View current month charges
3. Set budget alerts:
   - **Billing** → **Budgets & alerts**
   - Create budget: $1/month
   - Alert at 50%, 90%, 100%

---

## Appendix A: Quick Reference

### A.1 Deployment Completion Checklist

After following this guide, verify all items:

**VM Setup:**
- [ ] VM created in `us-central1` region
- [ ] Machine type: `e2-micro`
- [ ] Boot disk: 30 GB Standard persistent disk
- [ ] External IP noted (e.g., `34.123.45.67`)

**Docker & Application:**
- [ ] Docker installed and running
- [ ] Container running: `docker ps | grep tadss`
- [ ] Container restart policy: `unless-stopped`
- [ ] Health endpoint responds: `curl http://YOUR_IP:8000/health`

**Configuration:**
- [ ] `.env` file created with Telegram credentials
- [ ] `CORS_ORIGINS` in comma-separated format (not JSON array)
- [ ] `SECRET_KEY` generated with `openssl rand -hex 32`

**Firewall & Access:**
- [ ] Firewall rule created: `allow-tadss-api`
- [ ] Port 8000 open for API access
- [ ] API accessible from external network

**Monitoring & Alerts:**
- [ ] Telegram test alert received
- [ ] Scheduler running (check logs for "every hour at :10")
- [ ] Google Cloud Monitoring enabled
- [ ] Health check script created: `~/health-check.sh`

**Backup & Maintenance:**
- [ ] Backup script created: `~/backup-db.sh`
- [ ] Cron job scheduled for weekly backups
- [ ] Log rotation configured

**Cost Verification:**
- [ ] Billing shows $0.00 (or < $0.01)
- [ ] Free tier eligibility confirmed

---

### A.2 Essential Commands

```bash
# Connect to VM
gcloud compute ssh tadss-vm --zone us-central1-a

# Check container status
docker ps

# View logs
docker logs tadss --tail 50

# Restart container
docker restart tadss

# Check resource usage
docker stats tadss --no-stream

# Update application
cd ~/tadss-monitor
git pull
docker build -t tadss-monitor:latest -f docker/Dockerfile .
docker restart tadss
```

---

### A.2 File Locations

| File | Path | Purpose |
|------|------|---------|
| **.env** | `~/tadss-monitor/.env` | Environment variables |
| **Database** | `~/tadss-monitor/data/positions.db` | SQLite database |
| **Logs** | `~/tadss-monitor/logs/` | Application logs |
| **Dockerfile** | `~/tadss-monitor/docker/Dockerfile` | Docker config |
| **Backup Script** | `~/backup-db.sh` | Database backup |

---

### A.3 Important URLs

| Resource | URL |
|----------|-----|
| **Google Cloud Console** | https://console.cloud.google.com |
| **VM Instances** | https://console.cloud.google.com/compute/instances |
| **Billing** | https://console.cloud.google.com/billing |
| **Monitoring Dashboard** | https://console.cloud.google.com/monitoring |
| **API Endpoint** | `http://VM_EXTERNAL_IP:8000` (see `.env`) |
| **API Docs** | `http://VM_EXTERNAL_IP:8000/docs` |
| **Health Check** | `http://VM_EXTERNAL_IP:8000/health` |
| **Test Alert** | `http://VM_EXTERNAL_IP:8000/api/v1/positions/scheduler/test-alert` |

---

### A.4 Dashboard Access (Local to Production)

**Connect to production API from your local dashboard:**

**Option 1: Production Script (Recommended)**
```bash
cd trading-order-monitoring-system
./scripts/run-dashboard-production.sh
```

**Option 2: Environment Variable**
```bash
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

**Option 3: UI Toggle (In Dashboard Settings)**
```bash
# 1. Start dashboard: streamlit run src/ui.py --server.port 8503
# 2. Go to Settings (⚙️) → API Connection
# 3. Select "🌐 Production (Google Cloud)"
# 4. Click "Test Connection" to verify
# 5. View positions in Open Positions (📋)
```

**Note:** `VM_EXTERNAL_IP` is configured in your `.env` file (not committed to git).

---

### A.5 File Locations

| File | Path | Purpose |
|------|------|---------|
| **.env** | `~/tadss-monitor/.env` | Environment variables |
| **Database** | `~/tadss-monitor/data/positions.db` | SQLite database |
| **Logs** | `~/tadss-monitor/logs/` | Application logs |
| **Dockerfile** | `~/tadss-monitor/docker/Dockerfile` | Docker config |
| **Health Check Script** | `~/health-check.sh` | System health verification |
| **Backup Script** | `~/backup-db.sh` | Database backup |
| **Deployment Info** | `~/deployment-info.txt` | Quick reference |
| **Dashboard Script** | `~/tadss-monitor/scripts/run-dashboard-production.sh` | Local dashboard launch |

---

## Appendix B: Cost Calculator

### B.1 Monthly Cost Estimate
Compute (e2-micro in us-central1):     $0.00
Storage (30 GB HDD):                   $0.00
Network (1 GB egress):                 $0.00
IP Address (1 external IPv4):          $0.00
------------------------------------------------
Total Monthly Cost:                    $0.00
```

### B.2 Potential Overage Scenarios

| Scenario | Monthly Cost | Likelihood |
|----------|--------------|------------|
| **Normal TA-DSS usage** | $0.00 | ✅ Expected |
| **Network 2x normal** | $0.00 (still under 1 GB) | ✅ Likely |
| **Network 20x normal** | ~$0.12 | ❌ Unlikely |
| **Accidental VM upgrade** | ~$15-30 | ❌ Preventable |
| **Snapshot backups (10 GB)** | ~$0.26 | ⚠️ Optional |

---

## Appendix C: Comparison with Other Providers

| Feature | Google Cloud e2-micro | Oracle Cloud Free | GitHub Actions |
|---------|----------------------|-------------------|----------------|
| **CPU** | 2 vCPU (shared) | 4 OCPU (ARM) | Shared runners |
| **RAM** | 1 GB | 24 GB | Ephemeral |
| **Storage** | 30 GB | 200 GB | None (stateless) |
| **Network** | 1 GB egress | Unlimited | N/A |
| **Uptime** | 24/7 | 24/7 (when available) | Scheduled only |
| **Setup** | 15 min | 30-60 min | 10 min |
| **Capacity Issues** | Rare | Frequent | None |
| **Privacy** | Full | Full | Code only |
| **Database** | SQLite | SQLite | Cloud DB needed |

---

## Appendix D: Deployment Summary (Real-World Results)

### ✅ Successfully Deployed: March 4, 2026

**What Was Deployed:**
- VM: `tadss-vm` in `us-central1-a`
- Machine: `e2-micro` (2 vCPU, 1 GB RAM)
- Disk: 30 GB Standard persistent disk
- Container: TA-DSS running on port 8000
- Scheduler: Every hour at :10 minutes

**What Worked:**
- ✅ Free tier eligibility (us-central1 region)
- ✅ Docker containerization
- ✅ SQLite database persistence
- ✅ Telegram alerts integration
- ✅ Auto-restart on failure
- ✅ Health check endpoint
- ✅ API documentation at `/docs`

**Issues Encountered & Fixed:**
1. **Docker architecture mismatch** → Used x86_64 Dockerfile
2. **CORS_ORIGINS format** → Changed from JSON array to comma-separated
3. **Free tier pricing display** → Confirmed us-central1 region

**Current Status:**
- ✅ Running 24/7 (no laptop required)
- ✅ $0.00/month (free tier)
- ✅ Telegram alerts working
- ✅ Scheduler checking positions hourly
- ✅ Database persisting data
- ✅ Auto-restart configured

---

**Document Version:** 1.1
**Last Updated:** March 4, 2026
**Status:** ✅ Successfully Deployed & Verified
