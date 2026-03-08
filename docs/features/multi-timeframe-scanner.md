# Feature: Multi-Timeframe (MTF) Scanner
_Status: Done_
_Last updated: 2026-03-07_

## What It Does

Scans multiple trading pairs for high-probability setups by analyzing three timeframes simultaneously (Higher → Middle → Lower). Scores alignment 0-3, filters by R:R ratio, and surfaces entry/stop/target levels. Exposes results via API, dashboard panel, and Telegram alerts.

**Goal:** Transforms the system from "monitor existing positions" to "detect new opportunities."

---

## Architecture / Logic Flow

```
Data (OHLCV cache / live fetch)
         |
         v
  [HTF Bias Detector]  [MTF Setup Detector]  [LTF Entry Finder]
   50/200 SMA            20/50 SMA              20 EMA
   Price structure        RSI divergence         Candlestick patterns
   Key S/R levels         Pullback / breakout    EMA reclaim / RSI turn
         |                      |                      |
         +----------------------+----------------------+
                                |
                                v
                    [Alignment Scorer]
                     3/3 = HIGHEST
                     2/3 = GOOD
                     1/3 = POOR
                     0/3 = AVOID
                                |
              +-----------------+-----------------+
              v                 v                 v
    [Target Calculator]  [Divergence Detector]  [Opportunity Scanner]
     5 methods             4 types (reg/hidden)   Pattern matching
     S/R, Fib, ATR         bullish/bearish         Filter by min alignment
     Measured move                                 Filter by min R:R
              |
   +----------+----------+
   v          v          v
API (5      Dashboard  Telegram
routes)     Panel      Alerts (throttled)
```

**Trading style timeframe mapping:**

| Style | HTF | MTF | LTF | Best For |
|-------|-----|-----|-----|----------|
| POSITION | Monthly | Weekly | Daily | Long-term |
| SWING | Weekly | Daily | 4H | Swing traders (default) |
| INTRADAY | Daily | 4H | 1H | Day traders |
| DAY | 4H | 1H | 15M | Full-time traders |
| SCALPING | 1H | 15M | 5M | High-frequency |

---

## Key Design Decisions

- **HTF uses structural tools only** — 50/200 SMA + price structure (HH/HL, LH/LL). No RSI or MACD on HTF (lag too much at that scale). See research basis in `docs/archive/research/multi_timeframe.md`.
- **MTF is stateless** — no scan results persisted in DB. Each API call or dashboard scan runs fresh analysis. Acceptable latency for the use case; avoids stale-state bugs.
- **Separate router, not integrated into position monitor** — MTF opportunity scanning is an independent workflow from position health monitoring. Keeps concerns separated; `routes_mtf.py` can be developed/tested independently.
- **Alignment threshold 2/3 default** — 3/3 is rare; 1/3 is noise. 2/3 balances signal quality vs opportunity frequency. Users can override via API param or dashboard slider.
- **Alert throttle 3/day** — prevents fatigue from high-frequency styles (DAY/SCALPING can produce many signals).

---

## Out of Scope

- Backtesting (future enhancement)
- Persisting scan history to DB
- Position sizing recommendations
- Elliott Wave / harmonic patterns
- Mobile push notifications (Telegram only)

---

## As Built
_Added after implementation — 2026-03-07_

### Files Created (21 total)

**Core services (9):**
- `src/models/mtf_models.py` — 14 enums, 10 dataclasses
- `src/services/mtf_bias_detector.py` — HTF bias (50/200 SMA, price structure)
- `src/services/mtf_setup_detector.py` — pullback, breakout, divergence, consolidation
- `src/services/mtf_entry_finder.py` — candlestick patterns, EMA reclaim, RSI turn
- `src/services/mtf_alignment_scorer.py` — 0-3 scoring + MTFAnalyzer orchestrator
- `src/services/divergence_detector.py` — 4 RSI divergence types
- `src/services/target_calculator.py` — 5 target methods
- `src/services/support_resistance_detector.py` — swing, volume, round numbers, converging
- `src/services/mtf_opportunity_scanner.py` — multi-pair scanner with filters

**API, UI, alerts (3):**
- `src/api/routes_mtf.py` — 5 REST endpoints
- `src/ui_mtf_scanner.py` — Streamlit dashboard panel
- `src/services/mtf_notifier.py` — Telegram alerts (opportunity, divergence, daily summary)

**Modified (3):**
- `src/main.py` — MTF router registered
- `src/ui.py` — MTF Scanner page added
- `src/services/ohlcv_cache_manager.py` — extended for multi-TF support

**Tests (6 files, 149 tests):**
- `tests/test_mtf/test_mtf_models.py` — 32 tests
- `tests/test_mtf/test_htf_bias_detector.py` — 24 tests
- `tests/test_mtf/test_mtf_setup_detector.py` — 24 tests
- `tests/test_mtf/test_ltf_entry_finder.py` — 24 tests
- `tests/test_mtf/test_mtf_alignment_scorer.py` — 24 tests
- `tests/test_mtf/test_session3_components.py` — 21 tests

**Scripts:**
- `scripts/generate_mtf_report.py` — CLI report generator (live data)

### What Changed from Design

- `mtf_analyzer.py` was planned as a standalone class file but got folded into `mtf_alignment_scorer.py` as `MTFAnalyzer` — reduced file count, same result.
- Gate.io integration for XAGUSD/XAUUSD was added mid-build (Session 3) — not in original plan. `data_fetcher.py` updated to support swap contract format fallback.
- `POST /api/v1/mtf/scan` endpoint planned — implemented as `GET /api/v1/mtf/opportunities` with query params instead. POST body felt like overengineering for a simple scan trigger.

### Known Limitations

- HTF bias detector needs 200+ candles for full analysis; Gate.io and CCXT free tiers return ~50-100 candles. HTF analysis may show NEUTRAL bias when data is insufficient.
- XAUUSD h4 uses 1h data as proxy (Twelve Data free tier doesn't support 4h). Affects MTF signal quality for that pair.
- MTF scanner uses the same OHLCV cache as the position monitor. If cache is cold (VM just restarted), MTF scans may return no results until the scheduler's :10 run populates it.
- No backtesting — signals are live-only.

### Follow-up Tasks

- Backtesting framework (historical signal testing, win rate stats)
- Machine learning for confidence score optimization
- Portfolio-level correlation analysis across MTF opportunities
- Restrict firewall port 8000 (Task 5 — low priority since API key auth is in)

---

## Related Docs

- **User guide:** [`docs/features/mtf-user-guide.md`](mtf-user-guide.md)
- **Strategy research:** [`docs/archive/research/multi_timeframe.md`](../archive/research/multi_timeframe.md)
- **Build session logs:** [`docs/archive/mtf-sessions/`](../archive/mtf-sessions/)
- **Example reports:** [`docs/reports/`](../reports/)
