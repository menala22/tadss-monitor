# Market Data Fetching Skill

**Location:** `.qwen/skills/market-data-fetching.md`
**Status:** Active
**Last updated:** 2026-03-08

---

## Purpose

This skill provides expertise in fetching, caching, and managing market data for the TA-DSS trading monitoring system. It covers multi-provider API routing, cache-first architecture, and data quality tracking.

---

## Capabilities

### 1. Multi-Provider Data Fetching

**Expertise:**
- Route trading pairs to optimal free API sources
- Handle symbol normalization across different APIs
- Implement retry logic with exponential backoff
- Cache-first architecture to minimize API costs

**Supported Providers:**
| Provider | Asset Classes | Cost | Limits |
|----------|---------------|------|--------|
| CCXT/Kraken | Crypto (BTC, ETH, SOL, etc.) | Free | Unlimited |
| Twelve Data | Metals (XAU), Forex, Stocks | Free tier | 800 calls/day |
| Gate.io | Silver (XAG swap) | Free | Unlimited |

**Routing Logic:**
```python
XAG*  → Gate.io      # Free swap contracts
XAU*  → Twelve Data  # Free tier works
BTC*, ETH* → CCXT    # Free, no API key
Forex → Twelve Data  # Default fallback
```

### 2. OHLCV Cache Management

**Expertise:**
- Incremental fetch (only new candles)
- Multi-timeframe caching (w1, d1, h4, h1, etc.)
- Cache status tracking (quality, freshness)
- Deduplication of timeframe variations

**Cache Strategy:**
1. Check `ohlcv_cache` table first
2. Calculate missing candles since last update
3. Fetch only missing candles from API
4. Merge cached + new, save to cache
5. Return complete dataset

**Benefits:**
- 80% reduction in API calls
- Scan speed: <1s (was 5-15s)
- Zero API calls during MTF scans

### 3. Data Quality Tracking

**Expertise:**
- 4-tier quality assessment (EXCELLENT/GOOD/STALE/MISSING)
- Timeframe-relative age thresholds
- MTF readiness checks
- Dashboard visibility with refresh controls

**Quality Criteria:**
| Level | Candle Count | Max Age | Use Case |
|-------|--------------|---------|----------|
| EXCELLENT | 200+ | < 2× timeframe interval | Full HTF analysis |
| GOOD | 100-199 | < 4× timeframe interval | Standard MTF |
| STALE | 50-99 | < 24 hours | Refresh recommended |
| MISSING | < 50 | ≥ 24 hours | Refresh required |

**Example Assessment:**
```python
# d1 timeframe with 150 candles, 12h old
tf_hours = 24  # d1 = 24 hours
max_age_good = 24 * 4 = 96 hours
12 < 96 and 150 >= 100 → GOOD ✅
```

### 4. Timeframe Normalization

**Expertise:**
- Handle API format variations (`1week`, `1w`, `w1` → `w1`)
- Merge duplicate entries intelligently
- Sort timeframes logically (longest first)

**Normalization Map:**
```python
'1week', '1w', 'week' → 'w1'
'1day', '1d', 'day'   → 'd1'
'1hour', '1h', 'hour' → 'h1'
'4h', '2h', etc.      → 'h4', 'h2'
```

**Merge Strategy:**
When duplicates exist, keep:
1. Highest candle count
2. Best quality rating
3. Newest `fetched_at` timestamp

---

## Files & Components

### Core Implementation

| File | Purpose | Lines |
|------|---------|-------|
| `src/data_fetcher.py` | Multi-provider fetcher | 1013 |
| `src/services/ohlcv_cache_manager.py` | Cache management | 400+ |
| `src/services/market_data_service.py` | Status tracking | 540 |
| `src/models/market_data_status_model.py` | Quality model | 246 |
| `src/models/ohlcv_cache_model.py` | Cache schema | 150 |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/market-data/status` | GET | All pairs status |
| `/api/v1/market-data/status/{pair}` | GET | Single pair details |
| `/api/v1/market-data/summary` | GET | Summary statistics |
| `/api/v1/market-data/refresh` | POST | Refresh specific pair |
| `/api/v1/market-data/refresh-all` | POST | Refresh all stale pairs |
| `/api/v1/market-data/watchlist` | GET | Watchlist with status |

### Dashboard UI

| Component | Location | Purpose |
|-----------|----------|---------|
| Market Data Page | `src/ui_market_data.py` | Status dashboard |
| Summary Cards | Top of page | Total, MTF ready, by quality |
| View Modes | Table/Cards/Details | Flexible display |
| Refresh Controls | Bottom of page | Manual refresh triggers |

---

## Common Tasks

### Task 1: Fetch Data for a Pair

```python
from src.data_fetcher import DataFetcher

fetcher = DataFetcher()  # Auto-detect source

# Fetch 100 daily candles
df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)

# Fetch is cache-first:
# 1. Checks ohlcv_cache table
# 2. Fetches only missing candles
# 3. Saves to cache automatically
```

### Task 2: Check Data Status

```python
from src.services.market_data_service import MarketDataService
from src.database import get_db_context

with get_db_context() as db:
    service = MarketDataService(db)
    
    # Get status for all pairs
    statuses = service.get_all_statuses()
    
    # Get status for single pair
    btc_status = service.get_pair_status('BTC/USDT')
    print(f"Quality: {btc_status.overall_quality}")
    print(f"MTF Ready: {btc_status.mtf_ready}")
    
    # Get stale pairs needing refresh
    stale = service.get_stale_pairs()
```

### Task 3: Refresh Stale Data

```python
# Via API
curl -X POST "http://localhost:8000/api/v1/market-data/refresh" \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"pair": "XAU/USD", "timeframes": ["d1", "h4"]}'

# Via service
result = service.update_status(
    pair='XAU/USD',
    timeframe='d1',
    candle_count=250,
    source='twelvedata'
)
```

### Task 4: Sync Status from Cache

```python
# Populate market_data_status from existing OHLCV cache
stats = service.sync_all_statuses()
# Returns: {'updated': N, 'created': N, 'deleted': N}
```

### Task 5: Check MTF Readiness

```python
# Check if pair has sufficient data for MTF scanning
ready_pairs = service.get_mtf_ready_pairs(trading_style='SWING')
# Returns: ['BTC/USDT', 'ETH/USDT'] if they have GOOD+ quality

# SWING requires: w1, d1, h4 all GOOD or EXCELLENT
```

---

## Troubleshooting

### Issue: "No data available" on first scan

**Cause:** Cache is empty (fresh deployment)

**Solution:**
```bash
# Trigger prefetch job manually
docker exec tadss python -c "
from src.services.mtf_cache_prefetcher import prefetch_mtf_cache
from src.database import get_db_context
with get_db_context() as db:
    prefetch_mtf_cache(db)
"

# Or wait for scheduled job (runs every 2h at :20)
```

### Issue: Duplicate timeframes (1w, 1week, w1)

**Cause:** Old cache entries with mixed formats

**Solution:**
```python
# Clean up old formats
from src.models.market_data_status_model import MarketDataStatus

old_formats = ['1w', '1week', '1d', '1day', '1h', '4h']
for tf in old_formats:
    db.query(MarketDataStatus).filter(
        MarketDataStatus.timeframe == tf
    ).delete()
db.commit()

# UI handles remaining duplicates via _merge_timeframe_data()
```

### Issue: Wrong quality (250 candles marked as MISSING)

**Cause:** Old status entries not updated after cache refresh

**Solution:**
```python
# Re-sync status from cache
stats = service.sync_all_statuses()
# This recalculates quality based on actual candle counts
```

### Issue: API key errors (Twelve Data)

**Cause:** Missing or invalid API key in `.env`

**Solution:**
```bash
# Check .env file
grep TWELVE_DATA_API_KEY .env

# Should show:
TWELVE_DATA_API_KEY=your_key_here

# Get free key at: https://twelvedata.com/
```

### Issue: CCXT not initialized for crypto

**Cause:** DataFetcher created with wrong source

**Solution:**
```python
# Use auto-detect (default)
fetcher = DataFetcher()  # auto_detect_source=True by default

# Or explicitly set
fetcher = DataFetcher(source='ccxt')
```

---

## Best Practices

### 1. Always Use Cache-First

❌ **Don't:**
```python
# Live fetch on every scan (slow, costly)
df = fetcher.get_ohlcv('BTC/USDT', 'd1')  # Always hits API
```

✅ **Do:**
```python
# Cache-first (fast, free)
df = cache_mgr.get_cached_ohlcv('BTC/USDT', 'd1', limit=100)
if df is None or len(df) < 10:
    # Only fetch if cache is empty/stale
    df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)
```

### 2. Normalize Timeframes

❌ **Don't:**
```python
# Store mixed formats
cache_mgr.save_ohlcv('BTC/USDT', '1week', df)  # Inconsistent
cache_mgr.save_ohlcv('BTC/USDT', 'w1', df)     # Also inconsistent
```

✅ **Do:**
```python
# Use normalized format consistently
cache_mgr.save_ohlcv('BTC/USDT', 'w1', df)  # Always 'w1'
```

### 3. Check Quality Before Scanning

❌ **Don't:**
```python
# Scan without checking data status
results = scanner.scan_opportunities(data)  # May fail silently
```

✅ **Do:**
```python
# Check status first
status = service.get_pair_status('BTC/USDT')
if status.overall_quality in ('STALE', 'MISSING'):
    # Refresh or warn user
    refresh_pair(pair)
else:
    # Proceed with scan
    results = scanner.scan_opportunities(data)
```

### 4. Monitor API Usage

❌ **Don't:**
```python
# Unlimited fetching (will hit rate limits)
for pair in watchlist:
    for tf in timeframes:
        fetcher.get_ohlcv(pair, tf)  # 20 calls instantly
```

✅ **Do:**
```python
# Batch with delays, respect limits
for pair in watchlist:
    for tf in timeframes:
        if not cache_is_fresh(pair, tf):
            fetcher.get_ohlcv(pair, tf)
            time.sleep(0.1)  # Rate limiting
```

### 5. Handle API Failures Gracefully

❌ **Don't:**
```python
# No error handling
df = fetcher.get_ohlcv('BTC/USDT', 'd1')  # Crashes on failure
```

✅ **Do:**
```python
# Retry logic with fallback
try:
    df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)
except DataFetchError as e:
    logger.warning(f"Fetch failed: {e}")
    df = cache_mgr.get_cached_ohlcv('BTC/USDT', 'd1')  # Fallback to cache
```

---

## Testing

### Unit Tests

```bash
# Run all market data tests
pytest tests/test_market_data/ -v

# Expected output:
# 68 passed (32 model + 23 service + 13 routes)
```

### Manual Testing

```bash
# Test data source detection
python -c "
from src.data_fetcher import _detect_data_source
print(_detect_data_source('BTC/USDT'))  # ccxt
print(_detect_data_source('XAU/USD'))   # twelvedata
print(_detect_data_source('XAG/USD'))   # gateio
"

# Test quality assessment
python -c "
from src.models.market_data_status_model import MarketDataStatus, DataQuality
q = MarketDataStatus.assess_quality(candle_count=150, age_hours=12, timeframe='d1')
print(q)  # DataQuality.GOOD
"

# Test API endpoint
curl "http://localhost:8000/api/v1/market-data/status" \
  -H "X-API-Key: your_key" | python -m json.tool
```

---

## Related Skills

- [`project-documentation`](project-documentation.md) — Documentation standards
- [`database-management`](database-management.md) — SQLite/PostgreSQL operations
- [`api-development`](api-development.md) — FastAPI endpoint design
- [`streamlit-dashboard`](streamlit-dashboard.md) — Dashboard UI components

---

## References

### Documentation
- [`docs/features/data-fetcher.md`](../../docs/features/data-fetcher.md) — Full DataFetcher design
- [`docs/features/market-data-caching.md`](../../docs/features/market-data-caching.md) — Caching strategy
- [`docs/features/database.md`](../../docs/features/database.md) — Database schemas

### Code
- `src/data_fetcher.py` — Main implementation
- `src/services/market_data_service.py` — Service layer
- `src/api/routes_market_data.py` — API endpoints

### Decisions
- **DEC-018:** Cache-first architecture for MTF scanner
- **DEC-019:** Quality-based data assessment
- **DEC-020:** Timeframe normalization with duplicate merging

---

## Quick Reference

### Data Source Routing
```
XAG*  → Gate.io      (free swap)
XAU*  → Twelve Data  (800/day free)
BTC*  → CCXT/Kraken  (unlimited free)
Forex → Twelve Data  (default)
```

### Quality Thresholds
```
EXCELLENT: 200+ candles, age < 2× tf interval
GOOD:      100+ candles, age < 4× tf interval
STALE:     50-99 candles OR age < 24h
MISSING:   <50 candles OR age ≥ 24h
```

### API Endpoints
```
GET  /api/v1/market-data/status       # All pairs
GET  /api/v1/market-data/summary      # Statistics
POST /api/v1/market-data/refresh      # Single pair
POST /api/v1/market-data/refresh-all  # Bulk refresh
```

### Key Commands
```bash
# Check status
curl http://localhost:8000/api/v1/market-data/status

# Refresh all stale
curl -X POST http://localhost:8000/api/v1/market-data/refresh-all

# Run tests
pytest tests/test_market_data/ -v
```
