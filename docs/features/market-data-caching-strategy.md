# Market Data Caching Strategy for MTF Scanner

**Status:** Draft
**Date:** 2026-03-08
**Issue:** MTF scanner fetches data for every scan — slow and costly (API calls)

---

## Problem Statement

### Current Behavior

1. **Every MTF scan triggers live API calls:**
   - User clicks "Scan Now" in dashboard
   - `routes_mtf.py` → `_load_pair_data()` reads from OHLCV cache
   - If cache is empty/stale → returns "no data" → user sees nothing
   - User must wait for prefetch job (runs every 2 hours at :20)

2. **Prefetch job limitations:**
   - Runs on fixed schedule (every 2 hours)
   - No visibility into what's cached
   - No manual refresh option
   - No prioritization (all pairs treated equally)

3. **No data status visibility:**
   - Users can't see which pairs have fresh data
   - No indication of candle count per timeframe
   - No quality metrics (EXCELLENT/GOOD/STALE/MISSING)

### Impact

| Issue | Impact |
|-------|--------|
| Slow scans | Users wait 5-15 seconds per pair during live fetch |
| API costs | Twelve Data free tier: 800 calls/day limit |
| Poor UX | "No data" errors with no explanation or fix |
| Blind spots | Can't tell which pairs need refresh |

---

## Solution Overview

### Goals

1. **Zero live API calls during MTF scans** — all data from cache
2. **Full visibility** — dashboard shows data status per pair/timeframe
3. **Smart refresh** — prioritize stale data, skip fresh caches
4. **Manual control** — on-demand refresh for specific pairs
5. **Cost optimization** — reduce API calls by 80%+

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Market Data Service                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Status     │    │    Cache     │    │    Refresh   │      │
│  │   Tracker    │    │   Manager    │    │   Scheduler  │      │
│  │              │    │              │    │              │      │
│  │ - Quality    │    │ - Read       │    │ - Priority   │      │
│  │ - Freshness  │    │ - Write      │    │ - Throttle   │      │
│  │ - Coverage   │    │ - Validate   │    │ - Retry      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │          SQLite Database               │
        ├───────────────────────────────────────┤
        │                                       │
        │  ┌─────────────────────────────────┐  │
        │  │ market_data_status (NEW)        │  │
        │  │ - pair, timeframe               │  │
        │  │ - candle_count, last_update     │  │
        │  │ - data_quality, source          │  │
        │  └─────────────────────────────────┘  │
        │                                       │
        │  ┌─────────────────────────────────┐  │
        │  │ ohlcv_cache (EXISTING)          │  │
        │  │ - symbol, timeframe, timestamp  │  │
        │  │ - open, high, low, close, vol   │  │
        │  └─────────────────────────────────┘  │
        │                                       │
        └───────────────────────────────────────┘
```

---

## Database Schema

### New Table: `market_data_status`

Metadata table tracking cache health for each pair/timeframe combination.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `pair` | String(20) | Trading pair (e.g., "BTC/USDT", "XAU/USD") |
| `timeframe` | String(10) | Timeframe (e.g., "h4", "d1", "w1") |
| `candle_count` | Integer | Number of cached candles |
| `last_candle_time` | DateTime | Timestamp of most recent candle |
| `fetched_at` | DateTime | When this status was last updated |
| `data_quality` | String(20) | EXCELLENT / GOOD / STALE / MISSING |
| `source` | String(20) | Data source (ccxt, twelvedata, gateio) |

**Indexes:**
- `(pair, timeframe)` — Unique constraint
- `(pair)` — Fast lookup for single pair (all timeframes)
- `(data_quality)` — Filter by quality (e.g., show only STALE)

**Example Row:**
```
id=1, pair='BTC/USDT', timeframe='d1', candle_count=150,
last_candle_time='2026-03-08 00:00:00', fetched_at='2026-03-08 02:20:00',
data_quality='GOOD', source='ccxt'
```

---

## Data Quality Assessment

### Quality Levels

| Level | Candle Count | Max Age | Use Case |
|-------|--------------|---------|----------|
| **EXCELLENT** | 200+ | < 2× timeframe interval | Full HTF analysis (50/200 SMA) |
| **GOOD** | 100-199 | < 4× timeframe interval | Standard MTF analysis |
| **STALE** | 50-99 | < 24 hours | Limited analysis, refresh soon |
| **MISSING** | < 50 | ≥ 24 hours | Insufficient data, do not scan |

### Quality Calculation

```python
def assess_quality(candle_count: int, age_hours: float, timeframe: str) -> DataQuality:
    tf_hours = get_timeframe_hours(timeframe)  # h4=4, d1=24, w1=168

    if candle_count < 50:
        return DataQuality.MISSING

    if candle_count < 100:
        return DataQuality.STALE

    if candle_count >= 200 and age_hours < tf_hours * 2:
        return DataQuality.EXCELLENT

    if candle_count >= 100 and age_hours < tf_hours * 4:
        return DataQuality.GOOD

    return DataQuality.STALE
```

**Example:**
- `BTC/USDT` on `d1` with 150 candles, last updated 12 hours ago
  - `tf_hours = 24`
  - `max_age_good = 24 × 4 = 96 hours`
  - `12 < 96` → **GOOD**

---

## API Endpoints

### 1. Get All Pairs Status

```http
GET /api/v1/market-data/status
```

**Response:**
```json
{
  "timestamp": "2026-03-08T02:20:00Z",
  "total_pairs": 4,
  "summary": {
    "excellent": 2,
    "good": 1,
    "stale": 1,
    "missing": 0
  },
  "pairs": [
    {
      "pair": "BTC/USDT",
      "overall_quality": "GOOD",
      "timeframes": {
        "w1": { "candles": 50, "quality": "GOOD", "last_update": "2026-03-07T00:00:00Z" },
        "d1": { "candles": 150, "quality": "GOOD", "last_update": "2026-03-08T00:00:00Z" },
        "h4": { "candles": 100, "quality": "EXCELLENT", "last_update": "2026-03-08T00:00:00Z" }
      }
    },
    {
      "pair": "XAU/USD",
      "overall_quality": "STALE",
      "timeframes": {
        "w1": { "candles": 30, "quality": "STALE", "last_update": "2026-03-01T00:00:00Z" },
        "d1": { "candles": 80, "quality": "STALE", "last_update": "2026-03-07T00:00:00Z" },
        "h4": { "candles": 50, "quality": "MISSING", "last_update": "2026-03-06T00:00:00Z" }
      }
    }
  ]
}
```

### 2. Get Single Pair Status

```http
GET /api/v1/market-data/status/{pair}
```

**Response:**
```json
{
  "pair": "BTC/USDT",
  "fetched_at": "2026-03-08T02:20:00Z",
  "overall_quality": "GOOD",
  "timeframes": [
    {
      "timeframe": "w1",
      "candle_count": 50,
      "last_candle_time": "2026-03-07T00:00:00Z",
      "quality": "GOOD",
      "source": "ccxt",
      "needs_refresh": false
    },
    {
      "timeframe": "d1",
      "candle_count": 150,
      "last_candle_time": "2026-03-08T00:00:00Z",
      "quality": "GOOD",
      "source": "ccxt",
      "needs_refresh": false
    },
    {
      "timeframe": "h4",
      "candle_count": 100,
      "last_candle_time": "2026-03-08T00:00:00Z",
      "quality": "EXCELLENT",
      "source": "ccxt",
      "needs_refresh": false
    }
  ],
  "mtf_ready": true,
  "recommendation": "Ready for MTF analysis"
}
```

### 3. Refresh Pair Data

```http
POST /api/v1/market-data/refresh
Content-Type: application/json

{
  "pair": "XAU/USD",
  "timeframes": ["d1", "h4"]  // Optional, defaults to all MTF timeframes
}
```

**Response:**
```json
{
  "status": "success",
  "pair": "XAU/USD",
  "refreshed": [
    {"timeframe": "d1", "candles_fetched": 20, "quality": "GOOD"},
    {"timeframe": "h4", "candles_fetched": 35, "quality": "EXCELLENT"}
  ],
  "skipped": [],
  "errors": []
}
```

### 4. Bulk Refresh (All Stale Pairs)

```http
POST /api/v1/market-data/refresh-all
```

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_pairs": 4,
    "refreshed": 2,
    "skipped": 2,
    "errors": 0
  },
  "details": [
    {"pair": "XAU/USD", "status": "refreshed", "timeframes": 3},
    {"pair": "BTC/USDT", "status": "skipped", "reason": "Cache fresh"}
  ]
}
```

---

## Dashboard UI

### Market Data Status Panel

**Location:** New page under "📊 Market Data" (alongside existing MTF Scanner)

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Market Data Status                              [Refresh All]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Summary: 2 Excellent | 1 Good | 1 Stale | 0 Missing            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Pair       │ Overall │ W1    │ D1    │ H4    │ Last Update│  │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ BTC/USDT   │ 🟢 GOOD │ 🟢    │ 🟢    │ 🟢    │ 2h ago     │  │
│  │ ETH/USDT   │ 🟢 GOOD │ 🟢    │ 🟢    │ 🟢    │ 2h ago     │  │
│  │ XAU/USD    │ 🟡 STALE│ 🟡    │ 🟡    │ 🔴    │ 18h ago    │  │
│  │ XAG/USD    │ 🟢 GOOD │ 🟢    │ 🟢    │ 🟢    │ 2h ago     │  │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [Expand Row for Details ▼]                                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ XAU/USD Details                                          │   │
│  │ ───────────────────────────────────────────────────────  │   │
│  │ Timeframe │ Candles │ Quality   │ Last Candle    │ Source│  │
│  │ W1        │ 30      │ 🟡 STALE  │ Mar 1, 2026    │ Gate.io│ │
│  │ D1        │ 80      │ 🟡 STALE  │ Mar 7, 2026    │ Gate.io│ │
│  │ H4        │ 45      │ 🔴 MISSING│ Mar 6, 2026    │ Gate.io│ │
│  │                                                          │  │
│  │ [Refresh This Pair]                                       │  │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Color Coding

| Badge | Meaning | Action |
|-------|---------|--------|
| 🟢 EXCELLENT | 200+ candles, very fresh | No action needed |
| 🟢 GOOD | 100+ candles, recent | No action needed |
| 🟡 STALE | 50-99 candles OR old | Refresh soon |
| 🔴 MISSING | <50 candles | Refresh required |

### User Actions

1. **View Status:** See all pairs and their data quality at a glance
2. **Expand Details:** Click row to see timeframe breakdown
3. **Refresh Single Pair:** Click "Refresh This Pair" button
4. **Refresh All Stale:** Click "Refresh All" to update all stale/missing pairs
5. **Auto-Refresh Toggle:** Enable/disable automatic background refresh

---

## Cache Refresh Strategy

### Priority Queue

Refresh jobs are prioritized based on data quality:

| Priority | Quality | Pairs | Refresh Frequency |
|----------|---------|-------|-------------------|
| **P0 (Critical)** | MISSING | All pairs with any MISSING timeframe | Immediate |
| **P1 (High)** | STALE | Pairs not refreshed in 12+ hours | Next available slot |
| **P2 (Normal)** | GOOD | Pairs not refreshed in 6+ hours | Scheduled window |
| **P3 (Low)** | EXCELLENT | Fresh pairs | Skip (no refresh needed) |

### Refresh Triggers

1. **Scheduled (Background):**
   - Runs every 2 hours at :20 (existing prefetch job)
   - Only refreshes STALE or MISSING pairs
   - Skips GOOD and EXCELLENT caches

2. **Manual (User-Triggered):**
   - User clicks "Refresh" button in dashboard
   - Immediate refresh for selected pair(s)
   - Shows progress indicator during fetch

3. **On-Demand (API):**
   - MTF scan detects stale data
   - Returns "no data" with suggestion to refresh
   - User can trigger refresh from scan results page

### Rate Limiting

To avoid API throttling:

- Max 10 concurrent fetches
- 1-second delay between API calls
- Twelve Data: Respect 800 calls/day limit
- CCXT: Respect exchange rate limits

---

## MTF Scanner Integration

### Current Flow (Problematic)

```
User clicks "Scan Now"
    ↓
Load pair data from cache
    ↓
Cache empty? → Return "no data" ❌
    ↓
User waits for next prefetch job (up to 2 hours)
```

### New Flow (Cache-First with Fallback)

```
User clicks "Scan Now"
    ↓
Check market_data_status table
    ↓
All timeframes GOOD+? → Scan immediately ✅
    ↓
Any timeframe STALE/MISSING? → Show warning + [Refresh] button
    ↓
User clicks [Refresh] → Fetch from API → Update cache → Scan
```

### Code Changes

**Before:**
```python
def _load_pair_data(pair, config, cache_mgr):
    data = cache_mgr.get_multi_timeframe_ohlcv(pair, [htf, mtf, ltf])
    if any(df is None for df in data.values()):
        return None  # "No data" — user stuck
    return data
```

**After:**
```python
def _load_pair_data(pair, config, cache_mgr, status_service):
    # Check status first
    status = status_service.get_pair_status(pair)
    
    if status.overall_quality in ("MISSING", "STALE"):
        # Return status with actionable error
        return {
            "error": "stale_data",
            "quality": status.overall_quality,
            "needs_refresh": status.stale_timeframes,
        }
    
    # Load from cache
    data = cache_mgr.get_multi_timeframe_ohlcv(pair, [htf, mtf, ltf])
    return data
```

---

## Implementation Plan

### Phase 1: Database Models (Task 1-2)
- [ ] Create `market_data_status` table model
- [ ] Add `DataQuality` enum
- [ ] Create migration function
- [ ] Update `database.py` to create table on init

### Phase 2: Service Layer (Task 3)
- [ ] Create `MarketDataService` class
- [ ] Implement `get_pair_status()` method
- [ ] Implement `get_all_statuses()` method
- [ ] Implement `refresh_pair()` method
- [ ] Implement `assess_quality()` logic
- [ ] Integrate with `OHLCVCacheManager`

### Phase 3: API Endpoints (Task 4)
- [ ] Create `routes_market_data.py`
- [ ] `GET /api/v1/market-data/status` endpoint
- [ ] `GET /api/v1/market-data/status/{pair}` endpoint
- [ ] `POST /api/v1/market-data/refresh` endpoint
- [ ] `POST /api/v1/market-data/refresh-all` endpoint
- [ ] Add to `main.py` router

### Phase 4: Dashboard UI (Task 5)
- [ ] Create `ui_market_data.py` panel
- [ ] Status table with color-coded badges
- [ ] Expandable row details
- [ ] Refresh buttons (single + bulk)
- [ ] Progress indicators during refresh
- [ ] Add to `ui.py` navigation

### Phase 5: Scheduler Integration (Task 6-7)
- [ ] Update `mtf_cache_prefetcher.py` to use quality assessment
- [ ] Add priority queue for refresh jobs
- [ ] Update `scheduler.py` to track status after prefetch
- [ ] Add manual refresh endpoint support

### Phase 6: MTF Scanner Integration (Task 6)
- [ ] Update `routes_mtf.py` to check status before scan
- [ ] Show actionable errors for stale data
- [ ] Add "Refresh & Scan" button flow
- [ ] Update `ui_mtf_scanner.py` with status indicators

### Phase 7: Testing & Documentation (Task 8-9)
- [ ] Write unit tests for `MarketDataService`
- [ ] Write integration tests for API endpoints
- [ ] Update README with new feature
- [ ] Add user guide section
- [ ] Update API docs

---

## Benefits

### Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Scan time (4 pairs) | 5-15s | <1s | 10-15× faster |
| API calls per scan | 12 (3 TFs × 4 pairs) | 0 | 100% reduction |
| Cache hit rate | ~50% | ~95% | 45% increase |

### Cost Savings

| Provider | Before (calls/day) | After (calls/day) | Savings |
|----------|-------------------|-------------------|---------|
| Twelve Data | ~200 (25 scans × 8 calls) | ~40 (prefetch only) | 80% |
| CCXT | ~200 | ~40 | 80% |
| Gate.io | ~200 | ~40 | 80% |

### User Experience

- **Visibility:** Know exactly which pairs have fresh data
- **Control:** Manual refresh when needed
- **Speed:** Instant scans from cache
- **Reliability:** No more "no data" surprises

---

## Monitoring & Alerts

### Metrics to Track

1. **Cache Health:**
   - % of pairs with EXCELLENT/GOOD quality
   - Average candle count per timeframe
   - Time since last refresh

2. **API Usage:**
   - Calls per day per provider
   - Remaining quota (Twelve Data: 800/day)
   - Failed fetches

3. **User Actions:**
   - Manual refreshes per day
   - Most-refreshed pairs
   - Scan success rate

### Future Enhancements

1. **Smart Prefetch:**
   - Learn user's scan patterns
   - Pre-refresh pairs before typical scan times
   - Prioritize frequently-scanned pairs

2. **Multi-Source Fallback:**
   - If CCXT fails, try Gate.io
   - If Twelve Data quota exhausted, skip metals
   - Automatic source switching based on availability

3. **Data Retention Policy:**
   - Auto-delete candles older than 1 year
   - Keep only last 500 candles per pair/timeframe
   - Compress historical data

---

## Migration Path

### Existing Users

1. **Database Migration:**
   ```bash
   # Run migration script
   python -m src.database migrate-market-data-status
   ```

2. **Backfill Status Table:**
   ```bash
   # Populate status from existing OHLCV cache
   python scripts/backfill_market_data_status.py
   ```

3. **Update Dashboard:**
   - New "Market Data" page appears in navigation
   - Existing MTF Scanner page unchanged
   - Users can adopt new workflow at their pace

### New Users

- Fresh install includes `market_data_status` table by default
- First-time setup wizard suggests initial data prefetch
- Default watchlist pre-populated with 4 pairs

---

## Conclusion

This caching strategy transforms the MTF scanner from a slow, API-dependent tool into a fast, cache-first system with full visibility and user control. The implementation is backward-compatible, incrementally deployable, and provides immediate value through reduced API costs and improved scan speeds.

**Next Steps:**
1. Review and approve this strategy document
2. Create implementation tasks in todo list
3. Begin Phase 1 (Database Models)
