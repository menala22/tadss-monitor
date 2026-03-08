# Changelog
_Last updated: 2026-03-08_

All notable changes to the TA-DSS project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - MTF Scanner dashboard fixes — 2026-03-08

### Fixed
- **BUG-021** `ui_mtf_scanner.py` `_get_api_base_url()` had no `.env` file fallback — fell back to `localhost:8000` if `API_BASE_URL` not explicitly set in shell; dashboard showed "Cannot connect to API" on every scan.
- **BUG-022** "Scan Anyway" button was silently unreachable — Streamlit only processes a button click on the run where the button is *rendered*; because it was gated by `scan_button`, on the rerun triggered by clicking "Scan Anyway" (where `scan_button=False`) the button was never evaluated and the click was lost.
- **BUG-023** `check_status=True` hardcoded in scan request — even if scan fired, pairs with quality "MISSING" were excluded from `ready_pairs` server-side, guaranteeing zero results for newly-added pairs.

### Changed
- **MTF Scanner scan flow** simplified: removed stale-data pre-check and "Scan Anyway" / "Refresh All Stale" intermediate step. "Scan Now" fires immediately with `check_status=False`. Server handles missing data gracefully (pairs with no `ohlcv_universal` rows are skipped; result summary shows `pairs_no_data` count). See DEC-023.

---

## [Unreleased] - Phase 9: Internal Market Database

### Added — 2026-03-08 (Phase 6)
- **Position Monitor Migration**: Updated `src/monitor.py` to read from `ohlcv_universal` (read-only) with API fallback. Position checks now <100ms (was 2-5s), zero API calls per check.

### Changed — 2026-03-08 (Phase 8)
- **Scheduler Cleanup**: Removed redundant `mtf_cache_prefetch` job (ran every 2h at :20). Now only `market_data_prefetch` runs every hour at :10. Scheduler jobs reduced from 4 → 3.
- **Removed unused method**: `_run_mtf_prefetch()` removed from `src/scheduler.py`.

### Migration Progress
| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1-5 | ✅ Complete | Core architecture |
| Phase 6 | ✅ Complete | Position monitor migrated |
| Phase 7 | ⏸️ Backlog | Dashboard charts (low priority) |
| Phase 8 | ✅ Complete | Scheduler cleanup |
| Phase 9 | ⏳ Pending | ohlcv_cache cleanup (after 7-14 days) |

### Added — 2026-03-08
- **OHLCV Universal Table** (`src/models/ohlcv_universal_model.py`): Single source of truth for all market data with standardized symbol formats (XAU/USD) and normalized timeframes (w1, d1, h4).
- **MarketDataOrchestrator** (`src/services/market_data_orchestrator.py`): Smart fetch service with staleness detection, provider routing (CCXT/Twelve Data/Gate.io), and data validation.
- **Scheduler Integration**: Prefetch job runs every hour at :10 to keep ohlcv_universal fresh.
- **Manual Prefetch API** (`src/api/routes_market_data_prefetch.py`): POST /api/v1/market-data/prefetch endpoint for on-demand refresh.
- **Migration Script** (`scripts/migrate_ohlcv_to_universal.py`): Migrates 2,084 candles from ohlcv_cache with normalization and deduplication.
- **Test Scripts** (`scripts/phase5_test_verify.py`, `scripts/phase5_cleanup_cache.py`): Comprehensive testing and safe cleanup tools.

### Changed — 2026-03-08
- **MTF Scanner Migration**: Now reads exclusively from ohlcv_universal (read-only, zero live API calls).
- **Scheduler Jobs**: Added market_data_prefetch at :10 alongside position_monitoring.
- **Data Normalization**: Timeframe formats standardized (1w/1week/1wk → w1, 1d → d1, 4h → h4).

### Fixed — 2026-03-08
- **Duplicate Timeframes**: Eliminated 3× storage waste from 1w/1week/1wk variations.
- **Symbol Format Inconsistency**: Standardized XAUUSD/XAU/USD → XAU/USD.
- **Data Quality**: 0 NULL values, 0 duplicate candles in ohlcv_universal.

---

## [Unreleased] - Phase 8: Market Data Caching + MTF Integration

### Added — 2026-03-08
- **Market Data Status Dashboard** (`src/ui_market_data.py`): new dashboard page showing data quality for all pairs with timeframe breakdown, refresh controls, and MTF readiness indicators.
- **Market Data Service** (`src/services/market_data_service.py`): service layer for tracking data quality (EXCELLENT/GOOD/STALE/MISSING), syncing with OHLCV cache, identifying stale pairs, and determining MTF readiness.
- **Market Data Status Model** (`src/models/market_data_status_model.py`): SQLite table tracking candle count, last update time, quality assessment, and data source per pair/timeframe.
- **Market Data API** (`src/api/routes_market_data.py`): 6 REST endpoints — `GET /status`, `GET /status/{pair}`, `GET /summary`, `POST /refresh`, `POST /refresh-all`, `GET /watchlist`.
- **Timeframe normalization**: `_normalize_timeframe()` and `_merge_timeframe_data()` functions handle variations from different APIs (1week/1w/w1 → w1).
- **MTF scanner pre-scan check**: checks data status before scanning, warns user if stale, offers one-click refresh.
- **Test suite**: 68 tests covering model (32), service (23), and routes (13).

### Changed — 2026-03-08
- **MTF scanner integration**: now checks `market_data_status` before scanning, returns `data_issues` array with actionable errors.
- **Dashboard UI**: "📈 Market Data" page added to navigation with table/cards/details views and refresh controls.
- **Quality assessment logic**: 4-tier system (EXCELLENT: 200+ candles, GOOD: 100+, STALE: 50-99, MISSING: <50) with timeframe-relative age thresholds.

### Fixed — 2026-03-08
- **Duplicate timeframe entries**: cleaned up old formats (1w, 1week, 1d, 1h, 4h) that duplicated normalized formats (w1, d1, h4, h1).
- **Wrong quality assessments**: 250 candles incorrectly marked as MISSING — now correctly shows EXCELLENT/GOOD based on merged data.
- **Empty source field**: now shows "N/A" instead of blank when source is null (synced from cache doesn't track source).
- **Details view not showing data**: fixed to use already-fetched data instead of trying to re-fetch from non-existent API endpoint.

---

## [Unreleased] - Phase 8: MTF Wiring + Cache-First Architecture

### Added — 2026-03-08
- **MTF Cache Prefetcher** (`src/services/mtf_cache_prefetcher.py`): background job that pre-populates OHLCV cache for all watchlist pairs × SWING + INTRADAY timeframes; skips fresh data, fetches only when stale (see DEC-016).
- **MTF Prefetch Scheduler Job**: runs every 2 hours at :20 via APScheduler (3rd job alongside position monitoring at :10 and daily heartbeat). `job_count` updated to 3.
- **MTF Persistent Watchlist**: `mtf_watchlist` SQLite table + `MTFWatchlistItem` model; auto-seeds defaults (BTC/USDT, ETH/USDT, XAU/USD, XAG/USD); GET / POST / DELETE CRUD endpoints in `routes_mtf.py`; watchlist management panel in `ui_mtf_scanner.py`.

### Changed — 2026-03-08
- **MTF scan route — cache-only**: `_load_pair_data()` no longer does live API fetches on cache miss; returns "no data" instead. Removes 30-60s blocking requests from dashboard. See DEC-017.
- **MTF scan route — freshness check removed**: scan trusts cache content; prefetcher handles staleness. Fixes false-no-data on weekends for gold (market closed → last candle looks "stale" by h4 threshold even though no newer data exists).
- **MTF routes — API key auth**: all 5 MTF endpoints now require `X-API-Key` header (same as positions routes).
- **MTF alignment scorer**: TargetCalculator wired in (Step 5 in `analyze_pair()`); real R:R ratio replaces 2.5× placeholder for scored BUY/SELL setups.
- **MTF scan endpoints**: `send_mtf_opportunity_alert` called for score=3 opportunities in both `scan_opportunities` and `trigger_mtf_scan`.
- **DataFetcher — CCXT lazy init**: `_fetch_ccxt()` no longer raises `RuntimeError` when `_exchange` is None; initializes exchange on first call.
- **HTF bias — minimum candle requirement**: lowered from 200 (`sma200_period`) to 50 (`sma50_period`); NaN-safe SMA-200 (returns AT/neutral when insufficient history instead of BELOW/bearish).
- **MTF dashboard auth**: `_get_api_headers()` in `ui_mtf_scanner.py` reads `.env` file directly as fallback (matches `ui.py` pattern).

### Fixed — 2026-03-08
- RSI division by zero in `divergence_detector.py`, `mtf_setup_detector.py`, `mtf_entry_finder.py` (BUG-020): `rs = gain / loss.replace(0, nan)` + `rsi.fillna(100)`.
- MTF watchlist 404 — all MTF files deployed to VM (BUG-016).
- MTF dashboard 401 — API key not being sent (BUG-019).
- CCXT uninitialized for BTC/USDT, ETH/USDT in MTF scan (BUG-018).
- HTF NEUTRAL on all weekly data due to 200-candle minimum (BUG-017).

---

## [Unreleased] - Phase 7: MTF Scanner

### Added — 2026-03-07 MTF Feature (6 sessions)
- **Multi-Timeframe Opportunity Scanner**: scans multiple pairs across 3 timeframes simultaneously (HTF → MTF → LTF), scores alignment 0-3, filters by R:R, surfaces entry/stop/target.
- **HTF Bias Detector** (`mtf_bias_detector.py`): price structure (HH/HL, LH/LL) + 50/200 SMA. Structural tools only — no oscillators on HTF.
- **MTF Setup Detector** (`mtf_setup_detector.py`): pullback to SMA20/50, RSI divergence, breakout, consolidation detection.
- **LTF Entry Finder** (`mtf_entry_finder.py`): candlestick patterns (engulfing, hammer, pinbar), EMA20 reclaim, RSI turn from key levels, stop loss calculation.
- **Alignment Scorer** (`mtf_alignment_scorer.py`): 0-3 score; HIGHEST/GOOD/POOR/AVOID quality; BUY/SELL/WAIT/AVOID recommendation.
- **Divergence Detector** (`divergence_detector.py`): 4 RSI divergence types (regular/hidden bullish/bearish).
- **Target Calculator** (`target_calculator.py`): 5 methods — next HTF S/R, measured move, Fibonacci extension (1.272/1.618/2.618), ATR-based, prior swing.
- **S/R Detector** (`support_resistance_detector.py`): swing, volume, round number, and converging cross-TF levels.
- **Opportunity Scanner** (`mtf_opportunity_scanner.py`): multi-pair scan with pattern matching, min alignment + min R:R filters, ranked results.
- **MTF API** (`routes_mtf.py`): 5 REST endpoints — `GET /api/v1/mtf/opportunities`, `GET /api/v1/mtf/opportunities/{pair}`, `GET /api/v1/mtf/configs`, `POST /api/v1/mtf/scan`, `GET /api/v1/mtf/watchlist`.
- **MTF Dashboard panel** (`ui_mtf_scanner.py`): trading style selector, alignment/R:R filters, scan results with expandable cards, detailed breakdown.
- **MTF Telegram alerts** (`mtf_notifier.py`): opportunity alert (3/3 alignment only), divergence alert, daily summary; throttled to max 3/day.
- **Gate.io integration** for XAGUSD/XAUUSD via swap contracts (added to `data_fetcher.py`).
- **OHLCV cache** extended for multi-timeframe support (`ohlcv_cache_manager.py`).
- **149 unit tests** across 6 test files in `tests/test_mtf/`.
- **Report generator** (`scripts/generate_mtf_report.py`): CLI tool for real-time MTF analysis reports saved to `docs/reports/`.

See [`docs/features/multi-timeframe-scanner.md`](docs/features/multi-timeframe-scanner.md) for full design + as-built notes.
See [`docs/features/mtf-user-guide.md`](docs/features/mtf-user-guide.md) for user-facing guide.

---

## [Unreleased] - Phase 6: Security Hardening

### Added — 2026-03-07 Security Audit
- **API key authentication**: `src/api/auth.py` — `verify_api_key` dependency applied to all `/api/v1/positions/*` routes. 401 without key, `/health` stays public. Auth skips in dev mode (no key set). See DEC-013.
- **Dashboard auth header**: `ui.py::get_api_headers()` sends `X-API-Key` on all API requests.

### Changed — 2026-03-07 Security Audit
- **sqlite-web startup**: added `-r` flag (read-only mode) — write queries now rejected at DB level, not just by discipline. Updated `docs/features/remote-db-access.md`.
- **VM .env permissions**: fixed from `664` (world-readable) to `600` (owner-only) via `chmod 600`.

### Security Audit Summary — 2026-03-07
| Area | Status | Notes |
|------|--------|-------|
| API auth | Fixed | API key required for all /api/v1/* |
| Firewall port 8000 | Open (Task 5) | 0.0.0.0/0 — lower priority now auth is in place |
| SSH private key | Clean | 600 permissions, ~/.ssh/ is 700 |
| Secrets in git | Clean | .env never committed; git grep found only code references |
| Docker user | Root (low risk) | No extra caps; fix would require Dockerfile rebuild |
| sqlite-web writes | Fixed | -r flag enforces read-only at DB level |
| Disk encryption | Clean | GCP default encryption active |
| Open ports | Note | RDP 3389 open (GCP default rule, no service listening on Linux VM) |

---

## [Unreleased] - Phase 5: Deployment

### Fixed — 2026-03-07 Session
- **BUG-013** Double anti-spam gating: `monitor.py` now passes `reason` to `send_position_alert`; notifier skips internal gate when reason is provided
- **BUG-014** Raw SignalState enums passed to notifier: `monitor.py` converts signal_states to plain `{str: str}` before calling notifier; notifier also normalises defensively
- **BUG-015** OTT missing from Telegram alert message: added OTT to `notifier._format_message` signals loop

### Added — 2026-03-07 Session
- **Startup Telegram message**: fires when container starts — shows position count and next check time (`scheduler.py`)
- **Daily heartbeat message**: fires at 00:00 UTC / 07:00 GMT+7 — confirms system is running (`scheduler.py`)

### Changed — 2026-03-07 Session (3)
- **Positions table sort order**: rows now sorted by pair name A→Z, then timeframe shortest→longest (`ui.py::render_positions_table`)

### Changed — 2026-03-07 Session (2)
- **Contradiction warning** in Telegram alert message (`notifier._format_message`):
  - Graduated severity: 2/4 indicators `⚠️ Caution`, 3/4 `🔶 Warning`, 4/4 `🚨 Strong Warning` (was binary all-or-nothing)
  - Now checks MA10, MA20, MA50, OTT (4 indicators, was MA10/MA20/MA50 only)
  - Suppressed when reason is "Status changed" — avoids redundancy with the reason line
  - See DEC-012

### Removed — 2026-03-07 Session
- **GitHub Actions workflow** (`.github/workflows/monitor.yml`) and script (`scripts/github_monitor.py`): VM scheduler runs every hour and is more capable — GitHub Actions every-4-hour cron was redundant and causing duplicate Telegram messages. See DEC-011.

---

### Added - 2026-03-01 Session

#### OTT (Optimized Trend Tracker) Indicator
- **Full implementation from TradingView Pine Script**
- 8 moving average types: SMA, EMA, WMA, TMA, VAR, WWMA, ZLEMA, TSF
- Variable Moving Average (VAR) using CMO for adaptive smoothing
- Zero Lag EMA (ZLEMA) for reduced lag
- Time Series Forecast (TSF) for predictive element
- Wilder's Welles Moving Average (WWMA)
- Configurable parameters: ott_period (default: 2), ott_percent (default: 1.4), ott_ma_type (default: "VAR")
- Trend direction signals (BULLISH when Trend=1, BEARISH when Trend=-1)
- Dynamic trailing stop levels (MT)
- OTT-based warnings in signal engine
- **Files:** `src/services/technical_analyzer.py` (+400 lines), `tests/test_ott.py` (7 tests)

#### Important Indicators Alert Feature
- **New alert trigger for MA10 and OTT changes** (early warning system)
- Alerts when MA10 changes (fast moving average - early warning)
- Alerts when OTT changes (trend confirmation)
- Alerts even if overall status doesn't change
- Database column: `last_important_indicators` VARCHAR(50)
- Format: "MA10_status,OTT_status" (e.g., "BULLISH,BULLISH")
- **Files:** `src/models/position_model.py`, `src/monitor.py` (+50 lines)
- **Migration:** Added `last_important_indicators` column to positions table

#### Dashboard Enhancements
- OTT display in position detail view (signal breakdown table)
- OTT value, MT (trailing stop), and Trend displayed
- OTT included in conflicting signals detection
- Signal summary updated to show 6 indicators (was 5)
- Timeframe display in position detail header (e.g., "📍 XAUUSD - LONG 1d")
- **Files:** `src/ui.py` (+75 lines)

#### Signal Stability Improvements
- **EMA stability threshold:** 0.3% buffer to prevent flip-flopping
- **MACD stability threshold:** 0.01% of price buffer
- Signals no longer flip on tiny price movements
- **Files:** `src/services/technical_analyzer.py` (+30 lines)

#### Data Source Detection Fix
- **Keyword-based crypto detection** (was string length-based)
- Added crypto keywords: BTC, ETH, SOL, DOGE, XRP, ADA, DOT, LTC, BCH, LINK, AVAX, MATIC, UNI, ATOM
- Added precious metals: XAU, XAG, GOLD, SILVER
- Fixes chart loading for BTC-USD, XAUUSD, ETHUSD, etc.
- **Files:** `src/ui.py` (3 locations fixed)

#### Health Status Logic Fix
- **Unified alignment-based health logic** (was inconsistent between main table and detail page)
- Main table now uses same logic as detail page and backend
- HEALTHY: ≥60% aligned with position
- WARNING: 21-59% aligned
- CRITICAL: ≤20% aligned
- **Files:** `src/ui.py` (2 functions updated)

### Changed

#### Configuration
- **Monitor interval changed from 4 hours to 1 hour** (better for h1 timeframe)
- Default: MONITOR_INTERVAL=3600 (was 14400)
- **Files:** `src/config.py`, `.env`

#### Signal Aggregation
- Now includes 6 indicators (was 5): MA10, MA20, MA50, MACD, RSI, **OTT**
- Confidence scoring updated for 6 indicators
- **Files:** `src/services/technical_analyzer.py`

#### Documentation
- **TELEGRAM_ALERT_GUIDE.md** updated to v2.1
  - Added Important Indicators section
  - Added database storage section
  - Updated alert logic flow diagram
  - Added changelog section
- **OTT_IMPLEMENTATION.md** - Complete OTT implementation guide
- **BULLISH_BEARISH_DEFINITION.md** - Signal definition reference
- **CHANGELOG.md** - This file

### Technical Details

- **Source:** TradingView Pine Script by @kivancozbilgic and @Anil_Ozeksi (OTT)
- **License:** Mozilla Public License 2.0
- **Implementation:** Python with pandas/numpy
- **Lines added:** ~600 lines of code
- **Lines modified:** ~150 lines
- **Test coverage:** 7 new OTT tests (100% passing)
- **Total tests:** 117 tests (100% passing)

### Testing Results

```
✅ test_ott.py: 7/7 tests passing
✅ test_signal_engine.py: 31/31 tests passing
✅ All existing tests: 117/117 tests passing (100%)
✅ No regressions introduced
```

### Migration Required

Run database migration for Important Indicators feature:

```python
from src.models.position_model import migrate_add_signal_columns
migrate_add_signal_columns()

# Output:
# ✓ Added last_signal_status column
# ✓ Added last_checked_at column
# ✓ Added last_important_indicators column
```

**Note:** Database is located at `data/positions.db` (not root `positions.db`)

### Planned
- Docker containerization
- Docker Compose for multi-service deployment
- Production PostgreSQL setup
- WebSocket for real-time price updates
- Enhanced charting and visualizations

---

## [2026-02-28] – Phase 4: Dashboard Complete

### Added
- **Streamlit Dashboard (`src/ui.py`)**
  - Main dashboard with real-time position monitoring
  - Summary cards (Total, Long, Short, Warnings)
  - Position details table with PnL and signals
  - Color-coded warning indicators
  - Add new position form with validation
  - Settings page (Telegram config, monitoring interval, thresholds)
  - Custom CSS styling (hidden menu, improved tables, responsive)
  - Footer with timestamp
  - Modular code structure (render_* functions)
  - Mobile-responsive design

- **Dashboard Configuration**
  - `.streamlit/config.toml` for port and theme settings
  - Default port: 8503 (to avoid conflicts)
  - Headless mode for server deployment
  - Custom theme colors

- **Dashboard Features**
  - `render_sidebar()` - Navigation with session state
  - `render_summary_cards()` - Top-level metrics
  - `render_main_page()` - Position list with signals
  - `render_add_position_page()` - Trade logging form
  - `render_settings_page()` - Configuration UI
  - `render_footer()` - Timestamp footer
  - `fetch_position_with_signals()` - Live data + signals
  - `get_db_session()` - Database connection helper

- **Documentation**
  - Updated README.md with Dashboard features
  - Updated PROJECT_STATUS.md with Phase 4 completion
  - Updated CHANGELOG.md (this file)

### Changed
- **README.md**
  - Updated status to "Phase 4 Complete"
  - Added Dashboard to feature table
  - Added dashboard launch instructions
  - Updated progress to ~95%
  - Updated next steps to Phase 5 (Deployment)

- **PROJECT_STATUS.md**
  - Updated to Phase 4 completion report
  - Added Dashboard features and screenshots
  - Updated progress table (Dashboard at 100%)

### Technical Details
- **Streamlit:** 1.54.0
- **Layout:** Wide mode for better table viewing
- **Styling:** Custom CSS for professional appearance
- **Responsiveness:** Mobile-friendly with media queries

### Test Results
```
Dashboard Tests:
- UI module imports: ✅
- All render functions: ✅
- Database fetch: ✅
- Position with signals: ✅

Manual Testing:
- Dashboard loads: ✅
- Summary cards display: ✅
- Position table renders: ✅
- Add position form works: ✅
- Settings page functional: ✅
```

---

## [2026-02-28] – Phase 3: Automated Monitoring System Complete

### Added
- **Database Schema Updates**
  - Added `last_signal_status` column to positions table for spam prevention
  - Added `last_checked_at` column to track last analysis time
  - Created `migrate_add_signal_columns()` migration function
  - Added `update_signal_status()` method to Position model

- **Position Monitor (`src/monitor.py`)**
  - New `PositionMonitor` class orchestrating full monitoring workflow
  - `check_all_positions()` method for batch position checking
  - Auto-detection of data source (CCXT for crypto, yfinance for stocks)
  - PnL calculation with configurable thresholds
  - Overall status determination from individual signals
  - Anti-spam comparison logic (previous vs current status)
  - Alert triggers: status change, stop loss (-5%), take profit (+10%)
  - Database updates after each check
  - Comprehensive logging to `logs/monitor.log`
  - Error handling (try/except per position)

- **Scheduler Integration (`src/scheduler.py`)**
  - Integrated PositionMonitor with APScheduler
  - Configurable monitoring interval via `CHECK_INTERVAL_HOURS`
  - Added `run_now()` method for manual triggers
  - Added `run_monitoring_check_now()` global function
  - Non-blocking background execution
  - Graceful shutdown on app close

- **Telegram Notifications (`src/notifier.py`)**
  - New lightweight TelegramNotifier class (requests library)
  - `send_position_alert()` with anti-spam logic
  - Markdown message formatting for mobile
  - Error handling with 1 retry
  - Logging to `logs/telegram.log`
  - `test_notification()` function for verification
  - `send_alert()` convenience function

- **FastAPI Integration (`src/main.py`)**
  - Scheduler starts automatically on app startup
  - Graceful shutdown on app close
  - Added `/api/v1/positions/scheduler/status` endpoint
  - Added `/api/v1/positions/scheduler/test-alert` endpoint

- **Testing**
  - Created `test_monitor.py` for manual full-flow testing
  - 26 new unit tests for notifier
  - 28 new unit tests for scheduler
  - Total: 110 tests (100% passing)

- **Configuration**
  - Updated `.env.example` with `CHECK_INTERVAL_HOURS`
  - Created `.env` file with Telegram credentials
  - Fixed CORS_ORIGINS format for pydantic-settings

- **Documentation**
  - Updated README.md with Phase 3 features
  - Updated PROJECT_STATUS.md with completion report
  - Updated CHANGELOG.md (this file)

### Changed
- **Technical Analyzer**
  - Updated to handle both "close" and "Close" column names
  - Added column name standardization (lowercase conversion)

- **Data Fetcher**
  - Updated to handle both "close" and "Close" column names
  - Fixed CCXT exchange close method

- **Database**
  - Changed default database URL to `sqlite:///./positions.db`
  - Updated Position model with new columns

### Fixed
- Column name mismatch between DataFetcher ("Close") and TechnicalAnalyzer ("close")
- CCXT exchange close method ('binance' object has no attribute 'close')
- CORS_ORIGINS parsing error in pydantic-settings
- Migration function for existing databases

### Technical Details
- **Python:** 3.12.9
- **FastAPI:** 0.109.0
- **SQLAlchemy:** 2.0.25
- **pandas:** 2.3.3
- **pandas_ta:** 0.4.71b0
- **ccxt:** 4.2.34
- **yfinance:** 0.2.36
- **APScheduler:** 3.10.4
- **pytest:** 9.0.2
- **requests:** (latest)

### Test Results
```
Total Tests: 110 (100% passing)

- test_signal_engine.py:    31 tests ✅
- test_data_fetcher.py:     25 tests ✅
- test_scheduler.py:        28 tests ✅
- test_notifier.py:         26 tests ✅

Manual Test:
- test_monitor.py:          Full flow verified ✅
```

### Verified Workflow
1. ✅ Log position via API
2. ✅ Scheduler checks every 4 hours
3. ✅ Fetches live data from CCXT/yfinance
4. ✅ Calculates RSI, MACD, EMA signals
5. ✅ Determines overall status (BULLISH/BEARISH/NEUTRAL)
6. ✅ Compares with previous status
7. ✅ Sends Telegram alert if:
   - Status changed (BULLISH → BEARISH)
   - PnL < -5% (Stop Loss Warning)
   - PnL > +10% (Take Profit Warning)
8. ✅ Updates database with new status
9. ✅ Logs to `logs/monitor.log`

---

## [2026-02-27] – Core Backend Complete

### Added
- **Project Setup**
  - Python 3.12.9 environment via pyenv
  - Virtual environment configuration
  - Dependencies with pinned versions (requirements.txt)
  - Comprehensive .gitignore
  - Security checklist for AI-assisted development

- **Database Layer**
  - SQLAlchemy Position model with enums (PositionType, PositionStatus)
  - Database initialization script with table creation
  - Session management for FastAPI dependency injection
  - Context manager for background jobs/scripts
  - SQLite with PostgreSQL-ready schema

- **Configuration**
  - Pydantic-settings for environment variables
  - Timeframe validation for yfinance and CCXT
  - Automatic fallback for unsupported timeframes (h4 → 1h for yfinance)
  - Ticker normalization (BTCUSD → BTC-USD for yfinance, BTC/USDT for CCXT)

- **Backend API (FastAPI)**
  - FastAPI application with CORS and lifespan events
  - Pydantic schemas for request/response validation
  - Position CRUD endpoints (create, list, close, delete)
  - Service layer for business logic
  - Automatic OpenAPI documentation

- **Data Fetching**
  - DataFetcher class with unified yfinance/CCXT interface
  - Retry logic (3 attempts with exponential backoff)
  - Custom DataFetchError exception
  - Data validation (empty checks, null checks, datetime index)
  - Logging to `logs/data_fetch.log`

- **Technical Analysis**
  - TechnicalAnalyzer class using pandas_ta
  - EMA calculation (10, 20, 50 periods)
  - MACD calculation (12, 26, 9 parameters)
  - RSI calculation (14 periods)
  - Signal generation (BULLISH/BEARISH/NEUTRAL/OVERBOUGHT/OVERSOLD)
  - Overall signal aggregation with confidence score
  - Warning detection for divergences

- **Signal Engine**
  - evaluate_position_health() function
  - Health matrix (HEALTHY/WARNING/CRITICAL)
  - Alert logic with spam prevention
  - Alert message formatting for Telegram
  - Portfolio health evaluation

- **Testing**
  - 56 unit tests (100% passing)
  - Signal engine tests (31 tests)
  - Data fetcher tests (25 tests)
  - pytest configuration

### Changed
- Updated README.md with comprehensive project documentation
- Created PROJECT_STATUS.md for progress tracking
- Organized project structure following 12-Factor App methodology

### Fixed
- Timeframe validation edge cases (empty DataFrame, insufficient data)
- CCXT exchange cleanup on object destruction
- Test assertions for retry logic timing

### Technical Details
- **Python:** 3.12.9
- **FastAPI:** 0.109.0
- **SQLAlchemy:** 2.0.25
- **pandas:** 2.3.3
- **pandas_ta:** 0.4.71b0
- **ccxt:** 4.2.34
- **yfinance:** 0.2.36
- **pytest:** 9.0.2

---

## [2026-02-20] – Project Initialization

### Added
- Initial project structure
- Python virtual environment setup
- Basic directory layout (src/, tests/, data/, logs/)
- Environment configuration template

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 0.4.0 | Unreleased | Phase 4: Dashboard (In Development) |
| 0.3.0 | 2026-02-28 | Phase 3: Automated Monitoring (Complete) |
| 0.2.0 | 2026-02-27 | Phase 2: Core Backend (Complete) |
| 0.1.0 | 2026-02-20 | Phase 1: Project Setup (Complete) |

---

## Legend

- **Added** – New features or functionality
- **Fixed** – Bug fixes
- **Changed** – Modifications to existing features
- **Removed** – Deleted features
- **Security** – Security improvements

---

**Next Release:** v0.4.0 - Phase 4: Dashboard (Streamlit)
