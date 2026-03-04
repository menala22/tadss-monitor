# Session #3: x86 Micro VM Deployment Workplan

**Date:** March 4, 2026  
**Objective:** Deploy TA-DSS to Oracle Cloud x86 Micro VM (24/7 monitoring)  
**Estimated Duration:** 2.5-3 hours  
**Owner:** AI Agent + User  

---

## Pre-Session Checklist

### Before Starting

- [ ] Oracle Cloud account is active
- [ ] SSH key exists: `ls -la ~/.ssh/oracle-trading-key*`
- [ ] Public key ready: `cat ~/.ssh/oracle-trading-key.pub`
- [ ] Telegram Bot Token available (in `.env`)
- [ ] Telegram Chat ID available (in `.env`)
- [ ] Stable internet connection
- [ ] ~3 hours of focused time

---

## Session Workplan

### Phase 1: Create VM Instance (15-30 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 1.1 | Login to Oracle Cloud Console | User | ⏳ |
| 1.2 | Navigate to Compute → Instances | User | ⏳ |
| 1.3 | Click "Create Instance" | User | ⏳ |
| 1.4 | Configure instance (see settings below) | User | ⏳ |
| 1.5 | Wait for provisioning (2-5 min) | - | ⏳ |
| 1.6 | Note Public IP address | User | ⏳ |
| 1.7 | Test SSH connection | User | ⏳ |

#### VM Configuration Settings

| Setting | Value |
|---------|-------|
| **Name** | `tadss-production` |
| **Compartment** | Root (default) |
| **Availability Domain** | Any (AD-1, AD-2, or AD-3) |
| **Image** | Canonical Ubuntu 22.04 LTS (**NOT** Minimal) |
| **Shape Family** | **x86_64** |
| **Shape** | VM.Standard.E2.Micro |
| **Networking** | Create new VCN + public subnet |
| **Public IPv4** | ✅ Enabled |
| **SSH Keys** | Paste `~/.ssh/oracle-trading-key.pub` |
| **Boot Volume** | 50 GB (default) |

#### Verification Commands

```bash
# Test SSH (from local machine)
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>

# Expected output: Welcome to Ubuntu 22.04.x LTS
```

**✅ Phase 1 Complete When:** SSH connection successful

---

### Phase 2: Configure VM (30 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 2.1 | SSH into VM | User | ⏳ |
| 2.2 | Update system packages | User | ⏳ |
| 2.3 | **Create 4GB swap file (CRITICAL)** | User | ⏳ |
| 2.4 | Verify swap is active | User | ⏳ |
| 2.5 | Install Python 3.12 + dependencies | User | ⏳ |
| 2.6 | Verify Python installation | User | ⏳ |

#### Commands to Run

```bash
# SSH into VM
ssh -i ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>

# Update packages
sudo apt update && sudo apt upgrade -y

# Create swap file (CRITICAL for 1 GB RAM)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify swap
free -h  # Should show ~4G swap

# Install Python 3.12
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev git python3-pip

# Verify Python
python3.12 --version  # Should show Python 3.12.x
```

**✅ Phase 2 Complete When:** Python 3.12 installed, swap active

---

### Phase 3: Deploy Application (45 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 3.1 | Create app directory | User | ⏳ |
| 3.2 | Clone/copy code to VM | User | ⏳ |
| 3.3 | Create virtual environment | User | ⏳ |
| 3.4 | Install dependencies | User | ⏳ |
| 3.5 | Create .env file | User | ⏳ |
| 3.6 | Initialize database | User | ⏳ |
| 3.7 | Test run application | User | ⏳ |

#### Commands to Run

```bash
# Create app directory
sudo mkdir -p /opt/trading-monitor
sudo chown $USER:$USER /opt/trading-monitor
cd /opt/trading-monitor

# Clone code (Option A: Git)
git clone <YOUR_REPO_URL> .

# OR copy via SCP (Option B: from local machine)
# From local: scp -r ./* ubuntu@<PUBLIC_IP>:/opt/trading-monitor/

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p data logs

# Copy .env from local (from your local machine)
# scp ~/.ssh/oracle-trading-key ubuntu@<PUBLIC_IP>:/tmp/
# OR create manually:
nano .env
```

#### .env File Content

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

```bash
# Secure .env
chmod 600 .env

# Initialize database
python -m src.database init
```

**✅ Phase 3 Complete When:** Database initialized, test run successful

---

### Phase 4: Configure systemd Service (20 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 4.1 | Create service file | User | ⏳ |
| 4.2 | Configure service with memory limits | User | ⏳ |
| 4.3 | Enable service | User | ⏳ |
| 4.4 | Start service | User | ⏳ |
| 4.5 | Verify service status | User | ⏳ |

#### Commands to Run

```bash
# Create service file
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

# Memory limits (CRITICAL for 1 GB RAM)
MemoryMax=700M
MemoryHigh=600M

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-monitor

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trading-monitor
sudo systemctl start trading-monitor

# Check status
sudo systemctl status trading-monitor
```

**✅ Phase 4 Complete When:** Service shows "active (running)"

---

### Phase 5: Configure Firewall (15 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 5.1 | Add Oracle Cloud security rules | User | ⏳ |
| 5.2 | Enable UFW on VM | User | ⏳ |
| 5.3 | Allow SSH (port 22) | User | ⏳ |
| 5.4 | Allow API (port 8000) | User | ⏳ |
| 5.5 | Verify firewall status | User | ⏳ |

#### Oracle Cloud Console (Security Lists)

1. Navigate to: **Networking → Virtual Cloud Networks**
2. Click your VCN
3. Click your subnet
4. Click **Security Lists**
5. Add Ingress Rules:

| Source | Port Range | Protocol | Description |
|--------|------------|----------|-------------|
| 0.0.0.0/0 | 22 | TCP | SSH Access |
| 0.0.0.0/0 | 8000 | TCP | API Server |

#### VM Firewall (UFW)

```bash
# Enable firewall
sudo ufw enable

# Allow required ports
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp

# Check status
sudo ufw status verbose
```

**✅ Phase 5 Complete When:** Firewall enabled, ports 22 and 8000 allowed

---

### Phase 6: Test & Verify (30 min)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 6.1 | Test health endpoint | User | ⏳ |
| 6.2 | Test scheduler status | User | ⏳ |
| 6.3 | Test API documentation | User | ⏳ |
| 6.4 | Test Telegram alert | User | ⏳ |
| 6.5 | Monitor memory usage | User | ⏳ |
| 6.6 | Verify logs | User | ⏳ |
| 6.7 | Document deployment | User | ⏳ |

#### Verification Commands

```bash
# Health check
curl http://<PUBLIC_IP>:8000/health
# Expected: {"status":"healthy","timestamp":"..."}

# Scheduler status
curl http://<PUBLIC_IP>:8000/api/v1/positions/scheduler/status
# Expected: {"running":true,"next_run_time":"...","job_count":1}

# Open positions
curl http://<PUBLIC_IP>:8000/api/v1/positions/open
# Expected: {"positions":[...]}

# API documentation (open in browser)
http://<PUBLIC_IP>:8000/docs

# Test Telegram alert
curl -X POST http://<PUBLIC_IP>:8000/api/v1/positions/scheduler/test-alert
# Check your Telegram for test message

# Monitor memory (on VM)
free -h
swapon --show
ps aux --sort=-%mem | head -10

# View logs
sudo journalctl -u trading-monitor --since "5 minutes ago"
```

**✅ Phase 6 Complete When:** All tests pass, Telegram alert received

---

## Post-Deployment Checklist

### Immediate (Day 1)

- [ ] Health endpoint returns "healthy"
- [ ] Service is running: `systemctl is-active trading-monitor`
- [ ] Scheduler is running
- [ ] Telegram alert received
- [ ] Memory usage < 700 MB
- [ ] Swap is active
- [ ] Firewall configured correctly

### First Week

- [ ] Check logs daily for errors
- [ ] Verify scheduler runs every 4 hours
- [ ] Monitor disk space usage
- [ ] Test backup procedure

### Ongoing (Monthly)

- [ ] Review system updates
- [ ] Check log file sizes
- [ ] Verify database backups
- [ ] Review Telegram alert frequency

---

## Troubleshooting Quick Reference

### Service Won't Start

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

### High Memory Usage

```bash
# Check memory
free -h

# Check swap is active
swapon --show

# If swap not active, re-enable:
sudo swapon /swapfile
```

### Can't Access API

```bash
# Check VM firewall
sudo ufw status

# Check Oracle Cloud security list
# Verify port 8000 is allowed

# Test locally on VM
curl http://localhost:8000/health
```

---

## Time Tracking

| Phase | Planned | Actual | Status |
|-------|---------|--------|--------|
| Phase 1: Create VM | 15-30 min | | ⏳ |
| Phase 2: Configure VM | 30 min | | ⏳ |
| Phase 3: Deploy App | 45 min | | ⏳ |
| Phase 4: systemd Service | 20 min | | ⏳ |
| Phase 5: Firewall | 15 min | | ⏳ |
| Phase 6: Test & Verify | 30 min | | ⏳ |
| **Total** | **~2.5-3 hours** | | |

---

## Session Achievements (To Fill)

### Completed Tasks

- [ ] Phase 1: VM instance created
- [ ] Phase 2: VM configured with swap and Python
- [ ] Phase 3: Application deployed
- [ ] Phase 4: systemd service configured
- [ ] Phase 5: Firewall configured
- [ ] Phase 6: All tests passed

### Issues Encountered

| Issue | Resolution | Status |
|-------|------------|--------|
| | | |

### Files Modified/Created

| File | Purpose |
|------|---------|
| `/etc/systemd/system/trading-monitor.service` | systemd service |
| `/opt/trading-monitor/.env` | Environment variables |
| `/swapfile` | Swap space (4 GB) |

### Next Session Plan

| Task | Owner | Timing |
|------|-------|--------|
| Monitor first 24 hours | User | Ongoing |
| Set up backup automation | AI Agent | Next session |
| Configure log rotation | AI Agent | Next session |

---

## Success Criteria

**Deployment is successful when:**

1. ✅ VM instance is running with public IP
2. ✅ SSH connection works
3. ✅ Swap file is active (4 GB)
4. ✅ Python 3.12 is installed
5. ✅ Application is running via systemd
6. ✅ Health endpoint returns 200 OK
7. ✅ Scheduler is running (next_run_time set)
8. ✅ Telegram test alert received
9. ✅ Memory usage < 700 MB
10. ✅ Firewall allows ports 22 and 8000

---

## Ready to Start?

**When you're ready to begin Phase 1, let me know and I'll guide you through each step!**

**Or if you've already created the VM, share:**
```
✅ VM instance created!
📝 Public IP: [your-public-ip]
```

Then we'll continue with Phase 2 (VM configuration).
