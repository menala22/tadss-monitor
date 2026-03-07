# Troubleshooting Log: Alert History Not Logging

**Date:** March 2, 2026  
**Issue:** ETHUSD h1 MA signal change triggered no Telegram alert and no database record  
**Status:** ✅ RESOLVED

---

## Problem Report

**User Report:**
> "The ETHUSD pair 1h has MA signal change in the last hour. However, I do not see any record in the alert_history table and no Telegram message."

**Expected Behavior:**
- Signal changes (MA10, OTT, overall status) should trigger Telegram alerts
- All alerts (sent, skipped, failed) should be logged to `alert_history` table

**Actual Behavior:**
- No Telegram message received
- No record in `alert_history` table
- Position data showed `last_ma10_status = 'BEARISH'`, `last_ott_status = 'BULLISH'`, `last_signal_status = 'BULLISH'`

---

## Investigation Steps

### Step 1: Check Position Data

```bash
sqlite3 data/positions.db "
  SELECT id, pair, position_type, timeframe, status, 
         last_ma10_status, last_ott_status, last_signal_status, last_checked_at 
  FROM positions 
  WHERE pair LIKE '%ETH%' OR pair LIKE '%ETHUSD%';
"
```

**Result:**
```
3 |ETHUSD|SHORT|h4|OPEN|||BULLISH|2026-03-01 15:20:43
7 |ETHUSD|SHORT|h4|CLOSED||||
9 |ETHUSD|SHORT|h1|OPEN|BEARISH|BULLISH|BULLISH|2026-03-01 15:20:54
```

**Finding:** Position 9 (ETHUSD h1) exists with last status = BULLISH, last checked at 15:20

---

### Step 2: Check Alert History Table

```bash
sqlite3 data/positions.db "SELECT * FROM alert_history ORDER BY timestamp DESC LIMIT 10;"
```

**Result:** Only 2 test records from earlier migration test, no production alerts

**Finding:** Alert history table exists but no alerts were being logged

---

### Step 3: Check Monitor Logs

```bash
tail -100 logs/monitor.log
```

**Key Findings:**
```
2026-03-01 22:20:54 - INFO - Alert triggered for ETHUSD: Important Indicators Changed
2026-03-01 22:20:54 - INFO - Telegram alert sent for ETHUSD
```

**Last automated check:** March 1, 22:20 (over 11 hours ago)

**Finding:** Scheduler not running - FastAPI server likely stopped

---

### Step 4: Code Review - Alert Flow

**File:** `src/monitor.py` (Line 419)

```python
# BEFORE (Buggy Code)
if self.telegram_enabled:
    self._telegram_notifier.send_custom_message(message)
    logger.info(f"Telegram alert sent for {position.pair}")
```

**Problem Identified:** 
- `send_custom_message()` sends Telegram alert but **does NOT log to database**
- New alert logging was added to `send_position_alert()` but `monitor.py` was never updated to use it

---

### Step 5: Code Review - Notifier

**File:** `src/notifier.py` (Line 363-370)

```python
# BEFORE (Buggy Code)
send_success = self._send_with_retry(
    message,                    # ← Positional argument
    alert_type=alert_type,
    pair=pair,
    current_status=current_status,
    reason=reason,
    message=message,            # ← Duplicate keyword argument!
    previous_status=previous_status,
    price_movement_pct=price_movement_pct,
)
```

**Problem Identified:**
- `message` passed twice (positional + keyword)
- Causes: `TypeError: got multiple values for argument 'message'`

---

## Root Causes

### Primary Issue: Alert Logging Bypass
**File:** `src/monitor.py`  
**Line:** 419

The monitoring code was calling `send_custom_message()` directly instead of `send_position_alert()`. This meant:
- ✅ Telegram alerts were sent (when scheduler was running)
- ❌ **No database logging occurred**

### Secondary Issue: Parameter Bug
**File:** `src/notifier.py`  
**Line:** 363-370

Duplicate `message` parameter caused TypeError when alerts were attempted.

### Tertiary Issue: Scheduler Not Running
**File:** `src/scheduler.py`

The background scheduler only runs when FastAPI server is active. Server was likely stopped, so no automated checks occurred since March 1, 22:20.

---

## Fixes Applied

### Fix 1: Update monitor.py to Use Proper Alert Method

**File:** `src/monitor.py`  
**Lines:** 405-427

```python
# AFTER (Fixed Code)
if self.telegram_enabled:
    # Use send_position_alert which logs to database
    self._telegram_notifier.send_position_alert(
        position={
            'pair': position.pair,
            'position_type': position.position_type.value,
            'entry_price': position.entry_price,
            'timeframe': position.timeframe,
        },
        signals=signal.signal_states,
        previous_status=position.last_signal_status,
        current_price=current_price,
        is_daily_summary=False,
    )
    logger.info(f"Telegram alert sent for {position.pair}")
```

**Change:** Now calls `send_position_alert()` which:
- Sends Telegram alert
- Logs to `alert_history` table (SENT, FAILED, or SKIPPED)
- Tracks alert type, reason, price movement, errors

---

### Fix 2: Remove Duplicate Parameter

**File:** `src/notifier.py`  
**Lines:** 363-370

```python
# AFTER (Fixed Code)
send_success = self._send_with_retry(
    message=message,              # ← Only as keyword argument
    alert_type=alert_type,
    pair=pair,
    current_status=current_status,
    reason=reason,
    previous_status=previous_status,
    price_movement_pct=price_movement_pct,
)
```

---

## Verification

### Test Command
```bash
python -c "
from src.monitor import run_monitoring_check
result = run_monitoring_check()
print(f'Total: {result[\"total\"]}')
print(f'Successful: {result[\"successful\"]}')
print(f'Alerts sent: {result[\"alerts_sent\"]}')
print(f'Errors: {result[\"errors\"]}')
"
```

### Result
```
Total: 4
Successful: 4
Alerts sent: 3
Errors: 0
```

### Database Verification
```bash
sqlite3 data/positions.db "
  SELECT id, datetime(timestamp), pair, alert_type, status, reason 
  FROM alert_history 
  ORDER BY timestamp DESC 
  LIMIT 10;
"
```

### Result
```
id|timestamp           |pair   |alert_type    |status|reason
5 |2026-03-02 02:54:42 |ETHUSD |SIGNAL_CHANGE |SENT  |Signal status changed: BULLISH → BEARISH
4 |2026-03-02 02:54:38 |ETHUSD |SIGNAL_CHANGE |SENT  |Signal status changed: BULLISH → BEARISH
3 |2026-03-02 02:54:35 |BTC-USD|PRICE_MOVEMENT|SENT  |Signal status changed: BULLISH → BEARISH
2 |2026-03-02 01:29:25 |ETH/USDT|SIGNAL_CHANGE|SKIPPED|No significant change
1 |2026-03-02 01:29:25 |BTC/USDT|POSITION_HEALTH|SENT |Test alert - status changed
```

✅ **Alerts now being logged correctly!**

---

## Lessons Learned

### 1. Code Integration Gap
When new features (alert logging) are added to one module (`notifier.py`), all calling code must be updated (`monitor.py`). 

**Action:** Add integration tests that verify end-to-end flow.

### 2. Silent Failures
The duplicate parameter bug caused alerts to fail silently (returned `False` but didn't crash).

**Action:** Add better error logging in `_send_with_retry()`.

### 3. Scheduler Dependency
Automated monitoring depends on FastAPI server running.

**Action:** 
- Document scheduler dependency in README
- Consider standalone cron job as backup

---

## Recommendations

### Immediate Actions

1. **Start FastAPI Server** (if automated monitoring needed):
   ```bash
   python -m src.main
   ```

2. **Verify Telegram Configuration**:
   ```bash
   python -c "from src.notifier import test_notification; test_notification()"
   ```

3. **Check Alert History Regularly**:
   ```bash
   sqlite3 data/positions.db "
     SELECT date(timestamp), COUNT(*) as alerts 
     FROM alert_history 
     GROUP BY date(timestamp) 
     ORDER BY date(timestamp) DESC 
     LIMIT 7;
   "
   ```

### Long-term Improvements

1. **Add Health Check Endpoint** - API endpoint to verify:
   - Scheduler is running
   - Last check timestamp
   - Recent alert count

2. **Add Alert Retry Dashboard** - View failed alerts and retry manually

3. **Add Monitoring for the Monitor** - External heartbeat check

4. **Update Tests** - Add integration test for alert logging flow

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/monitor.py` | 405-427 | Use `send_position_alert()` with DB logging |
| `src/notifier.py` | 363-370 | Fix duplicate `message` parameter |

---

## Related Documentation

- **DATABASE_GUIDE.md** - Query alert history
- **src/models/alert_model.py** - Alert schema
- **src/migrations/migrate_alert_history.py** - Migration script

---

## Contact

For questions about this troubleshooting session, refer to:
- Project documentation in `DATABASE_GUIDE.md`
- Monitor logs in `logs/monitor.log`
- Telegram logs in `logs/telegram.log`
