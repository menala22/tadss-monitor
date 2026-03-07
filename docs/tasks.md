# Task Tracker
_Last updated: 2026-03-07_

---

## In Progress

_(none)_

---

## Backlog

### Security (Critical)
- [ ] **Comprehensive security audit** — NEXT SESSION
  Full review of all attack surfaces: API auth, SSH key exposure, firewall, secrets, Docker, sqlite-web write risk, data at rest.
  See [`docs/features/security-audit.md`](features/security-audit.md) for session plan.

- [ ] **Task 4: Add API Key Authentication** — CRITICAL
  Production API is open to the internet with no authentication. Anyone with the VM IP can read/modify positions.
  Implementation: add `API_SECRET_KEY` to `.env`, FastAPI middleware on protected endpoints, dashboard sends key in headers.
  See: `docs/archive/TASKS_2026-03-05.md` for full spec.

- [ ] **Task 5: Restrict Firewall to Your IP** — Medium
  Change GCP firewall `allow-tadss-api` source from `0.0.0.0/0` to your home IP (`/32`).

### Infrastructure
- [ ] **Reserve Static IP for VM** — Medium
  Ephemeral IP changes on every VM restart, requiring manual `.env` update and dashboard restart.
  Run: `gcloud compute addresses create tadss-static-ip --region=us-central1`
  See: `docs/archive/ISSUE_DASHBOARD_NO_DATA_2026-03-07.md` for full setup steps.

- [ ] **Task 6: DBeaver SSH Tunnel** — completed as sqlite-web (2026-03-08), see docs/features/remote-db-access.md

### UX
- [ ] **Dashboard row click visual feedback** — Medium (30 min)
  Table rows look unclickable: no hover effect, no selected-row highlight. Add CSS hover + "View" button.
  File: `src/ui.py` — `render_positions_table()`
  See: `docs/archive/UX_BACKLOG.md` for full spec.

---

## Done

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
- [x] Remote DB access via sqlite-web + SSH tunnel — completed 2026-03-08
- [x] Fix Telegram double anti-spam gating (BUG-013) — completed 2026-03-07
- [x] Fix raw SignalState enums passed to notifier (BUG-014) — completed 2026-03-07
- [x] Fix OTT missing from Telegram alert message (BUG-015) — completed 2026-03-07
- [x] Add startup Telegram message on container start — completed 2026-03-07
- [x] Add daily heartbeat message at 07:00 GMT+7 — completed 2026-03-07
- [x] Remove GitHub Actions workflow (superseded by VM scheduler) — completed 2026-03-07
- [x] Improve Telegram contradiction warning (graduated severity, OTT added, redundancy suppressed) — completed 2026-03-07
