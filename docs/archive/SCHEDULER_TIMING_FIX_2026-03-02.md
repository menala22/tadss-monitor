# Scheduler Timing Fix - Cron Trigger

**Date:** March 2, 2026  
**Issue:** Alerts sent at 10:55 instead of expected 10:10  
**Status:** ✅ FIXED

---

## Problem

User received Telegram alert at **10:55** instead of the expected **10:10** schedule.

### Root Cause

The alert at 10:55 was **NOT from the scheduler** - it was from a **manual monitoring check**.

The scheduler was using an `interval` trigger which:
- Calculated first run time based on when server started
- If server started after :10, would wait until next hour's :10
- Subsequent runs were relative to first run time

**Example of old behavior:**
- Server starts at 10:45 → First check at 11:10 → Next at 12:10
- This was CORRECT but confusing because manual checks were interspersed

---

## Solution

Changed scheduler from `interval` trigger to `cron` trigger for predictable scheduling.

### Code Changes

**File:** `src/scheduler.py`

**Before (Interval Trigger):**
```python
# Calculate next :10 past the hour
tz = pytz.timezone(settings.timezone)
now = datetime.now(tz)
if now.minute < 10:
    first_run = now.replace(minute=10, second=0, microsecond=0)
else:
    first_run = now.replace(hour=now.hour+1, minute=10, second=0, microsecond=0)

self.scheduler.add_job(
    func=self.monitor.check_all_positions,
    trigger='interval',
    hours=check_interval_hours,
    start_date=first_run,  # Relative timing
    ...
)
```

**After (Cron Trigger):**
```python
self.scheduler.add_job(
    func=self.monitor.check_all_positions,
    trigger='cron',
    minute=10,  # Always runs at :10 past the hour
    hour='*',   # Every hour
    ...
)
```

### Benefits

1. **Predictable Schedule:** Always runs at :10 past every hour, regardless of server start time
2. **Simpler Code:** No need to calculate first run time
3. **Clearer Documentation:** "Runs at :10" is easier to understand than "10 minutes after start"
4. **Timezone Aware:** Respects `TIMEZONE` setting from `.env`

---

## Verification

**Test Command:**
```bash
python -c "
from src.scheduler import SchedulerManager
manager = SchedulerManager()
manager.start()
job = manager.scheduler.get_job('position_monitoring')
print(f'Trigger: {job.trigger}')
print(f'Next run: {job.next_run_time}')
manager.stop()
"
```

**Expected Output:**
```
Trigger: cron[hour='*', minute='10']
Next run: 2026-03-02 XX:10:00+00:00  # Next :10 mark
```

---

## Updated Schedule

**With cron trigger:**
```
Every hour at :10 UTC:
- 10:10 - Automated check
- 11:10 - Automated check
- 12:10 - Automated check
- 13:10 - Automated check
...
```

**Manual checks** (via API or Python) can still be triggered anytime:
```bash
# Manual check (anytime)
curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now
```

---

## Documentation Updates

**TELEGRAM_ALERT_COMPLETE_GUIDE.md** updated with:
- Clarified that cron trigger is used (not interval)
- Added examples showing server start time vs first check time
- Emphasized that checks always run at :10 regardless of startup time

**Example Timeline:**
```
Server starts at 14:45 → First check at 15:10 → Then 16:10, 17:10, etc.
Server starts at 09:05 → First check at 09:10 → Then 10:10, 11:10, etc.
```

---

## Why 10:55 Alert Happened

The alert at 10:55 was triggered by a **manual monitoring check**, not the scheduler:

```
2026-03-02 09:52:56 - Manual check (testing)
2026-03-02 09:54:30 - Manual check (testing) ← You were debugging
2026-03-02 10:55:56 - Manual check (testing) ← This caused the 10:55 alert
```

The **scheduler's first automated check** will be at the next :10 mark after you start the FastAPI server with `python -m src.main`.

---

## How to Ensure Automated Alerts Work

1. **Start FastAPI server:**
   ```bash
   python -m src.main
   ```

2. **Verify scheduler is running:**
   ```bash
   curl http://localhost:8000/api/v1/positions/scheduler/status
   ```
   
   Expected response:
   ```json
   {
     "running": true,
     "next_run_time": "2026-03-02T11:10:00Z",
     "job_count": 1
   }
   ```

3. **Check logs for scheduled runs:**
   ```bash
   tail -f logs/monitor.log | grep "Starting position monitoring check"
   ```
   
   You should see entries at :10 past each hour.

---

## Files Modified

| File | Change |
|------|--------|
| `src/scheduler.py` | Changed from `interval` to `cron` trigger |
| `src/scheduler.py` | Removed complex first_run calculation |
| `src/scheduler.py` | Removed unused `pytz` import |
| `TELEGRAM_ALERT_COMPLETE_GUIDE.md` | Updated timing documentation |

---

## Related Issues

- Alert logging to database: ✅ Fixed (see `TROUBLESHOOTING_ALERT_LOGGING_2026-03-02.md`)
- Signal changes tracking: ✅ Implemented (see `DATABASE_GUIDE.md`)

---

**Next Steps:**
1. Start FastAPI server to enable automated monitoring
2. Wait for next :10 mark to verify automated check runs
3. Check `logs/monitor.log` for "Monitoring check completed" entries
