# Task Tracker
_Last updated: 2026-03-08 (Phases 6-8 complete)_

---

## In Progress

- [ ] **Fix remaining RSI div/0 in MTF scan (XAG/USD)** — started 2026-03-08
  mtf_setup_detector + mtf_entry_finder RSI fixes deployed; XAG/USD still failing — second div/0 source TBD (likely mtf_alignment_scorer rr_ratio or mtf_bias_detector slope when price=0)

---

## Backlog

### Dashboard UI (Optional)
- [ ] **Phase 7: Migrate Dashboard Charts to ohlcv_universal** — Low (30 min)
  Update position detail charts in Streamlit dashboard to read from `ohlcv_universal` instead of live API calls.
  
  **Files to modify:**
  - `src/api/routes.py` — Update `/positions/{id}` endpoint
  - `src/ui.py` — Update chart rendering
  
  **Benefits:**
  - Chart load time: 2-5s → <1s (5× faster)
  - Zero API calls per view
  
  **Priority:** Low — Current charts work, just slower. Can batch with other UI improvements.

### Cleanup Tasks (After Monitoring Period)
- [ ] **Phase 9: Cleanup ohlcv_cache table** — Medium (15 min)
  Remove legacy `ohlcv_cache` table after 7-14 days of stable operation.
  
  **Prerequisites:**
  - [ ] 7+ days of stable operation with no errors
  - [ ] All consumers migrated to `ohlcv_universal` (MTF ✅, Position Monitor ✅)
  - [ ] Backup verified (`ohlcv_cache_backup` table exists)
  
  **Steps:**
  1. Run: `python scripts/phase5_cleanup_cache.py`
  2. Type 'yes' to confirm
  3. Verify all features still work
  4. Update documentation
  
  **Risk:** Low — Dual-table period is safe. Can rollback if needed.
  
  **Target Date:** After 7-14 days monitoring (around 2026-03-15 to 2026-03-22)

### Quick Fixes
- [ ] **Re-add USDCAD to MTF watchlist as USD/CAD** — Low (5 min)
  Removed from watchlist (wrong format). Twelve Data expects `USD/CAD` (with slash). Add via Manage Watchlist in dashboard. Orchestrator will auto-fetch on next :10 prefetch.

### MTF Report Improvements
- [ ] **Add chart visualizations to MTF reports** — High (4-8h)
  Generate candlestick charts with annotations for each timeframe (HTF/MTF/LTF) and embed in markdown reports.
  
  **Requirements:**
  - Use `plotly` or `mplfinance` for chart generation
  - HTF chart: Show 50/200 SMA, key S/R levels, price structure (HH/HL markers)
  - MTF chart: Show 20/50 SMA, pullback zone, RSI panel
  - LTF chart: Show 20 EMA, entry candle highlighted, stop/target lines
  - Export as PNG (static) or HTML (interactive)
  - Embed in markdown report with `![chart](path/to/chart.png)`
  
  **Files to modify:**
  - `scripts/generate_mtf_report.py` — Add chart generation logic
  - `docs/reports/` — Store chart images alongside reports
  
  **Example output:**
  ```
  docs/reports/
  ├── BTCUSDT-mtf-analysis-swing-20260308.md
  ├── BTCUSDT-htf-w1-chart-20260308.png
  ├── BTCUSDT-mtf-d1-chart-20260308.png
  └── BTCUSDT-ltf-h4-chart-20260308.png
  ```
  
  **Dependencies:** `plotly`, `kaleido` (for PNG export), or `mplfinance`

### Market Data Follow-up
- [ ] **Add source tracking to sync_all_statuses()** — Low
  Currently synced entries have `source=null`. Should track which API provided each timeframe.

- [ ] **Add automatic refresh trigger** — Medium
  When quality drops to STALE, automatically trigger refresh (configurable threshold).

- [ ] **Add data retention policy** — Low
  Delete candles older than 1 year, keep only last 500 per pair/timeframe.

- [ ] **Add chart preview** — Low (1-2h)
  Show last N candles for each timeframe in details view.

### Security
- [ ] **Task 5: Restrict Firewall to Your IP** — Medium
  Change GCP firewall `allow-tadss-api` source from `0.0.0.0/0` to your home IP (`/32`).
  Now lower priority since API key auth is in place.

### Infrastructure
- [ ] **Reserve Static IP for VM** — Medium
  Ephemeral IP changes on every VM restart, requiring manual `.env` update and dashboard restart.
  Run: `gcloud compute addresses create tadss-static-ip --region=us-central1`
  See: `docs/archive/ISSUE_DASHBOARD_NO_DATA_2026-03-07.md` for full setup steps.

- [ ] **Task 6: DBeaver SSH Tunnel** — completed as sqlite-web (2026-03-07), see docs/features/remote-db-access.md

### UX
- [ ] **Dashboard row click visual feedback** — Medium (30 min)
  Table rows look unclickable: no hover effect, no selected-row highlight. Add CSS hover + "View" button.
  File: `src/ui.py` — `render_positions_table()`
  See: `docs/archive/UX_BACKLOG.md` for full spec.

---

## Done

- [x] **Phase 8: Remove Redundant Scheduler Job** — completed 2026-03-08
  Removed `mtf_cache_prefetch` job (ran every 2h at :20). Now only `market_data_prefetch` runs every hour at :10, populating `ohlcv_universal` for all consumers. Scheduler jobs reduced from 4 → 3.

- [x] **Phase 6: Migrate Position Monitor to ohlcv_universal** — completed 2026-03-08
  Updated `src/monitor.py` to read from `ohlcv_universal` (read-only) with API fallback. Position checks now <100ms (was 2-5s), zero API calls per check. Deployed to VM and verified.

- [x] **Internal Market Database Architecture (Phases 1-5)** — completed 2026-03-08
  Single source of truth (ohlcv_universal), MarketDataOrchestrator service, scheduler integration, MTF scanner migration. 2,844 candles, 5/5 tests passed. See `docs/features/internal-market-database-architecture.md`.

- [x] **Market Data Caching Feature** — completed 2026-03-08
  Full cache-first architecture with status tracking, dashboard UI, API endpoints, and MTF integration. 68 tests passing. See `docs/features/market-data-caching.md`.

- [x] **Fix duplicate timeframe entries** — completed 2026-03-08
  Cleaned up old format entries (1w, 1week, 1d, 1h, 4h) that duplicated normalized formats. Added `_merge_timeframe_data()` to UI for handling remaining duplicates.

- [x] **MTF cache-first architecture** — completed 2026-03-08
  `mtf_cache_prefetcher.py` pre-populates cache; scheduler runs prefetch every 2h at :20; routes go cache-only (no live API calls from dashboard). Mirrors positions architecture.
- [x] **MTF persistent watchlist** — completed 2026-03-08
  DB-backed `mtf_watchlist` table; CRUD endpoints (GET/POST/DELETE); auto-seeds defaults; dashboard management panel.
- [x] **Wire TargetCalculator + auth + notifier into MTF routes** — completed 2026-03-08
  TargetCalculator integrated in alignment scorer; API key auth on all MTF routes; `send_mtf_opportunity_alert` called from scan endpoints.
- [x] **Comprehensive security audit** — completed 2026-03-07 (see devlog + security-audit.md)
- [x] **Task 4: Add API Key Authentication** — completed 2026-03-07
  `src/api/auth.py` + router-level `Depends()` + `X-API-Key` header in dashboard. Deployed and verified.
- [x] **sqlite-web read-only mode** — completed 2026-03-07 (`-r` flag added to startup command)
- [x] Core backend (FastAPI, SQLAlchemy, DataFetcher, TechnicalAnalyzer) — completed 2026-02-27
- [x] Automated monitoring with Telegram alerts — completed 2026-02-28
- [x] Streamlit dashboard skeleton — completed 2026-02-28
- [x] OTT indicator implementation — completed 2026-03-01
- [x] Unified health status logic — completed 2026-03-01
- [x] Important Indicators alert feature (MA10 + OTT early warnings) — completed 2026-03-01
- [x] Signal stability buffers (EMA 0.3%, MACD 0.01%) — completed 2026-03-01
- [x] Alert history database (`alert_history` table) — completed 2026-03-02
- [x] Signal changes tracking (`signal_changes` table) — completed 2026-03-02
- [x] Confirmed close signal calculation (`iloc[-2]`) — completed 2026-03-02
- [x] Scheduler cron trigger (fixed timing to :10 every hour) — completed 2026-03-02
- [x] `POST /scheduler/run-now` endpoint — completed 2026-03-02
- [x] Google Cloud deployment (production live 24/7) — completed 2026-03-04
- [x] Dashboard production API connection (`API_BASE_URL` env var) — completed 2026-03-05
- [x] VM IP moved to `.env` (not committed) — completed 2026-03-05
- [x] Fix duplicate function shadowing (dashboard "Backend Connection Lost") — completed 2026-03-07
- [x] Fix health check 404 (strip `/api/v1` before calling `/health`) — completed 2026-03-07
- [x] Fix API blocking on cache miss (cache-only routes) — completed 2026-03-07
- [x] Fix missing schema fields (Health/Signal always NEUTRAL) — completed 2026-03-07
- [x] Fix CCXT/Gate.io fetchers not saving to OHLCV cache — completed 2026-03-07
- [x] Fix XAUUSD h4 cache key mismatch (save under original timeframe) — completed 2026-03-07
- [x] Remote DB access via sqlite-web + SSH tunnel — completed 2026-03-07
- [x] Fix Telegram double anti-spam gating (BUG-013) — completed 2026-03-07
- [x] Fix raw SignalState enums passed to notifier (BUG-014) — completed 2026-03-07
- [x] Fix OTT missing from Telegram alert message (BUG-015) — completed 2026-03-07
- [x] Add startup Telegram message on container start — completed 2026-03-07
- [x] Add daily heartbeat message at 07:00 GMT+7 — completed 2026-03-07
- [x] Remove GitHub Actions workflow (superseded by VM scheduler) — completed 2026-03-07
- [x] Improve Telegram contradiction warning (graduated severity, OTT added, redundancy suppressed) — completed 2026-03-07
- [x] Sort positions table by pair name then timeframe shortest→longest — completed 2026-03-07
- [x] **MTF Scanner feature** (6 sessions, 2026-03-07) — HTF bias detector, MTF setup detector, LTF entry finder, alignment scorer, divergence detector, target calculator, S/R detector, opportunity scanner, 5 API endpoints, dashboard panel, Telegram alerts, 149 tests. See `docs/features/multi-timeframe-scanner.md`.
