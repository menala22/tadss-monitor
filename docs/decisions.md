# Decision Log
_Last updated: 2026-03-08_

---

## DEC-023: Remove stale-data pre-check from MTF Scanner — scan directly
- **Date**: 2026-03-08
- **Decision**: Remove the "check data status before scanning" step from the MTF Scanner UI. "Scan Now" fires the `/mtf/opportunities` API call immediately with `check_status=False`.
- **Alternatives considered**: Fix the Streamlit state-machine so "Scan Anyway" works correctly (attempted twice, introduced bugs each time); keep the pre-check but restructure as a proper state machine.
- **Rationale**: The pre-check added two extra round-trips and three possible failure modes, all to show a warning the user had to dismiss anyway. The API already handles missing data gracefully — pairs with no `ohlcv_universal` rows are skipped, and the `pairs_no_data` count in the response gives visibility. The user can always check the Market Data page for freshness. Simpler is safer.
- **Consequences**: Users see no stale-data warning before scanning. If data is missing for a pair, it just doesn't appear in results (and `pairs_no_data` tells them). The Market Data page is the right place to manage data quality — the scanner should just scan.

---

## DEC-021: Single ohlcv_universal table as source of truth
- **Date**: 2026-03-08
- **Decision**: Create new ohlcv_universal table as single source of truth for all market data, replacing scattered ohlcv_cache reads.
- **Alternatives considered**: Modify ohlcv_cache in-place; keep both tables indefinitely; migrate to PostgreSQL immediately.
- **Rationale**: ohlcv_cache has design issues (mixed timeframe formats, duplicate symbols, no provider tracking). New table allows clean schema, normalized data, and safe migration with rollback. PostgreSQL can wait until 10M+ rows.
- **Consequences**: Requires migration script and consumer updates. Enables clean architecture with read-only consumers and centralized orchestrator.

---

## DEC-022: Hourly prefetch at :10 for market data freshness
- **Date**: 2026-03-08
- **Decision**: Run MarketDataOrchestrator smart fetch every hour at :10 (same time as position monitoring).
- **Alternatives considered**: Every 2 hours at :20 (like MTF prefetch); separate time slot at :15 or :05; on-demand only.
- **Rationale**: Hourly ensures intraday timeframes (h4, h1) stay fresh. Same time as position monitoring reduces API call fragmentation. Smart fetch skips fresh data, minimizing actual API calls.
- **Consequences**: May cause API rate limiting if many symbols need refresh simultaneously. Monitor and adjust to :15 if issues arise.

---

## DEC-023: MTF scanner migration before position monitor
- **Date**: 2026-03-08
- **Decision**: Migrate MTF scanner to ohlcv_universal first, keep position monitor on ohlcv_cache temporarily.
- **Alternatives considered**: Migrate both simultaneously; migrate position monitor first.
- **Rationale**: MTF scanner is more complex (3 timeframes per pair) and benefits more from normalized data. Position monitor uses single timeframe per position—simpler to migrate later. Phased approach reduces risk.
- **Consequences**: Temporary dual-system (some consumers read ohlcv_cache, others read ohlcv_universal). Both tables kept in sync by orchestrator until full migration complete.

---

## DEC-020: Timeframe normalization with duplicate merging
- **Date**: 2026-03-08
- **Decision**: Normalize all timeframe strings to standard format (`w1`, `d1`, `h4`) and merge duplicate entries by keeping the best (highest candle count, best quality, newest fetched_at). UI uses `_merge_timeframe_data()` to handle any remaining duplicates.
- **Alternatives considered**: Store exact API format (creates duplicates); store multiple formats (complex); delete old formats entirely (risk of data loss).
- **Rationale**: Different APIs use different formats (Twelve Data: `1week`, CCXT: `1w`, internal: `w1`). Duplicates cause confusion (same data appears 3× with different quality ratings). Merging ensures UI shows best available data regardless of format.
- **Consequences**: Old format entries (`1w`, `1week`, `1d`, etc.) cleaned from database. UI handles transition gracefully. Future syncs should use normalized formats only.

---

## DEC-019: Quality-based data assessment with timeframe-relative thresholds
- **Date**: 2026-03-08
- **Decision**: Use 4-tier quality system (EXCELLENT, GOOD, STALE, MISSING) with thresholds based on candle count AND age relative to timeframe interval (e.g., d1 EXCELLENT = 200+ candles AND <48h old).
- **Alternatives considered**: Binary fresh/stale; absolute age thresholds (e.g., always 24h); candle count only.
- **Rationale**: Binary is insufficient — need to distinguish "perfect for HTF analysis" from "barely usable". Timeframe-relative age makes sense: 12h is stale for h4 but fresh for d1. EXCELLENT tier (200+ candles) required for full HTF 50/200 SMA analysis.
- **Consequences**: MTF readiness check uses quality thresholds. Dashboard shows visual badges (🟢🟡🔴). Prefetch job prioritizes STALE/MISSING pairs.

---

## DEC-018: Cache-first architecture for MTF scanner
- **Date**: 2026-03-08
- **Decision**: MTF scanner reads ONLY from cache, never makes live API calls during scan. User must explicitly refresh to populate cache. Prefetch job runs every 2h to keep cache fresh.
- **Alternatives considered**: Live fetch on cache miss (original); hybrid (fetch if stale); automatic refresh on staleness.
- **Rationale**: Scans should be instant (<1s). API calls are costly (Twelve Data: 800/day limit). Blocking scan on live fetch creates poor UX (30-60s wait). User-triggered refresh provides control and visibility.
- **Consequences**: Scan returns "no data" if cache empty — user must refresh. Requires separate refresh UI/UX. Prefetch job becomes critical infrastructure. 80% reduction in API usage.

---

## DEC-017: MTF scan route is cache-only — no live API calls from dashboard
- **Date**: 2026-03-08
- **Decision**: `_load_pair_data()` in `routes_mtf.py` reads from SQLite OHLCV cache only. If a timeframe has fewer than 10 candles, the pair is skipped with a "no data" message. The freshness check was removed — the scan trusts whatever is in the cache.
- **Alternatives considered**: Keep live-fetch fallback on cache miss; check freshness and return 503 if stale.
- **Rationale**: Live fetches block the request for 30-60s and hit rate limits. Freshness checks caused false negatives on weekends (gold closes Friday; h4 cache looks "stale" after 12h but no newer data exists). The prefetcher job handles keeping data fresh — the scan route should not duplicate that logic. Mirrors the positions architecture (DEC-011).
- **Consequences**: First scan after deploy will return "no data" for pairs not yet in cache. Prefetch job seeds the cache within 2h. Manual prefetch possible via VM exec.

---

## DEC-016: MTF cache prefetcher as a scheduled background job
- **Date**: 2026-03-08
- **Decision**: New `src/services/mtf_cache_prefetcher.py` job pre-populates OHLCV cache for all watchlist pairs × SWING + INTRADAY timeframes. Runs as APScheduler cron every 2 hours at :20 (10 minutes after position monitoring at :10, to avoid API concurrency).
- **Alternatives considered**: Trigger prefetch on first scan miss (lazy); run prefetch hourly; run per-style on demand.
- **Rationale**: Separates concerns cleanly: background job owns data freshness, scan route owns analysis. 2h cadence is well within freshness windows (h4=12h, d1=48h, w1=168h). Running at :20 avoids collision with the positions monitoring job at :10.
- **Consequences**: Scan always completes in <5s (no API calls). Cache may lag by up to 2h on a fresh VM restart. USDCAD and other invalid symbols will log prefetch errors and produce no-data on scan — acceptable.

---

## DEC-015: MTF scanner is stateless — no scan results persisted to DB
- **Date**: 2026-03-07
- **Decision**: MTF opportunity scans run fresh on every API call / dashboard trigger. Results are not saved to the database.
- **Alternatives considered**: Cache scan results in a new `mtf_scans` table; cache in Redis; cache in memory with TTL.
- **Rationale**: Scan results are only meaningful at the moment of generation — market conditions change every candle. Persisting them creates stale-data risk. The OHLCV cache (already in DB) handles data freshness. Adding a results table would add DB schema complexity for no user benefit in this use case.
- **Consequences**: Every scan hits the analysis pipeline. Acceptable latency for a personal tool with a small watchlist (5-10 pairs).

---

## DEC-014: HTF bias uses structural tools only — no oscillators
- **Date**: 2026-03-07
- **Decision**: HTF bias detection uses price structure (HH/HL, LH/LL sequences) and 50/200 SMA only. RSI and MACD are not used on the HTF.
- **Alternatives considered**: Include RSI divergence on HTF as a bias signal.
- **Rationale**: Oscillators on high timeframes (weekly, monthly) lag price by so many candles they add noise rather than signal. Price structure and trend-aligned MAs are sufficient and more reliable at that scale. This principle comes from the MTF strategy research in `docs/archive/research/multi_timeframe.md`.
- **Consequences**: HTF analysis requires 200+ candles for full SMA-200 calculation. With Gate.io/CCXT free tiers returning ~50-100 candles, HTF may return NEUTRAL bias when data is insufficient — a known limitation.

---

## DEC-013: API key auth via router-level Depends(), not middleware
- **Date**: 2026-03-07
- **Decision**: Implement API key authentication using a FastAPI `Depends(verify_api_key)` on the router, not as global ASGI middleware.
- **Alternatives considered**: ASGI middleware (apply to all routes including /health); per-endpoint Depends; reverse proxy (nginx) with auth.
- **Rationale**: Router-level `dependencies=[]` applies to all 9 routes in the router with one line, while leaving `/health` and `/` public by design. Middleware would require explicit exclusion logic for /health. Per-endpoint would need 9 additions. nginx adds infrastructure overhead not warranted for a personal tool.
- **Consequences**: `/health` and `/` remain unauthenticated (correct — health checks need no auth). Auth can be disabled for local dev by not setting `API_SECRET_KEY`. Key rotated by updating .env on VM + local machine.

---

## DEC-012: Graduated contradiction warning with 4 indicators
- **Date**: 2026-03-07
- **Decision**: Replace binary MA-only contradiction warning with 3-level graduated warning using MA10, MA20, MA50, OTT. Suppress when overall status already changed.
- **Alternatives considered**: Keep binary warning; show contradicting indicator names explicitly.
- **Rationale**: Binary (all-or-nothing on 3 MAs) was too rare to be useful and missed early turning signals. Graduated levels (2/4, 3/4, 4/4) act as an early warning before full status flip. OTT added because it's a trend indicator equally relevant to MAs. Suppression on "Status changed" avoids repeating information already in the reason line.
- **Consequences**: Warning now fires more often (at 2/4 instead of 3/3) — gives earlier signal to review the position.

---

## DEC-011: Remove GitHub Actions workflow — VM scheduler supersedes it
- **Date**: 2026-03-07
- **Decision**: Delete `.github/workflows/monitor.yml` and `scripts/github_monitor.py`.
- **Alternatives considered**: Keep GitHub Actions as a fallback; disable schedule but keep `workflow_dispatch`; archive to a separate folder.
- **Rationale**: The VM scheduler runs every hour with smart scanning, startup messages, and daily heartbeat — strictly more capable than the 4-hour GitHub Actions cron. Having both caused duplicate Telegram alerts. Git history preserves the code if ever needed. Archiving to a folder adds clutter with no benefit for a solo project.
- **Consequences**: No automated fallback if the VM goes down. Acceptable because the daily heartbeat at 07:00 GMT+7 serves as a dead-man's switch — silence means the VM is down.

---

## DEC-010: sqlite-web over DBeaver for remote SQLite access
- **Date**: 2026-03-07
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
