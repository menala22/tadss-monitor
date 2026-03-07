# TA-DSS: Post-Trade Position Monitoring System

> **Technical Analysis Decision Support System** for monitoring manually-executed trading positions with automated technical analysis and Telegram alerts.

**Status:** 🟢 Phase 5 Complete - Production Deployment on Google Cloud
**Last Updated:** 2026-03-04
**Python:** 3.12.9
**Tests:** 117 passing (100%)
**Deployment:** ✅ Live on Google Cloud (24/7, $0/month)

---

## 📖 What Is This?

TA-DSS is a **post-trade monitoring system** for traders who:

1. Execute trades manually on external exchanges (Binance, Coinbase, etc.)
2. Log those trades into this system for monitoring
3. Receive automated technical analysis signals (RSI, MACD, EMA)
4. Get **Telegram alerts** when positions show warning/critical signals

**Key Value:** Never wonder "Should I close this trade?" – the system monitors your positions 24/7 and alerts you when technical signals turn against your position or when price moves significantly.

---

## ✨ Key Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Position Logging** | Manually log trades after execution | ✅ Complete |
| **Technical Analysis** | RSI, MACD, EMA, **OTT** calculations via pandas_ta | ✅ Complete |
| **Signal Generation** | BULLISH/BEARISH/NEUTRAL signals per indicator | ✅ Complete |
| **Position Health** | HEALTHY/WARNING/CRITICAL status evaluation | ✅ Complete |
| **Data Fetching** | yfinance (stocks) + CCXT (crypto) with retry logic | ✅ Complete |
| **REST API** | FastAPI backend with full CRUD operations | ✅ Complete |
| **Database** | SQLite (MVP) with PostgreSQL-ready schema | ✅ Complete |
| **Telegram Alerts** | Notifications on status changes (spam-free) | ✅ Complete |
| **Background Scheduler** | Automated monitoring every hour at :10 | ✅ Complete |
| **Dashboard** | Streamlit UI with 3 pages (Open Positions, Add Position, Settings) | ✅ Complete |
| **Independent MA10/OTT Tracking** | Separate alerts for MA10 and OTT signal changes | ✅ Complete |
| **Signal Change Logging** | Track all signal changes for backtesting | ✅ Complete |
| **24/7 Cloud Deployment** | Google Cloud e2-micro VM (free tier, $0/month) | ✅ Complete |

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.12+ (we use 3.12.9 via pyenv)
- pip (Python package manager)

### Option A: Local Development

#### 1. Clone & Setup Environment
```bash
cd trading-order-monitoring-system
source venv/bin/activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Telegram credentials
```

#### 4. Initialize Database
```bash
python -m src.database init
```

#### 5. Run Tests (Optional)
```bash
pytest tests/ -v
# Expected: 117 tests passing
```

#### 6. Start API Server
```bash
uvicorn src.main:app --reload
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### 7. Launch Dashboard

**Option A: Local Development (API server running on your laptop)**
```bash
streamlit run src/ui.py --server.port 8503
```

**Option B: Production API (API server on Google Cloud)**

Choose one of these methods:

**Method 1: Production Script (Recommended)**
```bash
./scripts/run-dashboard-production.sh
```

**Method 2: Environment Variable**
```bash
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

**Method 3: UI Toggle (In Dashboard Settings)**
```bash
# 1. Start dashboard normally
streamlit run src/ui.py --server.port 8503

# 2. Go to Settings (⚙️) → API Connection
# 3. Select "🌐 Production (Google Cloud)"
# 4. Click "Test Connection" to verify
```

**Access:**
- Dashboard: http://localhost:8503
- API (Local): http://localhost:8000
- API (Production): http://VM_EXTERNAL_IP:8000 (see `.env`)
- API Docs: http://localhost:8000/docs or http://VM_EXTERNAL_IP:8000/docs

**Note:** 
- Local mode: Dashboard connects to `localhost:8000` (API server must run locally)
- Production mode: Dashboard connects to `VM_EXTERNAL_IP:8000` (Google Cloud API, see `.env`)

---

### Option B: Production Deployment (Google Cloud)

**Already deployed!** The system is running 24/7 on Google Cloud Platform.

**Production VM:** See `.env` file for `VM_EXTERNAL_IP`

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│ Google Cloud Platform (us-central1)                     │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ e2-micro VM (2 vCPU, 1 GB RAM, 30 GB disk)       │ │
│  │                                                   │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │ Docker Container (TA-DSS API + Scheduler)   │ │ │
│  │  │  - FastAPI :8000 (24/7)                     │ │ │
│  │  │  - APScheduler (every hour at :10)          │ │ │
│  │  │  - SQLite Database                          │ │ │
│  │  │  - Telegram Bot Integration                 │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │
         │ HTTPS API
         ▼
┌─────────────────────────────────────────────────────────┐
│ Your Laptop (Dashboard - On Demand)                     │
│                                                         │
│  ./scripts/run-dashboard-production.sh                 │
│  - Connects to production API                          │
│  - View positions, charts, alerts                       │
│  - Run only when needed (not 24/7)                      │
└─────────────────────────────────────────────────────────┘
```

**Access:**
- **API:** `http://VM_EXTERNAL_IP:8000` (see `.env`)
- **API Docs:** `http://VM_EXTERNAL_IP:8000/docs`
- **Health Check:** `http://VM_EXTERNAL_IP:8000/health`

**Dashboard (3 Ways to Connect to Production):**

**Option 1: Production Script (Recommended)**
```bash
./scripts/run-dashboard-production.sh
```

**Option 2: Environment Variable**
```bash
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

**Option 3: UI Toggle (In Dashboard)**
```bash
# 1. Start dashboard normally
streamlit run src/ui.py --server.port 8503

# 2. Go to Settings page (⚙️)
# 3. Select "🌐 Production (Google Cloud)"
# 4. Click "Test Connection" to verify
# 5. Go to Open Positions (📋) to view data
```

- Opens at: http://localhost:8503
- Connects to production API (see `.env` for `VM_EXTERNAL_IP`)
- Run only when you want to view positions

**Why This Setup?**
- ✅ **API + Scheduler:** 24/7 on Google Cloud (no laptop needed)
- ✅ **Telegram Alerts:** Automatic (sent to your phone)
- ✅ **Dashboard:** On-demand (open when you want to check positions)
- ✅ **VM Resources:** Preserved (e2-micro has 1 GB RAM limit)
- ✅ **Security:** Dashboard not exposed to internet

**Deployment Guide:** See [`DEPLOYMENT_GOOGLE_CLOUD_GUIDE.md`](DEPLOYMENT_GOOGLE_CLOUD_GUIDE.md)

**Cost:** $0/month (Google Cloud free tier)

---

## 📡 API Endpoints

### Positions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/positions/open` | Log a new trade |
| `GET` | `/api/v1/positions/open` | List active positions |
| `GET` | `/api/v1/positions` | List all positions |
| `GET` | `/api/v1/positions/{id}` | Get position details |
| `POST` | `/api/v1/positions/{id}/close` | Close a position |
| `DELETE` | `/api/v1/positions/{id}` | Delete a position |

### Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/positions/scheduler/status` | Get scheduler status |
| `POST` | `/api/v1/positions/scheduler/test-alert` | Send test Telegram alert |

### Example: Create Position
```bash
curl -X POST http://localhost:8000/api/v1/positions/open \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTCUSD",
    "entry_price": 50000,
    "position_type": "LONG",
    "timeframe": "h4"
  }'
```

**Response:**
```json
{
  "id": 1,
  "pair": "BTCUSD",
  "entry_price": 50000.0,
  "position_type": "LONG",
  "timeframe": "h4",
  "status": "OPEN",
  "entry_time": "2026-02-28T14:00:00"
}
```

---

## 🔧 Technical Components

### 1. Database Layer (`src/models/`, `src/database.py`)
- SQLAlchemy ORM with Position model
- SQLite for MVP, PostgreSQL-ready
- Session management with dependency injection
- Signal tracking columns for spam prevention

### 2. Data Fetching (`src/data_fetcher.py`)
- **yfinance:** Stocks, ETFs, indices
- **CCXT:** 100+ crypto exchanges (Binance default)
- Retry logic (3 attempts, exponential backoff)
- Data validation (null checks, empty checks)

### 3. Technical Analysis (`src/services/technical_analyzer.py`)
| Indicator | Parameters | Signal Rules |
|-----------|------------|--------------|
| EMA | 10, 20, 50 | BULLISH if Close > MA |
| MACD | 12, 26, 9 | BULLISH if Histogram > 0 |
| RSI | 14 | BULLISH if > 50, OVERBOUGHT if > 70 |
| **OTT** | Trend-following overlay | BULLISH if Close > OTT |

**OTT (Overlay Trend Trigger):** Advanced trend-following indicator that adapts to market volatility. Provides earlier trend change signals compared to traditional moving averages.

### 4. Signal Engine (`src/services/signal_engine.py`)
Evaluates position health by comparing signals vs position direction:

| Position | Signals | Health | Action |
|----------|---------|--------|--------|
| LONG | Mostly BULLISH | HEALTHY | Maintain |
| LONG | Mostly BEARISH | CRITICAL | Close/Reduce |
| SHORT | Mostly BEARISH | HEALTHY | Maintain |
| SHORT | Mostly BULLISH | CRITICAL | Cover/Reduce |

### 5. Notification Service (`src/notifier.py`)
- Lightweight Telegram integration (requests library)
- Anti-spam logic (only alerts on significant changes)
- Markdown formatting for mobile readability
- Error handling with retry logic

### 6. Background Scheduler (`src/scheduler.py`)
- APScheduler AsyncIOScheduler
- Runs every hour at :10 minutes past the hour (fixed schedule)
- Non-blocking background thread
- Graceful shutdown on app close

### 7. Position Monitor (`src/monitor.py`)
- Orchestrates full monitoring workflow
- Fetches data → Analyzes → Alerts → Updates DB
- Configurable PnL thresholds (-5% stop loss, +10% take profit)
- **Independent MA10/OTT tracking** - alerts on individual indicator changes
- Comprehensive logging to `logs/monitor.log`

### 8. Dashboard (`src/ui.py`)
- Streamlit-based web interface with 3 pages:
  - **📋 Open Positions:** Summary cards, position table, detailed view with charts
  - **➕ Add New Position:** Form with validation, preset pairs, quick entry
  - **⚙️ Settings:** System info, Telegram config, scheduler status, thresholds
- Real-time position monitoring with live PnL calculations
- Signal breakdown with OTT integration
- Conflict detection (e.g., LONG position with bearish MAs)
- Responsive design (mobile-friendly)

### 9. API Layer (`src/api/`)
- FastAPI with automatic OpenAPI docs
- Pydantic validation for all requests
- CORS enabled for frontend integration

---

## 📁 Project Structure

```
trading-order-monitoring-system/
├── src/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Settings & timeframe validation
│   ├── database.py                # DB initialization & sessions
│   ├── data_fetcher.py            # yfinance/CCXT data fetching
│   ├── notifier.py                # Telegram notifications
│   ├── monitor.py                 # Position monitoring orchestrator
│   ├── scheduler.py               # Background scheduler (APScheduler)
│   ├── ui.py                      # Streamlit dashboard
│   │
│   ├── api/
│   │   ├── schemas.py             # Pydantic models
│   │   └── routes.py              # API endpoints
│   │
│   ├── models/
│   │   ├── position_model.py      # SQLAlchemy models
│   │   ├── alert_model.py         # Alert history tracking
│   │   └── signal_change_model.py # Signal change logging
│   │
│   ├── services/
│   │   ├── position_service.py       # Position CRUD
│   │   ├── market_data_service.py    # Market data
│   │   ├── technical_analyzer.py     # Technical indicators (EMA, MACD, RSI, OTT)
│   │   ├── signal_engine.py          # Position health evaluation
│   │   └── notification_service.py   # Telegram service
│   │
│   ├── schedulers/
│   │   └── __init__.py
│   │
│   ├── utils/
│   │   └── helpers.py             # Utility functions
│   │
│   └── tests/
│       └── test_alert_logging.py  # Alert logging tests
│
├── tests/
│   ├── test_signal_engine.py      # 31 tests - Position health logic
│   ├── test_data_fetcher.py       # 25 tests - Data fetching
│   ├── test_scheduler.py          # 28 tests - APScheduler integration
│   ├── test_notifier.py           # 26 tests - Telegram alerts
│   └── test_ott.py                # 7 tests - OTT indicator
│
├── data/                          # SQLite database (git-ignored)
│   └── positions.db
├── logs/                          # Application logs (git-ignored)
│   ├── monitor.log               # Monitoring logs
│   ├── data_fetch.log            # Data fetch logs
│   └── telegram.log              # Telegram notification logs
│
├── .github/
│   └── workflows/
│       └── monitor.yml           # GitHub Actions scheduled monitoring
│
├── .env                           # Environment variables (git-ignored)
├── .env.example                   # Environment template
├── requirements.txt               # Dependencies
├── test_monitor.py                # Manual monitoring test script
├── PROJECT_STATUS.md              # Detailed progress report
├── CHANGELOG.md                   # Version history
├── DEPLOYMENT_GITHUB_ACTIONS.md   # GitHub Actions deployment guide
├── DEPLOYMENT_GOOGLE_CLOUD_GUIDE.md  # ✅ Google Cloud deployment (PRODUCTION)
├── DEPLOYMENT_RAILWAY_GUIDE.md    # Railway.app deployment guide
└── SECURITY_CHECKLIST.md          # Security guidelines
```

---

## 🧪 Testing

**Test Coverage:** 117 tests (100% passing)

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_monitor.py -v  # Manual test script
pytest tests/test_scheduler.py -v
pytest tests/test_notifier.py -v
pytest tests/test_ott.py -v
```

**Test Categories:**
- Signal engine: LONG/SHORT scenarios, health scores, alert logic (31 tests)
- Data fetcher: Retry logic, validation, logging, DataFrame structure (25 tests)
- Scheduler: APScheduler integration, job registration (28 tests)
- Notifier: Telegram anti-spam, message formatting, retry logic (26 tests)
- OTT indicator: Trend-following overlay validation (7 tests)

---

## 🔐 Security

See [`SECURITY_CHECKLIST.md`](SECURITY_CHECKLIST.md) for complete guidelines.

**Quick Summary:**
- ✅ `.env` files never committed
- ✅ Database and logs excluded from git
- ✅ API keys via environment variables only
- ✅ Type validation on all inputs
- ✅ SQL injection protected (SQLAlchemy ORM)

---

## 📊 Current Progress

| Component | Progress | Tests |
|-----------|----------|-------|
| Project Setup | 100% | - |
| Database Layer | 100% | - |
| Configuration | 100% | - |
| Backend API | 100% | - |
| Data Fetching | 100% | 25 ✅ |
| Technical Analysis | 100% | - |
| Signal Engine | 100% | 31 ✅ |
| Telegram Notifications | 100% | 26 ✅ |
| Background Scheduler | 100% | 28 ✅ |
| Position Monitor | 100% | Manual test ✅ |
| Dashboard (Phase 4) | 100% | UI tested ✅ |
| **Core Backend** | **100%** | **117/117 ✅** |
| **Overall** | **~98%** | **100% ✅** |

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for detailed progress report.

---

## 🚧 Next Steps (Phase 6: Enhancements)

1. **Multi-timeframe Analysis** – Scan positions across multiple timeframes
2. **Performance Optimization** – Reduce API call latency, add caching
3. **Enhanced Dashboard** – Advanced filtering, charts, export features
4. **Backtesting Module** – Test strategies on historical data
5. **Position Sizing Calculator** – Risk management tools
6. **Multiple Strategies** – Run different scan strategies simultaneously

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for detailed roadmap.

---

## 🤝 How to Contribute

### For Developers
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes with tests
3. Run tests: `pytest tests/ -v`
4. Update `CHANGELOG.md` with your changes
5. Submit pull request

### For Non-Technical Stakeholders
1. Review `PROJECT_STATUS.md` weekly for updates
2. Test new features via API docs: http://localhost:8000/docs
3. Report issues via [GitHub Issues](link-to-your-repo) or email

---

## 📞 Support

| Role | Contact |
|------|---------|
| Development | TT |
| Questions | [Your Email] |
| Documentation | See `PROJECT_STATUS.md` |

---

## 📄 License

[Your License Here – MIT/Apache 2.0 recommended]

---

## 🙏 Acknowledgments

- **FastAPI** – Modern Python web framework
- **yfinance** – Yahoo Finance market data
- **CCXT** – Crypto exchange trading library
- **pandas_ta** – Technical analysis library
- **SQLAlchemy** – Python SQL toolkit
- **APScheduler** – Python scheduling library
- **python-telegram-bot** – Telegram Bot API

---

**Built with ❤️ for traders who want data-driven decisions**

---

## 📋 Phase 5 Completion Summary

**Completed:** 2026-03-04

### Key Achievements (Phase 5 - Production Deployment)
- ✅ **Google Cloud e2-micro VM deployed** (us-central1 region)
- ✅ **24/7 operation** - No laptop required
- ✅ **Free tier** - $0/month (Always Free eligible)
- ✅ **Docker containerization** - Consistent deployment
- ✅ **Auto-restart** - Container restarts on failure
- ✅ **Firewall configured** - Port 8000 open for API access
- ✅ **Health monitoring** - Google Cloud Monitoring enabled
- ✅ **Database persistence** - SQLite on persistent disk
- ✅ **Telegram alerts working** - Production verified
- ✅ **Scheduler running** - Every hour at :10 minutes
- ✅ **Backup strategy** - Weekly database backups
- ✅ **Log rotation** - Prevents disk full issues

### Production Architecture
```
┌─────────────────────────────────────────────────────────┐
│ Google Cloud Platform (us-central1)                     │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ e2-micro VM (2 vCPU, 1 GB RAM, 30 GB disk)       │ │
│  │                                                   │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │ Docker Container (TA-DSS)                   │ │ │
│  │  │  - FastAPI :8000                            │ │ │
│  │  │  - APScheduler (every hour at :10)          │ │ │
│  │  │  - SQLite Database                          │ │ │
│  │  │  - Telegram Bot Integration                 │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  │                                                   │ │
│  │  Firewall: Port 8000 (API), Port 22 (SSH)        │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Access: API from anywhere, SSH from your laptop       │
└─────────────────────────────────────────────────────────┘
```

### Production URLs
- **API:** `http://YOUR_VM_IP:8000`
- **API Docs:** `http://YOUR_VM_IP:8000/docs`
- **Health Check:** `http://YOUR_VM_IP:8000/health`

### Deployment Resources
- **Guide:** [`DEPLOYMENT_GOOGLE_CLOUD_GUIDE.md`](DEPLOYMENT_GOOGLE_CLOUD_GUIDE.md)
- **Troubleshooting:** Section 9 (Real Deployment Issues)
- **Monitoring:** Google Cloud Console → Monitoring
- **Cost:** $0.00/month (verified)

---

## 📋 Phase 4 Completion Summary (Previous)

**Completed:** 2026-03-01

### Key Achievements (Phase 3 + 4)
- ✅ Automated position monitoring every hour at :10 minutes
- ✅ Telegram alerts on signal changes and PnL thresholds
- ✅ **Independent MA10/OTT tracking** - separate alerts for each indicator
- ✅ **OTT indicator integration** - advanced trend-following signals
- ✅ Anti-spam logic (no duplicate alerts)
- ✅ Database tracking for signal history (alert_history, signal_changes tables)
- ✅ Comprehensive logging (`logs/monitor.log`, `logs/telegram.log`)
- ✅ Manual test script (`test_monitor.py`)
- ✅ 117 unit tests (100% passing)
- ✅ Streamlit dashboard with 3 pages (Open Positions, Add Position, Settings)
- ✅ Add new position form with validation
- ✅ Settings page (Telegram config, thresholds, system info)
- ✅ Responsive design (mobile-friendly)
- ✅ Signal change logging for backtesting

### What's Working
1. Log a position via API or Dashboard
2. Scheduler automatically checks every hour at :10 (Google Cloud)
3. Fetches live data from CCXT/yfinance with retry logic
4. Calculates technical signals (EMA 10/20/50, MACD, RSI, **OTT**)
5. Compares with previous status (overall + MA10 + OTT independently)
6. Sends Telegram alert if:
   - Overall status changed (BULLISH ↔ BEARISH)
   - MA10 status changed (independent tracking)
   - OTT status changed (independent tracking)
   - PnL < -5% (Stop Loss Warning)
   - PnL > +10% (Take Profit Warning)
7. Updates database with new status
8. Logs all signal changes to `signal_changes` table
9. View all positions on Dashboard with live PnL and signals

### Deployment Architecture

**Production (24/7):**
- **Platform:** Google Cloud e2-micro VM (us-central1)
- **Components:** FastAPI API + APScheduler + SQLite Database
- **Access:** `http://YOUR_VM_IP:8000`
- **Cost:** $0/month (Always Free tier)

**Dashboard (On-Demand):**
- **Platform:** Your laptop (local)
- **Components:** Streamlit UI
- **Access:** http://localhost:8503 (when running)
- **Command:** `streamlit run src/ui.py --server.port 8503`

**Why This Setup?**
- API + Scheduler run 24/7 (no laptop needed)
- Telegram alerts work automatically (phone notifications)
- Dashboard runs on-demand (open when you want to view positions)
- Preserves VM resources (e2-micro has 1 GB RAM limit)
- Dashboard not exposed to internet (more secure)

### Dashboard Features
- 📊 Summary cards (Total, Long, Short, Warnings)
- 📋 Position details table with PnL and signals
- 🔍 Detailed position view with:
  - Price metrics (Entry, Current, PnL %)
  - All 6 indicators (EMA 10/20/50, MACD, RSI, OTT)
  - Signal conflict warnings
  - Health status with recommendations
  - Candlestick chart with EMAs
- ➕ Add new position form
- ⚙️ Settings page (Telegram config, thresholds)
- 🔄 Manual refresh button
- 📱 Responsive design for mobile

### Alert System
| Alert Type | Trigger | Independent Tracking |
|------------|---------|---------------------|
| Overall Status | BULLISH ↔ BEARISH change | ✅ Yes |
| MA10 | BULLISH ↔ BEARISH change | ✅ Yes |
| OTT | BULLISH ↔ BEARISH change | ✅ Yes |
| Stop Loss | PnL < -5% | ✅ Yes |
| Take Profit | PnL > +10% | ✅ Yes |
| Daily Summary | Once per day (optional) | ✅ Yes |

### Ready for Phase 5
All core features are complete. Ready for production deployment:
- **GitHub Actions:** FREE, 2,000 minutes/month (see `DEPLOYMENT_GITHUB_ACTIONS.md`)
- **Docker/VM:** For 24/7 deployment (see `DEPLOYMENT_247_GUIDE.md`)
