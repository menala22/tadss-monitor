# Database Structure & Query Guide

**Trading Order Monitoring System**
*Last Updated: March 8, 2026*

---

## Table of Contents

1. [Overview](#overview)
2. [Database Location](#database-location)
3. [Table Schemas](#table-schemas)
   - [positions](#positions-table)
   - [alert_history](#alert_history-table)
   - [signal_changes](#signal_changes-table)
   - [ohlcv_cache](#ohlcv_cache-table)
   - [mtf_watchlist](#mtf_watchlist-table)
   - [market_data_status](#market_data_status-table)
4. [Entity Relationship Diagram](#entity-relationship-diagram)
5. [Common Queries](#common-queries)
6. [Python ORM Usage](#python-orm-usage)
7. [Database Migrations](#database-migrations)
8. [Best Practices](#best-practices)
9. [Related Documentation](#related-documentation)

---

## Overview

The Trading Order Monitoring System uses **SQLite** as its primary database for storing:
- Trading positions (open and closed)
- Alert history for audit trail and analysis
- Signal changes for MA10, OTT, and overall status tracking
- OHLCV cache for market data (reduces API calls)
- MTF watchlist for multi-timeframe scanner
- Market data status for tracking data quality

The system also supports **PostgreSQL** for production deployments via configuration.

### Key Features
- **Write-Ahead Logging (WAL)** for better concurrency
- **Foreign key constraints** enabled
- **Automatic connection pooling**
- **Indexed columns** for efficient querying

---

## Database Location

| Environment | Database URL | File Path |
|-------------|--------------|-----------|
| Development | `sqlite:///./data/positions.db` | `data/positions.db` |
| Production | Configured via `.env` | PostgreSQL or custom SQLite path |

### Access the Database

```bash
# Navigate to project directory
cd /path/to/trading-order-monitoring-system

# Open SQLite CLI
sqlite3 data/positions.db

# List all tables
.tables

# Show schema
.schema

# Exit
.exit
```

---

## Table Schemas

### positions Table

Stores all trading positions tracked by the monitoring system.

#### Schema

```sql
CREATE TABLE positions (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    pair                        VARCHAR(20) NOT NULL,
    entry_price                 FLOAT NOT NULL,
    entry_time                  DATETIME NOT NULL,
    position_type               VARCHAR(5) NOT NULL,  -- 'LONG' or 'SHORT'
    timeframe                   VARCHAR(10) NOT NULL, -- e.g., 'h4', 'd1'
    status                      VARCHAR(6) NOT NULL,  -- 'OPEN' or 'CLOSED'
    close_price                 FLOAT,
    close_time                  DATETIME,
    last_signal_status          VARCHAR(20),
    last_ma10_status            VARCHAR(20),
    last_ott_status             VARCHAR(20),
    last_important_indicators   VARCHAR(50),  -- DEPRECATED
    last_checked_at             DATETIME,
    created_at                  DATETIME NOT NULL,
    updated_at                  DATETIME NOT NULL
);

CREATE INDEX ix_positions_pair ON positions (pair);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `pair` | VARCHAR(20) | NO | Trading pair symbol (e.g., 'BTCUSD', 'ETH/USDT') |
| `entry_price` | FLOAT | NO | Price at which position was opened |
| `entry_time` | DATETIME | NO | Timestamp when position was opened |
| `position_type` | VARCHAR(5) | NO | Direction: `LONG` or `SHORT` |
| `timeframe` | VARCHAR(10) | NO | Analysis timeframe (e.g., 'h4', 'd1', 'w1') |
| `status` | VARCHAR(6) | NO | Current status: `OPEN` or `CLOSED` |
| `close_price` | FLOAT | YES | Price at which position was closed |
| `close_time` | DATETIME | YES | Timestamp when position was closed |
| `last_signal_status` | VARCHAR(20) | YES | Last overall signal status |
| `last_ma10_status` | VARCHAR(20) | YES | Last MA10 indicator status |
| `last_ott_status` | VARCHAR(20) | YES | Last OTT indicator status |
| `last_important_indicators` | VARCHAR(50) | YES | DEPRECATED - kept for compatibility |
| `last_checked_at` | DATETIME | YES | Timestamp of last analysis check |
| `created_at` | DATETIME | NO | Record creation timestamp |
| `updated_at` | DATETIME | NO | Record last update timestamp |

#### Enum Values

**position_type:**
- `LONG` - Bullish position (profit when price increases)
- `SHORT` - Bearish position (profit when price decreases)

**status:**
- `OPEN` - Position is currently active
- `CLOSED` - Position has been closed

**Signal statuses (last_signal_status, last_ma10_status, last_ott_status):**
- `BULLISH` - Bullish signal
- `BEARISH` - Bearish signal
- `NEUTRAL` - Neutral signal
- `OVERBOUGHT` - Overbought condition (warning)
- `OVERSOLD` - Oversold condition (warning)

---

### alert_history Table

Stores audit trail of all alerts sent by the monitoring system.

#### Schema

```sql
CREATE TABLE alert_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           DATETIME NOT NULL,
    pair                VARCHAR(20),
    alert_type          VARCHAR(15) NOT NULL,
    status              VARCHAR(7) NOT NULL,
    previous_status     VARCHAR(20),
    current_status      VARCHAR(20) NOT NULL,
    reason              VARCHAR(100) NOT NULL,
    message             TEXT NOT NULL,
    price_movement_pct  FLOAT,
    error_message       TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    created_at          DATETIME NOT NULL
);

CREATE INDEX ix_alert_history_timestamp ON alert_history (timestamp);
CREATE INDEX ix_alert_history_pair ON alert_history (pair);
CREATE INDEX ix_alert_history_status_timestamp ON alert_history (status, timestamp);
CREATE INDEX ix_alert_history_type_timestamp ON alert_history (alert_type, timestamp);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `timestamp` | DATETIME | NO | When the alert was generated |
| `pair` | VARCHAR(20) | YES | Trading pair symbol (nullable for system alerts) |
| `alert_type` | VARCHAR(15) | NO | Type of alert (see enum below) |
| `status` | VARCHAR(7) | NO | Delivery status (see enum below) |
| `previous_status` | VARCHAR(20) | YES | Status before the change |
| `current_status` | VARCHAR(20) | NO | Current status that triggered alert |
| `reason` | VARCHAR(100) | NO | Reason for triggering this alert |
| `message` | TEXT | NO | Full alert message sent to Telegram |
| `price_movement_pct` | FLOAT | YES | Price movement percentage if applicable |
| `error_message` | TEXT | YES | Error details if delivery failed |
| `retry_count` | INTEGER | NO | Number of retry attempts (default: 0) |
| `created_at` | DATETIME | NO | Record creation timestamp |

#### Enum Values

**alert_type:**
- `POSITION_HEALTH` - General position health alert
- `PRICE_MOVEMENT` - Significant price movement (>5%)
- `SIGNAL_CHANGE` - Signal status changed (e.g., BULLISH → BEARISH)
- `DAILY_SUMMARY` - Daily summary report
- `SYSTEM_ERROR` - System error notification
- `CUSTOM` - Custom message

**status:**
- `SENT` - Alert successfully delivered
- `FAILED` - Alert delivery failed
- `PENDING` - Alert pending delivery
- `SKIPPED` - Alert skipped (anti-spam logic)

---

### signal_changes Table

Stores detailed tracking of all signal status changes (MA10, OTT, Overall) for historical analysis and backtesting.

#### Schema

```sql
CREATE TABLE signal_changes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           DATETIME NOT NULL,
    pair                VARCHAR(20) NOT NULL,
    timeframe           VARCHAR(10) NOT NULL,
    signal_type         VARCHAR(7) NOT NULL,
    previous_status     VARCHAR(20) NOT NULL,
    current_status      VARCHAR(20) NOT NULL,
    price_at_change     FLOAT,
    price_movement_pct  FLOAT,
    position_type       VARCHAR(5),
    triggered_alert     INTEGER NOT NULL DEFAULT 0,
    extra_data          TEXT,
    created_at          DATETIME NOT NULL
);

CREATE INDEX ix_signal_changes_timestamp ON signal_changes (timestamp);
CREATE INDEX ix_signal_changes_pair ON signal_changes (pair);
CREATE INDEX ix_signal_changes_timeframe ON signal_changes (timeframe);
CREATE INDEX ix_signal_changes_signal_type ON signal_changes (signal_type);
CREATE INDEX ix_signal_changes_pair_signal ON signal_changes (pair, signal_type);
CREATE INDEX ix_signal_changes_pair_timeframe ON signal_changes (pair, timeframe);
CREATE INDEX ix_signal_changes_timestamp_pair ON signal_changes (timestamp, pair);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `timestamp` | DATETIME | NO | When the signal change occurred |
| `pair` | VARCHAR(20) | NO | Trading pair symbol (e.g., 'BTC/USDT', 'ETHUSD') |
| `timeframe` | VARCHAR(10) | NO | Analysis timeframe (e.g., 'h1', 'h4', 'd1') |
| `signal_type` | VARCHAR(7) | NO | Type of signal (see enum below) |
| `previous_status` | VARCHAR(20) | NO | Status before the change |
| `current_status` | VARCHAR(20) | NO | Status after the change |
| `price_at_change` | FLOAT | YES | Price when the signal changed |
| `price_movement_pct` | FLOAT | YES | PnL percentage at time of change |
| `position_type` | VARCHAR(5) | YES | Position direction: `LONG` or `SHORT` |
| `triggered_alert` | INTEGER | NO | 1 if alert was triggered, 0 otherwise |
| `extra_data` | TEXT | YES | Additional JSON metadata |
| `created_at` | DATETIME | NO | Record creation timestamp |

#### Enum Values

**signal_type:**
- `MA10` - 10-period Moving Average
- `MA20` - 20-period Moving Average
- `MA50` - 50-period Moving Average
- `OTT` - Optimized Trend Trader
- `MACD` - Moving Average Convergence Divergence
- `RSI` - Relative Strength Index
- `OVERALL` - Overall signal status (majority vote)

**Signal status values:**
- `BULLISH` - Bullish signal
- `BEARISH` - Bearish signal
- `NEUTRAL` - Neutral signal
- `OVERBOUGHT` - Overbought condition
- `OVERSOLD` - Oversold condition

---

### ohlcv_cache Table

Stores cached OHLCV (candlestick) data to reduce API calls. Populated by DataFetcher when fetching live data.

#### Schema

```sql
CREATE TABLE ohlcv_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      VARCHAR(20) NOT NULL,
    timeframe   VARCHAR(10) NOT NULL,
    timestamp   DATETIME NOT NULL,
    open        FLOAT NOT NULL,
    high        FLOAT NOT NULL,
    low         FLOAT NOT NULL,
    close       FLOAT NOT NULL,
    volume      FLOAT,
    fetched_at  DATETIME NOT NULL
);

CREATE UNIQUE INDEX uq_symbol_timeframe_timestamp ON ohlcv_cache (symbol, timeframe, timestamp);
CREATE INDEX idx_symbol_timeframe ON ohlcv_cache (symbol, timeframe);
CREATE INDEX idx_timestamp ON ohlcv_cache (timestamp);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `symbol` | VARCHAR(20) | NO | Trading pair symbol (e.g., 'BTC/USDT', 'XAU/USD') |
| `timeframe` | VARCHAR(10) | NO | Timeframe in API format (e.g., '1d', '4h', '1week') |
| `timestamp` | DATETIME | NO | Candle open time (UTC) |
| `open` | FLOAT | NO | Opening price |
| `high` | FLOAT | NO | Highest price |
| `low` | FLOAT | NO | Lowest price |
| `close` | FLOAT | NO | Closing price |
| `volume` | FLOAT | YES | Trading volume (may be 0 for forex/metals) |
| `fetched_at` | DATETIME | NO | When this candle was first fetched from API |

#### Usage Notes

- **Unique constraint**: Prevents duplicate candles for same symbol/timeframe/timestamp
- **Incremental fetch**: DataFetcher checks cache before API calls, fetches only missing candles
- **Multi-timeframe**: Cache supports MTF analysis by storing multiple timeframes per symbol
- **Data sources**: Twelve Data, CCXT, Gate.io, yfinance (see `src/data_fetcher.py`)

---

### mtf_watchlist Table

Stores the list of trading pairs scanned by the MTF opportunity scanner.

#### Schema

```sql
CREATE TABLE mtf_watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pair        VARCHAR(20) NOT NULL UNIQUE,
    added_at    DATETIME NOT NULL,
    notes       VARCHAR(255)
);

CREATE INDEX idx_mtf_watchlist_pair ON mtf_watchlist (pair);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `pair` | VARCHAR(20) | NO | Trading pair symbol (e.g., 'BTC/USDT', 'ETH/USDT') |
| `added_at` | DATETIME | NO | When the pair was added to watchlist |
| `notes` | VARCHAR(255) | YES | Optional notes about the pair |

#### Default Watchlist

Auto-seeded on first run:
- `BTC/USDT` - Bitcoin
- `ETH/USDT` - Ethereum
- `XAU/USD` - Gold
- `XAG/USD` - Silver

#### Usage Notes

- **CRUD operations**: GET/POST/DELETE endpoints in `src/api/routes_mtf.py`
- **Dashboard management**: Add/remove pairs via UI (`src/ui_mtf_scanner.py`)
- **MTF scanner**: Uses watchlist to determine which pairs to scan

---

### market_data_status Table

Tracks data quality and freshness for cached market data. Used by Market Data Status dashboard.

#### Schema

```sql
CREATE TABLE market_data_status (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pair                VARCHAR(20) NOT NULL,
    timeframe           VARCHAR(10) NOT NULL,
    candle_count        INTEGER NOT NULL DEFAULT 0,
    last_candle_time    DATETIME,
    fetched_at          DATETIME NOT NULL,
    data_quality        VARCHAR(20) NOT NULL,
    source              VARCHAR(20),
    UNIQUE (pair, timeframe)
);

CREATE INDEX idx_pair_timeframe ON market_data_status (pair, timeframe);
CREATE INDEX idx_pair ON market_data_status (pair);
CREATE INDEX idx_data_quality ON market_data_status (data_quality);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-increment |
| `pair` | VARCHAR(20) | NO | Trading pair symbol |
| `timeframe` | VARCHAR(10) | NO | Timeframe in normalized format (`w1`, `d1`, `h4`) |
| `candle_count` | INTEGER | NO | Number of cached candles |
| `last_candle_time` | DATETIME | YES | Timestamp of most recent candle |
| `fetched_at` | DATETIME | NO | When this status was last updated |
| `data_quality` | VARCHAR(20) | NO | Quality level (see enum below) |
| `source` | VARCHAR(20) | YES | Data source (`ccxt`, `twelvedata`, `gateio`) |

#### Enum Values

**data_quality:**
- `EXCELLENT` - 200+ candles, age < 2× timeframe interval (full HTF analysis)
- `GOOD` - 100+ candles, age < 4× timeframe interval (standard analysis)
- `STALE` - 50-99 candles OR age < 24 hours (refresh recommended)
- `MISSING` - <50 candles OR age ≥ 24 hours (refresh required)

#### Quality Assessment Logic

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

#### Usage Notes

- **Sync with cache**: `MarketDataService.sync_all_statuses()` populates from OHLCV cache
- **MTF readiness**: Pair is "MTF Ready" when all required timeframes have GOOD+ quality
- **Dashboard**: Shows quality badges (🟢🟡🔴) and refresh controls
- **Prefetch job**: Prioritizes STALE/MISSING pairs for refresh

---

## Entity Relationship Diagram

```
┌─────────────────────────┐
│       positions         │
├─────────────────────────┤
│ PK  id                  │
│     pair ───────────────┼──┬──────────────┐
│     entry_price         │  │              │
│     entry_time          │  │              │
│     position_type       │  │              │
│     timeframe           │  │              │
│     status              │  │              │
│     close_price         │  │              │
│     close_time          │  │              │
│     last_signal_status  │  │              │
│     last_ma10_status    │  │              │
│     last_ott_status     │  │              │
│     last_checked_at     │  │              │
│     created_at          │  │              │
│     updated_at          │  │              │
└─────────────────────────┘  │              │
                             │              │
                             │ (logical)    │ (logical)
                             │              │
                             ▼              ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│     alert_history       │  │    signal_changes       │
├─────────────────────────┤  ├─────────────────────────┤
│ PK  id                  │  │ PK  id                  │
│     timestamp           │  │     timestamp           │
│     pair ───────────────┼──┤     pair ───────────────┼──┐
│     alert_type          │  │     timeframe           │  │
│     status              │  │     signal_type         │  │
│     previous_status     │  │     previous_status     │  │
│     current_status      │  │     current_status      │  │
│     reason              │  │     price_at_change     │  │
│     message             │  │     price_movement_pct  │  │
│     price_movement_pct  │  │     position_type       │  │
│     error_message       │  │     triggered_alert     │  │
│     retry_count         │  │     extra_data          │  │
│     created_at          │  │     created_at          │  │
└─────────────────────────┘  └─────────────────────────┘

┌─────────────────────────┐
│     ohlcv_cache         │
├─────────────────────────┤
│ PK  id                  │
│     symbol              │
│     timeframe           │
│     timestamp           │
│     open/high/low/close │
│     volume              │
│     fetched_at          │
└─────────────────────────┘

┌─────────────────────────┐
│    mtf_watchlist        │
├─────────────────────────┤
│ PK  id                  │
│     pair (unique)       │
│     added_at            │
│     notes               │
└─────────────────────────┘

┌─────────────────────────┐
│  market_data_status     │
├─────────────────────────┤
│ PK  id                  │
│     pair                │
│     timeframe           │
│     candle_count        │
│     last_candle_time    │
│     fetched_at          │
│     data_quality        │
│     source              │
└─────────────────────────┘
```

**Note:** There is no foreign key constraint between `alert_history.pair`/`signal_changes.pair` and `positions.pair`. The relationships are logical, allowing tracking of signals and alerts for pairs that may no longer have active positions.

The `ohlcv_cache`, `mtf_watchlist`, and `market_data_status` tables are independent and used by the MTF scanner and market data caching system.

---

## Common Queries

### Positions Queries

#### 1. Get All Open Positions

```sql
SELECT 
    id,
    pair,
    position_type,
    entry_price,
    entry_time,
    timeframe,
    last_checked_at
FROM positions
WHERE status = 'OPEN'
ORDER BY entry_time DESC;
```

#### 2. Get Position History for a Specific Pair

```sql
SELECT 
    id,
    position_type,
    entry_price,
    close_price,
    entry_time,
    close_time,
    status,
    CASE 
        WHEN position_type = 'LONG' THEN close_price - entry_price
        ELSE entry_price - close_price
    END as pnl
FROM positions
WHERE pair = 'BTCUSD'
ORDER BY entry_time DESC;
```

#### 3. Calculate Win Rate

```sql
SELECT 
    COUNT(*) as total_positions,
    SUM(CASE WHEN 
        (position_type = 'LONG' AND close_price > entry_price) OR
        (position_type = 'SHORT' AND close_price < entry_price)
        THEN 1 ELSE 0 END) as winning_positions,
    ROUND(
        100.0 * SUM(CASE WHEN 
            (position_type = 'LONG' AND close_price > entry_price) OR
            (position_type = 'SHORT' AND close_price < entry_price)
            THEN 1 ELSE 0 END) / COUNT(*), 
        2
    ) as win_rate_pct
FROM positions
WHERE status = 'CLOSED';
```

#### 4. Get Positions by Timeframe

```sql
SELECT 
    timeframe,
    COUNT(*) as position_count,
    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count,
    SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_count
FROM positions
GROUP BY timeframe
ORDER BY position_count DESC;
```

#### 5. Get Average Position Duration

```sql
SELECT 
    AVG(julianday(close_time) - julianday(entry_time)) as avg_duration_days,
    MIN(julianday(close_time) - julianday(entry_time)) as min_duration_days,
    MAX(julianday(close_time) - julianday(entry_time)) as max_duration_days
FROM positions
WHERE status = 'CLOSED' 
  AND close_time IS NOT NULL;
```

#### 6. Get Positions with Stale Checks

```sql
SELECT 
    id,
    pair,
    position_type,
    last_checked_at,
    datetime('now') as current_time,
    ROUND((julianday('now') - julianday(last_checked_at)) * 24, 2) as hours_since_check
FROM positions
WHERE status = 'OPEN'
  AND (
    last_checked_at IS NULL 
    OR julianday('now') - julianday(last_checked_at) > 0.0417  -- 1 hour
  )
ORDER BY last_checked_at ASC;
```

---

### Alert History Queries

#### 1. Get Recent Alerts

```sql
SELECT 
    id,
    datetime(timestamp) as alert_time,
    pair,
    alert_type,
    status,
    reason
FROM alert_history
ORDER BY timestamp DESC
LIMIT 20;
```

#### 2. Get Alert Statistics by Type

```sql
SELECT 
    alert_type,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent_count,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
    SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) as skipped_count,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) / COUNT(*), 
        2
    ) as success_rate_pct
FROM alert_history
GROUP BY alert_type
ORDER BY total_alerts DESC;
```

#### 3. Get Alerts by Pair

```sql
SELECT 
    pair,
    COUNT(*) as alert_count,
    MAX(timestamp) as last_alert,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count
FROM alert_history
WHERE pair IS NOT NULL
GROUP BY pair
ORDER BY alert_count DESC;
```

#### 4. Get Failed Alerts with Errors

```sql
SELECT 
    id,
    datetime(timestamp) as alert_time,
    pair,
    alert_type,
    reason,
    error_message
FROM alert_history
WHERE status = 'FAILED'
ORDER BY timestamp DESC
LIMIT 50;
```

#### 5. Get Daily Alert Volume

```sql
SELECT 
    date(timestamp) as alert_date,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent,
    SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) as skipped,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
FROM alert_history
GROUP BY date(timestamp)
ORDER BY alert_date DESC
LIMIT 30;
```

#### 6. Get Alerts with Significant Price Movement

```sql
SELECT 
    id,
    datetime(timestamp) as alert_time,
    pair,
    alert_type,
    price_movement_pct,
    reason,
    status
FROM alert_history
WHERE price_movement_pct IS NOT NULL
  AND ABS(price_movement_pct) > 5.0
ORDER BY ABS(price_movement_pct) DESC;
```

#### 7. Check Alert Frequency (Anti-Spam Analysis)

```sql
SELECT 
    pair,
    date(timestamp) as alert_date,
    COUNT(*) as alerts_sent,
    SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) as alerts_skipped
FROM alert_history
WHERE pair IS NOT NULL
GROUP BY pair, date(timestamp)
HAVING alerts_sent > 5  -- More than 5 alerts per day
ORDER BY alerts_sent DESC;
```

---

### Combined Queries (Positions + Alerts)

#### 1. Get Open Positions with Their Last Alert

```sql
SELECT 
    p.id as position_id,
    p.pair,
    p.position_type,
    p.entry_price,
    p.status,
    a.timestamp as last_alert_time,
    a.alert_type,
    a.status as alert_status,
    a.reason
FROM positions p
LEFT JOIN alert_history a ON p.pair = a.pair
WHERE p.status = 'OPEN'
  AND a.timestamp = (
    SELECT MAX(a2.timestamp) 
    FROM alert_history a2 
    WHERE a2.pair = p.pair
  )
ORDER BY p.entry_time DESC;
```

#### 2. Get Positions That Never Triggered Alerts

```sql
SELECT 
    id,
    pair,
    position_type,
    entry_price,
    entry_time,
    status
FROM positions
WHERE pair NOT IN (
    SELECT DISTINCT pair 
    FROM alert_history 
    WHERE pair IS NOT NULL
)
ORDER BY entry_time DESC;
```

#### 3. Alert-to-Position Ratio Analysis

```sql
SELECT 
    p.pair,
    COUNT(DISTINCT p.id) as position_count,
    COUNT(a.id) as alert_count,
    ROUND(
        1.0 * COUNT(a.id) / COUNT(DISTINCT p.id), 
        2
    ) as alerts_per_position
FROM positions p
LEFT JOIN alert_history a ON p.pair = a.pair
GROUP BY p.pair
ORDER BY alerts_per_position DESC;
```

---

### Signal Changes Queries

#### 1. Get Recent Signal Changes

```sql
SELECT 
    id,
    datetime(timestamp) as change_time,
    pair,
    timeframe,
    signal_type,
    previous_status,
    current_status,
    price_at_change,
    triggered_alert
FROM signal_changes
ORDER BY timestamp DESC
LIMIT 20;
```

#### 2. Get MA10 Changes for Specific Pair

```sql
SELECT 
    datetime(timestamp) as change_time,
    timeframe,
    previous_status,
    current_status,
    price_at_change,
    price_movement_pct
FROM signal_changes
WHERE pair = 'ETHUSD'
  AND signal_type = 'MA10'
ORDER BY timestamp DESC
LIMIT 50;
```

#### 3. Get OTT Signal Changes by Timeframe

```sql
SELECT 
    timeframe,
    COUNT(*) as change_count,
    SUM(triggered_alert) as alerts_triggered,
    AVG(price_movement_pct) as avg_pnl_at_change
FROM signal_changes
WHERE signal_type = 'OTT'
GROUP BY timeframe
ORDER BY change_count DESC;
```

#### 4. Get Signal Change Frequency by Pair

```sql
SELECT 
    pair,
    signal_type,
    COUNT(*) as total_changes,
    COUNT(DISTINCT date(timestamp)) as days_with_changes,
    ROUND(1.0 * COUNT(*) / COUNT(DISTINCT date(timestamp)), 2) as changes_per_day
FROM signal_changes
GROUP BY pair, signal_type
HAVING total_changes > 1
ORDER BY total_changes DESC;
```

#### 5. Get Bullish to Bearish Transitions

```sql
SELECT 
    pair,
    timeframe,
    signal_type,
    datetime(timestamp) as change_time,
    price_at_change,
    price_movement_pct,
    position_type,
    triggered_alert
FROM signal_changes
WHERE (previous_status = 'BULLISH' AND current_status = 'BEARISH')
   OR (previous_status = 'BEARISH' AND current_status = 'BULLISH')
ORDER BY timestamp DESC
LIMIT 50;
```

#### 6. Get Signal Changes with Alert Triggered

```sql
SELECT 
    datetime(timestamp) as change_time,
    pair,
    timeframe,
    signal_type,
    previous_status,
    current_status,
    price_at_change,
    price_movement_pct
FROM signal_changes
WHERE triggered_alert = 1
ORDER BY timestamp DESC
LIMIT 30;
```

#### 7. Analyze Signal Patterns Before Price Reversals

```sql
-- Find MA10 changes that occurred when position was in profit > 5%
SELECT 
    pair,
    timeframe,
    datetime(timestamp) as change_time,
    signal_type,
    previous_status,
    current_status,
    price_movement_pct,
    CASE 
        WHEN price_movement_pct > 5 THEN 'Profitable'
        WHEN price_movement_pct < -5 THEN 'Loss'
        ELSE 'Neutral'
    END as position_state
FROM signal_changes
WHERE signal_type IN ('MA10', 'OTT')
  AND ABS(price_movement_pct) > 5
ORDER BY ABS(price_movement_pct) DESC;
```

#### 8. Get Daily Signal Change Summary

```sql
SELECT 
    date(timestamp) as change_date,
    signal_type,
    COUNT(*) as total_changes,
    SUM(CASE WHEN previous_status != current_status THEN 1 ELSE 0 END) as actual_changes,
    SUM(triggered_alert) as alerts_triggered
FROM signal_changes
GROUP BY date(timestamp), signal_type
ORDER BY change_date DESC, total_changes DESC
LIMIT 30;
```

#### 9. Compare MA10 vs OTT Change Frequency

```sql
SELECT 
    signal_type,
    COUNT(*) as total_changes,
    COUNT(DISTINCT pair) as unique_pairs,
    COUNT(DISTINCT timeframe) as unique_timeframes,
    ROUND(100.0 * SUM(triggered_alert) / COUNT(*), 2) as alert_trigger_rate_pct
FROM signal_changes
WHERE signal_type IN ('MA10', 'OTT')
GROUP BY signal_type
ORDER BY total_changes DESC;
```

#### 10. Get Signal Changes Joined with Alert History

```sql
SELECT 
    s.datetime(timestamp) as signal_change_time,
    s.pair,
    s.timeframe,
    s.signal_type,
    s.previous_status,
    s.current_status,
    a.alert_type,
    a.status as alert_status,
    a.reason
FROM signal_changes s
LEFT JOIN alert_history a ON s.pair = a.pair 
    AND a.timestamp BETWEEN s.timestamp AND datetime(s.timestamp, '+5 minutes')
WHERE s.triggered_alert = 1
ORDER BY s.timestamp DESC
LIMIT 50;
```

---

## Python ORM Usage

### Setup

```python
from src.database import get_db_context
from src.models import Position, PositionStatus, PositionType
from src.models import AlertHistory, AlertType, AlertStatus
from src.models import SignalChange, SignalType, SignalStatus
```

### Query Positions

```python
# Get all open positions
with get_db_context() as db:
    open_positions = db.query(Position).filter(
        Position.status == PositionStatus.OPEN
    ).all()

# Get positions by pair
with get_db_context() as db:
    btc_positions = db.query(Position).filter(
        Position.pair == 'BTCUSD'
    ).order_by(Position.entry_time.desc()).all()

# Create a new position
with get_db_context() as db:
    new_position = Position(
        pair='ETHUSD',
        entry_price=3500.0,
        position_type=PositionType.LONG,
        timeframe='h4'
    )
    db.add(new_position)
    # Automatically committed by context manager

# Update position status
with get_db_context() as db:
    position = db.query(Position).filter_by(id=1).first()
    position.close(close_price=3600.0)
    # Automatically committed by context manager
```

### Query Alerts

```python
# Get recent alerts
with get_db_context() as db:
    recent_alerts = db.query(AlertHistory).order_by(
        AlertHistory.timestamp.desc()
    ).limit(20).all()

# Get failed alerts
with get_db_context() as db:
    failed_alerts = db.query(AlertHistory).filter(
        AlertHistory.status == AlertStatus.FAILED
    ).all()

# Create an alert record
with get_db_context() as db:
    alert = AlertHistory.create_alert(
        alert_type=AlertType.POSITION_HEALTH,
        current_status='WARNING',
        reason='Status changed from HEALTHY to WARNING',
        message='Position health alert for BTC/USDT...',
        pair='BTC/USDT',
        previous_status='HEALTHY',
        price_movement_pct=-2.5
    )
    db.add(alert)
    # Automatically committed by context manager

# Aggregate alert statistics
from sqlalchemy import func

with get_db_context() as db:
    stats = db.query(
        AlertHistory.alert_type,
        func.count(AlertHistory.id).label('total'),
        func.sum(func.case((AlertHistory.status == AlertStatus.SENT, 1), else_=0)).label('sent')
    ).group_by(AlertHistory.alert_type).all()
```

### Query Signal Changes

```python
# Get recent signal changes
with get_db_context() as db:
    recent_changes = db.query(SignalChange).order_by(
        SignalChange.timestamp.desc()
    ).limit(20).all()

# Get MA10 changes for specific pair
with get_db_context() as db:
    ma10_changes = db.query(SignalChange).filter(
        SignalChange.pair == 'ETHUSD',
        SignalChange.signal_type == SignalType.MA10
    ).order_by(SignalChange.timestamp.desc()).all()

# Create a signal change record
with get_db_context() as db:
    change = SignalChange.create_change(
        pair='BTC/USDT',
        timeframe='h4',
        signal_type=SignalType.MA10,
        previous_status='BULLISH',
        current_status='BEARISH',
        price_at_change=50000.0,
        price_movement_pct=-2.5,
        position_type='LONG',
        triggered_alert=True
    )
    db.add(change)
    # Automatically committed by context manager

# Aggregate signal change statistics
from sqlalchemy import func

with get_db_context() as db:
    stats = db.query(
        SignalChange.signal_type,
        func.count(SignalChange.id).label('total'),
        func.sum(SignalChange.triggered_alert).label('alerts_triggered')
    ).group_by(SignalChange.signal_type).all()
```

### Raw SQL Execution

```python
from sqlalchemy import text

with get_db_context() as db:
    result = db.execute(text("""
        SELECT pair, COUNT(*) as alert_count
        FROM alert_history
        WHERE status = 'FAILED'
        GROUP BY pair
    """))
    for row in result:
        print(f"{row.pair}: {row.alert_count} failed alerts")
```

---

## Database Migrations

### Run Migrations

```bash
# Run alert history migration
python -m src.migrations.migrate_alert_history

# Run signal changes migration
python -m src.migrations.migrate_signal_changes

# Run with quiet mode
python -m src.migrations.migrate_signal_changes --quiet

# Specify custom database URL
python -m src.migrations.migrate_signal_changes --database-url sqlite:///custom/path.db
```

### Create New Migration

1. Create a new file in `src/migrations/`:

```python
"""
Migration: Add new column example

Usage:
    python -m src.migrations.migrate_example
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from src.database import db_manager

def migrate_add_column(database_url: str = None, verbose: bool = True) -> bool:
    """Add new column to positions table."""
    from src.config import settings
    
    db_url = database_url or settings.database_url
    
    try:
        engine = db_manager.engine
        
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE positions ADD COLUMN new_column VARCHAR(50)
            """))
            conn.commit()
        
        if verbose:
            print("✓ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_add_column()
    sys.exit(0 if success else 1)
```

---

## Best Practices

### 1. Connection Management

- Always use the context manager (`get_db_context()`) for database operations
- The context manager handles commit, rollback, and connection cleanup
- Avoid long-running transactions

```python
# ✓ Good
with get_db_context() as db:
    positions = db.query(Position).all()

# ✗ Bad - manual connection management
db = db_manager.create_session()
positions = db.query(Position).all()
db.close()  # Easy to forget!
```

### 2. Index Usage

Query indexed columns for better performance:

```python
# ✓ Good - uses index
db.query(Position).filter(Position.pair == 'BTCUSD').all()

db.query(AlertHistory).filter(AlertHistory.timestamp >= some_date).all()

# ✗ Avoid - full table scan
db.query(Position).filter(Position.entry_price > 50000).all()
```

### 3. Batch Operations

For bulk inserts, use `bulk_insert_mappings()`:

```python
with get_db_context() as db:
    db.bulk_insert_mappings(
        AlertHistory,
        [
            {'alert_type': 'TEST', 'current_status': 'OK', 'reason': 'Test', 'message': 'Test 1'},
            {'alert_type': 'TEST', 'current_status': 'OK', 'reason': 'Test', 'message': 'Test 2'},
        ]
    )
```

### 4. Error Handling

```python
from sqlalchemy.exc import SQLAlchemyError

try:
    with get_db_context() as db:
        # Database operations
        pass
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    # Handle error appropriately
```

### 5. Query Optimization

- Use `.limit()` for large result sets
- Select only needed columns with `.with_entities()`
- Use database-side filtering instead of Python filtering

```python
# ✓ Good - efficient
db.query(Position).with_entities(
    Position.pair, Position.status
).filter(
    Position.status == PositionStatus.OPEN
).limit(100).all()

# ✗ Bad - loads all columns and rows
all_positions = db.query(Position).all()
result = [(p.pair, p.status) for p in all_positions if p.status == 'OPEN'][:100]
```

### 6. Date/Time Handling

SQLite stores datetime as text. Use consistent formatting:

```python
from datetime import datetime

# Store
position.entry_time = datetime.utcnow()

# Query with date functions
db.query(Position).filter(
    Position.entry_time >= datetime(2026, 1, 1)
).all()
```

---

## Troubleshooting

### Database Locked Error

```bash
# Check for WAL files
ls -la data/positions.db*

# If needed, checkpoint WAL
sqlite3 data/positions.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Reset Database (Development Only)

```python
from src.database import db_manager, Base

# Drop and recreate all tables
db_manager.drop_db()
db_manager.init_db()
```

### Check Database Integrity

```bash
sqlite3 data/positions.db "PRAGMA integrity_check;"
```

### Export Data

```bash
# Export to CSV
sqlite3 -header -csv data/positions.db "SELECT * FROM positions;" > positions.csv
sqlite3 -header -csv data/positions.db "SELECT * FROM alert_history;" > alerts.csv

# Export full database dump
sqlite3 data/positions.db ".dump" > backup.sql
```

### Import Data

```bash
# Restore from dump
sqlite3 data/positions.db < backup.sql
```

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [`data-fetcher.md`](data-fetcher.md) | DataFetcher multi-provider routing logic |
| [`market-data-caching.md`](market-data-caching.md) | Market data caching strategy |
| [`multi-timeframe-scanner.md`](multi-timeframe-scanner.md) | MTF opportunity scanner |
| [`ohlcv-cache-manager.md`](ohlcv-cache-manager.md) | OHLCV cache management |

---

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review `README.md` for setup instructions
3. Check `PROJECT_STATUS.md` for current status
