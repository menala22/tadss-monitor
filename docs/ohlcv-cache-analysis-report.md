# OHLCV Cache Data Analysis Report

**Date:** 2026-03-08  
**Database:** `positions-vm-backup.db` (844KB)  
**Analyst:** AI Agent  
**Purpose:** Identify data quality issues and improvement opportunities

---

## Executive Summary

### Current State
- **Total Candles:** 3,235
- **Unique Symbols:** 7 (4 watchlist + 3 duplicates/variations)
- **Timeframes:** 6 distinct formats
- **Date Range:** May 2021 → March 2026 (1,746 days)
- **MTF Ready:** 3/4 watchlist pairs (75%)

### Critical Issues Found

| Issue | Severity | Impact |
|-------|----------|--------|
| **Duplicate timeframe formats** | 🔴 HIGH | `1w`, `1week`, `1wk` all exist for same pair |
| **Duplicate symbol formats** | 🔴 HIGH | `XAU/USD` and `XAUUSD` both exist |
| **Missing ETH/USDT daily data** | 🔴 HIGH | No `1d` data for ETH/USDT (MTF scans fail) |
| **Stale 4h/1h data** | 🟡 MEDIUM | All 4h and 1h data marked STALE (>12h old) |
| **No market_data_status table** | 🟡 MEDIUM | Cannot track quality programmatically |

---

## 1. Data Overview

### Overall Statistics

| Metric | Value |
|--------|-------|
| Total Candles | 3,235 |
| Unique Symbols | 7 |
| Unique Timeframes | 6 |
| Oldest Candle | 2021-05-27 00:00:00 |
| Newest Candle | 2026-03-07 18:00:00 |
| Date Range | 1,745.8 days (4.8 years) |

### Data Distribution by Symbol

| Symbol | Candles | Timeframes | Oldest | Newest | Span (hours) |
|--------|---------|------------|--------|--------|--------------|
| **XAU/USD** | 1,100 | 6 | 2025-06-15 | 2026-03-07 | 6,360 |
| **BTC/USDT** | 750 | 4 | 2021-05-27 | 2026-03-07 | 41,896 |
| **ETH/USDT** | 500 | 2 | 2021-05-27 | 2026-03-05 | 41,832 |
| **XAG/USD** | 265 | 5 | 2026-01-14 | 2026-03-07 | 1,248 |
| **XAUUSD** | 243 | 3 | 2025-11-27 | 2026-03-07 | 2,400 |
| **ETHUSD** | 219 | 2 | 2026-02-18 | 2026-03-07 | 418 |
| **XAGUSD** | 158 | 2 | 2026-01-14 | 2026-03-07 | 1,264 |

**⚠️ Issue:** Symbol format inconsistency
- `XAU/USD` (1,100 candles) vs `XAUUSD` (243 candles)
- `ETH/USDT` (500 candles) vs `ETHUSD` (219 candles)
- `XAG/USD` (265 candles) vs `XAGUSD` (158 candles)

**Recommendation:** Standardize to slash format (`XAU/USD`, `ETH/USDT`, `XAG/USD`)

---

## 2. Timeframe Format Issues

### Current Timeframe Formats

| Timeframe | Candles | Symbols Covered | Format Type |
|-----------|---------|-----------------|-------------|
| `1week` | 803 | 4 | Twelve Data |
| `1w` | 803 | 4 | CCXT |
| `1wk` | 250 | 1 | Gate.io? |
| `1d` | 449 | 5 | Universal |
| `4h` | 563 | 6 | Universal |
| `1h` | 367 | 4 | Universal |

### Duplicate Timeframe Formats per Symbol

| Symbol | Timeframe Variations | Count |
|--------|---------------------|-------|
| **XAU/USD** | `1d`, `1h`, `1w`, `1week`, `1wk`, `4h` | 6 ⚠️ |
| **XAG/USD** | `1d`, `1h`, `1w`, `1week`, `4h` | 5 ⚠️ |
| **BTC/USDT** | `1d`, `1w`, `1week`, `4h` | 4 ⚠️ |
| **ETH/USDT** | `1w`, `1week` | 2 ⚠️ |

**🔴 Critical Issue:** Same data stored 3× for weekly timeframes!

**Example:**
```
BTC/USDT weekly data:
- 1w:   250 candles (2021-05-27 → 2026-03-05)
- 1week: 250 candles (2021-05-27 → 2026-03-05) ← DUPLICATE
- 1wk:  250 candles (2025-06-15 → 2026-03-07) ← Different source
```

**Recommendation:** 
1. Normalize all to internal format (`w1`, `d1`, `h4`, `h1`)
2. Merge duplicates (keep newest/highest count)
3. Enforce single format on write

---

## 3. Data Freshness Analysis

### Freshness by Symbol/Timeframe

| Symbol | TF | Candles | Newest Candle | Hours Old | Status |
|--------|----|---------|---------------|-----------|--------|
| **BTC/USDT** | 1w/1week | 500 | 2026-03-05 | 77.8 | 🟢 FRESH |
| **ETH/USDT** | 1w/1week | 500 | 2026-03-05 | 77.8 | 🟢 FRESH |
| **XAU/USD** | 1w/1week/1wk | 750 | 2026-03-07 | 29.8 | 🟢 FRESH |
| **XAG/USD** | 1w/1week | 106 | 2026-03-07 | 29.8 | 🟢 FRESH |
| **BTC/USDT** | 1d | 150 | 2026-03-07 | 29.8 | 🟢 FRESH |
| **XAU/USD** | 1d | 150 | 2026-03-07 | 29.8 | 🟢 FRESH |
| **XAG/USD** | 1d | 53 | 2026-03-07 | 29.8 | 🟢 FRESH |
| **BTC/USDT** | 4h | 100 | 2026-03-07 16:00 | 13.8 | 🟡 STALE |
| **XAU/USD** | 4h | 100 | 2026-03-07 00:00 | 29.8 | 🟡 STALE |
| **XAG/USD** | 4h | 53 | 2026-03-07 00:00 | 29.8 | 🟡 STALE |
| **XAU/USD** | 1h | 100 | 2026-03-07 00:00 | 29.8 | 🟡 STALE |
| **XAG/USD** | 1h | 53 | 2026-03-07 00:00 | 29.8 | 🟡 STALE |

**Staleness Thresholds Used:**
- `1h`: 4 hours
- `4h`: 12 hours
- `1d`: 48 hours
- `1w`: 240 hours (10 days)

**🟡 Issue:** All 4h and 1h data is stale (last fetch was >12h ago)

**Recommendation:** 
- Prefetch job should run every 2-4 hours for intraday timeframes
- Daily prefetch sufficient for `1d` and `1w`

---

## 4. MTF Readiness Check

### SWING Style Requirements (w1 + d1 + h4)

| Symbol | w1 | d1 | h4 | MTF Status |
|--------|----|----|----|------------|
| **BTC/USDT** | ✅ 500 | ✅ 150 | ✅ 100 | ✅ READY |
| **XAU/USD** | ✅ 750 | ✅ 150 | ✅ 100 | ✅ READY |
| **XAG/USD** | ✅ 106 | ✅ 53 | ✅ 53 | ✅ READY |
| **ETH/USDT** | ✅ 500 | ❌ 0 | ❌ 0 | ❌ NOT READY |

**🔴 Critical Issue:** ETH/USDT missing daily and 4h data!

**Impact:** MTF scanner will fail for ETH/USDT with "no data" error.

**Recommendation:** 
1. Immediately fetch `1d` and `4h` data for ETH/USDT
2. Add data validation before MTF scans

---

## 5. Data Quality Issues

### NULL/Zero Value Check

✅ **No NULL or zero values found** — data quality is good.

### Duplicate Candle Check

✅ **No exact duplicates** (same symbol/timeframe/timestamp) found.

---

## 6. Gaps Analysis (Recent 7 Days)

### Missing Candles in Recent Week

| Symbol | TF | Expected | Actual | Missing |
|--------|----|----------|--------|---------|
| **ETHUSD** | 1h | 168 | 114 | 54 ⚠️ |
| **XAUUSD** | 1h | 168 | 5 | 163 🔴 |
| **XAU/USD** | 1h | 168 | 6 | 162 🔴 |
| **XAG/USD** | 1h | 168 | 6 | 162 🔴 |
| **XAUUSD** | 4h | 42 | 5 | 37 🔴 |
| **XAU/USD** | 4h | 42 | 6 | 36 🔴 |
| **XAG/USD** | 4h | 42 | 6 | 36 🔴 |
| **BTC/USDT** | 4h | 42 | 39 | 3 🟡 |
| **BTC/USDT** | 1d | 7 | 6 | 1 🟡 |
| **XAU/USD** | 1d | 7 | 6 | 1 🟡 |

**🔴 Critical Issue:** Massive gaps in 1h and 4h data for XAU/USD, XAG/USD, XAUUSD

**Root Cause:** 
- Prefetch job not running frequently enough (should be every 2-4h for intraday)
- Some symbols (`XAUUSD` without slash) may not be in watchlist

**Recommendation:**
1. Increase prefetch frequency for intraday timeframes (every 2-4h)
2. Standardize symbol format (use slash consistently)
3. Add gap detection to prefetch job

---

## 7. Schema Issues

### Missing Tables

| Table | Status | Purpose |
|-------|--------|---------|
| `ohlcv_cache` | ✅ Exists | Current cache table |
| `mtf_watchlist` | ✅ Exists | MTF scanner watchlist |
| `market_data_status` | ❌ **MISSING** | Quality tracking metadata |
| `ohlcv_universal` | ❌ Not created | Proposed single source of truth |

**🟡 Issue:** No `market_data_status` table on VM

**Impact:** Cannot track data quality programmatically, no MTF readiness checks.

**Recommendation:** 
1. Deploy `market_data_status` table to VM
2. Populate from existing `ohlcv_cache`
3. Implement quality assessment logic

---

## 8. Symbol Format Inconsistency

### Current Symbol Formats

| Base Asset | Format 1 | Format 2 | Total Candles |
|------------|----------|----------|---------------|
| **Gold** | XAU/USD (1,100) | XAUUSD (243) | 1,343 |
| **Silver** | XAG/USD (265) | XAGUSD (158) | 423 |
| **Ethereum** | ETH/USDT (500) | ETHUSD (219) | 719 |

**🔴 Critical Issue:** Same asset, different formats = fragmented data

**Root Cause:**
- Twelve Data returns `XAU/USD`
- Gate.io returns `XAGUSD`
- CCXT returns `ETH/USDT` or `ETHUSD` depending on exchange

**Recommendation:**
1. Normalize all symbols to slash format on write
2. Create mapping table for provider-specific formats
3. Migrate existing data to standard format

---

## 9. Storage Efficiency

### Current Storage

| Table | Rows | Estimated Size |
|-------|------|----------------|
| `ohlcv_cache` | 3,235 | ~600KB |
| `positions` | 9 | ~10KB |
| `mtf_watchlist` | 4 | ~1KB |
| `alert_history` | 40 | ~20KB |
| `signal_changes` | 24 | ~10KB |
| **Total** | 3,312 | **~844KB** |

### Duplicate Data Waste

| Duplicate Type | Rows Wasted | Estimated Waste |
|----------------|-------------|-----------------|
| `1w` vs `1week` (BTC, ETH, XAU, XAG) | ~1,000 | ~180KB |
| `XAU/USD` vs `XAUUSD` | 243 | ~40KB |
| `ETH/USDT` vs `ETHUSD` | 219 | ~35KB |
| **Total Waste** | ~1,462 | **~255KB (30%)** |

**💰 Potential Savings:** 30% storage reduction after deduplication

---

## 10. Recommendations Summary

### Priority 1: Critical (Fix This Week)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1.1 | **Fetch ETH/USDT `1d` and `4h` data** | MTF scans work for ETH | 10 min |
| 1.2 | **Deploy `market_data_status` table** | Quality tracking enabled | 30 min |
| 1.3 | **Normalize timeframe formats** (`1w`, `1week`, `1wk` → `w1`) | 30% storage savings | 1 hour |
| 1.4 | **Normalize symbol formats** (`XAUUSD` → `XAU/USD`) | Consistent queries | 1 hour |

### Priority 2: High (Fix This Month)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 2.1 | **Implement prefetch scheduler** (every 2h at :20) | Fresh intraday data | 2 hours |
| 2.2 | **Add gap detection logic** | Catch missing candles early | 1 hour |
| 2.3 | **Create `ohlcv_universal` table** | Single source of truth | 2 hours |
| 2.4 | **Migrate consumers to read-only** | Zero live API calls | 4 hours |

### Priority 3: Medium (Next Quarter)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 3.1 | **Add data retention policy** (delete >1 year) | Reduce DB size | 1 hour |
| 3.2 | **Implement provider routing** | Cost optimization | 2 hours |
| 3.3 | **Add quality assessment automation** | Auto staleness detection | 2 hours |
| 3.4 | **Build dashboard for data status** | Visibility into cache health | 4 hours |

---

## 11. Migration Script (Priority 1.3 + 1.4)

```sql
-- Step 1: Normalize timeframe formats
UPDATE ohlcv_cache SET timeframe = 'w1' WHERE timeframe IN ('1w', '1week', '1wk');
UPDATE ohlcv_cache SET timeframe = 'd1' WHERE timeframe = '1d';
UPDATE ohlcv_cache SET timeframe = 'h4' WHERE timeframe = '4h';
UPDATE ohlcv_cache SET timeframe = 'h1' WHERE timeframe = '1h';

-- Step 2: Normalize symbol formats
UPDATE ohlcv_cache SET symbol = 'XAU/USD' WHERE symbol = 'XAUUSD';
UPDATE ohlcv_cache SET symbol = 'XAG/USD' WHERE symbol = 'XAGUSD';
UPDATE ohlcv_cache SET symbol = 'ETH/USDT' WHERE symbol = 'ETHUSD';

-- Step 3: Remove duplicates (keep newest fetched_at)
DELETE FROM ohlcv_cache 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM ohlcv_cache 
    GROUP BY symbol, timeframe, timestamp
);

-- Step 4: Create market_data_status table
CREATE TABLE IF NOT EXISTS market_data_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    candle_count INTEGER NOT NULL DEFAULT 0,
    last_candle_time DATETIME,
    fetched_at DATETIME NOT NULL,
    data_quality VARCHAR(20) NOT NULL,
    provider VARCHAR(20),
    UNIQUE(symbol, timeframe)
);

-- Step 5: Populate market_data_status from ohlcv_cache
INSERT OR REPLACE INTO market_data_status (symbol, timeframe, candle_count, last_candle_time, fetched_at, data_quality)
SELECT 
    symbol,
    timeframe,
    COUNT(*) as candle_count,
    MAX(timestamp) as last_candle_time,
    datetime('now') as fetched_at,
    CASE 
        WHEN COUNT(*) >= 200 THEN 'EXCELLENT'
        WHEN COUNT(*) >= 100 THEN 'GOOD'
        WHEN COUNT(*) >= 50 THEN 'STALE'
        ELSE 'MISSING'
    END as data_quality
FROM ohlcv_cache
GROUP BY symbol, timeframe;
```

---

## 12. Next Steps

1. **Review this report** and approve recommendations
2. **Run migration script** (Priority 1.3 + 1.4)
3. **Fetch missing ETH/USDT data** (Priority 1.1)
4. **Deploy `market_data_status` table** (Priority 1.2)
5. **Implement prefetch scheduler** (Priority 2.1)
6. **Monitor data freshness** via new status table

---

**Report Generated:** 2026-03-08 12:38 UTC  
**Database Analyzed:** `positions-vm-backup.db`  
**Contact:** AI Agent
