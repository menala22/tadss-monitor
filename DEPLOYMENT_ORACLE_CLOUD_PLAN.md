# Oracle Cloud Free Tier Deployment Plan

**Project:** TA-DSS - Trading Order Monitoring System  
**Version:** 3.0  
**Last Updated:** March 4, 2026  
**Status:** 🔄 Pivoting to GitHub Actions - Oracle Cloud Blocked  

---

## ⚠️ Important Update: Deployment Strategy Changed

**Current Status:** Oracle Cloud deployment is blocked due to:
1. ⏸️ ARM instances (VM.Standard.A1.Flex): Capacity issues in all ADs
2. ❌ x86 instances (VM.Standard.E2.1.Micro): Shape compatibility issues

**New Recommended Approach:** GitHub Actions (serverless, event-driven)

| Aspect | Oracle VM (Old Plan) | GitHub Actions (New Plan) |
|--------|---------------------|---------------------------|
| **Infrastructure** | 24/7 VM | Serverless (runs on schedule) |
| **Cost** | $0/month | $0/month |
| **Setup Time** | 2-3 hours (blocked) | 30-60 minutes |
| **Maintenance** | VM management required | Zero maintenance |
| **Data Source** | MT5 or API | Yahoo Finance API |
| **Architecture** | Continuous process | Event-driven (scan → alert → stop) |
| **Status** | ❌ Blocked | 🟢 **Recommended** |

**Next Steps:** See [`DEPLOYMENT_GITHUB_ACTIONS.md`](./DEPLOYMENT_GITHUB_ACTIONS.md) for complete GitHub Actions deployment guide.

---

## Working Session Log

### Session #1: March 3, 2026

| Field | Details |
|-------|---------|
| **Objective** | Set up Oracle Cloud Free Tier deployment for TA-DSS |
| **Duration** | ~1.5 hours |
| **Owner** | AI Agent + User |

#### Workplan

| # | Task | Planned Time |
|---|------|--------------|
| 1 | Research Oracle Cloud Free Tier specs | 10 min |
| 2 | Create Oracle Cloud account | 30 min |
| 3 | Prepare deployment configuration | 45 min |
| 4 | Create VM instance | 15 min |
| 5 | Configure networking | 15 min |
| 6 | Deploy application | 30 min |
| 7 | Configure environment | 15 min |
| 8 | Set up systemd service | 15 min |
| 9 | Test deployment | 30 min |
| 10 | Configure monitoring | 15 min |
| 11 | Create documentation | 20 min |

#### Achievements

- ✅ Task 1: Researched Oracle Cloud Free Tier specifications
- ✅ Task 2: Created Oracle Cloud account (activated)
- ✅ Task 3: Prepared deployment configuration files
  - Created `docker/` directory with ARM64 Docker files
  - Created `scripts/deploy-oracle.sh` deployment script
  - Created deployment guides
- ✅ Task 4 (Partial): Attempted VM instance creation
  - SSH key generated: `~/.ssh/oracle-trading-key`
  - Navigated to Compute → Instances
  - Configured all settings correctly

#### Issues Encountered

| Issue | Impact | Status |
|-------|--------|--------|
| ARM capacity shortage | Cannot create VM.Standard.A1.Flex instance | ⏸️ Blocked |

**Error Message:**
```
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-3.
Create the instance in a different availability domain or try again later.
```

**Actions Taken:**
1. ✅ Tried AD-1 - Same error (out of capacity)
2. ✅ Tried AD-2 - Same error (out of capacity)
3. ✅ Tried AD-3 - Same error (out of capacity)

#### Pending Tasks

| Task | Status | Next Action |
|------|--------|-------------|
| 4. Create VM instance | ⏸️ Blocked | Retry ARM or switch to x86 Micro |
| 5-11. Remaining tasks | ⏳ Pending | Continue after VM created |

#### Files Created This Session

| File | Purpose |
|------|---------|
| `docker/Dockerfile` | Multi-stage ARM64 build |
| `docker/docker-compose.yml` | Service orchestration with keep-alive |
| `docker/docker-entrypoint.sh` | Container initialization |
| `docker/keepalive.sh` | Idle prevention (health checks every 30 min) |
| `docker/.dockerignore` | Build exclusions |
| `scripts/deploy-oracle.sh` | One-click deployment script |
| `docker/README_DOCKER_DEPLOYMENT.md` | Docker deployment guide |
| `docker/DOCKER_COMPOSE_QUICKSTART.md` | Quick reference |
| `scripts/DEPLOYMENT_SCRIPT_GUIDE.md` | Script documentation |

#### Time Summary

| Activity | Duration |
|----------|----------|
| Configuration | ~45 minutes |
| Account setup | ~30 minutes |
| VM creation attempts | ~15 minutes |
| **Total Spent** | **~1.5 hours** |
| **Remaining** | **~2 hours** (after VM creation) |

#### Next Session Plan

**Decision Point:** Choose deployment path

| Option | Action | Timing |
|--------|--------|--------|
| A: ARM | Retry VM creation in 2-6 hours or next day | Best: early morning/late evening |
| B: x86 Micro | Proceed with VM.Standard.E2.Micro | Available now |

**Recommended:** Start with Option B (x86 Micro) to get system running, migrate to ARM later if needed.

---

### Session #2: March 4, 2026 (Today)

| Field | Details |
|-------|---------|
| **Objective** | Research alternative deployment options, update deployment plan |
| **Duration** | ~30 minutes |
| **Owner** | AI Agent + User |

#### Workplan

| # | Task | Status |
|---|------|--------|
| 1 | Research alternative cloud providers (Vultr, AZDigi, etc.) | ✅ Done |
| 2 | Analyze GitHub hosting options | ✅ Done |
| 3 | Evaluate Oracle x86 Micro fallback option | ✅ Done |
| 4 | Update deployment plan with x86 Micro work plan | ✅ Done |
| 5 | Reorganize document structure | ✅ Done |

#### Achievements

- ✅ Researched alternative deployment options:
  - GitHub Actions (not suitable for 24/7)
  - Render, Railway, Fly.io (free tier limitations)
  - Vultr ($6/month)
  - AZDigi (~80,000-160,000 VND/month)
  - Oracle x86 Micro (free, available now)
- ✅ Created complete x86 Micro deployment work plan (6 phases)
- ✅ Added memory analysis for 1 GB RAM constraint
- ✅ Added comparison table: ARM vs x86 Micro
- ✅ Reorganized document structure (v2.0 → v2.1)
- ✅ Added Working Session Log section

#### Decisions Made

| Decision | Rationale |
|----------|-----------|
| Proceed with Oracle x86 Micro | Free, available now, sufficient for TA-DSS |
| Skip Docker for x86 | Direct Python deployment (simpler, less overhead) |
| Add swap file (4GB) | Critical for 1 GB RAM constraint |
| Keep ARM as future option | Can migrate later if performance needed |

#### Pending Tasks (Carry Over)

| Task | Status | Owner |
|------|--------|-------|
| Create x86 Micro VM instance | 🟢 Ready | User + AI |
| Configure networking | ⏳ Pending | User + AI |
| Deploy application (Python) | ⏳ Pending | AI Agent |
| Configure environment | ⏳ Pending | User + AI |
| Set up systemd service | ⏳ Pending | AI Agent |
| Test deployment | ⏳ Pending | User + AI |
| Configure monitoring | ⏳ Pending | AI Agent |

#### Next Session Plan

**Immediate Next Steps:**
1. User creates x86 Micro VM instance (Phase 1)
2. Follow Phase 2-6 for deployment
3. Test and verify deployment

**When VM is ready, message:**
```
✅ x86 Micro VM instance created successfully!
📝 Public IP: [your-public-ip]
📍 Shape: VM.Standard.E2.Micro
```

---

### Session #3: March 4, 2026 (Later)

| Field | Details |
|-------|---------|
| **Objective** | Attempt x86 Micro VM creation, evaluate GitHub Actions alternative |
| **Duration** | ~45 minutes |
| **Owner** | AI Agent + User |

#### Workplan

| # | Task | Status |
|---|------|--------|
| 1 | Create x86 Micro VM instance (Phase 1) | ⏳ In Progress |
| 2 | Troubleshoot shape compatibility issues | ✅ Done |
| 3 | Evaluate GitHub Actions as alternative | ✅ Done |
| 4 | Create GitHub Actions deployment plan | ✅ Done |
| 5 | Update deployment strategy | ✅ Done |

#### Achievements

- ✅ Attempted x86 Micro VM creation in Oracle Cloud
- ✅ Identified shape compatibility issue: `VM.Standard.E2.1.Micro` not compatible with selected image/AD
- ✅ Tried all troubleshooting steps:
  - Different Availability Domains (AD-1, AD-2, AD-3)
  - Different Ubuntu images (22.04 LTS, 22.04 Minimal, 20.04 LTS)
  - Different shape families (x86_64)
- ✅ Researched GitHub Actions as deployment alternative
- ✅ Created complete GitHub Actions deployment plan
- ✅ Documented in `DEPLOYMENT_GITHUB_ACTIONS.md`

#### Issues Encountered

| Issue | Impact | Status |
|-------|--------|--------|
| Oracle x86 shape compatibility | Cannot create VM.Standard.E2.1.Micro instance | ❌ Blocked |

**Error Message:**
```
This shape is either not compatible with the selected image, 
or not available in the current availability domain.
```

**Actions Taken:**
1. ✅ Tried all 3 Availability Domains - Same error
2. ✅ Tried different Ubuntu images - Same error
3. ✅ Tried Oracle Linux - User preferred to explore alternatives
4. ✅ Decided to pivot to GitHub Actions

#### Decisions Made

| Decision | Rationale |
|----------|-----------|
| **Pivot to GitHub Actions** | Oracle Cloud consistently blocked (ARM + x86) |
| Use Yahoo Finance data | No MT5 bridge needed, simpler architecture |
| Event-driven architecture | Scan → Alert → Stop (no 24/7 VM needed) |
| Free tier sufficient | 2,000 min/month, usage ~900 min/month |

#### Comparison: Oracle VM vs GitHub Actions

| Factor | Oracle VM | GitHub Actions | Winner |
|--------|-----------|----------------|--------|
| **Cost** | $0/month | $0/month | 🤝 Tie |
| **Setup Time** | 2-3 hours | 30-60 min | ✅ GitHub |
| **Availability** | ⏸️ Blocked | 🟢 Always available | ✅ GitHub |
| **Complexity** | VM management | Zero ops | ✅ GitHub |
| **Maintenance** | Updates, monitoring | None | ✅ GitHub |
| **Data Source** | MT5 or API | Yahoo Finance | ✅ GitHub |
| **Architecture** | 24/7 process | Event-driven | ✅ GitHub |

#### Pending Tasks (Carry Over to GitHub Actions)

| Task | Status | Owner |
|------|--------|-------|
| Create GitHub repository | 🟢 Ready | User |
| Configure workflow scheduler | 🟢 Ready | AI Agent |
| Create scan script | 🟢 Ready | AI Agent |
| Set up Telegram integration | 🟢 Ready | User + AI |
| Test manual workflow run | ⏳ Pending | User + AI |
| Verify scheduled execution | ⏳ Pending | User + AI |

#### Files Created This Session

| File | Purpose |
|------|---------|
| `DEPLOYMENT_GITHUB_ACTIONS.md` | Complete GitHub Actions deployment guide |
| `DEPLOYMENT_ORACLE_CLOUD_PLAN.md` | Updated with session log and decision |

#### Time Summary

| Activity | Duration |
|----------|----------|
| Oracle VM troubleshooting | ~30 minutes |
| GitHub Actions research | ~15 minutes |
| Documentation update | ~30 minutes |
| **Total Spent** | **~1.25 hours** |

#### Next Session Plan

**Immediate Next Steps (GitHub Actions):**
1. Create GitHub repository (5 min)
2. Configure secrets (Telegram credentials) (5 min)
3. Create workflow file (10 min)
4. Create scan script (15 min)
5. Test manual workflow run (5 min)
6. Verify first scheduled run (wait for cron)

**When ready to start, message:**
```
✅ GitHub repository created!
📝 Repo: [your-username]/tadss-scheduler
```

Then we'll continue with workflow configuration and testing.

---

## Quick Navigation

| Section | Description | Link |
|---------|-------------|------|
| **⚠️ Important Update** | Deployment strategy changed to GitHub Actions | [Above](#-important-update-deployment-strategy-changed) |
| **Working Session Log** | All 3 sessions documented | [§1](#working-session-log) |
| **GitHub Actions Guide** | Complete new deployment method | [DEPLOYMENT_GITHUB_ACTIONS.md](./DEPLOYMENT_GITHUB_ACTIONS.md) |
| **Option A: ARM** | Best performance (capacity issues) | [§4](#4-option-a-arm-deployment) |
| **Option B: x86** | Available now (compatibility issues) | [§5](#5-option-b-x86-micro-deployment) |
| **Troubleshooting** | Common issues and fixes | [§7](#7-troubleshooting) |
| **Maintenance** | Ongoing operations | [§8](#8-maintenance--operations) |
| **Appendices** | Reference materials | [Appendix](#appendices) |

---

## 1. Executive Summary

### 1.1 Overview

This document provides complete deployment instructions for the TA-DSS Trading Order Monitoring System to Oracle Cloud Free Tier, enabling 24/7 automated monitoring and Telegram alerts for all trading positions.

### 1.2 Key Benefits

| Benefit | Description |
|---------|-------------|
| ✅ **Always Free** | No monthly costs (unlimited time) |
| ✅ **24/7 Operation** | Automated monitoring every 4 hours |
| ✅ **Zero Maintenance** | systemd auto-restart on failures |
| ✅ **Reliable Infrastructure** | Enterprise-grade cloud hosting |
| ✅ **Scalable** | Room to grow within free tier limits |

### 1.3 Deployment Options at a Glance

| Feature | Option A: ARM | Option B: x86 Micro |
|---------|---------------|---------------------|
| **Shape** | VM.Standard.A1.Flex | VM.Standard.E2.Micro |
| **CPU** | 2 OCPUs | 1/8 OCPU (shared) |
| **RAM** | 12 GB | 1 GB |
| **Availability** | ⏸️ Capacity issues | 🟢 Available now |
| **Deployment** | Docker | Direct Python |
| **Best For** | Production performance | Quick start / testing |

### 1.4 Recommendation

| Scenario | Recommended Option |
|----------|-------------------|
| Need it running today | **Option B: x86 Micro** |
| Best long-term performance | **Option A: ARM** (retry later) |
| Can wait for capacity | Option A: ARM |
| Want Docker deployment | Option A: ARM |
| Prefer simple setup | Option B: x86 Micro |

**Our Advice:** Start with **x86 Micro** today to get the system running, then migrate to ARM later if needed.

---

## 2. Deployment Options Comparison

### 2.1 Detailed Specifications

| Resource | Option A: ARM | Option B: x86 Micro |
|----------|---------------|---------------------|
| **Shape** | VM.Standard.A1.Flex | VM.Standard.E2.Micro |
| **Architecture** | ARM64 (Ampere A1) | x86_64 (AMD/Intel) |
| **CPU** | 2 OCPUs | 1/8 OCPU (shared) |
| **RAM** | 12 GB | 1 GB |
| **Boot Volume** | 50 GB | 50 GB |
| **Network** | Up to 1 Gbps | Up to 1 Gbps |
| **Cost** | $0/month | $0/month |
| **Availability** | ⏸️ Often blocked | 🟢 Excellent |

### 2.2 Pros & Cons

#### Option A: ARM (VM.Standard.A1.Flex)

| Pros | Cons |
|------|------|
| ✅ 12 GB RAM (excellent performance) | ⏸️ Frequent capacity issues |
| ✅ 2 OCPUs (fast processing) | ⏸️ May require multiple retry attempts |
| ✅ Docker deployment (clean isolation) | ⏸️ Requires Docker knowledge |
| ✅ Room for additional services | ⏸️ ARM64 architecture (less common) |

#### Option B: x86 Micro (VM.Standard.E2.Micro)

| Pros | Cons |
|------|------|
| ✅ Available now (no waiting) | ⚠️ Limited to 1 GB RAM |
| ✅ Simple Python deployment | ⚠️ Shared CPU (slower) |
| ✅ x86_64 architecture (universal) | ⚠️ Requires swap file configuration |
| ✅ Same free tier benefits | ⚠️ No Docker (direct deployment) |

### 2.3 Memory Analysis: x86 Micro

| Component | Estimated RAM Usage |
|-----------|---------------------|
| Ubuntu 22.04 (base) | ~150-200 MB |
| FastAPI + Uvicorn | ~100-200 MB |
| Python + Dependencies | ~100-150 MB |
| SQLite Database | ~50-100 MB |
| System overhead | ~100 MB |
| **Total** | **~500-750 MB** |

**Verdict:** ✅ Fits within 1 GB RAM (with swap space configured)

---

## 3. Prerequisites

### 3.1 Required (Both Options)

- [ ] **Credit/Debit Card** - Oracle Cloud verification (virtual cards not accepted)
- [ ] **Valid Email Address** - Oracle Cloud account
- [ ] **Phone Number** - SMS verification
- [ ] **SSH Key Pair** - Generate with:
  ```bash
  ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle-trading-key
  ```
- [ ] **Telegram Bot Token** - Configured in `.env`
- [ ] **Telegram Chat ID** - Configured in `.env`
- [ ] **Time Commitment** - ~2.5-3 hours

### 3.2 Option-Specific Requirements

#### For ARM Deployment (Option A)

- [ ] Docker installed locally
- [ ] Docker Compose installed locally
- [ ] Patience for capacity retries

#### For x86 Micro Deployment (Option B)

- [ ] Basic Python/virtualenv knowledge
- [ ] Comfortable with SSH terminal
- [ ] No Docker required

### 3.3 Recommended

- [ ] GitHub Account - For repository access
- [ ] Database backup - In case migration needed
- [ ] Stable internet connection

---

## 4. Option A: ARM Deployment

> **Status:** ⏸️ Capacity Issues - Retry in a few hours or next day  
> **Best Time:** Early morning or late evening (your local time)

### 4.1 Create VM Instance

#### Console Steps

1. Go to Oracle Cloud Console → Compute → Instances
2. Click "Create Instance"
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `tadss-production` |
| Compartment | Root (default) |
| Availability Domain | Try AD-1, then AD-2, then AD-3 |
| Image | Canonical Ubuntu 22.04 Minimal Aarch64 |
| Shape Family | **Arm** |
| Shape | VM.Standard.A1.Flex |
| OCPUs | 2 |
| Memory | 12 GB |
| Networking | Create new VCN + public subnet |
| Public IPv4 | Enabled |
| SSH Keys | Paste `~/.ssh/oracle-trading-key.pub` |

#### Verification

```bash
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>
```

### 4.2 Deploy with Docker

See `docker/README_DOCKER_DEPLOYMENT.md` for complete Docker deployment instructions.

**Quick Start:**
```bash
# From local machine
./scripts/deploy-oracle.sh <PUBLIC_IP>
```

### 4.3 If Capacity Issues Persist

1. **Wait 2-6 hours** and retry
2. **Try different region:**
   - US East (Ashburn) - `us-ashburn-1`
   - US West (Phoenix) - `us-phoenix-1`
   - Europe (Frankfurt) - `eu-frankfurt-1`
   - Asia Pacific (Tokyo) - `ap-tokyo-1`
3. **Fallback to Option B** (x86 Micro)

---

## 5. Option B: x86 Micro Deployment

> **Status:** 🟢 Available Now  
> **Estimated Time:** 2.5-3 hours  
> **Deployment Method:** Direct Python + systemd

### 5.1 Phase 1: Create VM Instance

#### Console Steps

1. Go to Oracle Cloud Console → Compute → Instances
2. Click "Create Instance"
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `tadss-production` |
| Compartment | Root (default) |
| Availability Domain | Any (AD-1, AD-2, or AD-3) |
| Image | Canonical Ubuntu 22.04 LTS (**NOT** Minimal) |
| Shape Family | **x86_64** |
| Shape | VM.Standard.E2.Micro |
| Memory | 1 GB (auto-set) |
| Networking | Create new VCN + public subnet |
| Public IPv4 | Enabled |
| SSH Keys | Paste `~/.ssh/oracle-trading-key.pub` |
| Boot Volume | 50 GB (default) |

#### Verification

```bash
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>
```

---

### 5.2 Phase 2: Configure VM

> ⚠️ **CRITICAL:** Swap file setup is required for 1 GB RAM

#### Step 1: SSH and Update

```bash
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>
sudo apt update && sudo apt upgrade -y
```

#### Step 2: Create Swap File (Required)

```bash
# Create 4GB swap file
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h  # Should show ~4G swap
```

#### Step 3: Install Python 3.12

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev git python3-pip
```

---

### 5.3 Phase 3: Deploy Application

#### Step 1: Create Application Directory

```bash
sudo mkdir -p /opt/trading-monitor
sudo chown $USER:$USER /opt/trading-monitor
cd /opt/trading-monitor
```

#### Step 2: Clone/Copy Code

```bash
# Option A: Git clone
git clone <YOUR_REPO_URL> .

# Option B: SCP from local
# From local machine: scp -r ./* ubuntu@<PUBLIC_IP>:/opt/trading-monitor/
```

#### Step 3: Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Initialize Database

```bash
mkdir -p data logs
python -m src.database init
```

---

### 5.4 Phase 4: Configure Environment

#### Create .env File

```bash
cp .env.example .env
nano .env
```

#### Environment Variables

```ini
# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_CHAT_ID=your_actual_chat_id_here
TELEGRAM_ENABLED=true

# Database
DATABASE_URL=sqlite:///./data/positions.db

# Application Settings
APP_ENV=production
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Scheduler
MONITOR_INTERVAL=14400
TIMEZONE=UTC
```

#### Secure Permissions

```bash
chmod 600 .env
```

---

### 5.5 Phase 5: Configure systemd Service

#### Create Service File

```bash
sudo nano /etc/systemd/system/trading-monitor.service
```

#### Service Configuration

```ini
[Unit]
Description=TA-DSS Trading Order Monitoring System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/trading-monitor
Environment="PATH=/opt/trading-monitor/venv/bin"
ExecStart=/opt/trading-monitor/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Memory limits (critical for 1 GB RAM)
MemoryMax=700M
MemoryHigh=600M

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-monitor

[Install]
WantedBy=multi-user.target
```

#### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-monitor
sudo systemctl start trading-monitor
sudo systemctl status trading-monitor
```

---

### 5.6 Phase 6: Configure Firewall

#### Oracle Cloud Security List

1. Navigate to: Networking → Virtual Cloud Networks → Your VCN → Security Lists
2. Add Ingress Rules:

| Source | Port | Protocol | Description |
|--------|------|----------|-------------|
| 0.0.0.0/0 | 22 | TCP | SSH |
| 0.0.0.0/0 | 8000 | TCP | API |

#### VM Firewall (UFW)

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw status verbose
```

---

## 6. Post-Deployment

### 6.1 Verification Checklist

#### Health Check

```bash
curl http://<PUBLIC_IP>:8000/health
# Expected: {"status":"healthy","timestamp":"..."}
```

#### Service Status

```bash
sudo systemctl status trading-monitor
# Expected: active (running)
```

#### API Endpoints

```bash
# Scheduler status
curl http://<PUBLIC_IP>:8000/api/v1/positions/scheduler/status

# Open positions
curl http://<PUBLIC_IP>:8000/api/v1/positions/open

# API documentation
# Open browser: http://<PUBLIC_IP>:8000/docs
```

#### Telegram Test

```bash
curl -X POST http://<PUBLIC_IP>:8000/api/v1/positions/scheduler/test-alert
```

#### Memory Monitoring

```bash
# Check RAM usage
free -h

# Check swap usage
swapon --show

# Monitor process memory
ps aux --sort=-%mem | head -10
```

### 6.2 First Week Monitoring

- [ ] Check logs daily: `sudo journalctl -u trading-monitor --since "1 hour ago"`
- [ ] Verify scheduler runs on schedule (every 4 hours)
- [ ] Monitor disk space: `df -h`
- [ ] Test backup/restore procedure

---

## 7. Troubleshooting

### 7.1 Common Issues

#### Service Won't Start

```bash
# Check status
sudo systemctl status trading-monitor

# View recent logs
sudo journalctl -u trading-monitor --since "10 minutes ago"

# Common fixes:
# - Python path wrong → Edit ExecStart in service file
# - .env missing → Copy .env file
# - Port 8000 in use → sudo lsof -i :8000
```

#### Can't Access API

```bash
# Check VM firewall
sudo ufw status

# Check Oracle Cloud security list
# Verify port 8000 is allowed

# Test locally
curl http://localhost:8000/health
```

#### High Memory Usage (x86 Micro)

```bash
# Check memory
free -h

# Check swap is active
swapon --show

# If swap not active, re-enable:
sudo swapon /swapfile
```

#### Telegram Alerts Not Working

```bash
# Test endpoint
curl -X POST http://<PUBLIC_IP>:8000/api/v1/positions/scheduler/test-alert

# Check .env variables
cat /opt/trading-monitor/.env | grep TELEGRAM
```

---

## 8. Maintenance & Operations

### 8.1 Routine Tasks

| Frequency | Task | Command |
|-----------|------|---------|
| Daily | Check logs | `sudo journalctl -u trading-monitor -f` |
| Weekly | Check disk space | `df -h` |
| Weekly | Check memory | `free -h` |
| Monthly | System updates | `sudo apt update && sudo apt upgrade -y` |

### 8.2 Backup Procedure

#### Create Backup Script

```bash
nano /opt/trading-monitor/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/trading-monitor"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/trading-monitor/data/positions.db $BACKUP_DIR/positions_$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "positions_*.db" -mtime +30 -delete
```

#### Schedule Daily Backup

```bash
crontab -e
# Add: 0 2 * * * /opt/trading-monitor/backup.sh
```

### 8.3 Update Procedure

```bash
cd /opt/trading-monitor
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart trading-monitor
```

### 8.4 Migration Path (x86 → ARM)

If you start with x86 Micro and later get ARM capacity:

1. Backup database on x86 instance
2. Create ARM instance when available
3. Deploy using Docker method
4. Restore database
5. Update configurations
6. Decommission x86 instance

---

## Appendices

### Appendix A: Cost Breakdown

| Resource | Cost | Notes |
|----------|------|-------|
| ARM Compute (4 OCPUs, 24 GB) | $0/month | Always Free |
| x86 Compute (1/8 OCPU, 1 GB) | $0/month | Always Free |
| Boot Volume (200 GB total) | $0/month | Always Free |
| Network Transfer (10 TB/month) | $0/month | Always Free |
| **Total** | **$0/month** | |

### Appendix B: Security Checklist

- [ ] SSH key authentication (no passwords)
- [ ] Firewall (UFW) enabled
- [ ] `.env` file permissions (600)
- [ ] systemd service with limited privileges
- [ ] No root access for application
- [ ] Oracle Cloud DDoS protection (recommended)
- [ ] Automatic security updates (recommended)

### Appendix C: Quick Reference Commands

```bash
# SSH Connection
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>

# Service Management
sudo systemctl start|stop|restart|status trading-monitor
sudo journalctl -u trading-monitor -f

# Memory Monitoring
free -h
swapon --show
ps aux --sort=-%mem | head -10

# Network
sudo ufw status verbose
curl http://localhost:8000/health
```

### Appendix D: Related Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview |
| `docker/README_DOCKER_DEPLOYMENT.md` | Docker deployment guide |
| `scripts/DEPLOYMENT_SCRIPT_GUIDE.md` | Deployment script reference |
| `DATABASE_GUIDE.md` | Database management |
| `TELEGRAM_ALERT_COMPLETE_GUIDE.md` | Telegram setup |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.0 | 2026-03-04 | AI Agent | Pivoted to GitHub Actions strategy, documented Oracle blockers |
| 2.1 | 2026-03-04 | AI Agent | Added Working Session Log section with session history |
| 2.0 | 2026-03-04 | AI Agent | Complete reorganization, cleaner structure |
| 1.3 | 2026-03-04 | AI Agent | Added x86 Micro fallback option |
| 1.2 | 2026-03-03 | AI Agent | Added capacity issue notes |
| 1.1 | 2026-03-03 | AI Agent | Added Docker deployment option |
| 1.0 | 2026-03-03 | AI Agent | Initial deployment plan |

### Version 3.0 Changes (Latest)

- ✅ Documented Oracle Cloud deployment blockers (ARM + x86)
- ✅ Added GitHub Actions as recommended deployment strategy
- ✅ Created `DEPLOYMENT_GITHUB_ACTIONS.md` (complete guide)
- ✅ Updated status: Pivoting to GitHub Actions
- ✅ Added comparison table: Oracle VM vs GitHub Actions
- ✅ Updated Session #3 log with decision rationale

### Version 2.1 Changes

- ✅ Added Working Session Log section at the beginning
- ✅ Recovered Session #1 (March 3) history with full details
- ✅ Added Session #2 (March 4) summary
- ✅ Documented all achievements, issues, and pending tasks
- ✅ Added time tracking and next session plans

### Version 2.0 Changes

- ✅ Complete document reorganization
- ✅ Clear numbered sections with anchor links
- ✅ Consolidated duplicate content
- ✅ Separated Option A and Option B clearly
- ✅ Moved reference materials to appendices

---

**End of Document**
