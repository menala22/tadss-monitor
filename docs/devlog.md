# Dev Log
_Last updated: 2026-03-07_

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
