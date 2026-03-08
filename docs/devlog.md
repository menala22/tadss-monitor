# Dev Log
_Last updated: 2026-03-08 (Phase 6-8 complete)_

---

## 2026-03-08 — Internal Market Database Migration Complete (Phases 6-8)
Started: Complete migration to ohlcv_universal architecture.
Done: Phase 6 (Position Monitor migrated to ohlcv_universal, <100ms checks, zero API calls), Phase 8 (removed redundant mtf_cache_prefetch scheduler job, 4→3 jobs); deployed to VM and verified; Phase 7 logged as optional backlog (dashboard charts, low priority), Phase 9 scheduled for after 7-14 days monitoring (ohlcv_cache cleanup). All critical consumers now read from ohlcv_universal. See `docs/tasks.md` for remaining items.

---

## 2026-03-08 — MTF Scanner dashboard bug-fix session
Started: Troubleshoot MTF Scanner "Scan Now" giving ConnectionError and "Scan Anyway" returning no results.
Done: Fixed 3 bugs in `ui_mtf_scanner.py` — missing `.env` fallback in `_get_api_base_url()` (BUG-021), Streamlit state-machine flaw making "Scan Anyway" unreachable (BUG-022/023). Final resolution: removed stale-data pre-check entirely; scan now fires immediately on "Scan Now" with `check_status=False` (DEC-023). Verified 0 INTRADAY opportunities is correct (all pairs in consolidation on h4). USDCAD removed from watchlist (wrong symbol format); needs re-adding as USD/CAD.

---

## 2026-03-08 — Internal Market Database Architecture (Phases 1-5)
Started: Build internal market database with ohlcv_universal as single source of truth.
Done: Created `ohlcv_universal` table (normalized symbols/timeframes) + `MarketDataOrchestrator` service (smart fetch, staleness detection, provider routing) + scheduler job (every hour at :10) + manual prefetch API endpoints; migrated MTF scanner to read-only from ohlcv_universal; 2,844 candles migrated; 5/5 Phase 5 tests passed; ohlcv_cache ready for cleanup. See `docs/features/internal-market-database-architecture.md`.

---

## 2026-03-08 — Market Data Caching Feature (Phase 8)
Started: Build market data caching strategy to eliminate slow/costly API calls during MTF scans.
Done: Created `market_data_status` table + `MarketDataService` (25+ methods) + 6 API endpoints + dashboard page (`ui_market_data.py`); implemented 4-tier quality system (EXCELLENT/GOOD/STALE/MISSING) with timeframe-relative thresholds; added timeframe normalization (`1week`/`1w` → `w1`) with duplicate merging; MTF scanner now checks status before scanning and shows actionable errors; 68 tests passing; deployed to VM; cleaned up duplicate timeframe entries; BTC/USDT now shows MTF Ready: ✅ with correct quality (GOOD/EXCELLENT). See `docs/features/market-data-caching.md`, DEC-018/019/020.

---

## 2026-03-08 — MTF wiring, watchlist, cache-first architecture
Started: Wire remaining MTF pieces (TargetCalculator, auth, notifier), build watchlist management, implement cache-first scan strategy.
Done: TargetCalculator wired into alignment scorer; API key auth on all MTF routes; notifier wired into scan endpoints; persistent DB-backed watchlist with full CRUD (add/remove/seed defaults); fixed 401 on MTF dashboard (env file fallback for API key); fixed CCXT lazy init for BTC/ETH; lowered HTF minimum candles 200→50 (free-tier weekly data); fixed RSI div/0 in divergence_detector, mtf_setup_detector, mtf_entry_finder; implemented cache-first MTF scan (`mtf_cache_prefetcher.py` + scheduler job every 2h at :20, routes go cache-only with no live fallback); deployed all to VM — 4/5 watchlist pairs now scan successfully.

---

## 2026-03-07 — MTF Scanner (6 sessions)
Started: Build multi-timeframe opportunity scanner from scratch (6 planned sessions).
Done: Complete MTF feature — HTF bias detector (50/200 SMA, price structure), MTF setup detector (pullback, divergence, breakout), LTF entry finder (candlestick patterns, EMA reclaim), alignment scorer (0-3), divergence detector (4 types), target calculator (5 methods), S/R detector, opportunity scanner, 5 API endpoints, dashboard panel, Telegram alerts, Gate.io integration for XAGUSD. 149 unit tests passing; grand total 266 tests. See `docs/features/multi-timeframe-scanner.md`.

---

## 2026-03-07 — Security Audit
Started: Comprehensive security audit (all 8 attack surfaces from security-audit.md).
Done: API key auth implemented and deployed (401 without key, 200 with key, /health public). VM .env permissions fixed 664→600. sqlite-web startup updated to use -r flag (read-only enforced). Git history clean (no secrets). Disk encrypted (GCP default). Docker caps: none added. Firewall RDP rule present (GCP default, Linux VM, no service listening — low risk). Firewall port 8000 still open to 0.0.0.0/0 — Task 5 remains.

---

## 2026-03-07 (Session 4)
Started: Improve dashboard positions table sort order.
Done: Table now sorted by pair name A→Z then timeframe shortest→longest (using minute-based sort key). Deployed to VM.

---

## 2026-03-07 (Session 3)
Started: Improve Telegram alert contradiction warning.
Done: Replaced binary all-or-nothing MA warning with graduated severity (2/4 ⚠️, 3/4 🔶, 4/4 🚨). Added OTT to the 4 key indicators checked (was only MA10/20/50). Warning now suppressed when reason is "Status changed" to avoid redundancy. Deployed to VM.

---

## 2026-03-07 (Session 2)
Started: Review and improve Telegram alert system.
Done: Fixed 3 bugs — double anti-spam gating blocked valid alerts, raw SignalState enums passed to notifier (status comparison always wrong), OTT missing from alert message body. Added startup Telegram message on container start and daily heartbeat at 07:00 GMT+7. Removed GitHub Actions workflow (VM scheduler supersedes it). Pushed all changes to GitHub.

---

## 2026-03-07 (Session 1 — earlier)
Started: Set up remote DB access to production SQLite on VM.
Done: sqlite-web running on VM via SSH port forward — accessible at `http://localhost:8080` in browser. DB confirmed volume-mounted at `/home/aiagent/tadss-monitor/data/positions.db` (Scenario A — no docker cp needed). DBeaver dropped in favour of sqlite-web (DBeaver has no SSH tunnel tab for file-based SQLite). Two issues hit and resolved: `pip` not found (used `sudo apt install python3-pip`), `sqlite_web` not in PATH (run via `~/.local/bin/sqlite_web`).

---

## 2026-03-07
Started: Debug dashboard data issues after VM restart; fix Health/Signal columns; OHLCV cache bugs.
Done: Fixed 6 bugs — duplicate function shadowing timeout, health check 404, blocking API route on cache miss, missing schema fields (Health/Signal always NEUTRAL), CCXT/Gate.io fetchers not saving to cache, XAUUSD h4 cache key mismatch. Deployed all fixes via docker cp hot-copy. Dashboard now shows correct PnL, Health, and Signal for all 6 positions.

## 2026-03-05
Started: Connect local dashboard to production API; clean up VM IP from git history.
Done: Added `API_BASE_URL` env var support to dashboard, Settings page API Mode toggle, `run-dashboard-production.sh` script. Moved VM IP to `.env` (not committed). Identified security gap: API has no authentication (Task 4, CRITICAL pending).

## 2026-03-04
Started: Deploy system to Google Cloud VM for 24/7 operation.
Done: Production live on Google Cloud e2-micro (us-central1-a, Always Free tier). Docker container `tadss` running on port 8000, auto-restart enabled. Scheduler confirmed running at :10 past every hour. Total cost: $0/month.

## 2026-03-02
Started: Add alert history database, fix confirmed close signals, fix scheduler timing, add missing API endpoint.
Done: Created `alert_history` and `signal_changes` tables with full audit trail. Fixed signals to use confirmed close candle (`iloc[-2]`) — eliminates false signals from forming candles. Changed scheduler from interval to cron trigger (always fires at :10). Added missing `POST /scheduler/run-now` endpoint (was 404). Fixed alert logging bypass bug.

## 2026-03-01
Started: Implement OTT indicator, fix health status inconsistency, improve signal stability.
Done: Full OTT (Optimized Trend Tracker) implementation from TradingView Pine Script — 8 MA types, trend direction, dynamic trailing stops. Unified health status logic across main table and detail page (alignment-based: ≥60% HEALTHY, ≤20% CRITICAL). Added Important Indicators alert feature (MA10 + OTT early warnings). Fixed data source detection (keyword-based, not string-length). Added signal stability buffers (EMA 0.3%, MACD 0.01%). 117 tests passing.

## 2026-02-28 (Evening)
Started: Fix P&L showing 0%, restore Signal column, remove redundant Details section.
Done: 18x page load improvement (18s → <1s) by removing expensive live market fetches from main table. Discovered lack of git version control mid-session — unable to revert changes. Lesson: always initialize git before development. Created VERSION_MANAGEMENT_GUIDE.md as reference. Git repo initialized after session.

## 2026-02-28 (Afternoon)
Started: Build Streamlit dashboard skeleton — Phase 4.
Done: Dashboard skeleton 100% complete. All 3 pages built: Open Positions (summary cards, table, detail view with chart), Add New Position (form, presets, validation), Settings (Telegram, scheduler, thresholds, system info). Caching with `@st.cache_data`, auto-refresh, error handling. Logged UX improvements to backlog.

## 2026-02-28
Started: Phase 3 — automated monitoring system.
Done: `PositionMonitor` class, APScheduler integration, Telegram notifier with anti-spam logic. Alert triggers: signal change, PnL < -5% (stop loss), PnL > +10% (take profit). 110 unit tests passing. Full flow verified: DB → Fetch → Analyze → Alert → DB Update.

## 2026-02-27
Started: Phase 2 — core backend.
Done: FastAPI app, SQLAlchemy Position model, DataFetcher (CCXT + yfinance), TechnicalAnalyzer (EMA/MACD/RSI with pandas_ta), signal engine, 56 unit tests. Project structure follows 12-Factor App methodology.

## 2026-02-20
Started: Project initialization.
Done: Directory structure, Python virtual environment, environment config template, basic project layout (src/, tests/, data/, logs/).
