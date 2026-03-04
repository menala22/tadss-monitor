# GitHub Actions Deployment Plan

**Project:** TA-DSS - Trading Order Monitoring System  
**Version:** 1.0  
**Date:** March 4, 2026  
**Status:** 🟢 Recommended Deployment Method  
**Estimated Time:** 30-60 minutes  

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Overview](#1-overview) | Why GitHub Actions? |
| [Architecture](#2-architecture) | How it works |
| [Prerequisites](#3-prerequisites) | What you need |
| [Setup Guide](#4-step-by-step-setup-guide) | Complete walkthrough |
| [Workflow Configuration](#5-workflow-configuration) | Cron scheduler setup |
| [Scan Script](#6-scan-script-template) | Yahoo Finance + Telegram |
| [Testing](#7-testing--verification) | Manual and automated tests |
| [Monitoring](#8-monitoring--logs) | View execution history |
| [Troubleshooting](#9-troubleshooting) | Common issues |
| [Cost Analysis](#10-cost-analysis) | Free tier limits |
| **[Contingency Plans](#11-contingency-plans-when-free-tier-is-exceeded)** | **What to do when limit exceeded** |
| [Security](#12-security-best-practices) | Best practices |
| [Next Steps](#13-next-steps) | Enhancements |
| [Appendices](#appendix-a-complete-file-templates) | Reference materials |

---

## 1. Overview

### 1.1 What is GitHub Actions?

GitHub Actions is a CI/CD platform that allows you to automate workflows directly from your GitHub repository. For TA-DSS, we'll use it as a **cloud-based scheduler** to run signal scans on a schedule.

### 1.2 Why GitHub Actions for TA-DSS?

| Benefit | Description |
|---------|-------------|
| ✅ **FREE** | 2,000 minutes/month (public repos) |
| ✅ **Zero Server Management** | No VM, no updates, no monitoring |
| ✅ **Built-in Scheduling** | Cron syntax for scheduled runs |
| ✅ **Yahoo Finance Compatible** | No MT5 bridge needed |
| ✅ **Secure** | Secrets management for API keys |
| ✅ **Easy Logging** | View execution logs in GitHub UI |
| ✅ **Git-based Deployment** | Push to update code |

### 1.3 Architecture Comparison

| Component | VM Deployment | GitHub Actions |
|-----------|---------------|----------------|
| **Infrastructure** | Oracle Cloud VM | GitHub-hosted runners |
| **Scheduler** | APScheduler (inside VM) | GitHub cron workflow |
| **Execution** | Continuous 24/7 | On-demand (runs then stops) |
| **Data Source** | MT5 bridge or API | Yahoo Finance API |
| **State** | SQLite database | Stateless (or file-based) |
| **Cost** | $0-6/month | **FREE** |
| **Setup Time** | 2-3 hours | **30-60 minutes** |

---

## 2. Architecture

### 2.1 How It Works

```
┌─────────────────────────────────────────────────────────┐
│ GitHub Repository                                       │
│                                                         │
│  .github/workflows/scan.yml  (Scheduler)                │
│     │                                                   │
│     │ Every 4 hours (cron)                              │
│     ▼                                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ GitHub Actions Runner (ubuntu-latest)           │   │
│  │                                                  │   │
│  │  1. Checkout code                                │   │
│  │  2. Set up Python                                │   │
│  │  3. Install dependencies                         │   │
│  │  4. Run scan_and_alert.py                        │   │
│  │     - Fetch data from Yahoo Finance              │   │
│  │     - Detect signals                             │   │
│  │     - Send Telegram alert                        │   │
│  │  5. Complete (runner shuts down)                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Secrets:                                               │
│  - TELEGRAM_BOT_TOKEN                                   │
│  - TELEGRAM_CHAT_ID                                     │
└─────────────────────────────────────────────────────────┘
         │
         │ HTTPS POST
         ▼
┌─────────────────────────┐
│ Telegram Bot            │
│ - Signal alerts         │
│ - PnL notifications     │
│ - Status updates        │
└─────────────────────────┘
```

### 2.2 Execution Flow

```
Scheduled Time (e.g., 00:10, 04:10, 08:10, ...)
    │
    ├─ 1. GitHub triggers workflow (cold start: ~30 sec)
    │
    ├─ 2. Runner checks out code (~10 sec)
    │
    ├─ 3. Python setup (~15 sec)
    │
    ├─ 4. Install dependencies (~30 sec, cached after first run)
    │
    ├─ 5. Run scan script (~1-2 min)
    │   ├─ Fetch Yahoo Finance data (50 symbols × 1 sec)
    │   ├─ Process indicators
    │   ├─ Detect signals
    │   └─ Send Telegram alerts
    │
    └─ 6. Workflow completes, runner shuts down

Total Time: ~2-3 minutes per run
```

---

## 3. Prerequisites

### 3.1 Required

- [ ] **GitHub Account** - Free account at https://github.com
- [ ] **Telegram Bot Token** - From @BotFather
- [ ] **Telegram Chat ID** - Your chat ID for receiving alerts
- [ ] **Python Knowledge** - Basic understanding of Python scripts
- [ ] **Git Basics** - Clone, commit, push

### 3.2 Optional (But Recommended)

- [ ] **GitHub Desktop** - Easier Git management
- [ ] **VS Code** - Code editor with Git integration
- [ ] **Postman** - For testing Telegram bot

### 3.3 What You DON'T Need

- ❌ Credit card (GitHub Actions is free)
- ❌ Server/VM management
- ❌ Docker knowledge
- ❌ MT5 bridge or trading platform
- ❌ 24/7 running computer

---

## 4. Step-by-Step Setup Guide

### 4.1 Create GitHub Repository (5 min)

#### Option A: GitHub Web Interface

1. Go to https://github.com/new
2. **Repository name:** `tadss-scheduler`
3. **Description:** "TA-DSS Signal Scanner with Telegram Alerts"
4. **Visibility:** Public (for free unlimited minutes)
5. ✅ Check "Add a README file"
6. Click **Create repository**

#### Option B: Command Line

```bash
# Create directory
mkdir tadss-scheduler
cd tadss-scheduler

# Initialize Git
git init

# Create initial commit
echo "# TA-DSS Scheduler" > README.md
git add README.md
git commit -m "Initial commit"

# Create repo on GitHub (requires GitHub CLI)
gh repo create tadss-scheduler --public --source=. --remote=origin
```

---

### 4.2 Create Project Structure (10 min)

```bash
# Navigate to repo
cd tadss-scheduler

# Create directories
mkdir -p src .github/workflows

# Create files
touch scan_and_alert.py
touch requirements.txt
touch src/scanner.py
touch src/telegram_alert.py
touch src/signal_detector.py
```

#### Final Structure

```
tadss-scheduler/
├── .github/
│   └── workflows/
│       └── scan.yml          # Scheduler configuration
├── src/
│   ├── scanner.py            # Yahoo Finance data fetcher
│   ├── telegram_alert.py     # Telegram notification sender
│   └── signal_detector.py    # Signal detection logic
├── scan_and_alert.py         # Main entry point
├── requirements.txt          # Python dependencies
└── README.md
```

---

### 4.3 Configure GitHub Secrets (5 min)

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret**

#### Add These Secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | Your chat ID | `-987654321` |

5. Click **Add secret** for each

---

### 4.4 Create Workflow File (10 min)

Create `.github/workflows/monitor.yml`:

```yaml
name: TA-DSS Position Monitor

on:
  # Schedule: Every 4 hours at minute 10 (UTC)
  # Runs at: 00:10, 04:10, 08:10, 12:10, 16:10, 20:10 UTC
  # Note: Local scheduler runs every hour; GitHub Actions uses 4-hour intervals to save free tier minutes
  schedule:
    - cron: '10 */4 * * *'

  # Allow manual trigger from GitHub Actions tab
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run position monitor
        run: python scripts/github_monitor.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          DATABASE_URL: sqlite:///./data/positions.db
          APP_ENV: production
          LOG_LEVEL: INFO

      - name: Upload logs (on failure)
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: monitor-logs
          path: |
            logs/*.log
          retention-days: 7
```

---

### 4.5 Create Requirements File (5 min)

Your `requirements.txt` is already in the project root. It includes all necessary dependencies:

```txt
# Data sources
yfinance>=0.2.31          # Stocks, ETFs, indices
ccxt>=4.2.34              # Crypto exchanges (100+)

# Telegram notifications
python-telegram-bot>=22.6
requests>=2.31.0

# Technical analysis
pandas>=2.0.0
pandas-ta>=0.4.71b0
numpy>=1.24.0

# Database
sqlalchemy>=2.0.25

# Utilities
python-dotenv>=1.0.0
```

**Note:** The GitHub Actions workflow will automatically install all dependencies from `requirements.txt`.

---

## 5. Workflow Configuration

### 5.1 Cron Schedule Syntax

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

### 5.2 Schedule Options

#### Every 4 Hours (Recommended for GitHub Actions)
```yaml
schedule:
  - cron: '10 */4 * * *'
# Runs at: 00:10, 04:10, 08:10, 12:10, 16:10, 20:10 UTC
# Daily usage: 6 runs × ~3 min = ~18 minutes/day
# Monthly usage: ~540 minutes (27% of free tier)
```

**Why 4 hours for GitHub Actions?**
- Your **local scheduler runs every hour** at :10 (configured in `src/scheduler.py`)
- GitHub Actions uses **4-hour intervals** to conserve free tier minutes
- This provides a **backup monitoring system** in case your local server goes down
- Still catches critical signal changes within 4 hours

#### Every 6 Hours (Conservative)
```yaml
schedule:
  - cron: '15 */6 * * *'
# Runs at: 00:15, 06:15, 12:15, 18:15 UTC
# Daily usage: 4 runs × ~3 min = ~12 minutes/day
# Monthly usage: ~360 minutes (18% of free tier)
```

#### Specific Times (Market Open/Close)
```yaml
schedule:
  - cron: '30 1 * * 1-5'   # 01:30 UTC Mon-Fri (market open prep)
  - cron: '30 20 * * 1-5'  # 20:30 UTC Mon-Fri (market close analysis)
```

### 5.3 Architecture Difference: Local vs GitHub Actions

| Aspect | Local Scheduler | GitHub Actions |
|--------|-----------------|----------------|
| **Schedule** | Every hour at :10 | Every 4 hours at :10 |
| **Trigger** | APScheduler cron | GitHub cron workflow |
| **Execution** | Continuous 24/7 | On-demand (runs then stops) |
| **Database** | SQLite (`data/positions.db`) | Same DB (via Git LFS or external) |
| **Purpose** | Primary monitoring | Backup monitoring |
| **Cost** | $0-6/month (VM) | FREE (2,000 min/month) |

**Recommended Setup:**
1. **Local scheduler** (every hour) = Primary monitoring
2. **GitHub Actions** (every 4 hours) = Backup + redundancy

### 5.4 Timezone Consideration

GitHub Actions uses **UTC** by default. Convert your timezone:

| Your Timezone | UTC Offset | Example Schedule (Every 4h) |
|---------------|------------|-----------------------------|
| Vietnam (ICT) | UTC+7 | `10 */4 * * *` = 17:10, 21:10, 01:10, ... |
| Japan (JST) | UTC+9 | `10 */4 * * *` = 19:10, 23:10, 03:10, ... |
| US East (EST) | UTC-5 | `10 */4 * * *` = 05:10, 09:10, 13:10, ... |
| UK (GMT) | UTC+0 | `10 */4 * * *` = 00:10, 04:10, 08:10, ... |

---

## 6. Monitor Script Template

### 6.1 Main Entry Point: `scripts/github_monitor.py`

This script uses your **existing TA-DSS monitoring system** (`src.monitor.PositionMonitor`) rather than creating separate scanners.

```python
#!/usr/bin/env python3
"""
TA-DSS Position Monitor for GitHub Actions.

This script is designed to run on GitHub Actions scheduled workflows.
It checks all open positions and sends Telegram alerts on signal changes.

Usage:
    python scripts/github_monitor.py

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram bot token (required)
    TELEGRAM_CHAT_ID: Telegram chat ID (required)
    DATABASE_URL: Database connection string (default: sqlite:///./data/positions.db)
    APP_ENV: Application environment (default: production)
    LOG_LEVEL: Logging level (default: INFO)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitor import PositionMonitor
from src.config import settings

# Setup logging for GitHub Actions
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Run position monitoring check on GitHub Actions.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    logger.info("=" * 60)
    logger.info("TA-DSS Position Monitor - GitHub Actions")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}Z")
    logger.info("=" * 60)

    # Check Telegram configuration
    if not settings.telegram_enabled:
        logger.error("❌ Telegram not configured!")
        logger.error("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        logger.error("   in GitHub Secrets (Settings → Secrets and variables → Actions)")
        return 1

    logger.info("✅ Telegram configured")

    try:
        # Initialize monitor
        monitor = PositionMonitor(telegram_enabled=True)
        logger.info("✅ PositionMonitor initialized")

        # Run monitoring check
        logger.info("🔍 Starting position check...")
        results = monitor.check_all_positions()

        # Log summary
        logger.info("=" * 60)
        logger.info("📊 SCAN SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Total positions: {results.get('total', 0)}")
        logger.info(f"   Successful: {results.get('successful', 0)}")
        logger.info(f"   Alerts sent: {results.get('alerts_sent', 0)}")
        logger.info(f"   Errors: {results.get('errors', 0)}")
        logger.info("=" * 60)

        # Check for errors
        if results.get('errors', 0) > 0:
            logger.warning(f"⚠️ {results['errors']} error(s) occurred during scan")
            # Log individual errors
            for result in results.get('results', []):
                if result.get('error'):
                    logger.warning(f"   - {result.get('pair', 'Unknown')}: {result['error']}")

        # Check if database exists
        db_path = Path("data/positions.db")
        if not db_path.exists():
            logger.warning("⚠️ Database not found at data/positions.db")
            logger.warning("   This is normal if no positions have been created yet.")
            logger.warning("   Create positions via API or Dashboard first.")

        logger.info(f"✅ Scan completed at {datetime.utcnow().isoformat()}Z")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Key Features:**
- ✅ Uses **existing `PositionMonitor`** class (same as local scheduler)
- ✅ **Automatic logging** to GitHub Actions console
- ✅ **Error handling** with detailed error messages
- ✅ **Exit codes** for workflow status (0 = success, 1 = error)
- ✅ **Database check** to handle missing DB gracefully

---

### 6.2 How It Works

The script leverages your **complete TA-DSS monitoring system**:

```
scripts/github_monitor.py
    │
    ├─► src.monitor.PositionMonitor
    │       │
    │       ├─► src.data_fetcher.DataFetcher
    │       │   ├─► yfinance (stocks, ETFs, indices)
    │       │   └─► ccxt (crypto: BTC, ETH, etc.)
    │       │
    │       ├─► src.services.technical_analyzer.TechnicalAnalyzer
    │       │   ├─► EMA 10, 20, 50
    │       │   ├─► MACD (12, 26, 9)
    │       │   ├─► RSI (14)
    │       │   └─► OTT (Overlay Trend Trigger)
    │       │
    │       ├─► src.monitor._should_send_alert()
    │       │   ├─► Overall status change (BULLISH ↔ BEARISH)
    │       │   ├─► MA10 change (independent tracking)
    │       │   └─► OTT change (independent tracking)
    │       │
    │       └─► src.notifier.TelegramNotifier
    │           ├─► Anti-spam logic
    │           ├─► Message formatting
    │           └─► Retry logic
    │
    └─► SQLite database (data/positions.db)
            ├─► Update last_signal_status
            ├─► Update last_ma10_status
            ├─► Update last_ott_status
            └─► Log to signal_changes table
```

**Indicator Calculation (6 total):**

| Indicator | Parameters | Bullish Condition |
|-----------|------------|-------------------|
| MA10 | EMA 10 | Close > EMA + 0.3% |
| MA20 | EMA 20 | Close > EMA + 0.3% |
| MA50 | EMA 50 | Close > EMA + 0.3% |
| MACD | 12, 26, 9 | Histogram > threshold |
| RSI | 14 | RSI > 50 (and < 70) |
| OTT | Trend-following | Trend = 1 |

**Overall Status:** Majority wins (4+ bullish = BULLISH, 4+ bearish = BEARISH)

---

### 6.3 Alert Logic

Alerts are sent **only on changes** (anti-spam logic):

| Trigger Condition | Alert Message Example | Priority |
|-------------------|----------------------|----------|
| Overall status change | `Status changed: BULLISH → BEARISH` | 1 (highest) |
| MA10 change | `MA10 Changed: BULLISH → BEARISH` | 2 |
| OTT change | `OTT Changed: BULLISH → BEARISH` | 3 |

**Note:** Only ONE alert is sent per position per check (first matching condition wins).

---

### 6.4 Database Schema

The script uses the **same SQLite database** as your local system:

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    entry_price FLOAT NOT NULL,
    position_type VARCHAR(5) NOT NULL,  -- LONG or SHORT
    timeframe VARCHAR(10) NOT NULL,
    status VARCHAR(6) NOT NULL,         -- OPEN or CLOSED

    -- Signal tracking (updated on every check)
    last_signal_status VARCHAR(20),     -- Overall: BULLISH/BEARISH/NEUTRAL
    last_ma10_status VARCHAR(20),       -- MA10: BULLISH/BEARISH/NEUTRAL
    last_ott_status VARCHAR(20),        -- OTT: BULLISH/BEARISH/NEUTRAL
    last_checked_at DATETIME,

    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE signal_changes (
    id INTEGER PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,   -- MA10, OTT, or OVERALL
    previous_status VARCHAR(20),
    current_status VARCHAR(20),
    price_at_change FLOAT,
    price_movement_pct FLOAT,
    triggered_alert BOOLEAN,
    changed_at DATETIME NOT NULL
);

CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY,
    alert_type VARCHAR(20) NOT NULL,
    pair VARCHAR(20) NOT NULL,
    current_status VARCHAR(20),
    reason VARCHAR(200),
    message TEXT,
    previous_status VARCHAR(20),
    price_movement_pct FLOAT,
    status VARCHAR(20) NOT NULL,        -- SENT, FAILED, SKIPPED
    error_message TEXT,
    created_at DATETIME NOT NULL
);
```

**Database Handling on GitHub Actions:**

| Scenario | Solution |
|----------|----------|
| **First run** (no DB) | Script warns, exits gracefully |
| **Existing DB** | Commit `data/positions.db` to Git (or use Git LFS) |
| **Concurrent writes** | SQLite handles locking automatically |
| **Backup** | Download artifact after each run |

**Recommended:** Use GitHub Actions as **backup monitoring only**. Your local scheduler (every hour) is the primary system with full database access.

---

## 7. Testing & Verification

### 7.1 Pre-Deployment Checklist

Before deploying to GitHub Actions, verify your local system works:

```bash
# 1. Test local monitoring
python scripts/github_monitor.py

# Expected output:
# ============================================================
# TA-DSS Position Monitor - GitHub Actions
# Started at: 2026-03-04T10:10:00Z
# ============================================================
# ✅ Telegram configured
# ✅ PositionMonitor initialized
# 🔍 Starting position check...
# ============================================================
# 📊 SCAN SUMMARY
# ============================================================
#    Total positions: 3
#    Successful: 3
#    Alerts sent: 1
#    Errors: 0
# ============================================================
# ✅ Scan completed at 2026-03-04T10:12:30Z
# ============================================================
```

**If you see errors:**
- `Telegram not configured`: Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- `No module named 'src'`: Run from project root, not from `scripts/` directory
- `Database not found`: Create a position first via API or Dashboard

---

### 7.2 Manual Test (First Run)

1. **Commit and push all files:**
   ```bash
   git add .
   git commit -m "Add GitHub Actions monitoring workflow"
   git push origin main
   ```

2. **Trigger workflow manually:**
   - Go to repository → **Actions** tab
   - Click "TA-DSS Position Monitor" workflow
   - Click **Run workflow** dropdown
   - Click **Run workflow** button

3. **Monitor execution:**
   - Click on the running job
   - Watch logs in real-time

---

### 7.3 Expected Output

```
Run python scripts/github_monitor.py
  env:
    TELEGRAM_BOT_TOKEN: ***
    TELEGRAM_CHAT_ID: ***
    DATABASE_URL: sqlite:///./data/positions.db
    APP_ENV: production
    LOG_LEVEL: INFO

2026-03-04 10:10:05 - INFO - ============================================================
2026-03-04 10:10:05 - INFO - TA-DSS Position Monitor - GitHub Actions
2026-03-04 10:10:05 - INFO - Started at: 2026-03-04T10:10:05Z
2026-03-04 10:10:05 - INFO - ============================================================
2026-03-04 10:10:05 - INFO - ✅ Telegram configured
2026-03-04 10:10:05 - INFO - ✅ PositionMonitor initialized
2026-03-04 10:10:05 - INFO - 🔍 Starting position check...
2026-03-04 10:10:07 - INFO - Alert triggered for BTCUSD: MA10 Changed: BULLISH → BEARISH
2026-03-04 10:10:08 - INFO - Telegram alert sent for BTCUSD
2026-03-04 10:10:08 - INFO - Checked position 5 (BTCUSD): status=BEARISH, PnL=-2.3%
2026-03-04 10:10:08 - INFO - ============================================================
2026-03-04 10:10:08 - INFO - 📊 SCAN SUMMARY
2026-03-04 10:10:08 - INFO - ============================================================
2026-03-04 10:10:08 - INFO -    Total positions: 3
2026-03-04 10:10:08 - INFO -    Successful: 3
2026-03-04 10:10:08 - INFO -    Alerts sent: 1
2026-03-04 10:10:08 - INFO -    Errors: 0
2026-03-04 10:10:08 - INFO - ============================================================
2026-03-04 10:10:08 - INFO - ✅ Scan completed at 2026-03-04T10:10:08Z
2026-03-04 10:10:08 - INFO - ============================================================
```

---

### 7.4 Verification Checklist

- [ ] Workflow triggered successfully (green checkmark)
- [ ] All steps completed without errors
- [ ] Telegram alert received (check your Telegram chat)
- [ ] Scan completed in < 5 minutes
- [ ] Database updated (check `last_checked_at` timestamp)
- [ ] Signal changes logged (query `signal_changes` table)

---

### 7.5 Test Alert Scenarios

**Scenario 1: Overall Status Change**
```sql
-- Manually set previous status to opposite
UPDATE positions 
SET last_signal_status = 'BULLISH' 
WHERE pair = 'BTCUSD';

-- Run monitor
python scripts/github_monitor.py

-- Expected: Alert "Status changed: BULLISH → BEARISH"
```

**Scenario 2: MA10 Change**
```sql
UPDATE positions 
SET last_ma10_status = 'BULLISH' 
WHERE pair = 'ETHUSD';

-- Run monitor
python scripts/github_monitor.py

-- Expected: Alert "MA10 Changed: BULLISH → BEARISH"
```

**Scenario 3: No Change (No Alert)**
```sql
-- Current status matches database
-- Run monitor
python scripts/github_monitor.py

-- Expected: No alert (only status update message)
```

---

## 8. Monitoring & Logs

### 8.1 View Execution History

1. Go to repository → **Actions** tab
2. See list of all workflow runs
3. Click any run to view details
4. Click individual steps to see logs

### 8.2 Log Retention

- **GitHub keeps logs for 90 days** (free tier)
- Download important logs as backup
- Use artifacts to save scan results

### 8.3 Notifications

#### Get Email on Failure

1. Go to repository → **Settings**
2. Click **Notifications**
3. Enable email notifications

#### Get Telegram on Failure (Advanced)

Add to workflow:

```yaml
on:
  workflow_run:
    workflows: ["TA-DSS Signal Scan"]
    types: [completed]

jobs:
  on-failure:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    steps:
      - name: Notify failure
        run: |
          curl -X POST "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
            -d "chat_id=${{ secrets.TELEGRAM_CHAT_ID }}" \
            -d "text=❌ TA-DSS scan failed! Check: ${{ github.event.workflow_run.html_url }}"
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Workflow Not Running on Schedule

**Problem:** Cron schedule not triggering

**Solutions:**
1. Check cron syntax (use https://crontab.guru/)
2. Verify workflow is on `main` branch
3. Check GitHub Actions isn't disabled
4. Wait up to 1 hour (GitHub has slight delays)

#### "No data for symbol" Error

**Problem:** Yahoo Finance returns no data

**Solutions:**
1. Verify symbol is correct (case-sensitive)
2. Check symbol is traded on supported exchange
3. Add rate limiting (`time.sleep(1)`)
4. Try different period/interval

#### Telegram Alerts Not Received

**Problem:** No alerts in Telegram

**Solutions:**
1. Verify bot token is correct
2. Verify chat ID is correct (include minus sign for groups)
3. Check bot is not blocked
4. Test bot manually: `https://api.telegram.org/bot<TOKEN>/getUpdates`

#### Rate Limit Exceeded

**Problem:** Yahoo Finance rate limiting

**Solutions:**
```python
# Add between API calls
import time
time.sleep(1)  # 1 second delay
```

#### Workflow Timeout (6 hours)

**Problem:** Scan takes too long

**Solutions:**
1. Reduce number of symbols
2. Optimize data fetching (parallel requests)
3. Reduce historical data period
4. Add timeout to HTTP requests

### 9.2 Debug Mode

Add debug output to workflow:

```yaml
- name: Debug environment
  run: |
    echo "Python version: $(python --version)"
    echo "Working directory: $(pwd)"
    echo "Files: $(ls -la)"
```

---

## 10. Cost Analysis

### 10.1 Free Tier Limits

| Resource | Limit | Your Usage | Remaining |
|----------|-------|------------|-----------|
| **Minutes/month** | 2,000 | ~540 (6 runs/day × 3 min × 30 days) | 1,460 |
| **Storage** | 5 GB | ~50 MB (with database) | 4.95 GB |
| **Bandwidth** | Unlimited | Minimal | Unlimited |
| **Concurrent jobs** | 1 | 1 | OK |

### 10.2 Usage Estimate

**GitHub Actions Schedule (Every 4 Hours):**
```
Runs per day: 6 (every 4 hours: 00:10, 04:10, 08:10, 12:10, 16:10, 20:10)
Time per run: ~3 minutes (depends on number of positions)
Days per month: 30

Monthly usage: 6 × 3 × 30 = 540 minutes
Usage percentage: 540 / 2,000 = 27%
Remaining buffer: 1,460 minutes (73%)

✅ Well within free limits!
```

**Local Scheduler (Every Hour) - For Comparison:**
```
Runs per day: 24 (every hour at :10)
Time per run: ~3 minutes
Days per month: 30

Monthly usage: 24 × 3 × 30 = 2,160 minutes
Usage percentage: 2,160 / 2,000 = 108% (would exceed free tier!)

❌ Exceeds free tier by 160 minutes
```

**Why 4-Hour Schedule?**
- Your **local scheduler runs every hour** (primary monitoring)
- GitHub Actions is a **backup** (every 4 hours)
- This keeps GitHub Actions at **27% of free tier** with plenty of buffer
- If local scheduler fails, GitHub Actions still catches issues within 4 hours

### 10.3 Cost if Exceeding Free Tier

| Package | Price | Minutes |
|---------|-------|---------|
| Pay-as-you-go | $0.008/minute | Additional minutes |
| Example: 3,000 min/month | ~$8/month | 1,000 overage |
| Example: 2,500 min/month | ~$4/month | 500 overage |

**For your usage (540 min/month):** $0/month (stays within free tier)

### 10.4 Cost Optimization Strategies

| Strategy | New Usage | Savings | Trade-off |
|----------|-----------|---------|-----------|
| **Current (4h)** | 540 min/month | - | 4-hour detection delay |
| Every 6 hours | 360 min/month | 33% | 6-hour detection delay |
| Every 8 hours | 270 min/month | 50% | 8-hour detection delay |
| Every 12 hours | 180 min/month | 67% | 12-hour detection delay |
| Once daily | 90 min/month | 83% | 24-hour detection delay |

**Recommendation:** Stay with **every 4 hours** as backup to local hourly scheduler.

---

## 11. Contingency Plans: When Free Tier Is Exceeded

### 11.1 What Happens When You Exceed 2,000 Minutes?

| Outcome | Details |
|---------|---------|
| **Workflows stop running** | New workflow runs are queued until next month |
| **No automatic charges** | GitHub doesn't auto-charge without consent |
| **Reset on billing cycle** | Minutes reset on your anniversary date |

**Good News:** At ~900 minutes/month usage, you're at **45% of free tier** with plenty of buffer!

---

### 11.2 Option 1: Optimize GitHub Actions Usage ⭐ (First Step)

**Reduce minute consumption:**

| Optimization | Savings | How |
|--------------|---------|-----|
| Cache dependencies | ~30% | Already implemented in workflow |
| Reduce scan frequency | 50-75% | Every 6 hours instead of 4 = 4 runs/day |
| Optimize code speed | 20-30% | Faster data fetching, parallel processing |
| Use self-hosted runner | 100% free | Run on your own machine (not recommended) |

**Example: Reduce to Every 6 Hours**
```yaml
# Change from:
- cron: '10 */4 * * *'  # 6 runs/day = 180 min/month

# To:
- cron: '15 */6 * * *'  # 4 runs/day = 120 min/month
```

**Result:** 33% reduction in usage (~60 minutes/month saved)

**Code Optimizations:**
```python
# Parallel API calls (fetch multiple symbols at once)
import asyncio
import aiohttp

async def fetch_multiple_symbols(symbols):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_symbol(session, sym) for sym in symbols]
        results = await asyncio.gather(*tasks)
    return results

# Reduces time from 50 seconds to ~10 seconds for 50 symbols
```

---

### 11.3 Option 2: Google Cloud Run ☁️ (Best Free Alternative)

**Why:** Generous free tier, auto-scaling, pay-only-for-usage

| Resource | Free Tier | Your Usage |
|----------|-----------|------------|
| **Requests** | 2 million/month | ~180 requests (6/day × 30) |
| **CPU Time** | 180,000 vCPU-seconds | ~540 seconds (3 min × 180) |
| **Memory** | 360,000 GB-seconds | ~900 GB-seconds |
| **Cost** | **FREE** | ✅ Well within limits |

**Quick Setup:**
```bash
# 1. Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# 2. Authenticate
gcloud auth login

# 3. Deploy
gcloud run deploy tadss-scan \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated

# 4. Add Cloud Scheduler trigger
gcloud scheduler jobs create http tadss-schedule \
  --schedule "*/4 * * * *" \
  --http-method POST \
  --uri "https://your-service-url.run.app"
```

**Pros:**
- ✅ Much more generous free tier
- ✅ Auto-scaling (handles any load)
- ✅ Global edge locations
- ✅ No minute limits

**Cons:**
- ⚠️ Requires credit card (for verification)
- ⚠️ More complex setup than GitHub Actions
- ⚠️ Need to learn GCP console

**Best For:** When you outgrow GitHub Actions

---

### 11.4 Option 3: Hugging Face Spaces 🤗 (Free, Underrated)

**Why:** Completely free, 16 GB RAM, no minute limits

| Resource | Free Tier |
|----------|-----------|
| **CPU** | 2 vCPU |
| **RAM** | 16 GB |
| **Storage** | Limited |
| **Cost** | **FREE** |

**Setup:**
```python
# app.py (runs continuously with schedule)
import schedule
import time
from datetime import datetime

def scan_and_alert():
    print(f"[{datetime.utcnow()}] Running scan...")
    # Your scan logic here
    pass

# Schedule every 4 hours
schedule.every(4).hours.do(scan_and_alert)

print("🤖 TA-DSS Scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(1)
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

**Deploy:**
1. Go to https://huggingface.co/new-space
2. Name: `tadss-scheduler`
3. Select **Docker** as Space SDK
4. Push your code

**Pros:**
- ✅ Completely free (no minute limits)
- ✅ 16 GB RAM (massive headroom)
- ✅ Docker support
- ✅ No credit card needed

**Cons:**
- ⚠️ ML-focused branding (but works for anything)
- ⚠️ Public by default (private spaces require payment)
- ⚠️ Less documented for non-ML apps

**Best For:** Free deployment with no minute limits

---

### 11.5 Option 4: Railway.app 🚂 (Low-Cost PaaS)

**Why:** Easy deployment, extremely cheap for your use case

| Plan | Cost | Includes |
|------|------|----------|
| **Trial** | $5 credit/month | ~500 hours of compute |
| **Paid** | Pay-as-you-go | ~$0.000007/second |

**Estimated Cost for Your Usage:**
```
4 runs/day × 3 min = 12 min/day
12 min × 30 days = 360 min/month
360 min × $0.000007/sec ≈ $0.15/month
```

**Setup:**
```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Deploy
railway init
railway up

# 4. Add cron trigger (in Railway dashboard)
# Settings → Cron → New Cron Job
# Schedule: */4 * * * *
```

**Pros:**
- ✅ Extremely cheap (~$0.15/month)
- ✅ Zero maintenance
- ✅ Auto-scaling
- ✅ Git-based deployment

**Cons:**
- ⚠️ $5 trial expires monthly (need to renew)
- ⚠️ Requires credit card

**Best For:** Low-cost, hands-off deployment

---

### 11.6 Option 5: Vultr Cloud Compute 💰 (Paid VM)

**Why:** Simple, predictable pricing, full control

| Plan | CPU | RAM | Storage | Cost |
|------|-----|-----|---------|------|
| **Entry** | 1 vCPU | 1 GB | 25 GB | **$6/month** |

**Pros:**
- ✅ Unlimited runs (no minute limits)
- ✅ Full VM control
- ✅ Simple pricing
- ✅ Can run 24/7 if needed

**Cons:**
- ❌ Not free ($6/month = ~150,000 VND)
- ❌ Requires server management

**Best For:** When you need unlimited runs and full control

---

### 11.7 Comparison Table

| Option | Cost | Setup | Maintenance | Best For |
|--------|------|-------|-------------|----------|
| **GitHub Actions** | FREE | Easy | None | Current setup (≤2,000 min) |
| **Optimize Usage** | FREE | Easy | None | Extending GitHub Actions life |
| **Google Cloud Run** | FREE | Medium | None | When outgrowing GitHub |
| **Hugging Face Spaces** | FREE | Medium | None | Free unlimited alternative |
| **Railway** | ~$0.15/month | Easy | None | Low-cost hands-off |
| **Vultr VM** | $6/month | Easy | Moderate | Unlimited runs, full control |

---

### 11.8 Recommended Escalation Path

#### Phase 1: Optimize Current Setup (Now)

```yaml
# 1. Reduce scan frequency
- cron: '15 */6 * * *'  # Every 6 hours (4 runs/day)

# 2. Optimize code speed
# - Parallel API calls
# - Reduce data fetch period
# - Cache aggressively
```

**Expected Usage:** 120 minutes/month (40% reduction)

---

#### Phase 2: Add Google Cloud Run (Backup)

When you hit 1,500 minutes/month:

1. Deploy to Google Cloud Run as backup
2. Keep GitHub Actions as primary
3. Switch when GitHub limit reached

**Cost:** FREE (within free tier)

---

#### Phase 3: Migrate to Paid (If Needed)

If you need >10,000 minutes/month:

| Option | Cost | Recommendation |
|--------|------|----------------|
| GitHub Pro | $4 + overage | If you love GitHub Actions |
| Railway | ~$0.15-1/month | **Best value** |
| Vultr VM | $6/month | If you need full control |

---

### 11.9 Emergency Plan (If You Hit Limit Unexpectedly)

**Immediate Actions:**

1. **Reduce frequency:**
   ```yaml
   # Change from every 4 hours to every 8 hours
   - cron: '10 */8 * * *'  # 3 runs/day = 45 min/month
   ```

2. **Deploy to Google Cloud Run** (same day)
   - Follow their quickstart guide
   - Takes ~30 minutes

3. **Or temporarily pause:**
   - Comment out cron schedule
   - Trigger manually when needed
   ```yaml
   # on:
   #   schedule:
   #     - cron: '10 */4 * * *'
   
   on:
     workflow_dispatch:  # Manual only
   ```

---

### 11.10 Summary: What To Do When

| Scenario | Solution | Cost |
|----------|----------|------|
| **Current (900 min/month)** | GitHub Actions | FREE |
| **Growing (1,500 min/month)** | Optimize frequency | FREE |
| **Exceeded (2,500+ min/month)** | Google Cloud Run | FREE |
| **Need unlimited runs** | Railway or Vultr | $0.15-6/month |
| **Enterprise scale** | GitHub Pro + overage | $4+ |

**Bottom Line:** You have **multiple free options** before needing to pay anything. GitHub Actions should last a long time at your current usage!

---

## 12. Security Best Practices

### 12.1 Secrets Management

✅ **DO:**
- Store tokens in GitHub Secrets
- Use environment variables in code
- Rotate tokens periodically

❌ **DON'T:**
- Hardcode tokens in code
- Commit `.env` files
- Share tokens in chat/logs

### 12.2 Rate Limiting

```python
# Yahoo Finance
time.sleep(1)  # Between requests

# Telegram
timeout=10  # HTTP request timeout
```

### 12.3 Error Handling

```python
try:
    # API call
except Exception as e:
    print(f"Error: {e}")
    # Don't expose sensitive info in logs
```

---

## 13. Next Steps

### 13.1 Enhancements

| Feature | Description | Priority |
|---------|-------------|----------|
| Multi-timeframe analysis | Scan multiple timeframes | Medium |
| Backtesting | Test strategy on historical data | Low |
| Database storage | Store signals in Supabase/Firebase | Medium |
| Web dashboard | View signals on web | Low |
| Multiple strategies | Run different scan strategies | Medium |

### 13.2 Monitoring Setup

```yaml
# Add to workflow
- name: Upload scan results
  uses: actions/upload-artifact@v4
  with:
    name: scan-results-${{ github.run_number }}
    path: results.json
```

---

## Appendix A: Complete File Templates

### A.1 `.github/workflows/scan.yml` (Complete)

See [Section 4.4](#44-create-workflow-file-10-min)

### A.2 `scan_and_alert.py` (Complete)

See [Section 6.1](#61-main-entry-point-scan_and_alertpy)

### A.3 `requirements.txt` (Complete)

See [Section 4.5](#45-create-requirements-file-5-min)

### A.4 Contingency Plans (Complete)

See [Section 11](#11-contingency-plans-when-free-tier-is-exceeded) - Complete guide to alternatives when exceeding free tier

---

## Appendix B: Quick Reference

### Cron Schedule Examples

```yaml
# Every 4 hours
- cron: '10 */4 * * *'

# Every 6 hours
- cron: '15 */6 * * *'

# Market open (9:30 AM EST = 14:30 UTC)
- cron: '30 14 * * 1-5'

# Hourly during market hours
- cron: '0 14-20 * * 1-5'
```

### Useful Commands

```bash
# Test locally
python scan_and_alert.py

# Check workflow syntax
act -n  # Dry run (requires act tool)

# View GitHub Actions status
https://www.githubstatus.com/
```

---

## Appendix C: Resources

| Resource | Link |
|----------|------|
| GitHub Actions Docs | https://docs.github.com/actions |
| Cron Schedule Tester | https://crontab.guru/ |
| yfinance Documentation | https://pypi.org/project/yfinance/ |
| Telegram Bot API | https://core.telegram.org/bots/api |
| GitHub Status | https://www.githubstatus.com/ |

---

**Document Version:** 1.0  
**Last Updated:** March 4, 2026  
**Status:** 🟢 Ready for Deployment
