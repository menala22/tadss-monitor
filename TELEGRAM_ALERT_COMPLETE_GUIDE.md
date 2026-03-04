# Telegram Alert System - Complete Guide

**Last Updated:** 2026-03-01  
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [Alert Trigger Scenarios](#alert-trigger-scenarios)
4. [Signal Calculation Logic](#signal-calculation-logic)
5. [Bug History & Troubleshooting](#bug-history--troubleshooting)
6. [Code Reference](#code-reference)

---

## Overview

The Telegram alert system monitors open trading positions and sends alerts when:
- Overall signal status changes (BULLISH ↔ BEARISH)
- MA10 indicator changes status (tracked independently)
- OTT indicator changes status (tracked independently)

**Key Design Decisions:**

1. **Independent Tracking:** MA10 and OTT are tracked in separate database columns, allowing independent alert triggers
2. **Initial Signals:** Signals are calculated immediately when a position is created, enabling alerts on the first monitoring check
3. **6 Indicators:** Overall status uses 6 indicators (MA10, MA20, MA50, MACD, RSI, OTT) with majority wins

---

## Configuration

### Environment Variables (`.env`)

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_ENABLED=true

# Monitoring Interval
MONITOR_INTERVAL=3600  # Check every 1 hour (default)
                       # Range: 3600 (1h) to 86400 (24h)

# Timezone
TIMEZONE=UTC  # All timestamps in UTC
```

---

## Timing & Scheduling

### When Are Alerts Sent?

**Monitoring Schedule:**
- **Default Interval:** Every hour at :10 minutes past the hour
- **Timezone:** UTC (Coordinated Universal Time)

**Example Schedule:**
```
10:10 UTC - Check all positions → Send alerts if changed
11:10 UTC - Check all positions → Send alerts if changed
12:10 UTC - Check all positions → Send alerts if changed
...
```

**Why 10-minute offset?**
- Avoids API congestion at round hour boundaries (:00)
- Many exchanges and data providers refresh at :00
- Reduces risk of rate limiting and slow responses
- More reliable data availability after initial refresh

### How Timing Works

**1. Scheduler Startup:**
```python
# When FastAPI starts (src/main.py lifespan)
start_scheduler()

# Scheduler uses cron trigger for predictable scheduling
scheduler.add_job(
    func=monitor.check_all_positions,
    trigger='cron',
    minute=10,  # Always runs at :10 past the hour
    hour='*',   # Every hour
    id="position_monitoring"
)

# First run: Next :10 mark (regardless of when server started)
# Subsequent runs: Every hour at :10
```

**Important:** The scheduler uses a **cron trigger** which ensures checks always run at :10 past every hour, regardless of when the server was started. This is different from an interval trigger which would count hours from the start time.

**Example:**
- Server starts at 14:45 → First check at 15:10 → Then 16:10, 17:10, etc.
- Server starts at 09:05 → First check at 09:10 → Then 10:10, 11:10, etc.

**2. Job Execution:**
```
┌─────────────────────────────────────────────────────────┐
│ 10:10:00 UTC - Scheduler triggers job                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Fetch all OPEN positions from database                  │
│ For each position:                                      │
│   1. Get latest market data (CCXT/yfinance)             │
│   2. Calculate indicators (MA10, MA20, MA50, etc.)      │
│   3. Compare with previous status                       │
│   4. Send Telegram alert if changed                     │
│   5. Update database with new status                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Job completes (~2-5 seconds for typical portfolio)      │
│ Next run scheduled for 11:10:00 UTC                     │
└─────────────────────────────────────────────────────────┘
```

**3. Anti-Spam Logic:**
- Only ONE alert per position per check
- Only alerts on **changes** (not every check)
- Priority: Status > MA10 > OTT (first match wins)

### Configuration Options

#### Change Check Interval

**In `.env`:**
```bash
# Check every 2 hours
MONITOR_INTERVAL=7200

# Check every 4 hours
MONITOR_INTERVAL=14400

# Check every 6 hours
MONITOR_INTERVAL=21600
```

**Trade-offs:**

| Interval | Pros | Cons | Best For |
|----------|------|------|----------|
| **1 hour** (Default) | ⚡ Fast alerts<br>📊 Current data | 🔋 More API calls | Active monitoring, h1 timeframe |
| 2-4 hours | ⚖️ Balanced | ⏰ Moderate delay | Day trading, h4 timeframe |
| 6-12 hours | 🔋 Fewer API calls | 🐌 Slower reaction | Swing trading, d1 timeframe |
| 24 hours | 🔋 Minimal API calls | 🐌 Daily only | Long-term positions |

#### Change Timezone

**In `.env`:**
```bash
# Default: UTC
TIMEZONE=UTC

# Alternative: Your local timezone
TIMEZONE=America/New_York    # EST/EDT
TIMEZONE=Europe/London       # GMT/BST
TIMEZONE=Asia/Tokyo          # JST
```

**Note:** Timezone affects:
- Log timestamps
- Database `last_checked_at` timestamps
- Next run time display

**Market data timeframes** are always in exchange time (UTC for crypto).

### Manual Trigger

**Run check immediately (without waiting for schedule):**

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now

# Via Python
from src.scheduler import run_monitoring_check_now
results = run_monitoring_check_now()
print(f"Checked {results['total']} positions")
```

**Use cases:**
- Testing alert configuration
- Immediate check after adding a position
- Catch up after system downtime

### Missed Execution Handling

**Grace Period:**
```python
# Scheduler configuration
scheduler = AsyncIOScheduler(
    timezone=settings.timezone,
    job_defaults={
        "coalesce": True,           # Combine missed runs
        "max_instances": 1,         # Only one job at a time
        "misfire_grace_time": 60,   # 60 seconds grace
    }
)
```

**What happens if check is missed:**
- System restarts at 14:30 instead of 14:10
- Grace period: 60 seconds
- If within grace period: Runs immediately
- If beyond grace period: Skips, waits for next scheduled time (15:10)
- Coalescing: Multiple missed runs → Single execution

### Example Timeline

```
09:00 UTC - System starts
          - Scheduler initialized
          - First check scheduled for 09:10 UTC
          
09:10 UTC - Scheduled check #1 (10 minutes past the hour)
          - Position: ETHUSD SHORT
          - Previous: MA10=BEARISH, OTT=BULLISH
          - Current:  MA10=BEARISH, OTT=BEARISH (changed!)
          - Alert: "OTT Changed: BULLISH → BEARISH"
          - Database updated
          
10:10 UTC - Scheduled check #2
          - Position: ETHUSD SHORT
          - Previous: MA10=BEARISH, OTT=BEARISH
          - Current:  MA10=BEARISH, OTT=BEARISH (no change)
          - No alert
          
11:10 UTC - Scheduled check #3
          - Position: ETHUSD SHORT
          - Previous: MA10=BEARISH, OTT=BEARISH
          - Current:  MA10=BULLISH, OTT=BEARISH (MA10 changed!)
          - Alert: "MA10 Changed: BEARISH → BULLISH"
          - Database updated
```

### Database Timestamps

**Tracked Columns:**
```sql
last_checked_at DATETIME  -- When position was last analyzed (UTC)
created_at    DATETIME    -- When position was created (UTC)
updated_at    DATETIME    -- When position was last modified (UTC)
```

**Query last check time:**
```sql
SELECT pair, timeframe, last_checked_at, last_ma10_status, last_ott_status
FROM positions
WHERE status = 'OPEN'
ORDER BY last_checked_at DESC;
```

### Monitoring & Debugging

**Check scheduler status:**
```bash
curl http://localhost:8000/api/v1/positions/scheduler/status
```

**Response:**
```json
{
  "running": true,
  "next_run_time": "2026-03-01T15:10:00Z",
  "job_count": 1
}
```

**View logs:**
```bash
# Real-time monitoring logs
tail -f logs/monitor.log

# See when checks run
grep "Monitoring check completed" logs/monitor.log

# See alerts sent
grep "Alert triggered" logs/monitor.log
```

**Sample log output:**
```
2026-03-01 10:10:00,123 - INFO - Starting position monitoring check
2026-03-01 10:10:00,125 - INFO - Found 3 open positions
2026-03-01 10:10:02,456 - INFO - Alert triggered for ETHUSD: OTT Changed: BULLISH → BEARISH
2026-03-01 10:10:03,789 - INFO - Telegram alert sent for ETHUSD
2026-03-01 10:10:03,792 - INFO - Checked position 9 (ETHUSD): status=BULLISH, PnL=0.5%
2026-03-01 10:10:03,793 - INFO - Monitoring check completed: 3/3 successful, 1 alerts sent, 0 errors
```

**Note:** All timestamps in logs are at :10 minutes past the hour (not :00).

---

## Alert Trigger Scenarios

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    entry_price FLOAT NOT NULL,
    position_type VARCHAR(5) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    status VARCHAR(6) NOT NULL,
    
    -- Signal tracking (populated immediately on creation)
    last_signal_status VARCHAR(20),      -- Overall: BULLISH/BEARISH/NEUTRAL
    last_ma10_status VARCHAR(20),        -- MA10: BULLISH/BEARISH/NEUTRAL
    last_ott_status VARCHAR(20),         -- OTT: BULLISH/BEARISH/NEUTRAL
    last_checked_at DATETIME,
    
    -- Deprecated (kept for backward compatibility)
    last_important_indicators VARCHAR(50),
    
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

---

## Alert Trigger Scenarios

### Summary Table

| Trigger Condition | Alert Message Example | Priority |
|-------------------|----------------------|----------|
| Overall status change | `Status changed: BULLISH → BEARISH` | 1 (highest) |
| MA10 change | `MA10 Changed: BULLISH → BEARISH` | 2 |
| OTT change | `OTT Changed: BULLISH → BEARISH` | 3 |

**Note:** Only ONE alert is sent per monitoring check (first matching condition wins).

---

### Category 1: Overall Status Change

Overall status is determined by majority of 6 indicators (MA10, MA20, MA50, MACD, RSI, OTT).

| Scenario | Previous | Current | Alert? |
|----------|----------|---------|--------|
| Status flip | BULLISH | BEARISH | ✅ YES |
| Status flip | BEARISH | BULLISH | ✅ YES |
| No change | BULLISH | BULLISH | ❌ NO |

**Example:**
```
Position: ETHUSD SHORT
Previous: 4 bullish, 2 bearish → BULLISH
Current:  2 bullish, 4 bearish → BEARISH
Alert: "Status changed: BULLISH → BEARISH"
```

---

### Category 2: MA10 Change (Independent)

MA10 is tracked independently from OTT in `last_ma10_status` column.

| Scenario | Previous | Current | Alert? |
|----------|----------|---------|--------|
| MA10 flip | BULLISH | BEARISH | ✅ YES |
| MA10 flip | BEARISH | BULLISH | ✅ YES |
| No change | BULLISH | BULLISH | ❌ NO |

**Example:**
```
Position: BTCUSD LONG
Previous: MA10=BULLISH, OTT=BULLISH
Current:  MA10=BEARISH, OTT=BULLISH (unchanged)
Alert: "MA10 Changed: BULLISH → BEARISH"
```

---

### Category 3: OTT Change (Independent)

OTT is tracked independently from MA10 in `last_ott_status` column.

| Scenario | Previous | Current | Alert? |
|----------|----------|---------|--------|
| OTT flip | BULLISH | BEARISH | ✅ YES |
| OTT flip | BEARISH | BULLISH | ✅ YES |
| No change | BULLISH | BULLISH | ❌ NO |

**Example:**
```
Position: ETHUSD h1 SHORT
Previous: MA10=BEARISH, OTT=BULLISH
Current:  MA10=BEARISH (unchanged), OTT=BEARISH (changed)
Alert: "OTT Changed: BULLISH → BEARISH"
```

---

### Category 4: No Alert Scenarios

| Scenario | Alert? | Reason |
|----------|--------|--------|
| All values unchanged | ❌ NO | No significant change |
| PnL within normal range (-5% to +10%) | ❌ NO | No threshold breach |

---

## Signal Calculation Logic

### Overall Status Calculation

```python
# Count bullish vs bearish from 6 indicators
signal_keys = ["MA10", "MA20", "MA50", "MACD", "RSI", "OTT"]
bullish_count = count(indicator in ["BULLISH", "OVERBOUGHT"])
bearish_count = count(indicator in ["BEARISH", "OVERSOLD"])

if bullish_count > bearish_count:
    return "BULLISH"
elif bearish_count > bullish_count:
    return "BEARISH"
else:
    return "NEUTRAL"
```

### Individual Indicator Logic

| Indicator | BULLISH Condition | BEARISH Condition |
|-----------|-------------------|-------------------|
| MA10/MA20/MA50 | Close > EMA + 0.3% | Close < EMA - 0.3% |
| MACD | Histogram > threshold | Histogram < -threshold |
| RSI | RSI > 50 (and < 70) | RSI < 50 (and > 30) |
| OTT | Trend = 1 | Trend = -1 |

**Special RSI States:**
- RSI ≥ 70 → OVERBOUGHT (counts as BULLISH)
- RSI ≤ 30 → OVERSOLD (counts as BEARISH)

---

## Bug History & Troubleshooting

### Bug #1: Inconsistent Indicator Counts

**Symptom:** Different alert status between main page, detail view, and Telegram alerts.

**Root Cause:**
- `technical_analyzer.py` used 6 indicators (includes OTT)
- `monitor.py` used 5 indicators (excluded OTT)
- `ui.py` mixed both approaches

**Impact:** Main page showed BULLISH while Telegram showed BEARISH for same position.

**Fix:** Standardized all modules to use 6 indicators (includes OTT).

**Files Changed:**
- `src/monitor.py` - Added OTT to `_determine_overall_status()`
- `src/ui.py` - Updated all signal calculations to use 6 indicators

---

### Bug #2: SignalState Enum Stored as String Representation

**Symptom:** OTT/MA10 changes not triggering alerts.

**Root Cause:**
```python
# Bug: Stored enum representation instead of value
ma10_status = signal.signal_states.get("MA10")  # SignalState.BEARISH (enum)
position.last_important_indicators = f"{ma10_status}"  # "SignalState.BEARISH"
```

Database stored: `"SignalState.BEARISH,SignalState.BULLISH"`  
Expected: `"BEARISH,BULLISH"`

**Impact:** Comparison always matched (no alerts triggered) because both previous and current had same string representation.

**Fix:**
```python
# Extract .value from enum
ma10_status = signal.signal_states.get("MA10")
if hasattr(ma10_status, 'value'):
    ma10_status = ma10_status.value  # "BEARISH"
```

**Files Changed:**
- `src/monitor.py` - Added enum value extraction in storage and comparison logic
- Database - Migrated existing records to remove "SignalState." prefix

---

### Bug #3: Combined MA10+OTT Field Caused Complex Logic

**Symptom:** Missed alerts when only one indicator changed.

**Root Cause:**
```python
# Single combined field
last_important_indicators = "BEARISH,BULLISH"  # MA10,OTT together

# Complex comparison logic
if previous_important != current_important:
    prev_parts = previous_important.split(",")
    curr_parts = current_important.split(",")
    # ... parse, compare each part, build message ...
```

**Impact:** 
- Hard to debug
- String format issues
- Missed alerts when parsing failed

**Fix:** Split into separate columns:
```python
# Independent tracking
last_ma10_status = "BEARISH"   # Separate column
last_ott_status = "BULLISH"    # Separate column

# Simple independent comparisons
if previous_ma10 != current_ma10:
    return True, f"MA10 Changed: {previous_ma10} → {current_ma10}"

if previous_ott != current_ott:
    return True, f"OTT Changed: {previous_ott} → {current_ott}"
```

**Files Changed:**
- `src/models/position_model.py` - Added `last_ma10_status` and `last_ott_status` columns
- `src/monitor.py` - Updated to track and compare independently
- Database - Added columns, migrated existing data

---

### Bug #4: NULL Values on Position Creation

**Symptom:** First monitoring check never triggered alerts.

**Root Cause:**
```python
# Position created with NULL values
last_signal_status = NULL
last_ma10_status = NULL
last_ott_status = NULL

# Alert logic required previous value
if previous_ma10 is not None and current_ma10 != previous_ma10:
    # Never executed on first check
```

**Impact:** First monitoring check (1 hour after creation) wasted. No alerts possible until second check.

**Initial Fix Attempt:** Added NULL checks (`if previous_ma10 is not None`)

**Problem with Fix:** Still no alerts on first check.

**Final Solution (Option A):** Calculate signals immediately on position creation:
```python
# In API endpoint when creating position
position = service.create_position(...)
signals = monitor.calculate_initial_signals(position)
position.last_ma10_status = signals['ma10']
position.last_ott_status = signals['ott']
db.commit()
```

**Benefits:**
- No NULL values ever
- First monitoring check can trigger alerts
- Dashboard shows signals immediately

**Trade-offs:**
- Position creation takes ~1-2 seconds longer
- Requires API availability

**Fallback:** If signals calculation fails, position is still created. First monitoring check will calculate signals.

**Files Changed:**
- `src/monitor.py` - Added `calculate_initial_signals()` method
- `src/api/routes.py` - Updated `open_position()` to calculate signals
- `src/monitor.py` - Removed NULL checks from `_should_send_alert()`

---

### Bug #5: Health Status Emoji Not Showing for NEUTRAL

**Fix:**
```python
# Added NEUTRAL case
elif health_status == "NEUTRAL":
    health_emoji = "🟡"

# Added CSS
.status-neutral {
    background-color: #fff3cd;
    color: #856404;
}
```

**Files Changed:**
- `src/ui.py` - Added NEUTRAL emoji, CSS class, and detail view message

---

## Code Reference

### Alert Logic (`src/monitor.py`)

```python
def _should_send_alert(self, position, current_status, pnl_pct, signal_states):
    previous_status = position.last_signal_status
    previous_ma10 = position.last_ma10_status
    previous_ott = position.last_ott_status
    
    current_ma10 = extract_value(signal_states.get("MA10"))
    current_ott = extract_value(signal_states.get("OTT"))
    
    # Check 1: Overall status change
    if previous_status and current_status != previous_status:
        return True, f"Status changed: {previous_status} → {current_status}"
    
    # Check 2: MA10 change (independent)
    if previous_ma10 and current_ma10 != previous_ma10:
        return True, f"MA10 Changed: {previous_ma10} → {current_ma10}"
    
    # Check 3: OTT change (independent)
    if previous_ott and current_ott != previous_ott:
        return True, f"OTT Changed: {previous_ott} → {current_ott}"
    
    return False, "No significant change"
```

### Initial Signals Calculation (`src/monitor.py`)

```python
def calculate_initial_signals(self, position):
    """Calculate signals when position is created."""
    try:
        # Fetch market data
        fetcher = DataFetcher(source="ccxt", retry_attempts=2)
        df = fetcher.get_ohlcv(symbol=position.pair, timeframe=position.timeframe, limit=100)
        
        # Calculate signals
        signal = self._technical_analyzer.analyze_position(
            df=df, pair=position.pair,
            position_type=position.position_type,
            timeframe=position.timeframe
        )
        
        # Extract values
        ma10 = extract_value(signal.signal_states.get("MA10"))
        ott = extract_value(signal.signal_states.get("OTT"))
        overall = signal.overall_signal.value
        
        return {'ma10': ma10, 'ott': ott, 'overall': overall}
    except Exception:
        return None  # Position still created, signals calculated on first check
```

### Position Creation API (`src/api/routes.py`)

```python
@router.post("/open")
def open_position(position_data: PositionCreate, db: Session):
    # Create position
    position = service.create_position(...)
    
    # Calculate initial signals (non-blocking)
    try:
        monitor = PositionMonitor()
        signals = monitor.calculate_initial_signals(position)
        
        if signals:
            position.last_ma10_status = signals['ma10']
            position.last_ott_status = signals['ott']
            position.last_signal_status = signals['overall']
            db.commit()
    except Exception as e:
        logger.warning(f"Initial signals calculation failed: {e}")
        # Position created, signals will be calculated on first check
    
    return position
```

---

## Quick Reference

### Signal States

| State | Meaning |
|-------|---------|
| BULLISH | Indicator suggests upward movement |
| BEARISH | Indicator suggests downward movement |
| NEUTRAL | No clear signal / insufficient data |
| OVERBOUGHT | RSI ≥ 70 (counts as BULLISH) |
| OVERSOLD | RSI ≤ 30 (counts as BEARISH) |

### Monitoring Interval

- **Default:** 1 hour (3600 seconds)
- **Configurable:** Via `MONITOR_INTERVAL` in `.env`
- **Timezone:** UTC

---

**Document Owner:** Development Team  
**Review Cycle:** Per feature update  
**Next Review:** When adding new indicators or modifying alert logic
