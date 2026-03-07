# Troubleshooting: Dashboard Shows No Data After Cache Implementation

**Date:** March 7, 2026  
**Issue:** Dashboard shows "Backend Connection Lost" or no positions after implementing Dashboard Reads from Database  
**Status:** 🔍 Root Cause Identified - API Timeout

---

## Symptoms

1. **Settings page shows old VM IP** (35.188.118.182 instead of 34.171.241.166)
2. **Main page shows no positions** or "Backend Connection Lost"
3. **Dashboard takes >30 seconds** to load (if it loads at all)
4. **Hard refresh doesn't help**

---

## Root Cause Analysis

### Test Results:

```bash
# Test 1: API works from inside VM (FAST)
gcloud compute ssh aiagent@tadss-vm --command="curl -s http://localhost:8000/api/v1/positions/open"
# Result: ✅ Returns 6 positions in <1 second

# Test 2: API works from local machine (SLOW)
curl http://34.171.241.166:8000/api/v1/positions/open
# Result: ✅ Returns 6 positions BUT takes 37 seconds!
```

### Problem Identified:

**API is timing out when fetching fresh data from external APIs!**

When cache is stale (>5 min old), the `/positions/open` endpoint tries to fetch fresh data from:
- Twelve Data (for XAUUSD, stocks)
- Gate.io (for XAGUSD)
- Kraken (for ETHUSD)

These external API calls are **very slow or timing out**, causing the entire endpoint to take 30+ seconds.

---

## Why This Happened

### Before Cache Implementation:
```
Dashboard → API → External APIs (parallel) → Return
Total: 6-18 seconds
```

### After Cache Implementation (Current):
```
Dashboard → API → Check Cache → Stale → External APIs (sequential) → Save Cache → Return
Total: 30-60 seconds (or timeout)
```

### The Flaw:

The current implementation fetches fresh data **synchronously** when cache is stale:

```python
# In src/api/routes.py
if not cache_fresh:
    # This blocks until API responds (can take 30+ seconds)
    df = fetcher.get_ohlcv(symbol=p.pair, timeframe=p.timeframe, limit=1)
```

When multiple positions have stale cache, it makes **sequential API calls**, multiplying the delay.

---

## Solutions

### Solution 1: Increase Timeout + Background Refresh (RECOMMENDED)

**Idea:** Return cached data immediately, refresh cache in background.

```python
# In src/api/routes.py

@router.get("/positions/open")
def list_open_positions(db: Session):
    cache_mgr = OHLCVCacheManager(db)
    positions = get_open_positions()
    
    for p in positions:
        cached_df = cache_mgr.get_cached_ohlcv(p.pair, p.timeframe, limit=1)
        
        if cached_df is not None:
            # Use cache immediately (even if stale)
            p.current_price = float(cached_df['Close'].iloc[-1])
        else:
            # No cache - use entry price as fallback
            p.current_price = p.entry_price
        
        # Schedule background refresh (don't block response)
        if should_refresh_cache(p, cached_df):
            background_tasks.add_task(refresh_position_cache, p)
    
    return positions

# Background task (runs after response is sent)
async def refresh_position_cache(position):
    fetcher = DataFetcher(source=get_source(position.pair))
    df = fetcher.get_ohlcv(...)
    cache_mgr.save_ohlcv(...)
```

**Pros:**
- ✅ Fast response (<2 seconds)
- ✅ Cache stays fresh
- ✅ No timeout issues

**Cons:**
- ⚠️ Prices may be 5-10 min old
- ⚠️ Requires FastAPI BackgroundTasks

---

### Solution 2: Increase Timeout + Parallel Fetch

**Idea:** Fetch all positions in parallel, not sequential.

```python
# In src/api/routes.py

from concurrent.futures import ThreadPoolExecutor

@router.get("/positions/open")
def list_open_positions(db: Session):
    positions = get_open_positions()
    
    # Fetch all positions in parallel (5 second timeout each)
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(process_position, positions))
    
    return results

def process_position(p):
    try:
        # 5 second timeout per position
        with timeout(5):
            cached_df = cache_mgr.get_cached_ohlcv(...)
            if not cache_fresh:
                df = fetcher.get_ohlcv(...)  # Has 5s timeout
    except TimeoutError:
        # Use cache or entry price on timeout
        p.current_price = p.entry_price
```

**Pros:**
- ✅ Faster than sequential (6 positions in 5s, not 30s)
- ✅ Timeout prevents hanging

**Cons:**
- ⚠️ Still slower than pure cache
- ⚠️ More complex code

---

### Solution 3: Longer Cache TTL + Scheduler Refresh

**Idea:** Make cache last longer (1 hour), let scheduler refresh it.

```python
# Change cache freshness check from 5 min to 60 min
cache_fresh = time_diff < timedelta(minutes=60)  # Was 5 minutes

# Scheduler refreshes cache every hour
@scheduler.scheduled_job('cron', minute='10')
def refresh_all_caches():
    for position in get_open_positions():
        df = fetcher.get_ohlcv(...)
        cache_mgr.save_ohlcv(...)
```

**Pros:**
- ✅ Simple change (1 line)
- ✅ Dashboard always fast
- ✅ Scheduler handles refresh

**Cons:**
- ⚠️ Prices up to 1 hour old
- ⚠️ Scheduler must run reliably

---

### Solution 4: Hybrid Approach (BEST FOR PRODUCTION)

**Combine all strategies:**

1. **Default:** Return cached data immediately
2. **If cache missing:** Fetch with 5s timeout, use entry price on timeout
3. **Background refresh:** Schedule refresh for stale caches
4. **Scheduler:** Hourly full refresh

```python
@router.get("/positions/open")
def list_open_positions(db: Session, background_tasks: BackgroundTasks):
    for p in positions:
        cached_df = cache_mgr.get_cached_ohlcv(...)
        
        if cached_df is not None:
            p.current_price = cached_df['Close'].iloc[-1]
            
            # Schedule refresh if >10 min old
            if is_stale(cached_df, minutes=10):
                background_tasks.add_task(refresh_cache, p)
        else:
            # No cache - try fetch with timeout
            try:
                with timeout(5):
                    df = fetcher.get_ohlcv(...)
                    p.current_price = df['Close'].iloc[-1]
                    cache_mgr.save_ohlcv(...)
            except TimeoutError:
                p.current_price = p.entry_price  # Fallback
    
    return positions
```

---

## Immediate Fix (For Now)

**Revert to simple caching (no fresh fetch):**

```python
# In src/api/routes.py - TEMPORARY FIX

@router.get("/positions/open")
def list_open_positions(db: Session):
    cache_mgr = OHLCVCacheManager(db)
    positions = get_open_positions()
    
    for p in positions:
        cached_df = cache_mgr.get_cached_ohlcv(p.pair, p.timeframe, limit=1)
        
        if cached_df is not None and not cached_df.empty:
            p.current_price = float(cached_df['Close'].iloc[-1])
            # Calculate PnL from cache
        else:
            # No cache - use entry price (will be updated by scheduler)
            p.current_price = p.entry_price
            p.unrealized_pnl = 0.0
            p.unrealized_pnl_pct = 0.0
    
    return positions
```

**Then rely on scheduler** to keep cache fresh (runs every hour at :10).

---

## VM IP Issue (Separate Problem)

**Symptom:** Settings page shows old VM IP (35.188.118.182)

**Cause:** Session state persists across restarts.

**Fix:** Already implemented in ui.py:
```python
# Force update session state if .env changed
if st.session_state.get("vm_external_ip") != current_vm_ip:
    st.session_state.vm_external_ip = current_vm_ip
```

**To apply:**
1. Clear browser cache completely
2. Or use Incognito/Private window
3. Or add `?clear_cache=1` to URL

---

## Action Items

### Immediate (Tonight):
1. ✅ Document the issue (this file)
2. ⏳ Revert to simple caching (no fresh fetch in API)
3. ⏳ Verify scheduler is running and refreshing cache

### Tomorrow:
1. ⏳ Implement Solution 4 (Hybrid Approach)
2. ⏳ Add timeout handling to all external API calls
3. ⏳ Add monitoring for cache freshness
4. ⏳ Test with various network conditions

---

## Testing Checklist

After fix:
- [ ] Dashboard loads in <5 seconds
- [ ] All 6 positions show correct data
- [ ] Settings page shows correct VM IP (34.171.241.166)
- [ ] Refresh button works
- [ ] Scheduler runs at :10 every hour
- [ ] Cache is refreshed by scheduler
- [ ] API response time <2 seconds

---

## References

- `SESSION_LOG_2026-03-07_API_OPTIMIZATION.md` - Original implementation
- `DATA_FETCHING_GUIDE.md` - Cache architecture
- `src/api/routes.py` - API endpoint code
- `src/services/ohlcv_cache_manager.py` - Cache manager
