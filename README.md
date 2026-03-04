# TA-DSS: Post-Trade Position Monitoring System

> **Technical Analysis Decision Support System** for monitoring manually-executed trading positions with automated technical analysis and Telegram alerts.

**Status:** 🟢 Phase 4 Complete - Dashboard & Advanced Features
**Last Updated:** 2026-03-04
**Python:** 3.12.9
**Tests:** 117 passing (100%)

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

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.12+ (we use 3.12.9 via pyenv)
- pip (Python package manager)

### 1. Clone & Setup Environment
```bash
cd trading-order-monitoring-system
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Telegram credentials
```

### 4. Initialize Database
```bash
python -m src.database init
```

### 5. Run Tests (Optional)
```bash
pytest tests/ -v
# Expected: 117 tests passing
```

### 6. Start API Server
```bash
uvicorn src.main:app --reload
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 7. Launch Dashboard
```bash
streamlit run src/ui.py --server.port 8503
```

**Access:**
- Dashboard: http://localhost:8503
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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

## 🚧 Next Steps (Phase 5: Deployment)

1. **GitHub Actions Deployment** – Scheduled monitoring via GitHub Actions (FREE, 2,000 min/month)
2. **Docker Deployment** – Container configuration for production VMs
3. **Real-time Updates** – WebSocket integration for live price updates
4. **Position Health Visualization** – Charts and graphs for signal trends
5. **Enhanced Dashboard** – More interactive features and filters

See [`DEPLOYMENT_GITHUB_ACTIONS.md`](DEPLOYMENT_GITHUB_ACTIONS.md) for deployment guide.

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

## 📋 Phase 4 Completion Summary

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
2. Scheduler automatically checks every hour at :10 minutes (XX:10 UTC)
3. Fetches live data from CCXT/yfinance with retry logic
4. Calculates technical signals (EMA 10/20/50, MACD, RSI, **OTT**)
5. Compares with previous status (overall + MA10 + OTT independently)
6. Sends Telegram alert if:
   - Overall status changed (BULLISH → BEARISH)
   - MA10 status changed (independent tracking)
   - OTT status changed (independent tracking)
   - PnL < -5% (Stop Loss Warning)
   - PnL > +10% (Take Profit Warning)
7. Updates database with new status
8. Logs all signal changes to `signal_changes` table
9. View all positions on Dashboard with live PnL and signals

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
