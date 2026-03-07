# Changelog

All notable changes to the TA-DSS project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Phase 6: Security Hardening

### Added — 2026-03-08 Security Audit
- **API key authentication**: `src/api/auth.py` — `verify_api_key` dependency applied to all `/api/v1/positions/*` routes. 401 without key, `/health` stays public. Auth skips in dev mode (no key set). See DEC-013.
- **Dashboard auth header**: `ui.py::get_api_headers()` sends `X-API-Key` on all API requests.

### Changed — 2026-03-08 Security Audit
- **sqlite-web startup**: added `-r` flag (read-only mode) — write queries now rejected at DB level, not just by discipline. Updated `docs/features/remote-db-access.md`.
- **VM .env permissions**: fixed from `664` (world-readable) to `600` (owner-only) via `chmod 600`.

### Security Audit Summary — 2026-03-08
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
