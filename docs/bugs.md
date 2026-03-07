# Bug Tracker
_Last updated: 2026-03-07_

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
