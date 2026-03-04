# API Endpoint Fix: /scheduler/run-now

**Date:** March 2, 2026  
**Issue:** `404 Not Found` when calling `/scheduler/run-now`  
**Status:** ✅ FIXED

---

## Problem

```bash
curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now
# Response: {"detail":"Not Found"}
```

**Root Cause:** The endpoint didn't exist in the API routes.

---

## Solution

Added new endpoint `/positions/scheduler/run-now` to `src/api/routes.py`.

### Code Added

**File:** `src/api/routes.py` (Lines 385-431)

```python
@router.post(
    "/scheduler/run-now",
    response_model=Dict[str, Any],
    summary="Run monitoring check immediately",
    description="Trigger an immediate position monitoring check without waiting for the scheduled time.",
    tags=["scheduler"],
)
def run_monitoring_now() -> Dict[str, Any]:
    """
    Run position monitoring check immediately.

    This endpoint triggers an immediate check of all open positions,
    calculating signals and sending Telegram alerts if needed.

    Returns:
        Dictionary with check results:
        - success: Whether the check completed
        - message: Status message
        - total: Total positions checked
        - successful: Number of successful checks
        - alerts_sent: Number of alerts sent
        - errors: Number of errors
    """
    from src.monitor import run_monitoring_check

    try:
        results = run_monitoring_check()

        return {
            "success": True,
            "message": f"Monitoring check completed",
            "total": results.get("total", 0),
            "successful": results.get("successful", 0),
            "alerts_sent": results.get("alerts_sent", 0),
            "errors": results.get("errors", 0),
        }

    except Exception as e:
        logger.error(f"Monitoring check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monitoring check failed: {str(e)}",
        )
```

---

## Usage

### Endpoint

```
POST /api/v1/positions/scheduler/run-now
```

### cURL Command

```bash
curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now
```

### Expected Response

```json
{
  "success": true,
  "message": "Monitoring check completed",
  "total": 4,
  "successful": 4,
  "alerts_sent": 2,
  "errors": 0
}
```

### Python Example

```bash
python -c "
import requests
response = requests.post('http://localhost:8000/api/v1/positions/scheduler/run-now')
print(response.json())
"
```

---

## Important Notes

### ⏱️ Response Time

**This endpoint takes 1-3 minutes to respond** because it:
1. Fetches live market data for ALL open positions (CCXT/yfinance APIs)
2. Calculates technical indicators (EMA, MACD, RSI, OTT)
3. Compares signals with previous state
4. Sends Telegram alerts if signals changed
5. Updates database with new signal states

**Factors affecting speed:**
- Number of open positions
- Data source (CCXT vs yfinance)
- Network latency to exchanges
- Timeframe (higher timeframes need more historical data)

**Typical times:**
- 1-2 positions: ~30-60 seconds
- 3-5 positions: ~1-2 minutes
- 5+ positions: ~2-3 minutes

### 🔁 When to Use

**Good use cases:**
- Manual monitoring check (don't want to wait for :10 schedule)
- Testing alert configuration
- After adding a new position (check immediately)
- Before making a trading decision

**Not recommended:**
- Frequent polling (use scheduled checks instead)
- Testing with many open positions (slow)

### 📊 Alternative: Faster Testing

For quick tests without full market data fetch, use:

```bash
# Check scheduler status (instant)
curl http://localhost:8000/api/v1/positions/scheduler/status

# Send test Telegram alert (fast, ~2-5 seconds)
curl -X POST http://localhost:8000/api/v1/positions/scheduler/test-alert
```

---

## All Scheduler Endpoints

| Endpoint | Method | Purpose | Speed |
|----------|--------|---------|-------|
| `/scheduler/status` | GET | Check if scheduler is running | ⚡ Instant |
| `/scheduler/test-alert` | POST | Send test Telegram message | ⚡ Fast (2-5s) |
| `/scheduler/run-now` | POST | Run full monitoring check | 🐌 Slow (1-3 min) |

---

## Troubleshooting

### "404 Not Found"

**Cause:** Server running old code

**Fix:**
```bash
# Kill existing server
pkill -f "uvicorn src.main"

# Restart with new code
cd /path/to/project
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
```

### Request Timeout

**Cause:** Too many positions or slow exchange APIs

**Fix:**
- Wait longer (up to 3 minutes)
- Close some positions to reduce load
- Check exchange API status

### "No open positions"

**Response:**
```json
{
  "success": true,
  "message": "Monitoring check completed",
  "total": 0,
  "successful": 0,
  "alerts_sent": 0,
  "errors": 0
}
```

**This is normal** if you have no open positions.

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/api/routes.py` | 385-431 | Added `run_monitoring_now()` endpoint |

---

## Related Documentation

- `TELEGRAM_ALERT_COMPLETE_GUIDE.md` - Alert system overview
- `DEPLOYMENT_247_GUIDE.md` - Running system 24/7
- `DATABASE_GUIDE.md` - Database structure and queries

---

**Quick Start:**
```bash
# 1. Make sure server is running
curl http://localhost:8000/api/v1/positions/scheduler/status

# 2. Run monitoring check (be patient - takes 1-3 minutes)
curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now

# 3. Check results
# Response will show total positions checked and alerts sent
```
