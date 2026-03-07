# TA-DSS: Post-Trade Position Monitoring System

> **Technical Analysis Decision Support System** — monitors manually-executed trading positions with automated technical analysis and Telegram alerts.

_Status: Stable — production live on Google Cloud_
_Last updated: 2026-03-07_

---

## What It Does

TA-DSS monitors trading positions you've logged manually. Every hour at :10 it fetches live prices, calculates technical signals (EMA, MACD, RSI, OTT), evaluates position health, and sends Telegram alerts when signals turn against your position or PnL crosses a threshold.

**You log the trade → system monitors it 24/7 → you get alerted when action is needed.**

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/positions/open` | Log a new trade |
| `GET` | `/api/v1/positions/open` | List open positions with PnL + signals |
| `POST` | `/api/v1/positions/{id}/close` | Close a position |
| `DELETE` | `/api/v1/positions/{id}` | Delete a position |
| `GET` | `/api/v1/positions/scheduler/status` | Scheduler status |
| `POST` | `/api/v1/positions/scheduler/run-now` | Trigger immediate monitoring check |
| `POST` | `/api/v1/positions/scheduler/test-alert` | Send test Telegram alert |

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
│   ├── api/
│   │   ├── routes.py                  # FastAPI endpoints (cache-only reads)
│   │   └── schemas.py                 # Pydantic request/response models
│   ├── models/
│   │   ├── position_model.py          # Position ORM model
│   │   ├── alert_model.py             # Alert history
│   │   ├── signal_change_model.py     # Signal change log
│   │   └── ohlcv_cache_model.py       # OHLCV cache
│   └── services/
│       ├── technical_analyzer.py      # EMA, MACD, RSI, OTT calculations
│       ├── signal_engine.py           # Health evaluation
│       ├── ohlcv_cache_manager.py     # Cache read/write, timeframe normalisation
│       └── position_service.py        # Position CRUD
├── tests/                             # 117 unit tests (100% passing)
├── scripts/
│   ├── run-dashboard-production.sh    # Launch dashboard → production API
│   └── push-db-to-production.sh       # DB sync utility
├── docker/
│   └── docker-compose.yml
├── docs/
│   ├── devlog.md                      # Session-by-session progress log
│   ├── tasks.md                       # Backlog + done list
│   ├── bugs.md                        # Bug history (BUG-001 → BUG-012)
│   ├── decisions.md                   # Tech decision log (DEC-001 → DEC-009)
│   ├── changelog.md                   # Feature changelog by milestone
│   ├── features/                      # Per-feature design docs
│   ├── deployment/                    # Deployment guides (GCP, Docker, CI)
│   └── archive/                       # Session logs, research, planning
├── CLAUDE.md                          # AI session context + skill registry
├── .env.example                       # Environment template
└── requirements.txt
```

---

## Testing

```bash
pytest tests/ -v          # all 117 tests
pytest tests/test_ott.py  # OTT indicator only
```

---

## Deployment

Production runs on Google Cloud e2-micro VM (us-central1, Always Free tier — $0/month).

- API + scheduler: 24/7 inside Docker container `tadss`
- Dashboard: local, connects via `API_BASE_URL`
- Deploy code changes: `docker cp src/<file>.py tadss:/app/src/<file>.py && docker restart tadss`
  (Full `docker build` fails on VM — Dockerfile has `--platform linux/arm64` hardcoded)

See [`docs/deployment/google-cloud.md`](docs/deployment/google-cloud.md) for full setup.
See [`docs/deployment/github-actions.md`](docs/deployment/github-actions.md) for CI-based deploy.

---

## Status / Known Issues

- Production is stable. 6 open positions monitored.
- VM IP is ephemeral — update `API_BASE_URL` in `.env` after any VM restart.
- Twelve Data free tier does not support 4h interval → XAUUSD h4 uses 1h price as proxy.
- API authentication not yet implemented — port 8000 is open to the internet (Task 4, CRITICAL backlog).

See [`docs/bugs.md`](docs/bugs.md) for full issue history.
See [`docs/tasks.md`](docs/tasks.md) for open backlog.
