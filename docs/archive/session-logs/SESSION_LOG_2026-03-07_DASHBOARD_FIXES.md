# Session Log: Dashboard Debug & Fix
**Date:** 2026-03-07
**Branch:** main
**Commits:** `4746b66`, `417b9b3`, `ad4d768`

---

## Starting State

- VM restarted → IP changed (35.188.118.182 → 34.171.241.166)
- Dashboard showed no data on main page ("Backend Connection Lost")
- Health/Signal columns always showed NEUTRAL
- Test Connection button returned HTTP 404
- 4 of 6 positions had `current_price = entry_price` (PnL = 0%)

---

## Bug 1 — Duplicate Function Shadowing the Timeout Fix

**File:** `src/ui.py`
**Symptom:** Main page showed "Backend Connection Lost" even with correct IP.

`fetch_open_positions_from_api` was defined **twice** in `ui.py`. Python keeps the last definition, so the 60-second timeout version (line 118) was silently overridden by a stale 10-second version (line 511). The VM's API was taking ~37 seconds to respond, which exceeded the effective 10-second timeout → returned `None` → "Backend Connection Lost".

**Fix:** Removed the duplicate definition (lines 511–533, timeout=10s). The surviving definition at line 118 uses `timeout=60`.

---

## Bug 2 — Test Connection Button Returned HTTP 404

**File:** `src/ui.py` — `test_api_connection()`
**Symptom:** Settings page "Test Connection" button always showed HTTP 404.

```python
# Before (wrong)
response = requests.get(f"{test_url}/health")
# test_url = "http://34.171.241.166:8000/api/v1"
# → calls: http://34.171.241.166:8000/api/v1/health  → 404

# After (correct)
health_base = test_url.split("/api/")[0] if "/api/" in test_url else test_url
response = requests.get(f"{health_base}/health")
# → calls: http://34.171.241.166:8000/health  → 200 OK
```

The `/health` endpoint is registered at the FastAPI root, not under the `/api/v1` router. The Quick Links section (line 2286) already did this correctly with `.replace("/api/v1", "")` — `test_api_connection` was the only place that didn't.

---

## Bug 3 — API Blocked for 30+ Seconds on Cache Miss

**File:** `src/api/routes.py` — `list_open_positions()`
**Symptom:** Dashboard timed out when cache was stale (>5 min old). API made sequential live fetches for each position — up to 6 × 30s = 180s.

**Fix:** Removed the live-fetch fallback entirely. When cache is present (fresh or stale), use it. When cache is completely absent, fall back to `entry_price`. The scheduler refreshes cache hourly.

```python
# Before: stale cache → live API fetch (blocking, 30+ seconds)
if not cache_fresh:
    df = fetcher.get_ohlcv(...)  # blocks

# After: use any cache; only fall back to entry_price if no cache at all
if cached_df is not None and not cached_df.empty:
    position_dict.current_price = float(cached_df['Close'].iloc[-1])
else:
    position_dict.current_price = p.entry_price  # scheduler will populate later
```

Also removed the now-unused inline `from src.data_fetcher import DataFetcher` import.

---

## Bug 4 — Health / Signal Columns Always Showed NEUTRAL

**Files:** `src/api/schemas.py`, `src/ui.py` — `fetch_position_with_signals_simple()`
**Symptom:** The main positions table showed 🟡 NEUTRAL for every row regardless of actual signal state.

**Two-part root cause:**

**Part A — Schema didn't expose stored signal fields.**
`PositionWithPnL` only included price/PnL fields. The DB columns `last_signal_status`, `last_ma10_status`, `last_ott_status`, and `last_checked_at` (set by the scheduler) were never serialised into the API response.

```python
# Added to PositionWithPnL in schemas.py:
last_signal_status: Optional[str] = None
last_ma10_status: Optional[str] = None
last_ott_status: Optional[str] = None
last_checked_at: Optional[datetime] = None
```

**Part B — UI hardcoded NEUTRAL instead of reading the API response.**
`fetch_position_with_signals_simple` contained:
```python
# Before (hardcoded)
health_status = "NEUTRAL"
signal_summary = "NEUTRAL"

# After (reads stored DB value, derives health from direction alignment)
last_signal = position.get("last_signal_status")
signal_summary = last_signal if last_signal in ("BULLISH", "BEARISH") else "NEUTRAL"

if signal_summary == "BULLISH":
    health_status = "HEALTHY" if position_type == "LONG" else "CRITICAL"
elif signal_summary == "BEARISH":
    health_status = "CRITICAL" if position_type == "LONG" else "HEALTHY"
else:
    health_status = "NEUTRAL"
```

---

## Bug 5 — XAGUSD and ETHUSD Never Cached (PnL Always 0%)

**File:** `src/data_fetcher.py`
**Symptom:** XAGUSD (both h4 and d1) and ETHUSD h4 always showed `current_price = entry_price`, PnL = 0%.

**Root cause:** The `save_ohlcv` call existed only inside `_fetch_twelvedata`. The other two fetchers — `_fetch_ccxt` (used for ETHUSD) and `_fetch_gateio` (used for XAGUSD) — fetched data successfully but never persisted it. Every API request → cache miss → fallback to entry_price.

**Fix:** Added a universal cache-save step in `get_ohlcv` after `_validate_and_clean`, covering all sources. The Twelve Data internal save (for incremental fetch) is left in place; duplicate saves are harmless (`save_ohlcv` skips existing rows by timestamp).

```python
# In get_ohlcv(), after _validate_and_clean():
try:
    with get_db_context() as db:
        cache_mgr = OHLCVCacheManager(db)
        cache_mgr.save_ohlcv(symbol, timeframe, df)
except Exception as cache_err:
    self.logger.warning(f"Cache save failed for {symbol} {timeframe}: {cache_err}")
```

---

## Bug 6 — XAUUSD h4 Cache Miss Despite Successful Fetch

**File:** `src/data_fetcher.py`
**Symptom:** XAUUSD h4 showed `current_price = entry_price` even though `_fetch_twelvedata` succeeded and returned price data.

**Root cause:** Twelve Data free tier doesn't support the 4h interval. `validate_timeframe("h4", "twelvedata")` silently fell back to "1h". Data was fetched (1h data) and saved under the key `XAUUSD / 1h`. But the positions table stores `timeframe = "h4"`, so `routes.py` queried the cache for `XAUUSD / 4h` → miss → fallback to entry_price.

**Fix:** The universal save in `get_ohlcv` (Bug 5 fix) saves under the **original** requested timeframe (`h4` → normalised to `4h`), not the validated/fallback one (`1h`). This is a deliberate key alias — the same price data is reachable under both `1h` (for the h1 position) and `4h` (for the h4 position).

---

## Deployment

All fixes were deployed to the production Google Cloud VM via:

```bash
# Local
git add src/api/routes.py src/api/schemas.py src/ui.py
git commit -m "Fix: dashboard Health/Signal columns and API performance"
git push origin main

git add src/data_fetcher.py
git commit -m "Fix: save OHLCV cache for CCXT and Gate.io fetchers"
git push origin main

git add src/data_fetcher.py
git commit -m "Fix: save cache under original timeframe, not validated fallback"
git push origin main

# VM (via gcloud ssh)
cd ~/tadss-monitor && git pull
docker cp src/api/routes.py tadss:/app/src/api/routes.py
docker cp src/api/schemas.py tadss:/app/src/api/schemas.py
docker cp src/data_fetcher.py tadss:/app/src/data_fetcher.py
docker restart tadss
```

> **Note:** Full Docker rebuild was skipped because the Dockerfile has `--platform linux/arm64` hardcoded (built for Mac), which fails on the VM's `linux/amd64`. Files were hot-copied into the running container instead. This works for Python file changes; a proper multi-arch Dockerfile should be addressed in a future session.

Cache was seeded immediately after deploy by running a direct Python script inside the container to fetch live prices for all 6 positions.

---

## Final State

| Position | Before | After |
|---|---|---|
| XAGUSD h4 | entry_price / 0% PnL | 83.79 / +7.42% |
| XAGUSD d1 | entry_price / 0% PnL | 83.81 / -1.40% |
| XAUUSD h1 | 5159.33 / -3.8% ✅ | 5159.33 / -3.8% ✅ |
| XAUUSD h4 | entry_price / 0% PnL | 5159.33 / -0.78% |
| XAUUSD d1 | 5145.38 / -1.5% ✅ | 5145.38 / -1.5% ✅ |
| ETHUSD h4 | entry_price / 0% PnL | 1980.04 / +1.54% |

| Dashboard feature | Before | After |
|---|---|---|
| Main page loads | ❌ "Backend Connection Lost" | ✅ Loads in <2s |
| API response time | 30–60s (live fetch on cache miss) | <1s (cache read only) |
| Health column | Always 🟡 NEUTRAL | Real value (🟢 HEALTHY / 🔴 CRITICAL) |
| Signal column | Always ⚪ Neutral | Real value (🟢 Bullish / 🔴 Bearish) |
| Test Connection | ❌ HTTP 404 | ✅ HTTP 200 |
| Cache coverage | 2/6 positions | 6/6 positions |

---

## Known Remaining Issues

1. **Dockerfile platform mismatch** — `FROM --platform linux/arm64` fails on the VM (`amd64`). Code changes must be hot-copied with `docker cp` until this is fixed. Fix: remove the `--platform` flag or use `linux/amd64`.

2. **XAUUSD h4 uses 1h price data** — Twelve Data free tier doesn't support 4h. The h4 position shows prices sourced from the 1h candle. This is acceptable (same asset, close price) but not technically the h4 close. Fix: upgrade Twelve Data plan, or accept 1h price as proxy for h4.

3. **Smart scanning skips positions** — The monitor's `_should_check_position` uses timeframe-based intervals to reduce API calls. This means `run-now` may not actually fetch all positions if they were recently checked. Cache seeding must be done directly when needed.
