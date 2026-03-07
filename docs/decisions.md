# Decision Log
_Last updated: 2026-03-08_

---

## DEC-010: sqlite-web over DBeaver for remote SQLite access
- **Date**: 2026-03-08
- **Decision**: Use sqlite-web (browser-based) via SSH port forward instead of DBeaver with SSH tunnel.
- **Alternatives considered**: DBeaver (SSH tunnel tab), TablePlus, Beekeeper Studio, manual `scp` copy.
- **Rationale**: DBeaver does not show an SSH tunnel tab for SQLite connections — SQLite is file-based with no server port, so DBeaver's tunnel feature doesn't apply. sqlite-web requires no local app install, runs on the VM, and is accessed securely through the existing SSH connection via port forwarding. Zero new attack surface.
- **Consequences**: A terminal must stay open during each DB browsing session. sqlite-web query editor can run writes — treat it as read-only by discipline (avoid INSERT/UPDATE/DELETE).

---

## DEC-009: Save OHLCV cache under original requested timeframe, not fallback
- **Date**: 2026-03-07
- **Decision**: When Twelve Data free tier falls back from h4 → 1h, save the cache under the original key `h4`, not `1h`.
- **Alternatives considered**: Save under fallback key and adjust the lookup.
- **Rationale**: The position record stores the user's requested timeframe (e.g., h4). Cache lookup uses that same key. If we save under the fallback key, the lookup will always miss — simpler to save under the original key and accept the imprecision in the data.
- **Consequences**: XAUUSD h4 signal is derived from 1h data — a known limitation documented in MEMORY.md.

---

## DEC-008: Cache-only API routes — no live fetch in route handlers
- **Date**: 2026-03-07
- **Decision**: `list_open_positions()` and related routes read from OHLCV cache only. On cache miss, fall back to `entry_price`. Never call external APIs from within a route handler.
- **Alternatives considered**: Async background fetch triggered on cache miss.
- **Rationale**: Route handlers run synchronously in the FastAPI event loop. A live CCXT/Twelve Data call blocks the entire API for 30s+. The scheduler refreshes cache every hour — stale data for <1 hour is acceptable for this use case.
- **Consequences**: If the scheduler hasn't run yet after a VM restart, positions show 0% PnL until the next :10 scheduled run.

---

## DEC-007: Deploy on Google Cloud e2-micro (Always Free tier)
- **Date**: 2026-03-04
- **Decision**: Use Google Cloud e2-micro VM in us-central1 for 24/7 production hosting.
- **Alternatives considered**: Railway, Oracle Cloud ARM, Raspberry Pi, VPS ($5/month).
- **Rationale**: e2-micro qualifies for GCP Always Free tier — $0/month indefinitely. SSH + gcloud CLI already familiar. Docker support built-in.
- **Consequences**: Only 1 GB RAM — Streamlit dashboard can't run on VM alongside API. Dashboard runs locally. Dockerfile has `--platform linux/arm64` hardcoded (dev machine is arm64) which breaks full docker build on the amd64 VM — hot-copy deploy workaround required.

---

## DEC-006: Dashboard runs locally, connects to VM API via `API_BASE_URL`
- **Date**: 2026-03-05
- **Decision**: Streamlit dashboard is not deployed on the VM. It runs locally and connects to the production API using `API_BASE_URL` environment variable.
- **Alternatives considered**: Deploy dashboard on VM (port 8503), always run locally against localhost.
- **Rationale**: e2-micro has 1 GB RAM — running both FastAPI + Streamlit would strain resources. Dashboard is a personal tool used on demand, not a 24/7 service.
- **Consequences**: Must restart dashboard with `API_BASE_URL=http://<VM_IP>:8000/api/v1` after VM IP changes. VM IP is ephemeral (changes on restart) — static IP reservation is in backlog.

---

## DEC-005: OTT indicator implemented from TradingView Pine Script (MPL-2.0)
- **Date**: 2026-03-01
- **Decision**: Implement the Optimized Trend Tracker (OTT) indicator in Python, ported from the TradingView Pine Script by @kivancozbilgic and @Anil_Ozeksi.
- **Alternatives considered**: Use only EMA/MACD/RSI (simpler, already implemented).
- **Rationale**: OTT provides trend confirmation with dynamic trailing stops that complement the existing MA-based signals. Reduces false signals from shorter-term indicators. The Pine Script is open-source under MPL-2.0.
- **Consequences**: Added 400+ lines to `technical_analyzer.py`. OTT is now the 6th indicator in the signal aggregation (was 5). Default MA type is VAR (Variable Moving Average using CMO for adaptive smoothing).

---

## DEC-004: Signal stability buffers to prevent flip-flopping
- **Date**: 2026-03-01
- **Decision**: Add dead-band buffers to EMA (0.3%) and MACD (0.01% of price) signal transitions.
- **Alternatives considered**: No buffer (raw threshold crossing), larger buffer (>1%).
- **Rationale**: Without buffers, tiny price movements near signal thresholds caused rapid BULLISH/BEARISH flipping, generating excessive Telegram alerts. A 0.3% EMA buffer requires price to clearly cross before a signal change is recorded.
- **Consequences**: Signals lag real market moves by a small margin. Acceptable trade-off for reducing alert fatigue.

---

## DEC-003: Use confirmed close candle (`iloc[-2]`) for indicator calculations
- **Date**: 2026-03-02
- **Decision**: Calculate technical indicators using the second-to-last candle (last confirmed closed candle), not the current forming candle.
- **Alternatives considered**: Use `iloc[-1]` (current candle, matches real-time charting tools).
- **Rationale**: The current candle is still forming — its OHLC values change every second. Using it causes indicator values to fluctuate continuously, generating false signal changes. Professional trading platforms (TradingView, Bloomberg) calculate indicators on closed candles.
- **Consequences**: Signals lag current price by one candle period (e.g., 1 hour for h1). PnL calculation still uses the current candle's close price for accuracy.

---

## DEC-002: APScheduler cron trigger — always fires at :10 past every hour
- **Date**: 2026-03-02
- **Decision**: Use APScheduler `cron` trigger with `minute=10` instead of `interval` trigger.
- **Alternatives considered**: `interval` trigger (fires N hours after server start), system cron job, Celery beat.
- **Rationale**: `interval` trigger fired at unpredictable times relative to server start. Cron trigger is clock-based and predictable — always :10 past the hour. Users can anticipate when to expect alerts.
- **Consequences**: If the server starts at 10:05, first job fires at 11:10 — up to ~55 min wait. Acceptable for hourly monitoring.

---

## DEC-001: Anti-spam logic in alert system — only alert on changes
- **Date**: 2026-02-28
- **Decision**: Telegram alerts only fire when signal status changes (BULLISH → BEARISH or vice versa) or PnL crosses a threshold. No repeated alerts for the same state.
- **Alternatives considered**: Alert on every monitoring check, alert only at thresholds (no status change alerts).
- **Rationale**: Repeated alerts for the same state cause notification fatigue and lead users to mute the bot. Status changes are the actionable events.
- **Consequences**: First alert after server restart may fire even if status hasn't changed (no previous state in DB). Stored in `last_signal_status` column — persists across restarts once populated.
