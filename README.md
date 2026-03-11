# TA-DSS: Post-Trade Position Monitoring System

> **Technical Analysis Decision Support System** — monitors manually-executed trading positions with automated technical analysis and Telegram alerts.

_Status: Stable — production live on Google Cloud_
_Last updated: 2026-03-10_

---

## What It Does

TA-DSS monitors trading positions you've logged manually. Every hour at :10 it fetches live prices, calculates technical signals (EMA, MACD, RSI, OTT), evaluates position health, and sends Telegram alerts when signals turn against your position or PnL crosses a threshold.

**You log the trade → system monitors it 24/7 → you get alerted when action is needed.**

---

## Latest: Market Data Orchestrator Fixes (v0.5.1)

**Resolved:** Three critical data architecture issues affecting market data quality.

### Issues Fixed

1. **BUG-032: Hourly Candle Corruption** — Hourly data showed only midnight timestamps (00:00:00) due to timeframe mapping fallback (`1h` → `1day`). Fixed by adding API format passthrough mappings.

2. **Dual-Cache Writes** — Data was being written to two tables (`ohlcv_cache` and `ohlcv_universal`) with different formats, causing redundant API calls and rate limit issues. Fixed by removing all cache writes from DataFetcher.

3. **Twelve Data 4h Limitation** — Free tier doesn't support 4h interval. Fixed by implementing 1h → 4h aggregation (4× 1h candles → 1× 4h candle).

### Impact

- **Hourly data coverage**: 1/24 hours → 24/24 hours ✅
- **h4 data availability**: 0 candles (failing) → 201 candles for XAU/USD ✅
- **Cache tables written**: 2 tables → 1 table (`ohlcv_universal` only) ✅
- **All verification tests passing** ✅

See [`docs/analysis-market-data-orchestrator-fix.md`](docs/analysis-market-data-orchestrator-fix.md) for complete details.

---

## New: Twelve Data Rate Limit Fix

**Resolved:** API rate limiting issues causing stale data for XAU/USD, USD/CAD, WTI pairs.

The system was exceeding Twelve Data's free tier limits (8 calls/minute, 800/day) due to burst requests at :20 each hour. Four solutions implemented:

1. **Per-Call Rate Limiting** - 8-second delay between Twelve Data API calls
2. **Spread Prefetch** - Fetches spread across 30-60s with 12s spacing for Twelve Data
3. **Reduced Frequency** - 50% reduction in fetch frequency (h1: 4h→2h, h4: 12h→6h, d1: 48h→24h)
4. **Forex to CCXT** - USD/CAD, EUR/USD moved to Kraken (free, no rate limits)

**Impact:** 54% reduction in API usage (~358 → ~166 calls/day), 79% reduction in burst rate.

See [`docs/reports/twelve-data-rate-limit-fix-summary.md`](docs/reports/twelve-data-rate-limit-fix-summary.md) for complete implementation details.

---

## New: MTF Report Generator with Charts

**Generate professional MTF analysis reports with interactive charts and data quality validation.**

The MTF Report Generator creates comprehensive trading analysis reports with:
- **Interactive HTML charts** - Zoom, pan, hover for detailed analysis
- **Data quality dashboard** - Validates data sufficiency and freshness
- **Validation warnings** - Alerts when data quality is compromised
- **Complete documentation** - Full logic explanation and examples

### Quick Start - Report Generator

```bash
# Generate report with charts (default: BTC/USDT SWING)
python scripts/generate_mtf_report.py BTC/USDT SWING

# Output:
# - Markdown report with embedded charts
# - Interactive HTML report (Plotly)
# - 4 PNG charts in charts/ folder
```

### Features

**📊 Interactive Charts:**
- Candlestick charts with SMAs/EMAs
- 4 synchronized panels (HTF, MTF, LTF, Alignment)
- Zoom, pan, hover tooltips
- Professional institutional quality

**✅ Data Quality Dashboard:**
- Candle count validation (HTF: 200, MTF: 50, LTF: 50)
- Freshness check (hours old per timeframe)
- Overall status (PASS/WARNING/FAIL)
- Actionable recommendations

**⚠️ Validation Warnings:**
- Prominent warnings when data is insufficient/stale
- MTF readiness check
- Recommendations to improve data quality

### Output Structure

```
docs/reports/
├── BTCUSDT-mtf-analysis-swing-20260308.md          ← Main report
├── BTCUSDT-mtf-analysis-interactive-20260308.html  ← Interactive HTML
└── charts/
    ├── BTCUSDT-htf-analysis.png
    ├── BTCUSDT-mtf-setup.png
    ├── BTCUSDT-ltf-entry.png
    └── BTCUSDT-alignment.png
```

### Documentation

- **Complete Logic:** [`docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md`](docs/MTF-ANALYSIS-LOGIC-EXPLAINED.md)
- **Report Improvements:** [`docs/MTF-REPORT-IMPROVEMENTS-FINAL.md`](docs/MTF-REPORT-IMPROVEMENTS-FINAL.md)
- **Chart Guide:** [`docs/mtf-report-with-charts-guide.md`](docs/mtf-report-with-charts-guide.md)
- **HTML Reports:** [`docs/mtf-interactive-html-summary.md`](docs/mtf-interactive-html-summary.md)

---

## New: Multi-Timeframe (MTF) Scanner

**Detect high-probability trading opportunities automatically.**

The MTF Scanner analyzes multiple timeframes simultaneously to find trades where:
- Higher timeframe trend aligns with middle timeframe setup
- Lower timeframe provides precise entry timing
- Risk:reward ratio meets minimum threshold (default 2:1)

### Quick Start - MTF Scanner

**Dashboard:**
```bash
streamlit run src/ui.py --server.port 8503
# Navigate to "🔍 MTF Scanner"
```

**API:**
```bash
# Scan for opportunities
curl "http://localhost:8000/api/v1/mtf/opportunities?trading_style=SWING&min_alignment=2"

# Get timeframe configs
curl "http://localhost:8000/api/v1/mtf/configs"
```

**Telegram Alerts:**
- Automatic for 3/3 alignment opportunities
- Maximum 3 alerts per day (throttled)
- Configure in `.env` with `TELEGRAM_BOT_TOKEN`

See [`docs/features/mtf-user-guide.md`](docs/features/mtf-user-guide.md) for the full user guide.
See [`docs/features/multi-timeframe-scanner.md`](docs/features/multi-timeframe-scanner.md) for architecture and design notes.

---

## New: MTF Opportunity Tracking System

**Automated hourly MTF scanning with opportunity persistence and Telegram alerts.**

The MTF Opportunity Tracking System automatically scans for trading opportunities every hour at :30 using the upgraded 4-layer MTF framework:

**What It Does:**
- **Hourly Scanning** - Runs automatically at :30 past every hour
- **4-Layer Framework** - Context classification, setup detection, quality scoring, weighted alignment
- **Database Persistence** - All opportunities saved to `mtf_opportunities` table
- **Telegram Alerts** - Sent for high-conviction setups (weighted score ≥ 0.60)
- **Auto-Expiration** - Opportunities expire after 24 hours
- **Dashboard Integration** - View all opportunities in "💼 MTF Opportunities" page

**Dashboard:**
```bash
streamlit run src/ui.py --server.port 8503
# Navigate to "💼 MTF Opportunities"
```

**API:**
```bash
# List active opportunities with minimum weighted score
curl "http://localhost:8000/api/v1/mtf-opportunities?status=ACTIVE&min_weighted_score=0.60"

# Get statistics
curl "http://localhost:8000/api/v1/mtf-opportunities/stats"

# Filter by context
curl "http://localhost:8000/api/v1/mtf-opportunities?mtf_context=TRENDING_PULLBACK"
```

**Architecture:**
- **Data Source:** `ohlcv_universal` table (read-only, no live API calls)
- **Scan Schedule:** Every hour at :30 (after market data prefetch at :20)
- **Quality Filtering:** Weighted score ≥ 0.50 to save, ≥ 0.60 to alert
- **No Throttling:** All qualifying opportunities trigger alerts
- **Context-Aware:** TRENDING_EXTENSION setups excluded (overextended markets)

**4-Layer Framework:**
1. **Layer 1: Context Classification** - ADX, ATR, EMA distance determine market state
2. **Layer 2: Context-Gated Setup Detection** - Only valid setups for the context run
3. **Layer 3: Pullback Quality Scoring** - 5-factor weighted score (distance, RSI, volume, confluence, structure)
4. **Layer 4: Weighted Alignment** - Confidence-weighted scoring + position sizing

See [`docs/features/mtf-opportunities-workplan.md`](docs/features/mtf-opportunities-workplan.md) for architecture and design notes.

---

## New: Market Data Status Dashboard

**Monitor cached data quality and freshness across all pairs.**

The Market Data Status page provides:
- **Real-time quality tracking** — 🟢 EXCELLENT/GOOD, 🟡 STALE, 🔴 MISSING
- **Timeframe breakdown** — candle count and last update per timeframe
- **One-click refresh** — refresh individual pairs or all stale pairs at once
- **MTF readiness** — see which pairs are ready for scanning

### Quick Start - Market Data

**Dashboard:**
```bash
streamlit run src/ui.py --server.port 8503
# Navigate to "📈 Market Data"
```

**API:**
```bash
# Get all pairs status
curl "http://localhost:8000/api/v1/market-data/status"

# Get summary statistics
curl "http://localhost:8000/api/v1/market-data/summary"

# Refresh all stale pairs
curl -X POST "http://localhost:8000/api/v1/market-data/refresh-all"
```

**Benefits:**
- MTF scans complete in <1 second (was 5-15s)
- Zero API calls during scanning (all from cache)
- 80% reduction in API usage (Twelve Data: 800/day → ~160/day)

See [`docs/features/market-data-caching.md`](docs/features/market-data-caching.md) for architecture and design notes.

---

## Quick Start

### Prerequisites
- Python 3.12+
- Telegram bot token + chat ID (for alerts)

### Local development

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add Telegram credentials, API keys

# 4. Initialize database
python -m src.database init

# 5. Start API server
uvicorn src.main:app --reload
# → API: http://localhost:8000
# → API docs: http://localhost:8000/docs

# 6. Launch dashboard (separate terminal)
streamlit run src/ui.py --server.port 8503
# → Dashboard: http://localhost:8503
```

### Connect dashboard to production VM

```bash
# Recommended — reads VM IP from .env automatically
./scripts/run-dashboard-production.sh

# Or explicitly
API_BASE_URL=http://<VM_IP>:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

> If VM IP changed after restart, update `API_BASE_URL` in `.env` and restart the dashboard with the explicit form above.

---

## Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Telegram chat/user ID | `-1001234567890` |
| `API_BASE_URL` | Production VM API URL (dashboard) | `http://34.x.x.x:8000/api/v1` |
| `TWELVE_DATA_API_KEY` | Twelve Data key (XAUUSD, forex) | `abc123...` |
| `MONITOR_INTERVAL` | Scheduler interval in seconds | `3600` |

See `.env.example` for the full list.

---

## How It Works

- **Scheduler** → runs every hour at :10 → calls monitor for each open position
- **Data fetcher** → Twelve Data (XAUUSD, forex), Gate.io (XAGUSD), CCXT/Kraken (ETHUSD, crypto) → saves to OHLCV cache
- **Technical analyzer** → calculates EMA 10/20/50, MACD, RSI, OTT on confirmed closed candle
- **Signal engine** → evaluates % of signals aligned with position direction → HEALTHY / WARNING / CRITICAL
- **Notifier** → sends Telegram alert on status change, MA10/OTT flip, or PnL threshold breach
- **API routes** → cache-only reads (never block on live fetch); scheduler keeps cache fresh
- **Dashboard** → Streamlit UI (local), connects to VM API via `API_BASE_URL`

See [`docs/features/`](docs/features/) for per-component design docs.

---

## API Endpoints

### Positions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/positions/open` | Log a new trade |
| `GET` | `/api/v1/positions/open` | List open positions with PnL + signals |
| `POST` | `/api/v1/positions/{id}/close` | Close a position |
| `DELETE` | `/api/v1/positions/{id}` | Delete a position |
| `GET` | `/api/v1/positions/scheduler/status` | Scheduler status |
| `POST` | `/api/v1/positions/scheduler/run-now` | Trigger immediate monitoring check |
| `POST` | `/api/v1/positions/scheduler/test-alert` | Send test Telegram alert |

### MTF Analysis (New)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/mtf/opportunities` | Scan for MTF opportunities |
| `GET` | `/api/v1/mtf/opportunities/{pair}` | Single pair analysis |
| `GET` | `/api/v1/mtf/configs` | Timeframe configurations |
| `POST` | `/api/v1/mtf/scan` | On-demand scan |
| `GET` | `/api/v1/mtf/watchlist` | Get watchlist |

Full interactive docs: `http://localhost:8000/docs` or `http://<VM_IP>:8000/docs`

---

## Project Structure

```
trading-order-monitoring-system/
├── src/
│   ├── main.py                        # FastAPI app + lifespan
│   ├── config.py                      # Settings, timeframe validation
│   ├── database.py                    # DB init, session management
│   ├── data_fetcher.py                # Twelve Data / Gate.io / CCXT fetchers
│   ├── notifier.py                    # Telegram alerts
│   ├── monitor.py                     # Monitoring orchestrator
│   ├── scheduler.py                   # APScheduler (cron, :10 every hour)
│   ├── ui.py                          # Streamlit dashboard
│   ├── ui_mtf_scanner.py              # MTF Scanner dashboard panel
│   ├── api/
│   │   ├── routes.py                  # FastAPI endpoints (cache-only reads)
│   │   └── routes_mtf.py              # MTF analysis endpoints
│   │   └── schemas.py                 # Pydantic request/response models
│   ├── models/
│   │   ├── position_model.py          # Position ORM model
│   │   ├── alert_model.py             # Alert history
│   │   ├── signal_change_model.py     # Signal change log
│   │   ├── mtf_models.py              # MTF data models (NEW)
│   │   └── ohlcv_cache_model.py       # OHLCV cache
│   └── services/
│       ├── technical_analyzer.py      # EMA, MACD, RSI, OTT calculations
│       ├── signal_engine.py           # Health evaluation
│       ├── ohlcv_cache_manager.py     # Cache read/write, timeframe normalisation
│       ├── position_service.py        # Position CRUD
│       ├── mtf_bias_detector.py       # HTF bias detection (NEW)
│       ├── mtf_setup_detector.py      # MTF setup identification (NEW)
│       ├── mtf_entry_finder.py        # LTF entry signals (NEW)
│       ├── mtf_alignment_scorer.py    # Alignment scoring (NEW)
│       ├── divergence_detector.py     # RSI divergence (NEW)
│       ├── target_calculator.py       # 5 target methods (NEW)
│       ├── support_resistance_detector.py  # S/R levels (NEW)
│       ├── mtf_opportunity_scanner.py # Opportunity scanner (NEW)
│       └── mtf_notifier.py            # MTF Telegram alerts (NEW)
├── tests/
│   ├── test_mtf/                      # MTF unit tests (NEW)
│   │   ├── test_mtf_models.py
│   │   ├── test_htf_bias_detector.py
│   │   ├── test_mtf_setup_detector.py
│   │   ├── test_ltf_entry_finder.py
│   │   ├── test_mtf_alignment_scorer.py
│   │   └── test_session3_components.py
│   └── ...
├── scripts/
│   ├── run-dashboard-production.sh    # Launch dashboard → production API
│   └── push-db-to-production.sh       # DB sync utility
├── docker/
│   └── docker-compose.yml
├── docs/
│   ├── features/
│   │   ├── multi-timeframe-scanner.md      # MTF feature: architecture + as-built
│   │   └── mtf-user-guide.md               # MTF user guide
│   ├── archive/
│   │   ├── mtf-sessions/                   # Build session logs (Sessions 1-6)
│   │   └── research/                       # Strategy research notes
│   └── ...
├── CLAUDE.md                          # AI session context + skill registry
├── .env.example                       # Environment template
└── requirements.txt
```

---

## Testing

```bash
# All tests
pytest tests/ -v

# MTF tests only
pytest tests/test_mtf/ -v

# OTT indicator only
pytest tests/test_ott.py
```

**Test Coverage:**
- Core system: 117 tests
- MTF feature: 149 tests
- **Total: 266 tests passing**

---

## Deployment

Production runs on Google Cloud e2-micro VM (us-central1, Always Free tier — $0/month).

- API + scheduler: 24/7 inside Docker container `tadss`
- Dashboard: local, connects via `API_BASE_URL`
- VM: `tadss-vm` (34.171.241.166) in us-central1-a

### Quick Deploy

**Single file:**
```bash
docker cp src/<file>.py tadss:/app/src/<file>.py && docker restart tadss
```

**Multiple files (recommended):**
```bash
./scripts/deploy-mtf-opportunities-fix.sh
```

**Full feature deployment:**
```bash
# Use comprehensive deployment script
./scripts/deploy-mtf-opportunities-fix.sh

# Or manual gcloud deployment
./scripts/deploy-with-gcloud.sh
```

### Important Deployment Notes

1. **Clear Python cache after deploying Python files:**
   ```bash
   docker exec tadss find /app -type d -name __pycache__ -exec rm -rf {} +
   docker stop tadss && docker start tadss
   ```

2. **Run migrations after model changes:**
   ```bash
   docker exec tadss python -m src.migrations.migrate_[name] run
   ```

3. **Verify imports after deployment:**
   ```bash
   docker exec tadss python -c "from src.module import X; print('OK')"
   ```

### Deployment Documentation

- **Complete Guide:** [`docs/deployment/google-cloud.md`](docs/deployment/google-cloud.md)
- **MTF Deployment Fix:** [`docs/MTF-OPPORTUNITIES-DEPLOYMENT-FIX.md`](docs/MTF-OPPORTUNITIES-DEPLOYMENT-FIX.md)
- **Deployment Scripts:** [`scripts/deploy-mtf-opportunities-fix.sh`](scripts/deploy-mtf-opportunities-fix.sh)

See [`docs/deployment/google-cloud.md`](docs/deployment/google-cloud.md) for full setup.
See [`docs/deployment/github-actions.md`](docs/deployment/github-actions.md) for CI-based deploy.

---

## Status / Known Issues

- Production is stable. 6 open positions monitored.
- **MTF Scanner: Complete** — Dashboard panel, API endpoints, Telegram alerts all functional.
- **API key auth active** — all `/api/v1/positions/*` routes require `X-API-Key` header; `/health` is public.
- VM IP is ephemeral — update `API_BASE_URL` in `.env` after any VM restart.
- Twelve Data free tier does not support 4h interval → XAUUSD h4 uses 1h price as proxy.
- Firewall port 8000 open to 0.0.0.0/0 — mitigated by API key auth (Task 5 = optional hardening).

See [`docs/bugs.md`](docs/bugs.md) for full issue history.
See [`docs/tasks.md`](docs/tasks.md) for open backlog.

---

## MTF Feature Summary

**Implementation complete in 6 sessions:**

| Session | Focus | Files Created |
|---------|-------|---------------|
| 1 | Models + HTF Bias | `mtf_models.py`, `mtf_bias_detector.py` |
| 2 | Setup + Entry + Alignment | `mtf_setup_detector.py`, `mtf_entry_finder.py`, `mtf_alignment_scorer.py` |
| 3 | Advanced Detection | `divergence_detector.py`, `target_calculator.py`, `support_resistance_detector.py`, `mtf_opportunity_scanner.py` |
| 4 | API + Cache | `routes_mtf.py`, OHLCV cache extension |
| 5 | Dashboard + Alerts | `ui_mtf_scanner.py`, `mtf_notifier.py` |
| 6 | Documentation | README update, session summaries |

**Total:** ~5,000 lines of code, 149 tests, 266 tests total

See [`docs/features/multi-timeframe-scanner.md`](docs/features/multi-timeframe-scanner.md) for architecture and design.
See [`docs/features/mtf-user-guide.md`](docs/features/mtf-user-guide.md) for the user guide.
