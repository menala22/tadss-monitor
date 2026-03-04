# Deployment & 24/7 Operation Guide

**Date:** March 2, 2026  
**Topic:** Running the Trading Order Monitoring System continuously  
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Do I Need 24/7 Operation?](#do-i-need-247-operation)
2. [Why Your Computer Must Be On](#why-your-computer-must-be-on)
3. [Option 1: Cloud VPS Deployment (Recommended)](#option-1-cloud-vps-deployment-recommended)
4. [Option 2: Raspberry Pi](#option-2-raspberry-pi)
5. [Option 3: Manual Checks Only](#option-3-manual-checks-only)
6. [Option 4: Cron Job Without FastAPI](#option-4-cron-job-without-fastapi)
7. [Comparison Table](#comparison-table)
8. [What Happens During Downtime](#what-happens-during-downtime)
9. [Decision Framework](#decision-framework)

---

## Do I Need 24/7 Operation?

### Quick Answer

| Use Case | 24/7 Required? |
|----------|----------------|
| **Automated Telegram alerts** | ✅ YES |
| **Scheduled monitoring at :10 every hour** | ✅ YES |
| **Manual monitoring checks** | ❌ NO |
| **Viewing positions in dashboard** | ❌ NO (just need server running) |
| **Database persistence** | ❌ NO (SQLite file-based) |

### If You Want:

- **Automated alerts while you sleep** → Need 24/7
- **Alerts during work hours only** → Run during work hours
- **Check positions manually** → Run only when needed
- **Dashboard access anytime** → Need 24/7

---

## Why Your Computer Must Be On

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│  Your Computer                                      │
│                                                     │
│  ┌─────────────┐    ┌─────────────┐                │
│  │  FastAPI    │───▶│  Scheduler  │                │
│  │  Server     │    │  (APScheduler)│               │
│  │  (port 8000)│    │             │                │
│  └─────────────┘    └──────┬──────┘                │
│                            │                        │
│                            ▼                        │
│                    ┌───────────────┐                │
│                    │ Monitoring    │                │
│                    │ Check at :10  │                │
│                    └───────┬───────┘                │
│                            │                        │
│                            ▼                        │
│                    ┌───────────────┐                │
│                    │ Telegram      │                │
│                    │ Alert         │                │
│                    └───────────────┘                │
└─────────────────────────────────────────────────────┘
```

### What Stops When Computer Sleeps/Shuts Down

| Component | Status When Off |
|-----------|-----------------|
| FastAPI server | ❌ Stopped |
| APScheduler | ❌ Stopped |
| Automated checks at :10 | ❌ Missed |
| Telegram alerts | ❌ Not sent |
| Database (SQLite) | ✅ Safe (file-based) |
| Position data | ✅ Safe (persisted) |
| Alert history | ✅ Safe (persisted) |

### What Happens on Restart

**Safe - No Data Loss:**
- ✅ Database persists (SQLite file)
- ✅ All positions remain in database
- ✅ Alert history preserved
- ✅ Signal change history preserved

**Resumes Automatically:**
- ✅ Scheduler starts at next :10 mark
- ✅ First check compares with last saved state
- ✅ Alerts trigger if signals changed during downtime

**Temporary Loss:**
- ❌ Missed scheduled checks during downtime
- ❌ No alerts while system was off

---

## Option 1: Cloud VPS Deployment (Recommended) ⭐

**Best for:** Production use, reliability, serious trading

### Recommended Providers

| Provider | Plan | Cost/Month | Specs | Difficulty |
|----------|------|------------|-------|------------|
| **DigitalOcean** | Basic Droplet | $6 | 1GB RAM, 1 CPU, 25GB SSD | Easy |
| **AWS Lightsail** | Nanode | $5 | 512MB RAM, 1 CPU, 20GB SSD | Medium |
| **Google Cloud** | e2-micro | ~$6 | 1GB RAM, 1 vCPU, 10GB SSD | Medium |
| **Hetzner** | CPX11 | €5 | 2GB RAM, 1 vCPU, 40GB SSD | Easy |
| **Linode** | Nanode | $5 | 1GB RAM, 1 CPU, 25GB SSD | Easy |

**Recommendation:** DigitalOcean or Hetzner for ease of use.

### Step-by-Step Setup (DigitalOcean Example)

#### 1. Create Server

```bash
# Go to digitalocean.com
# Create Droplet
# - OS: Ubuntu 22.04 LTS
# - Plan: Basic ($6/month)
# - Region: Choose closest to you
# - Authentication: SSH key (recommended) or password
```

#### 2. SSH Into Server

```bash
# Mac/Linux
ssh root@your-server-ip

# Windows (use PowerShell or PuTTY)
ssh root@your-server-ip
```

#### 3. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.12
apt install python3 python3-pip python3-venv -y

# Install Git
apt install git -y
```

#### 4. Clone Your Project

```bash
# Clone repository
git clone <your-repo-url> /opt/trading-monitor
cd /opt/trading-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 5. Configure Environment

```bash
# Copy .env file from local machine
# From your local machine:
scp .env root@your-server-ip:/opt/trading-monitor/.env

# Or create manually on server:
nano .env

# Add your configuration:
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_ENABLED=true
MONITOR_INTERVAL=3600
TIMEZONE=UTC
DATABASE_URL=sqlite:///./data/positions.db
HOST=0.0.0.0
PORT=8000
```

#### 6. Create Systemd Service

```bash
# Create service file
nano /etc/systemd/system/trading-monitor.service
```

**Service file content:**
```ini
[Unit]
Description=Trading Order Monitoring System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/trading-monitor
Environment="PATH=/opt/trading-monitor/venv/bin"
ExecStart=/opt/trading-monitor/venv/bin/python -m src.main
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-monitor

[Install]
WantedBy=multi-user.target
```

#### 7. Enable and Start Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable service (auto-start on boot)
systemctl enable trading-monitor

# Start service
systemctl start trading-monitor

# Check status
systemctl status trading-monitor

# View logs
journalctl -u trading-monitor -f
```

#### 8. Verify It's Working

```bash
# Check if server is running
curl http://localhost:8000/api/v1/positions/scheduler/status

# Expected response:
# {"running": true, "next_run_time": "2026-03-02T11:10:00Z", "job_count": 1}
```

#### 9. Firewall Configuration (Optional)

```bash
# Allow HTTP access (if you want dashboard access)
ufw allow 8000/tcp

# Or keep it private (only accessible via SSH)
ufw deny 8000/tcp
```

### Maintenance

#### Update Logs
```bash
# View recent logs
journalctl -u trading-monitor --since "1 hour ago"

# Follow logs in real-time
journalctl -u trading-monitor -f
```

#### Restart Service
```bash
systemctl restart trading-monitor
```

#### Stop Service
```bash
systemctl stop trading-monitor
```

#### Update Code
```bash
cd /opt/trading-monitor
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart trading-monitor
```

---

## Option 2: Raspberry Pi

**Best for:** Low power, home setup, one-time cost

### Hardware Requirements

| Component | Recommendation | Cost |
|-----------|---------------|------|
| **Raspberry Pi** | Pi 4 (2GB+) or Pi 5 | $35-80 |
| **MicroSD Card** | 16GB+ Class 10 | $10-15 |
| **Power Supply** | Official USB-C | $10 |
| **Case** | Any Pi case | $5-10 |
| **Total** | | **$60-115** (one-time) |

### Power Consumption

- **Pi 4:** ~5W average
- **Monthly cost:** ~$1-2 (depending on electricity rates)
- **Yearly cost:** ~$15-25

### Setup Steps

```bash
# 1. Install Raspberry Pi OS (64-bit)
# Download from: https://www.raspberrypi.com/software/

# 2. Boot Pi and SSH in
ssh pi@raspberrypi.local

# 3. Install Python
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# 4. Clone project
git clone <your-repo> ~/trading-monitor
cd ~/trading-monitor

# 5. Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Create systemd service (same as VPS)
sudo nano /etc/systemd/system/trading-monitor.service

# 7. Enable and start
sudo systemctl enable trading-monitor
sudo systemctl start trading-monitor
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ One-time cost (~$60-115) | ❌ Requires home internet |
| ✅ Very low power (~5W) | ❌ Home IP exposed (use SSH keys) |
| ✅ Always on at home | ❌ Physical hardware to manage |
| ✅ Full control | ❌ SD card can corrupt (use SSD) |

---

## Option 3: Manual Checks Only

**Best for:** Casual monitoring, no extra cost, testing

### How It Works

Run monitoring checks manually when you need them:

```bash
# Navigate to project directory
cd "/path/to/trading-order-monitoring-system"

# Run monitoring check
python -c "from src.monitor import run_monitoring_check; run_monitoring_check()"
```

### Sample Workflow

```
Morning (8:00 AM):
├─ Run check: python -c "from src.monitor import run_monitoring_check; run_monitoring_check()"
├─ Review Telegram alerts
└─ Check dashboard for position status

During Day (as needed):
├─ Before trading decisions
├─ After significant price movements
└─ When checking positions

Evening (8:00 PM):
├─ Run final check
├─ Review day's alerts
└─ Shut down computer (if desired)
```

### Create a Simple Script

```bash
# Create script
nano check_positions.sh
```

**Script content:**
```bash
#!/bin/bash
cd "/path/to/trading-order-monitoring-system"
source venv/bin/activate
python -c "from src.monitor import run_monitoring_check; run_monitoring_check()"
```

**Make executable:**
```bash
chmod +x check_positions.sh

# Run anytime
./check_positions.sh
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ No 24/7 requirement | ❌ No alerts while sleeping |
| ✅ No server costs | ❌ Manual effort required |
| ✅ Full control over timing | ❌ May miss important signals |
| ✅ Perfect for testing | ❌ Not suitable for active trading |

---

## Option 4: Cron Job Without FastAPI

**Best for:** Automation without web server, lightweight setup

### How It Works

Create a standalone Python script that runs via cron (Unix scheduler).

### Create Standalone Script

```bash
# Create script
nano /opt/trading-monitor/monitoring_script.py
```

**Script content:**
```python
#!/usr/bin/env python3
"""
Standalone monitoring script for cron execution.
Runs without FastAPI server.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.monitor import run_monitoring_check
from src.database import initialize_database

def main():
    """Run monitoring check."""
    try:
        # Initialize database (creates tables if needed)
        initialize_database(verbose=False)
        
        # Run monitoring check
        results = run_monitoring_check()
        
        # Log results
        print(f"✓ Checked {results['total']} positions")
        print(f"✓ Alerts sent: {results['alerts_sent']}")
        print(f"✓ Errors: {results['errors']}")
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Make executable:**
```bash
chmod +x /opt/trading-monitor/monitoring_script.py
```

### Test Script

```bash
# Run manually first
python3 /opt/trading-monitor/monitoring_script.py

# Expected output:
# ✓ Checked 4 positions
# ✓ Alerts sent: 2
# ✓ Errors: 0
```

### Add to Crontab

```bash
# Edit crontab
crontab -e
```

**Add these lines:**

```bash
# Trading monitor - every hour at :10
10 * * * * cd /opt/trading-monitor && /usr/bin/python3 monitoring_script.py >> /var/log/trading-monitor.log 2>&1

# Or every 4 hours at :10 past the hour
10 */4 * * * cd /opt/trading-monitor && /usr/bin/python3 monitoring_script.py >> /var/log/trading-monitor.log 2>&1

# Or specific times (9 AM, 1 PM, 6 PM)
10 9,13,18 * * * cd /opt/trading-monitor && /usr/bin/python3 monitoring_script.py >> /var/log/trading-monitor.log 2>&1
```

### View Logs

```bash
# View recent logs
tail -50 /var/log/trading-monitor.log

# Follow logs in real-time
tail -f /var/log/trading-monitor.log
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ Lightweight (no FastAPI) | ❌ Still needs computer/server on |
| ✅ Standard Unix scheduling | ❌ No API endpoints |
| ✅ Easy to set up | ❌ No dashboard access |
| ✅ Very reliable | ❌ Manual log checking |

---

## Comparison Table

| Feature | Your Computer | Cloud VPS | Raspberry Pi | Manual Only | Cron Job |
|---------|---------------|-----------|--------------|-------------|----------|
| **Setup Cost** | $0 | $5-12/month | $60-115 (one-time) | $0 | $0-5/month |
| **Monthly Cost** | $0 | $5-12 | ~$1-2 (electricity) | $0 | ~$1-2 |
| **24/7 Automation** | ✅ (if always on) | ✅ Yes | ✅ Yes | ❌ No | ✅ (if always on) |
| **Alerts While Sleeping** | ✅ (if on) | ✅ Yes | ✅ Yes | ❌ No | ✅ (if on) |
| **Setup Difficulty** | Easy | Medium | Medium | Easy | Easy |
| **Maintenance** | Low | Low | Low | None | Low |
| **Reliability** | Medium | High | High | N/A | High |
| **Dashboard Access** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Best For** | Testing | Production | Home setup | Casual | Lightweight |

---

## What Happens During Downtime

### Scenario: Computer Off for 8 Hours (10 PM - 6 AM)

```
Timeline:
22:00 - Computer shuts down (last check at 22:10)
23:10 - ❌ Missed check
00:10 - ❌ Missed check
01:10 - ❌ Missed check
02:10 - ❌ Missed check
03:10 - ❌ Missed check
04:10 - ❌ Missed check
05:10 - ❌ Missed check
06:00 - Computer starts up
06:10 - ✅ Scheduler runs, compares with last state (22:10)
       - ✅ Alerts trigger if signals changed
```

### Database State During Downtime

```sql
-- Last check before shutdown
SELECT pair, last_checked_at, last_ma10_status, last_ott_status
FROM positions
WHERE status = 'OPEN';

-- Example output:
-- BTCUSD  | 2026-03-01 22:10:00 | BULLISH | BULLISH
-- ETHUSD  | 2026-03-01 22:10:00 | BEARISH | BULLISH

-- These values are SAFE - no data loss
```

### When You Restart

**First Check Logic:**
```python
# Compare current signals with last saved state
if current_ma10 != last_ma10_status:  # Changed during downtime!
    send_alert("MA10 Changed: BULLISH → BEARISH")

# Update database with current state
position.last_ma10_status = current_ma10
position.last_checked_at = datetime.utcnow()
```

**Result:** You get alerts for any changes that happened during downtime, but only on the first check after restart.

---

## Decision Framework

### Ask Yourself These Questions

#### 1. How Many Positions Do You Monitor?

- **1-2 positions** → Manual checks fine
- **3-5 positions** → Consider automation
- **5+ positions** → Automation strongly recommended

#### 2. What's Your Risk Tolerance?

- **Low** (want to know immediately) → Cloud VPS
- **Medium** (check few times daily) → Manual + Cron
- **High** (only care about major moves) → Manual only

#### 3. What's the Cost of Missing an Alert?

Calculate:
```
If missing a 4-hour signal change could cost you >$50:
→ Automation pays for itself (VPS costs $6/month = $0.20/day)

If you trade small positions (<$1000):
→ Manual checks probably fine
```

#### 4. When Do You Need Alerts?

- **Only during trading hours** → Run manually or cron during those hours
- **24/7 including weekends** → Cloud VPS or Raspberry Pi
- **Only for major changes** → Manual checks ok

#### 5. What's Your Technical Comfort Level?

- **Beginner** → Manual checks or Raspberry Pi
- **Intermediate** → Cloud VPS with guide
- **Advanced** → Any option, customize as needed

---

## Recommended Paths

### Path A: Testing Phase (You Are Here)

```
Run on your computer
↓
Use manual checks when needed
↓
Evaluate if automation is worth it
↓
After 2-4 weeks, decide on deployment
```

### Path B: Serious Trading

```
Deploy to DigitalOcean ($6/month)
↓
Set up systemd service
↓
Monitor for 1 week
↓
Adjust MONITOR_INTERVAL if needed
↓
Focus on trading, not monitoring
```

### Path C: Budget-Conscious

```
Use manual checks during day
↓
Run cron job during evening/night if computer is on
↓
Accept missing overnight alerts
↓
Upgrade to VPS when ready
```

---

## Quick Start Commands

### Manual Check
```bash
cd "/path/to/trading-order-monitoring-system"
python -c "from src.monitor import run_monitoring_check; run_monitoring_check()"
```

### Check Scheduler Status
```bash
curl http://localhost:8000/api/v1/positions/scheduler/status
```

### View Recent Alerts
```bash
sqlite3 data/positions.db "SELECT datetime(timestamp), pair, alert_type, reason FROM alert_history ORDER BY timestamp DESC LIMIT 10;"
```

### View Last Check Time
```bash
sqlite3 data/positions.db "SELECT pair, datetime(last_checked_at) FROM positions WHERE status='OPEN';"
```

---

## Troubleshooting

### "Scheduler Not Running"

```bash
# Check if FastAPI is running
ps aux | grep "src.main"

# If not running, start it
python -m src.main

# Or check systemd status
systemctl status trading-monitor
```

### "Missed Alerts"

```bash
# Check last check time
sqlite3 data/positions.db "SELECT datetime(MAX(last_checked_at)) FROM positions;"

# If old, system was offline
# Restart and wait for next :10 mark
```

### "Service Won't Start"

```bash
# Check logs
journalctl -u trading-monitor --since "10 minutes ago"

# Common issues:
# - Python path wrong → Fix ExecStart in service file
# - .env missing → Copy .env file
# - Port 8000 in use → Kill other process or change port
```

---

## Summary

| If You Want... | Choose This |
|----------------|-------------|
| **Production reliability** | Cloud VPS ($6/month) |
| **Low-cost home setup** | Raspberry Pi ($60 one-time) |
| **No cost, manual control** | Manual checks |
| **Lightweight automation** | Cron job |
| **Testing/development** | Your computer |

**Bottom Line:** For serious trading with multiple positions, deploy to a $6/month VPS. For testing or casual use, manual checks work fine.

---

**Document Version:** 1.0  
**Last Updated:** March 2, 2026  
**Related Docs:** `DATABASE_GUIDE.md`, `TELEGRAM_ALERT_COMPLETE_GUIDE.md`, `SCHEDULER_TIMING_FIX_2026-03-02.md`
