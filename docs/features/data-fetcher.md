# DataFetcher - Multi-Provider Market Data

_Status: Done_
_Last updated: 2026-03-08_

## What It Does

Provides a unified interface for fetching OHLCV (candlestick) market data from multiple free API sources with automatic smart routing. Eliminates API key costs by routing each asset class to the best free provider.

**User-facing outcome:** Fetch market data for any trading pair without configuring API keys — crypto via CCXT/Kraken, metals via Twelve Data/Gate.io, forex via Twelve Data.

---

## Data Source Routing

### Automatic Detection (`_detect_data_source()`)

Routes pairs to optimal free data source based on symbol prefix:

| Pair Pattern | Data Source | API Key Required | Reason |
|--------------|-------------|------------------|--------|
| `XAG*` (Silver) | **Gate.io** | No (free swap) | Twelve Data requires paid plan for XAG |
| `XAU*` (Gold) | **Twelve Data** | No (free tier: 800/day) | Reliable, good coverage |
| `XPT*`, `XPD*` (Platinum, Palladium) | **Twelve Data** | Yes (paid plan) | Limited free tier support |
| `BTC*`, `ETH*`, `SOL*`, etc. | **CCXT/Kraken** | No (free) | Best crypto coverage, no limits |
| Stocks (`AAPL`, `TSLA`) | **Twelve Data** | No (free tier) | Reliable for US stocks |
| Forex (`EURUSD`, `GBPUSD`) | **Twelve Data** | No (free tier) | Default fallback |

### Supported Crypto Prefixes

```python
crypto_prefixes = {
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC',
    'LTC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'XLM', 'BCH', 'ALGO', 'VET',
    'XBT'  # Bitcoin alternative symbol (used by some exchanges)
}
```

Any pair starting with these prefixes routes to CCXT.

---

## Symbol Normalization

Different APIs use different symbol formats. DataFetcher normalizes automatically:

### Twelve Data Format

| Input | Normalized | Asset Class |
|-------|------------|-------------|
| `XAUUSD` | `XAU/USD` | Metals |
| `XAGUSD` | `XAG/USD` | Metals |
| `EURUSD` | `EUR/USD` | Forex |
| `BTCUSD` | `BTC/USD` | Crypto |
| `AAPL` | `AAPL` | Stocks |

### CCXT Format

Uses `normalize_ticker()` helper from `src/utils/helpers.py`:
- Converts to exchange-specific format
- Example: `BTCUSD` → `BTC/USDT` (Kraken format)

### Gate.io Format

Tries multiple formats until one succeeds:
1. `XAG/USDT:USDT` (swap contract — preferred)
2. `XAG/USD` (spot format)
3. `XAGUSD` (alternative)

Also handles gold:
1. `XAU/USDT:USDT`
2. `XAU/USD`
3. `XAUUSD`

---

## Fetch Flow

```
User/Job requests data for pair
         ↓
_detect_data_source(pair)
         ↓
    Routes to appropriate source
         ↓
    ┌─────────────────┬─────────────────┬──────────────┐
    │   Twelve Data   │     CCXT        │   Gate.io    │
    │   (XAU, Forex)  │   (Crypto)      │   (XAG)      │
    └────────┬────────┴────────┬────────┴──────┬───────┘
             │                 │               │
    Normalize symbol    Normalize symbol  Try multiple
    XAUUSD→XAU/USD      BTC/USDT→...      formats
             │                 │               │
    Fetch from API      Fetch from API    Fetch from API
             │                 │               │
    Save to cache       Save to cache     Save to cache
    (ohlcv_cache)       (ohlcv_cache)     (ohlcv_cache)
             │                 │               │
             └─────────────────┴───────────────┘
                          ↓
              Return DataFrame to caller
```

---

## Key Features

### 1. Smart Routing

```python
# Automatically detects best source
fetcher = DataFetcher()  # source auto-detected

df = fetcher.get_ohlcv('BTC/USDT', 'd1', limit=100)
# Routes to CCXT/Kraken automatically

df = fetcher.get_ohlcv('XAU/USD', 'd1', limit=100)
# Routes to Twelve Data automatically

df = fetcher.get_ohlcv('XAG/USD', 'd1', limit=100)
# Routes to Gate.io automatically
```

### 2. Cache-First with Incremental Fetch

1. **Check cache** — Queries `ohlcv_cache` table first
2. **Calculate missing** — Determines how many new candles needed
3. **Fetch only missing** — API call for new candles only
4. **Merge + save** — Combines cached + new, saves to cache
5. **Return merged** — Returns complete dataset

**Example:**
```
Cached: 100 candles (last: 2026-03-07)
Now: 2026-03-08
→ Fetch only 1 new candle, not full 100
```

### 3. Retry Logic

- **Attempts:** 3 retries by default
- **Backoff:** Exponential (1s, 2s, 4s delays)
- **Error handling:** Raises `DataFetchError` after all retries fail

### 4. Timeframe Mapping

Maps internal timeframe format to API-specific intervals:

| Internal | Twelve Data | CCXT | Gate.io |
|----------|-------------|------|---------|
| `m5` | `5min` | `5m` | `5m` |
| `h1` | `1h` | `1h` | `1h` |
| `h4` | `4h` | `4h` | `4h` |
| `d1` | `1day` | `1d` | `1d` |
| `w1` | `1week` | `1w` | `7d` |

---

## Current Watchlist Coverage

Your MTF watchlist uses all 3 working free sources:

| Pair | Data Source | Symbol Format | Status |
|------|-------------|---------------|--------|
| `BTC/USDT` | CCXT/Kraken | `BTC/USDT` | ✅ Free, no key |
| `ETH/USDT` | CCXT/Kraken | `ETH/USDT` | ✅ Free, no key |
| `XAU/USD` | Twelve Data | `XAU/USD` | ✅ Free tier (800/day) |
| `XAG/USD` | Gate.io | `XAG/USDT:USDT` | ✅ Free swap contract |

---

## API Usage & Costs

### Current Setup ($0/month)

| Provider | Daily Limit | Current Usage | Cost |
|----------|-------------|---------------|------|
| CCXT/Kraken | Unlimited | ~40 calls/day | $0 |
| Twelve Data | 800 calls/day | ~80 calls/day | $0 |
| Gate.io | Unlimited | ~40 calls/day | $0 |

### Usage Breakdown

**Prefetch job (every 2 hours):**
- 4 pairs × 5 timeframes × 12 runs/day = 240 calls/day
- Reduced to ~160/day with cache-first (80% reduction)

**Manual scans:**
- Zero API calls (all from cache)

**Total:** ~160-200 calls/day to Twelve Data (well within 800 free limit)

---

## As Built

_Added after implementation — 2026-03-08_

### What Changed from Design

1. **Added Gate.io integration** — Originally only Twelve Data for XAG, but free tier doesn't support silver
2. **Added lazy CCXT init** — `_fetch_ccxt()` initializes exchange on first call if not configured in constructor
3. **Added symbol fallback logic** — Tries multiple formats (e.g., `XAG/USDT:USDT`, `XAG/USD`, `XAGUSD`)

### Final Implementation

```python
# src/data_fetcher.py
class DataFetcher:
    def __init__(self, source="twelvedata", retry_attempts=3, retry_delay=1.0):
        # Initialize exchange if CCXT
        # Setup logging
        
    def get_ohlcv(self, symbol, timeframe, limit=100, auto_detect_source=True):
        # Auto-detect source based on symbol
        # Validate timeframe
        # Check cache first
        # Fetch from API if needed
        # Save to cache
        # Return DataFrame
```

### Known Limitations

1. **Twelve Data free tier limits:**
   - 800 calls/day
   - No 4h interval (uses 1h as proxy)
   - XAG/USD requires paid plan (use Gate.io instead)

2. **CCXT rate limits:**
   - Kraken: ~15 requests/minute
   - Handled by built-in rate limiting

3. **Gate.io history:**
   - Returns ~50-100 candles (limited vs CCXT's 500+)
   - Sufficient for monitoring, not for deep backtesting

4. **Symbol format variations:**
   - Old cache entries may have `1w`, `1week`, `w1` for same pair
   - UI merges duplicates via `_merge_timeframe_data()`

### Follow-up Tasks

- [ ] Add fallback chain (if Twelve Data fails, try yfinance)
- [ ] Add data validation (check for gaps, outliers)
- [ ] Add batch fetch for multiple pairs (reduce API calls)
- [ ] Add WebSocket support for real-time updates (future enhancement)

---

## Testing

**Integration tests:**
- Test data source detection for each asset class
- Test symbol normalization
- Test cache-first behavior
- Test retry logic

**Manual testing:**
```bash
# Test crypto fetch
python -c "from src.data_fetcher import DataFetcher; f = DataFetcher(); print(f.get_ohlcv('BTC/USDT', 'd1', 10))"

# Test metals fetch
python -c "from src.data_fetcher import DataFetcher; f = DataFetcher(); print(f.get_ohlcv('XAU/USD', 'd1', 10))"

# Test silver fetch
python -c "from src.data_fetcher import DataFetcher; f = DataFetcher(); print(f.get_ohlcv('XAG/USD', 'd1', 10))"
```

---

## Deployment Notes

**Environment variables required:**
```bash
# Twelve Data API key (free tier: 800 calls/day)
TWELVE_DATA_API_KEY=your_key_here

# CCXT exchange (default: kraken)
CCXT_EXCHANGE=kraken
```

**No API key needed for:**
- CCXT/Kraken (free, public API)
- Gate.io (free, public API)

**Cache initialization:**
```python
from src.database import get_db_context
from src.services.ohlcv_cache_manager import OHLCVCacheManager

with get_db_context() as db:
    cache_mgr = OHLCVCacheManager(db)
    # Cache table created automatically on init
```

---

## Related Files

| File | Purpose |
|------|---------|
| `src/data_fetcher.py` | Main implementation (1013 lines) |
| `src/config.py` | Timeframe validation, settings |
| `src/services/ohlcv_cache_manager.py` | Cache management |
| `src/models/ohlcv_cache_model.py` | Cache table schema |
| `src/utils/helpers.py` | `normalize_ticker()` helper |

---

## References

- [Twelve Data API Docs](https://twelvedata.com/docs)
- [CCXT Docs](https://docs.ccxt.com/)
- [Gate.io API Docs](https://www.gate.io/docs/developers/apiv4/)
- `docs/features/market-data-caching.md` — Cache-first architecture
- `docs/decisions.md` — DEC-018 (Cache-first architecture)
