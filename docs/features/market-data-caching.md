# Feature: Market Data Caching Strategy

_Status: Done_
_Last updated: 2026-03-08_

## What It Does

Provides a cache-first architecture for MTF (Multi-Timeframe) market data to eliminate slow, costly live API calls during scans. Tracks data quality and freshness for all watchlist pairs across timeframes, with dashboard visibility and manual refresh controls.

**User-facing outcome:** MTF scans complete in <1 second (was 5-15s), zero API calls during scanning, full visibility into data status.

---

## Data Structure

### `market_data_status` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `pair` | String(20) | Trading pair (e.g., `BTC/USDT`, `XAU/USD`) |
| `timeframe` | String(10) | Timeframe in normalized format (`w1`, `d1`, `h4`, etc.) |
| `candle_count` | Integer | Number of cached candles |
| `last_candle_time` | DateTime | Timestamp of most recent candle |
| `fetched_at` | DateTime | When status was last updated |
| `data_quality` | String(20) | `EXCELLENT`, `GOOD`, `STALE`, `MISSING` |
| `source` | String(20) | Data source (`ccxt`, `twelvedata`, `gateio`) |

**Indexes:** `(pair, timeframe)` unique, `(pair)`, `(data_quality)`

### DataQuality Enum

| Level | Candle Count | Max Age | Use Case |
|-------|--------------|---------|----------|
| `EXCELLENT` | 200+ | < 2× timeframe interval | Full HTF analysis (50/200 SMA) |
| `GOOD` | 100-199 | < 4× timeframe interval | Standard MTF analysis |
| `STALE` | 50-99 | < 24 hours | Limited analysis, refresh soon |
| `MISSING` | < 50 | ≥ 24 hours | Insufficient data |

---

## Logic / Flow

### Quality Assessment

```python
def assess_quality(candle_count, age_hours, timeframe):
    tf_hours = get_timeframe_hours(timeframe)  # h4=4, d1=24, w1=168
    
    if candle_count < 50: return MISSING
    if candle_count < 100: return STALE
    
    if candle_count >= 200 and age_hours < tf_hours * 2:
        return EXCELLENT
    if candle_count >= 100 and age_hours < tf_hours * 4:
        return GOOD
    return STALE
```

### Timeframe Normalization

Handles variations from different data sources:
- `1week`, `1w`, `week` → `w1`
- `1day`, `1d`, `day` → `d1`
- `1hour`, `1h` → `h1`
- `4h`, `2h`, etc. → `h4`, `h2`

### MTF Readiness Check

A pair is "MTF Ready" when ALL required timeframes for a trading style have `GOOD` or `EXCELLENT` quality:

```python
# SWING: requires w1, d1, h4
# INTRADAY: requires d1, h4, h1
mtf_ready = all(q in [GOOD, EXCELLENT] for q in required_timeframe_qualities)
```

---

## Key Design Decisions

### DEC-018: Cache-First Architecture (2026-03-08)

**Decision:** MTF scanner reads ONLY from cache, never makes live API calls during scan.

**Alternatives considered:**
1. Live fetch on cache miss (original behavior) — slow, costly
2. Hybrid: fetch if stale — still blocks scan

**Rationale:**
- Scans should be instant (<1s)
- API calls are costly (Twelve Data: 800/day limit)
- Prefetch job handles cache population asynchronously
- User can explicitly refresh when needed

**Consequences:**
- Scan returns "no data" if cache empty — user must refresh
- Requires separate refresh UI/UX
- Prefetch job becomes critical infrastructure

### DEC-019: Timeframe Normalization (2026-03-08)

**Decision:** Normalize all timeframes to standard format (`w1`, `d1`, `h4`) and merge duplicates.

**Alternatives considered:**
1. Store exact API format — simpler, but creates duplicates
2. Store multiple formats — complex, confusing

**Rationale:**
- Different APIs use different formats (Twelve Data: `1week`, CCXT: `1w`)
- Duplicates cause confusion (same data appears 3×)
- Normalization enables clean UI display

**Consequences:**
- Need migration to clean existing data
- UI must handle both old and new formats during transition

### DEC-020: Quality-Based Prioritization (2026-03-08)

**Decision:** Use 4-tier quality system to drive refresh priority and UI display.

**Rationale:**
- Binary fresh/stale is insufficient
- EXCELLENT (200+ candles) needed for HTF 50/200 SMA analysis
- GOOD (100+) sufficient for standard MTF
- Visual badges (🟢🟡🔴) provide instant status

---

## Open Questions

_None — all resolved during implementation._

---

## Out of Scope

- Real-time price tracking (this is cache metadata, not live data)
- Automatic refresh on staleness (user-triggered only)
- Data retention policies (handled separately)
- Multi-source failover logic (future enhancement)

---

## As Built

_Added after implementation — 2026-03-08_

### What Changed from Design

1. **Added Market Data Status page to dashboard** — not just MTF scanner integration
2. **Bulk refresh endpoint** (`/refresh-all`) — refreshes all stale pairs at once
3. **Watchlist with status endpoint** — combines watchlist + quality for pre-scan check
4. **MTF scanner pre-scan check** — warns user before scanning if data is stale

### Final Data Structure

```python
# src/models/market_data_status_model.py
class MarketDataStatus(Base):
    id, pair, timeframe, candle_count, last_candle_time,
    fetched_at, data_quality, source

# src/services/market_data_service.py
class MarketDataService:
    - get_all_statuses()
    - get_pair_status()
    - update_status()
    - sync_all_statuses()
    - get_mtf_ready_pairs()
    - get_stale_pairs()
```

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `src/models/market_data_status_model.py` | Database model + quality enum | 246 |
| `src/services/market_data_service.py` | Service layer (25+ methods) | 540 |
| `src/api/routes_market_data.py` | 6 REST endpoints | 650 |
| `src/ui_market_data.py` | Dashboard page | 670 |
| `tests/test_market_data/` | 68 tests (model + service + routes) | 800 |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/market-data/status` | All pairs with summary |
| `GET` | `/api/v1/market-data/status/{pair}` | Single pair details |
| `GET` | `/api/v1/market-data/summary` | Summary statistics |
| `POST` | `/api/v1/market-data/refresh` | Refresh specific pair |
| `POST` | `/api/v1/market-data/refresh-all` | Refresh all stale pairs |
| `GET` | `/api/v1/market-data/watchlist` | Watchlist with status |

### Known Limitations

1. **Source tracking is null for synced data** — `sync_all_statuses()` doesn't track which API was used
2. **No automatic refresh** — user must manually trigger or wait for prefetch job
3. **Timeframe format inconsistencies** — old data may have `1w`, `1week`, `w1` for same pair (UI merges these)

### Follow-up Tasks

- [ ] Add source tracking to `sync_all_statuses()` — know which API provided each timeframe
- [ ] Add automatic refresh trigger when quality drops to STALE
- [ ] Add data retention policy — delete candles older than 1 year
- [ ] Add chart preview — show last N candles for each timeframe

---

## Testing

**68 tests passing:**
- 32 model tests (quality assessment, timeframe conversion, CRUD operations)
- 23 service tests (status queries, sync, MTF readiness)
- 13 route tests (endpoint response structures, error handling)

```bash
pytest tests/test_market_data/ -v
# 68 passed
```

---

## Deployment Notes

**Database migration required:**
```bash
python -m src.database init
# Creates market_data_status table automatically
```

**Sync existing cache:**
```python
from src.services.market_data_service import MarketDataService
service = MarketDataService(db)
service.sync_all_statuses()  # Populates status from OHLCV cache
```

**Cleanup old format timeframes (if needed):**
```python
# Delete duplicate formats: 1w, 1week, 1d, 1h, 4h
# Keep normalized: w1, d1, h4, h1
```
