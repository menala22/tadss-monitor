# Bug Tracker
_Last updated: 2026-03-08_

---

## BUG-023: "Scan Anyway" hardcodes check_status=True — MISSING pairs always excluded
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: Even if "Scan Anyway" correctly triggered the scan (see BUG-022), the API call hardcoded `check_status=True`. The server-side `scan_opportunities` endpoint excludes pairs with quality `"MISSING"` from `ready_pairs` entirely. So XAG/USD or USDCAD with no rows in `ohlcv_universal` would be silently dropped before the scanner touched them, producing 0 results even though data might exist.
- **Reproduce**: Add a new pair (e.g. USDCAD) to the watchlist. It has no data yet → quality "MISSING". Click Scan Now → Scan Anyway → 0 results.
- **Impact**: High — "Scan Anyway" never scanned MISSING pairs regardless of user intent.
- **Fix**: Added `mtf_skip_status_check` session state flag. Set to `True` when "Scan Anyway" is clicked. Consumed at scan time via `st.session_state.pop("mtf_skip_status_check", False)` and passed as `check_status=not skip_status`. With `check_status=False`, all pairs in the watchlist go into `ready_pairs` and the scanner attempts them all. Pairs with truly no data in `ohlcv_universal` are still skipped inside `_load_pair_data_from_universal` (returns None if <10 candles).

---

## BUG-022: "Scan Anyway" button never triggered the scan (Streamlit state-machine flaw)
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: Clicking "Scan Anyway" did nothing. Confirmed via VM logs: `/api/v1/mtf/opportunities` was never called from the dashboard. Two layers of failure:
  1. **Original bug**: button body was `pass` — no state set at all.
  2. **First fix attempt was also broken**: even after adding `st.session_state.mtf_scan_triggered = True; st.rerun()`, the button was still unreachable. The button lives inside `if stale_pairs and scan_button:`, which requires `scan_button=True`. On the rerun triggered by clicking "Scan Anyway", `scan_button=False` — so the outer `if scan_button or mtf_scan_triggered:` was `True` (via mtf_scan_triggered), but *inside* that block, `if stale_pairs and scan_button:` was `False`, meaning the button was **never rendered**. Streamlit only registers a button click on the run where the button is actually evaluated. Since the button wasn't evaluated, the click was silently lost. `mtf_scan_triggered` was never actually set.
- **Root cause**: Streamlit's single-run button model — buttons must be *rendered* in the run where their click is processed. Any button whose rendering is gated by `scan_button` (a per-run value) is unreachable on subsequent runs.
- **Fix**: Refactored scan execution into an explicit 3-step state machine:
  1. `if scan_button:` — status check; parks stale pairs in `mtf_pending_stale` session state.
  2. `if st.session_state.get("mtf_pending_stale"):` — always renders the warning + buttons, independent of `scan_button`. "Scan Anyway" clears `mtf_pending_stale`, sets `mtf_scan_triggered=True`, reruns.
  3. `elif st.session_state.get("mtf_scan_triggered"):` — runs the actual scan.
- **Key lesson**: In Streamlit, any UI that a user must interact with across multiple reruns must be driven by session state, not by the current run's button values.

---

## BUG-021: MTF Scanner "Scan Now" → Cannot connect to API (localhost fallback)
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: Clicking "Scan Now" in the MTF Scanner page always showed "Cannot connect to API. Check that the server is running." even though the VM API was reachable and the main dashboard worked fine.
- **Root cause**: `_get_api_base_url()` in `ui_mtf_scanner.py` only called `os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")` — no `.env` file fallback. If Streamlit is started without `API_BASE_URL=...` explicitly in the shell, the env var is absent and the function silently returns `localhost:8000`. The main dashboard (`ui.py`) worked because it reads the `.env` file at module load via `_load_api_url_from_env()`. `ui_mtf_scanner.py` had no equivalent.
- **Reproduce**: Start Streamlit with `streamlit run src/ui.py` (no `API_BASE_URL=...` prefix). Navigate to MTF Scanner → click Scan Now.
- **Impact**: High — MTF Scanner completely non-functional unless env var explicitly set in shell.
- **Fix**: Updated `_get_api_base_url()` in `ui_mtf_scanner.py` to follow the same 3-step priority chain as `ui.py`: (1) session state override, (2) `os.getenv("API_BASE_URL")`, (3) read `.env` file for `API_BASE_URL` then `VM_EXTERNAL_IP`, (4) localhost fallback. `ui_market_data.py` already had this fallback correctly.
- **Note**: `_get_api_headers()` in `ui_mtf_scanner.py` already read from `.env` (fixed in BUG-019). Only `_get_api_base_url()` was missing the fallback.

---

## BUG-020: RSI division by zero in mtf_setup_detector + mtf_entry_finder
- **Status**: Open (partially fixed)
- **Found**: 2026-03-08
- **Description**: XAG/USD scan fails with `float division by zero`. `_calculate_rsi()` in both `mtf_setup_detector.py` and `mtf_entry_finder.py` used `rs = gain / loss` — crashes when all candles in a rolling window are up (loss rolling mean = 0). Same bug existed in `divergence_detector.py` (fixed earlier).
- **Reproduce**: Scan XAG/USD in any style. Silver had a sustained uptrend period in the cached data.
- **Impact**: High — XAG/USD always fails to scan.
- **Fix (partial)**: Both files updated with `loss.replace(0, float("nan"))` + `rsi.fillna(100)`. Deployed. XAG/USD still failing — a second division by zero source remains (likely in `mtf_alignment_scorer.py` rr_ratio or `mtf_bias_detector.py` slope calculation).

---

## BUG-019: MTF dashboard sending requests without API key (401 on all MTF endpoints)
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: `_get_api_headers()` in `ui_mtf_scanner.py` only used `os.getenv("API_SECRET_KEY")`. Key wasn't in shell env — the dashboard relies on reading `.env` file directly (as `ui.py` does). All MTF requests returned 401.
- **Fix**: Added `.env` file fallback reader to `_get_api_headers()` in `ui_mtf_scanner.py`, matching the pattern in `ui.py`.

---

## BUG-018: CCXT exchange not initialized for BTC/USDT and ETH/USDT in MTF scan
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: `DataFetcher()` with no args defaults `source="twelvedata"`, `_exchange=None`. Auto-detect routes crypto to ccxt, but `_fetch_ccxt()` raised `RuntimeError` when `_exchange is None`.
- **Fix**: Added lazy CCXT initialization in `_fetch_ccxt()` — creates and loads exchange on first call if not already set.

---

## BUG-017: HTF bias returns NEUTRAL for all weekly data (200-candle minimum too high)
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: `HTFBiasDetector.detect_bias()` required `len(df) >= sma200_period` (200 candles) before running. Free-tier weekly data returns 50-100 candles max, so HTF always returned NEUTRAL.
- **Fix**: Lowered minimum to `sma50_period` (50). Added NaN-safe SMA-200 handling — when SMA-200 value is NaN (insufficient history), returns `PriceVsSMA.AT` (neutral) instead of spuriously BELOW.

---

## BUG-016: MTF watchlist 404 — endpoints not deployed to VM
- **Status**: Resolved
- **Found**: 2026-03-08
- **Resolved**: 2026-03-08
- **Description**: All MTF endpoints returned 404 — the MTF code (`routes_mtf.py`, models, services) had never been deployed to the VM. `main.py` in git also lacked the MTF router registration.
- **Fix**: Deployed all 16 new MTF files to VM via `gcloud compute scp` + `docker cp` + `docker restart`.

---

## BUG-015: OTT missing from Telegram alert message body
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: Telegram alerts showed only 5 indicators (MA10, MA20, MA50, MACD, RSI). OTT was tracked and could trigger alerts but never appeared in the message.
- **Fix**: Added OTT to the signals loop in `notifier._format_message`. See commit `8ddc6b3`.

---

## BUG-014: Raw SignalState enums passed to notifier — status comparison always wrong
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: `monitor.py` passed `signal.signal_states` containing `SignalState` enum objects directly to the notifier. `notifier._should_send_alert` compared against string literals (`"BULLISH"`) — always `False` for enums. `_format_message` rendered enum repr (`SignalState.BULLISH`) instead of the value string.
- **Fix**: `monitor.py` now converts signal_states to a plain `{str: str}` dict before calling notifier. `notifier._should_send_alert` also normalises with `.value` defensively. See commit `8ddc6b3`.

---

## BUG-013: Double anti-spam gating silently blocked valid Telegram alerts
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: `monitor._should_send_alert` correctly decided to send (6 indicators + MA10 + OTT independent checks), then called `notifier.send_position_alert`. The notifier ran its own `_should_send_alert` using only 5 indicators (no OTT) with broken enum handling — could return `False` even when monitor returned `True`. MA10 and OTT change alerts were silently dropped.
- **Fix**: `monitor.py` now passes `reason=reason` to `send_position_alert`. Notifier skips its internal gate when `reason` is provided by the caller. See commit `8ddc6b3`.

---

## BUG-012: XAUUSD h4 cache miss — saved under wrong timeframe key
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: XAUUSD h4 positions always showed 0% PnL. Cache was being saved under `1h` (Twelve Data free-tier fallback) but read with key `h4` → always a miss.
- **Fix**: `data_fetcher.py` — save OHLCV cache under the **original requested timeframe** (`h4`), not the fallback timeframe (`1h`). See commit `ad4d768`.

---

## BUG-011: ETHUSD and XAGUSD always 0% PnL
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: CCXT and Gate.io fetchers never called `save_ohlcv()` after fetching. Cache was empty → `routes.py` fell back to `entry_price` → PnL = 0%.
- **Fix**: Added `save_ohlcv()` call at end of both CCXT and Gate.io fetch paths in `data_fetcher.py`. See commit `417b9b3`.

---

## BUG-010: Health and Signal columns always showed NEUTRAL
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: Dashboard Health and Signal columns always displayed NEUTRAL regardless of actual indicator values.
- **Root cause**: `PositionWithPnL` Pydantic schema in `src/api/schemas.py` was missing `last_signal_status`, `last_important_indicators`, `health_status`, and `signal_summary` fields. FastAPI silently dropped them → dashboard received `None`.
- **Fix**: Added missing fields to `PositionWithPnL` schema. See commit `4746b66`.

---

## BUG-009: API blocking for 30+ seconds on cache miss
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: `list_open_positions()` route did live external API fetches on cache miss — up to 6 positions × 30s = 180s blocking. Dashboard consistently timed out.
- **Root cause**: Route handler called `fetcher.get_ohlcv()` synchronously on stale/missing cache, blocking the event loop.
- **Fix**: Removed live-fetch fallback from route entirely. Routes are cache-only; scheduler refreshes cache hourly. See commit `4746b66`.

---

## BUG-008: Test Connection button returned HTTP 404
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: Settings page "Test Connection" button always showed HTTP 404.
- **Root cause**: `test_api_connection()` called `{api_url}/health` where `api_url` already contained `/api/v1` → hit non-existent path. The `/health` endpoint is at the FastAPI root, not under the API router.
- **Fix**: Strip `/api/v1` prefix before appending `/health`. See commit `4746b66`.

---

## BUG-007: Dashboard showed "Backend Connection Lost" with correct IP
- **Status**: Resolved
- **Found**: 2026-03-07
- **Resolved**: 2026-03-07
- **Description**: Main page showed "Backend Connection Lost" even after updating VM IP to `34.171.241.166`.
- **Root cause**: `fetch_open_positions_from_api` was defined twice in `ui.py`. Python uses the last definition — a stale version at line 511 with `timeout=10s` silently overrode the correct version at line 118 with `timeout=60s`. The VM API took ~37s → 10s timeout → returned `None`.
- **Fix**: Removed duplicate definition. See commit `4746b66`.

---

## BUG-006: `POST /scheduler/run-now` returned 404
- **Status**: Resolved
- **Found**: 2026-03-02
- **Resolved**: 2026-03-02
- **Description**: Manual monitoring trigger via API returned 404 Not Found.
- **Root cause**: Endpoint was not registered in `src/api/routes.py`.
- **Fix**: Added `run_monitoring_now()` endpoint to routes.

---

## BUG-005: Scheduler fired at unpredictable times
- **Status**: Resolved
- **Found**: 2026-03-02
- **Resolved**: 2026-03-02
- **Description**: User received alert at 10:55 instead of expected 10:10. Scheduler timing was relative to server start time.
- **Root cause**: Used APScheduler `interval` trigger, which calculates first run from start time.
- **Fix**: Changed to `cron` trigger with `minute=10` — always fires at :10 past the hour regardless of start time.

---

## BUG-004: Signals based on incomplete (forming) candles — false alerts
- **Status**: Resolved
- **Found**: 2026-03-02
- **Resolved**: 2026-03-02
- **Description**: Indicators calculated on the current (still-forming) candle caused false signal changes and unnecessary alerts.
- **Fix**: Changed `TechnicalAnalyzer` to use `df.iloc[-2]` (confirmed closed candle) for signal calculation. Current candle still used for PnL. Matches professional standard (TradingView, Bloomberg).

---

## BUG-003: Alert logging bypass — no DB records of sent alerts
- **Status**: Resolved
- **Found**: 2026-03-02
- **Resolved**: 2026-03-02
- **Description**: Alerts were being sent but not logged to `alert_history` table.
- **Root cause**: `monitor.py` called internal `_send_with_retry()` directly, bypassing the `send_position_alert()` method that handles DB logging. Also had a duplicate parameter bug causing `TypeError`.
- **Fix**: Updated `monitor.py` to use `send_position_alert()` which includes DB logging.

---

## BUG-002: P&L showing 0% for all positions
- **Status**: Resolved
- **Found**: 2026-02-28
- **Resolved**: 2026-02-28
- **Description**: Dashboard main table showed 0.00% PnL for every position.
- **Root cause**: `fetch_position_with_signals_simple()` used `entry_price` as `current_price` instead of fetching live market price.
- **Fix**: Updated function to fetch real current price from CCXT/yfinance. Also improved page load from 18s → <1s by fetching only 1 candle for main table (full signals loaded on-demand in detail view).

---

## BUG-001: No version control — unable to revert changes
- **Status**: Resolved
- **Found**: 2026-02-28
- **Resolved**: 2026-02-28
- **Description**: Development session made multiple rapid changes to `src/ui.py` without git initialized. User requested revert — impossible with no version control.
- **Impact**: High — multiple hours of work at risk, no safe recovery path.
- **Fix**: Initialized git repository, created initial commit, pushed to GitHub (`github.com/menala22/tadss-monitor`). Established commit-before-change workflow.
