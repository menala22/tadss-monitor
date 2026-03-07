# TA-DSS Dashboard Documentation

**Version:** 1.0.0  
**Last Updated:** March 5, 2026  
**Platform:** Streamlit Web Application  
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Dashboard Architecture](#3-dashboard-architecture)
4. [Page 1: Open Positions](#4-page-1-open-positions)
5. [Page 2: Add New Position](#5-page-2-add-new-position)
6. [Page 3: Settings](#6-page-3-settings)
7. [API Connection Modes](#7-api-connection-modes)
8. [Features Guide](#8-features-guide)
9. [Technical Details](#9-technical-details)
10. [Troubleshooting](#10-troubleshooting)
11. [Security Considerations](#11-security-considerations)

---

## 1. Overview

### 1.1 What Is the Dashboard?

The TA-DSS Dashboard is a **Streamlit-based web interface** for monitoring manually-executed trading positions with real-time technical analysis signals, PnL tracking, and Telegram alert management.

**Key Value:**
- View all your trading positions in one place
- See real-time technical signals (EMA, MACD, RSI, OTT)
- Monitor position health (HEALTHY / WARNING / CRITICAL)
- Add new positions without API calls
- Configure system settings

### 1.2 Key Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-time Position Monitoring** | View all open positions with live PnL | ✅ |
| **Technical Analysis Signals** | 6 indicators per position (EMA, MACD, RSI, OTT) | ✅ |
| **Position Health Status** | HEALTHY / WARNING / CRITICAL evaluation | ✅ |
| **Interactive Charts** | Candlestick charts with EMAs | ✅ |
| **Add New Position** | Form with validation and preset pairs | ✅ |
| **Close/Delete Positions** | One-click position management | ✅ |
| **API Mode Toggle** | Switch between Local ↔ Production | ✅ |
| **Telegram Integration** | Test alerts, view configuration | ✅ |
| **Scheduler Status** | View monitoring schedule and next run | ✅ |
| **Connection Testing** | Test API connectivity from UI | ✅ |

### 1.3 Supported Data Sources

| Source | Type | Pairs | API Key Required |
|--------|------|-------|------------------|
| **CCXT** | Crypto | BTCUSD, ETHUSD, SOLUSD, etc. | ❌ No |
| **yfinance** | Stocks | AAPL, TSLA, NVDA, etc. | ❌ No |

### 1.4 Supported Timeframes

| Timeframe | Code | Use Case |
|-----------|------|----------|
| 1 hour | `1h` | Intraday trading |
| 4 hours | `4h` | Swing trading (default) |
| 1 day | `1d` | Position trading |
| 1 week | `1w` | Long-term investing |

---

## 2. Quick Start

### 2.1 Prerequisites

- Python 3.12+
- TA-DSS API server running (local or production)
- Internet connection (for market data)

### 2.2 Launch Methods

#### Method 1: Production Script (Recommended)

For connecting to Google Cloud production API:

```bash
cd trading-order-monitoring-system
./scripts/run-dashboard-production.sh
```

**What it does:**
- Loads VM IP from `.env` file
- Sets `API_BASE_URL` automatically
- Tests API connection before launch
- Opens dashboard at http://localhost:8503

#### Method 2: Environment Variable

```bash
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

Replace `VM_EXTERNAL_IP` with your actual VM IP (from `.env` file).

#### Method 3: Local Development

```bash
# Terminal 1: Start API server
uvicorn src.main:app --reload

# Terminal 2: Start dashboard
streamlit run src/ui.py --server.port 8503
```

Both API and dashboard run on localhost.

#### Method 4: UI Toggle (After Launch)

1. Start dashboard normally: `streamlit run src/ui.py --server.port 8503`
2. Go to **Settings (⚙️)** → **API Connection**
3. Select **🌐 Production (Google Cloud)**
4. Click **🔌 Test Connection** to verify
5. Go to **Open Positions (📋)** to view data

### 2.3 Access URLs

| Component | URL | Notes |
|-----------|-----|-------|
| **Dashboard** | http://localhost:8503 | Main interface |
| **API (Local)** | http://localhost:8000 | Local development |
| **API (Production)** | http://VM_EXTERNAL_IP:8000 | Google Cloud |
| **API Docs** | http://localhost:8000/docs | Swagger UI |

---

## 3. Dashboard Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Your Browser (http://localhost:8503)                        │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Streamlit Dashboard (ui.py)                           │ │
│  │                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │ Open         │  │ Add New      │  │ Settings   │ │ │
│  │  │ Positions    │  │ Position     │  │ Page       │ │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │ API Client (requests library)                   │ │ │
│  │  │ - get_current_api_url()                         │ │ │
│  │  │ - Session state override support                │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │
         │ HTTP/HTTPS
         ▼
┌─────────────────────────────────────────────────────────────┐
│ TA-DSS API Server                                           │
│                                                             │
│  Local: http://localhost:8000                               │
│  Production: http://VM_EXTERNAL_IP:8000                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ FastAPI Backend                                       │ │
│  │ - Position CRUD operations                            │ │
│  │ - Technical analysis                                  │ │
│  │ - Scheduler management                                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ SQLite Database                                       │ │
│  │ - positions table                                     │ │
│  │ - alert_history table                                 │ │
│  │ - signal_changes table                                │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

1. **User opens dashboard** → Streamlit loads `ui.py`
2. **Dashboard fetches positions** → API call to `/api/v1/positions/open`
3. **API returns position data** → JSON with PnL, signals, health status
4. **Dashboard renders UI** → Cards, tables, charts
5. **User interacts** → Clicks position, adds new position, changes settings
6. **Dashboard updates** → API calls, session state changes, re-render

### 3.3 Caching Strategy

| Data Type | Cache TTL | Function |
|-----------|-----------|----------|
| **Open Positions (Sidebar)** | 30 seconds | `fetch_open_positions_cached()` |
| **Open Positions (Main)** | No cache | `fetch_open_positions_from_api()` |
| **System Info** | 60 seconds | `get_system_info_cached()` |

**Why different caching?**
- Sidebar stats: Can be slightly stale (performance)
- Main positions: Must be fresh (user expects real-time)
- System info: Rarely changes (can cache longer)

---

## 4. Page 1: Open Positions

### 4.1 Overview

**Purpose:** View and manage all your open trading positions with real-time signals and PnL.

**URL:** http://localhost:8503 (default page)

### 4.2 Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 📈 TA-DSS Position Monitor                                  │
│ Real-time monitoring of your trading positions              │
├─────────────────────────────────────────────────────────────┤
│ [Summary Cards Row]                                         │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│ │ Total   │ │ Long    │ │ Short   │ │ Warning │            │
│ │   5     │ │   3     │ │   2     │ │   1     │            │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │
├─────────────────────────────────────────────────────────────┤
│ [Search/Filter Bar]                                         │
│ 🔍 Search: [________]  Filter: [All ▼]  Sort: [Date ▼]     │
├─────────────────────────────────────────────────────────────┤
│ [Positions Table]                                           │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Pair  │ Type │ PnL    │ Signals │ Health   │ Actions  │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ BTCUSD│ LONG │ +5.2%  │ 🟢🟢🟢  │ HEALTHY  │ [View]   │ │
│ │ ETHUSD│ SHORT│ -2.1%  │ 🟡🟡🔴  │ WARNING  │ [View]   │ │
│ │ AAPL  │ LONG │ +12.3% │ 🟢🟢🟢  │ HEALTHY  │ [View]   │ │
│ └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Summary Cards

| Card | Description | Calculation |
|------|-------------|-------------|
| **Total Positions** | Count of all open positions | `len(positions)` |
| **Long Positions** | Count of LONG positions | `sum(p.type == 'LONG')` |
| **Short Positions** | Count of SHORT positions | `sum(p.type == 'SHORT')` |
| **Warnings** | Positions with WARNING/CRITICAL health | `sum(p.health != 'HEALTHY')` |

### 4.4 Positions Table

**Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| **Pair** | Trading pair symbol | `BTCUSD`, `AAPL` |
| **Type** | Position direction | `LONG 🟢`, `SHORT 🔴` |
| **Entry Price** | Entry price | `$50,000.00` |
| **Current Price** | Latest market price | `$52,500.00` |
| **PnL** | Profit/Loss percentage | `+5.2%` (green) or `-2.1%` (red) |
| **Signals** | Technical indicators status | 🟢🟢🟢 (all bullish) or 🟡🟡🔴 (mixed) |
| **Health** | Overall position health | `HEALTHY`, `WARNING`, `CRITICAL` |
| **Actions** | Action buttons | `[View]` |

**Signal Dots Meaning:**

| Dots | Interpretation |
|------|----------------|
| 🟢🟢🟢 | All indicators agree (strong signal) |
| 🟢🟢🟡 | Mostly bullish, one neutral |
| 🟢🟡🔴 | Mixed signals (conflict) |
| 🔴🔴🔴 | All indicators agree (strong opposite signal) |

### 4.5 Position Details View

**Trigger:** Click `[View]` button on any position

**Shows:**

#### A. Header Metrics

```
┌─────────────────────────────────────────────────────────────┐
│ BTCUSD LONG (4h)                                            │
│ Entry: $50,000 │ Current: $52,500 │ PnL: +5.2% (+$2,500)  │
│ Entry Time: 2026-03-01 14:00 UTC │ Duration: 4 days        │
└─────────────────────────────────────────────────────────────┘
```

#### B. Signal Breakdown

| Indicator | Value | Signal | Interpretation |
|-----------|-------|--------|----------------|
| **EMA 10** | $51,200 | 🟢 BULLISH | Price above EMA10 |
| **EMA 20** | $49,800 | 🟢 BULLISH | Price above EMA20 |
| **EMA 50** | $48,500 | 🟢 BULLISH | Price above EMA50 |
| **MACD** | +250 | 🟢 BULLISH | MACD above signal |
| **RSI** | 62 | 🟢 BULLISH | RSI > 50 (not overbought) |
| **OTT** | $50,800 | 🟢 BULLISH | Price above OTT |

**Overall Signal:** 🟢 BULLISH (6/6 indicators agree)

#### C. Health Status

| Status | Meaning | Recommendation |
|--------|---------|----------------|
| **HEALTHY** | Signals match position direction | Maintain position |
| **WARNING** | Some signals against position | Monitor closely |
| **CRITICAL** | Most signals against position | Consider closing |

**Example Recommendations:**
- HEALTHY LONG: "All indicators support your LONG position. Consider holding."
- WARNING LONG: "Some indicators showing bearish signals. Monitor closely."
- CRITICAL LONG: "Most indicators are bearish. Consider closing or reducing position."

#### D. Interactive Chart

**Chart Type:** Candlestick with EMAs

**Elements:**
- 🕯️ Candlesticks: Price action (green=up, red=down)
- 📈 Blue line: EMA 10
- 📈 Orange line: EMA 20
- 📈 Purple line: EMA 50
- 📊 Volume bars (optional)

**Interactions:**
- Zoom: Scroll wheel or pinch
- Pan: Click and drag
- Crosshair: Hover on chart
- Reset: Double-click

#### E. Action Buttons

| Button | Action | Confirmation |
|--------|--------|--------------|
| **🔒 Close Position** | Mark position as closed | Yes (modal) |
| **🗑️ Delete Position** | Permanently delete from DB | Yes (modal) |
| **← Back to Positions** | Return to main list | No |

**Close Position Flow:**
1. Click **🔒 Close Position**
2. Modal appears: "Are you sure you want to CLOSE this position?"
3. Shows: Pair, direction, entry price, current PnL
4. Click **Confirm Close** → Position status = CLOSED
5. Success message + confetti animation
6. Redirect to main positions list

**Delete Position Flow:**
1. Click **🗑️ Delete Position**
2. Modal appears: "Are you sure you want to DELETE this position?"
3. Warning: "This action cannot be undone"
4. Click **Confirm Delete** → Position removed from database
5. Success message + balloons animation
6. Redirect to main positions list

---

## 5. Page 2: Add New Position

### 5.1 Overview

**Purpose:** Log a new trading position to the system for monitoring.

**URL:** http://localhost:8503 (sidebar navigation: "➕ Add New Position")

### 5.2 Form Fields

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Pair/Symbol** | Text | Trading pair symbol | `BTCUSD`, `AAPL` |
| **Direction** | Radio | LONG or SHORT | `LONG 🟢` |
| **Timeframe** | Select | Analysis timeframe | `4h` |
| **Entry Price** | Number | Price at entry | `50000.00` |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Entry Date** | Date | When you entered | `2026-03-01` |
| **Entry Time** | Time | When you entered | `14:00` |
| **Notes** | Text area | Trade thesis | "Breaking out of resistance..." |

### 5.3 Preset Pairs

**Quick-select buttons for common pairs:**

#### Crypto Presets
- `BTCUSD` - Bitcoin
- `ETHUSD` - Ethereum
- `SOLUSD` - Solana
- `XAUUSD` - Gold

#### Stock Presets
- `AAPL` - Apple
- `TSLA` - Tesla
- `NVDA` - NVIDIA
- `MSFT` - Microsoft

**Custom Pair:** Enter any valid symbol in the text input.

### 5.4 Pair Format Guide

#### Valid Crypto Pairs
```
✅ BTCUSD
✅ ETH-USD
✅ SOLUSD
✅ XAUUSD
✅ BTC-USDT
```

#### Valid Stock Pairs
```
✅ AAPL
✅ TSLA
✅ NVDA
✅ MSFT
```

#### Invalid Formats (Will Cause Errors)
```
❌ BTC (missing quote currency)
❌ ETH (missing quote currency)
❌ XAU (missing quote currency)
❌ 123ABC (invalid format)
```

### 5.5 Validation Rules

| Rule | Error Message |
|------|---------------|
| Empty pair | "❌ Pair/Symbol cannot be empty" |
| Short crypto symbol | "❌ Invalid pair format: 'BTC' is missing quote currency. Use 'BTCUSD' or 'BTC-USD' instead." |
| Invalid entry price | "❌ Entry Price must be greater than 0" |
| Missing timeframe | "❌ Timeframe is not supported" |

### 5.6 Success Flow

1. Fill in form fields
2. Click **➕ Add Position**
3. Validation passes
4. API call: `POST /api/v1/positions/open`
5. Success response received
6. Show: "✅ Position added successfully!"
7. Show: "🎉 Position created! Redirecting..."
8. Confetti animation
9. Redirect to Open Positions page

### 5.7 Example: Adding a BTCUSD LONG Position

**Form Input:**
```
Pair/Symbol: BTCUSD
Direction: LONG 🟢
Timeframe: 4h
Entry Price: 50000.00
Entry Date: 2026-03-01
Entry Time: 14:00
Notes: Breaking out of resistance, RSI showing bullish divergence
```

**What Happens Next:**
1. Position saved to database
2. Scheduler starts monitoring (next run at :10)
3. You'll receive Telegram alerts when:
   - Technical signals change (BULLISH ↔ BEARISH)
   - PnL < -5% (Stop Loss Warning)
   - PnL > +10% (Take Profit Warning)
4. View real-time signals in Position Details

---

## 6. Page 3: Settings

### 6.1 Overview

**Purpose:** Configure system settings, view status, and manage connections.

**URL:** http://localhost:8503 (sidebar navigation: "⚙️ Settings")

### 6.2 Sections

#### A. API Connection 🔗

**Features:**

1. **Current API URL Display**
   ```
   API URL: http://localhost:8000/api/v1
   ```

2. **API Mode Selector** (Radio Buttons)
   - 💻 Local Development
   - 🌐 Production (Google Cloud)

3. **Mode Switch Behavior**
   - Select mode → Shows success message
   - Displays API URL that will be used
   - Note: "Restart dashboard for full effect"

4. **VM IP Configuration** (Production Mode Only)
   - Input field: "VM External IP"
   - Default: From `.env` or session state
   - Update: Saves to session state immediately

5. **Test Connection Button**
   - Tests API connectivity
   - Shows: ✅ Connected to [URL] or ❌ Error message
   - Timeout: 5 seconds

**Example: Switching to Production Mode**
```
1. Select: 🌐 Production (Google Cloud)
2. Message appears: "✅ Switched to Production Mode"
3. API URL shown: "http://VM_EXTERNAL_IP:8000/api/v1"
4. Note: "Restart dashboard for full effect"
5. Optional: Click "Test Connection" to verify
```

#### B. Telegram Notifications 📱

**When Configured:**
```
✅ Telegram is configured
Bot Token: your_bot_token_here (masked for security)
Chat ID: your_chat_id_here (masked for security)

[📤 Send Test Alert]
```

**Test Alert Flow:**
1. Click **📤 Send Test Alert**
2. Spinner: "Sending test message..."
3. API call to notifier service
4. Success: "✅ Test message sent! Check your Telegram."
5. Failure: "❌ Failed to send test message. Check logs/telegram.log"

**When Not Configured:**
```
⚠️ Telegram is not configured

To configure Telegram notifications:
1. Get a bot token from @BotFather
2. Get your chat ID from @userinfobot
3. Add them to your .env file
4. Restart the application
```

#### C. Monitoring Schedule ⏰

**Scheduler Status:**
```
✅ Scheduler is running
Next check: 2026-03-05 15:10:00 UTC
```

**Info Messages:**
```
ℹ️ Schedule: Every hour at :10 minutes past the hour (XX:10 UTC)
This avoids API congestion at round hour boundaries (:00).

Note: The monitoring interval is fixed at 1 hour. To change the
schedule, modify the cron trigger in src/scheduler.py.
```

**When Scheduler Not Running:**
```
⚠️ Scheduler is not running
```

#### D. Alert Thresholds 🚨

**Display:**
```
┌──────────────────────┐ ┌──────────────────────┐
│ Stop Loss Warning    │ │ Take Profit Warning  │
│       -5%            │ │       +10%           │
│ Triggers when        │ │ Triggers when        │
│ PnL < -5%            │ │ PnL > +10%           │
└──────────────────────┘ └──────────────────────┘
```

**Description:**
```
These thresholds determine when you receive alerts:

- Stop Loss Warning: When your position is down more than 5%
- Take Profit Warning: When your position is up more than 10%

To customize these, you would need to modify the PositionMonitor
class in src/monitor.py.
```

#### E. System Information ℹ️

**JSON Display:**
```json
{
  "Dashboard Version": "v1.0.0",
  "Python Version": "3.12.9",
  "FastAPI Version": "0.109.0",
  "Streamlit Version": "1.54.0",
  "Database Type": "SQLite",
  "Database Path": "/path/to/data/positions.db",
  "Total Positions": "5",
  "Open Positions": "3",
  "Closed Positions": "2",
  "Data Sources": ["yfinance (Stocks)", "CCXT (Crypto)"],
  "Technical Analysis": "pandas_ta",
  "Scheduler": "APScheduler 3.10.4"
}
```

#### F. Data Sources 📡

**Display:**
```
┌────────────────────────────┐ ┌────────────────────────────┐
│ 📈 yfinance (Stocks)       │ │ 🪙 CCXT (Crypto)           │
│ Status: Available          │ │ Status: Available          │
│ No API key required        │ │ Default exchange: Binance  │
└────────────────────────────┘ └────────────────────────────┘
```

#### G. Performance ⚡

**Caching:**
- Position data: Cached for 30 seconds
- System info: Cached for 60 seconds

**Auto-refresh:**
- Manual refresh: Available in sidebar
- Auto-refresh: Toggle in sidebar (30-second intervals)

**Tips for Better Performance:**
- Use auto-refresh sparingly (increases API calls)
- Clear browser cache if dashboard is slow
- Ensure API server is on same machine for lowest latency

#### H. Quick Links 🔗

| Button | URL |
|--------|-----|
| **📋 API Docs** | `{API_URL}/docs` (Swagger UI) |
| **🏥 Health Check** | `{API_URL}/health` |
| **📊 Dashboard** | http://localhost:8503 |

**Note:** API Docs and Health Check URLs adapt to current API mode (local or production).

---

## 7. API Connection Modes

### 7.1 Overview

The dashboard supports **dual-mode operation**:
- **Local Development:** Connects to `localhost:8000`
- **Production:** Connects to Google Cloud VM

### 7.2 Connection Priority

The dashboard determines API URL using this priority:

```
1. Session State Override (from Settings page toggle)
   ↓
2. Environment Variable (API_BASE_URL)
   ↓
3. Default (http://localhost:8000/api/v1)
```

### 7.3 Mode Comparison

| Aspect | Local Mode | Production Mode |
|--------|------------|-----------------|
| **API URL** | `http://localhost:8000` | `http://VM_EXTERNAL_IP:8000` |
| **Use Case** | Development, testing | Live trading |
| **Data** | Local database | Production database |
| **Latency** | ~1ms | ~50-100ms |
| **Availability** | When laptop running | 24/7 |

### 7.4 Switching Modes

#### Method 1: Environment Variable (Before Launch)

```bash
# Local (default)
streamlit run src/ui.py --server.port 8503

# Production
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

#### Method 2: UI Toggle (After Launch)

1. Go to **Settings (⚙️)** → **API Connection**
2. Select mode:
   - 💻 Local Development
   - 🌐 Production (Google Cloud)
3. **Note:** Restart required for full effect

#### Method 3: Production Script

```bash
./scripts/run-dashboard-production.sh
```

This automatically sets production mode via `.env` file.

### 7.5 Session State Behavior

**When you switch modes in UI:**
1. Selection saved to `st.session_state.api_base_url_override`
2. All API calls use new URL immediately
3. Cached data may still be from old URL (until cache expires)
4. Restart recommended for clean switch

**Why restart?**
- Some cached data may be stale
- Ensures all components use same URL
- Clears any conflicting session state

---

## 8. Features Guide

### 8.1 Real-time Position Monitoring

**What You See:**
- All open positions in a table
- Live PnL calculations
- Current technical signals
- Health status for each position

**How It Works:**
1. Dashboard fetches positions from API
2. API calculates current PnL and signals
3. Dashboard displays with color coding
4. Auto-refresh (optional) updates every 30 seconds

### 8.2 Technical Signals Display

**6 Indicators Shown:**

| Indicator | Parameters | Bullish When |
|-----------|------------|--------------|
| **EMA 10** | 10-period | Close > EMA |
| **EMA 20** | 20-period | Close > EMA |
| **EMA 50** | 50-period | Close > EMA |
| **MACD** | 12,26,9 | Histogram > 0 |
| **RSI** | 14-period | RSI > 50 |
| **OTT** | Trend-following | Close > OTT |

**Signal Aggregation:**
- 🟢 BULLISH: Indicator supports LONG position
- 🔴 BEARISH: Indicator supports SHORT position (against LONG)
- 🟡 NEUTRAL: Indicator unclear or conflicting

### 8.3 Position Health Evaluation

**Health Status Logic:**

| Position Type | Mostly BULLISH Signals | Mostly BEARISH Signals |
|---------------|------------------------|------------------------|
| **LONG** | HEALTHY ✅ | CRITICAL 🔴 |
| **SHORT** | CRITICAL 🔴 | HEALTHY ✅ |

**Warning Threshold:**
- 50-70% signals against position → WARNING ⚠️
- >70% signals against position → CRITICAL 🔴

### 8.4 Interactive Charts

**Chart Library:** Plotly (go.Candlestick)

**Chart Elements:**
- Candlesticks (green=up, red=down)
- EMA 10 (blue line)
- EMA 20 (orange line)
- EMA 50 (purple line)
- Volume bars (optional, bottom)

**Interactions:**
- **Zoom:** Scroll wheel or pinch gesture
- **Pan:** Click and drag
- **Crosshair:** Hover mouse over chart
- **Reset:** Double-click on chart

### 8.5 Telegram Alerts

**Alert Types:**

| Alert | Trigger | Example Message |
|-------|---------|-----------------|
| **Status Change** | HEALTHY → WARNING/CRITICAL | "⚠️ BTCUSD LONG: Health changed to WARNING" |
| **Stop Loss** | PnL < -5% | "🔴 BTCUSD: PnL -5.2% (Stop Loss Warning)" |
| **Take Profit** | PnL > +10% | "🟢 BTCUSD: PnL +10.5% (Take Profit Warning)" |
| **Signal Change** | MA10 or OTT flips | "📊 BTCUSD: MA10 changed BULLISH → BEARISH" |

**Anti-Spam Logic:**
- Only alerts on **changes** (not every check)
- Tracks previous status in database
- Compares before sending alert

### 8.6 Position Management

#### Close Position

**Flow:**
1. Click **🔒 Close Position** in details view
2. Confirmation modal appears
3. Shows: Pair, direction, entry price, current PnL
4. Click **Confirm Close**
5. API call: `POST /api/v1/positions/{id}/close`
6. Position status = CLOSED
7. Success message + confetti
8. Redirect to positions list

**What Happens:**
- Position marked as closed in database
- PnL finalized
- No more monitoring for this position
- Historical data preserved

#### Delete Position

**Flow:**
1. Click **🗑️ Delete Position** in details view
2. Confirmation modal appears
3. Warning: "This action cannot be undone"
4. Click **Confirm Delete**
5. API call: `DELETE /api/v1/positions/{id}`
6. Position removed from database
7. Success message + balloons
8. Redirect to positions list

**What Happens:**
- Position permanently deleted
- All data lost (signals, alerts, history)
- Cannot be recovered

---

## 9. Technical Details

### 9.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Frontend Framework** | Streamlit | 1.54.0 |
| **HTTP Client** | requests | 2.31.0 |
| **Charting** | Plotly | 5.18.0 |
| **Data Processing** | pandas | 2.1.4 |
| **Python** | CPython | 3.12.9 |

### 9.2 File Structure

```
src/
├── ui.py                          # Main dashboard application
├── config.py                      # Settings (loaded from .env)
├── database.py                    # Database connection
├── models/
│   └── position_model.py          # SQLAlchemy models
├── services/
│   ├── technical_analyzer.py      # Technical indicators
│   └── signal_engine.py           # Health evaluation
└── data_fetcher.py                # Market data (CCXT/yfinance)
```

### 9.3 Key Functions

#### API Communication

```python
def get_current_api_url() -> str:
    """Get API URL with session state override support."""
    if "api_base_url_override" in st.session_state:
        return st.session_state.api_base_url_override
    return os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

def fetch_open_positions_from_api() -> Optional[List[Dict]]:
    """Fetch positions WITHOUT caching (for fresh data)."""
    response = requests.get(f"{get_current_api_url()}/positions/open", timeout=10)
    response.raise_for_status()
    return response.json()

def test_api_connection(test_url: str = None) -> tuple[bool, str]:
    """Test API connectivity."""
    url = test_url if test_url else get_current_api_url()
    response = requests.get(f"{url}/health", timeout=5)
    response.raise_for_status()
    return True, f"✅ Connected to {url}"
```

#### Caching

```python
@st.cache_data(ttl=30)
def fetch_open_positions_cached() -> Optional[List[Dict]]:
    """Fetch positions WITH 30-second cache."""
    response = requests.get(f"{get_current_api_url()}/positions/open", timeout=10)
    return response.json()

@st.cache_data(ttl=60)
def get_system_info_cached() -> Dict:
    """Fetch system info with 60-second cache."""
    response = requests.get(f"{get_current_api_url()}/positions/scheduler/status", timeout=5)
    return response.json()
```

### 9.4 Session State Management

**State Variables:**

| Variable | Purpose | Type |
|----------|---------|------|
| `current_page` | Active page navigation | string |
| `selected_position_id` | Currently viewed position | int |
| `selected_position_data` | Cached position details | dict |
| `show_close_confirm` | Close confirmation modal | bool |
| `show_delete_confirm` | Delete confirmation modal | bool |
| `api_base_url_override` | API URL override from toggle | string |
| `vm_external_ip` | VM IP for production mode | string |
| `auto_refresh_enabled` | Auto-refresh toggle | bool |
| `manual_refresh_requested` | Manual refresh trigger | bool |
| `last_refresh_time` | Last refresh timestamp | float |

### 9.5 Error Handling

**API Errors:**
```python
try:
    response = requests.get(f"{get_current_api_url()}/positions/open", timeout=10)
    response.raise_for_status()
    return response.json()
except requests.exceptions.ConnectionError:
    st.error("🔌 Backend Connection Lost")
    st.info("Unable to connect to the API server...")
    return None
except requests.exceptions.Timeout:
    st.error("⏱️ Request Timeout")
    st.info("The API server took too long to respond...")
    return None
except Exception as e:
    st.error(f"❌ Unexpected error: {str(e)}")
    logger.error(f"API error: {e}", exc_info=True)
    return None
```

**Validation Errors:**
```python
validation_errors = []

if not pair or not pair.strip():
    validation_errors.append("❌ Pair/Symbol cannot be empty")

if not entry_price or entry_price <= 0:
    validation_errors.append("❌ Entry Price must be greater than 0")

if validation_errors:
    for error in validation_errors:
        st.error(error)
    return
```

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue 1: Backend Connection Lost

**Symptoms:**
```
⚠️ Backend Connection Lost
Unable to connect to the API server.
```

**Causes:**
- API server not running
- Wrong API URL configured
- Firewall blocking connection

**Solutions:**

**For Local Mode:**
```bash
# Start API server
cd trading-order-monitoring-system
uvicorn src.main:app --reload

# Verify
curl http://localhost:8000/health
```

**For Production Mode:**
```bash
# Test connection
curl http://VM_EXTERNAL_IP:8000/health

# Check VM is running (Google Cloud Console)
# Compute Engine → VM Instances → Status should be "Running"

# Check firewall allows port 8000
# VPC Network → Firewall → allow-tadss-api rule exists
```

#### Issue 2: Dashboard Won't Start

**Symptoms:**
```
Port 8503 already in use
```

**Solution:**
```bash
# Find process using port 8503
lsof -i :8503

# Kill process
kill -9 <PID>

# Or use different port
streamlit run src/ui.py --server.port 8504
```

#### Issue 3: Positions Not Loading

**Symptoms:**
- Dashboard loads but positions table is empty
- No error message

**Causes:**
- API returns empty list (no positions)
- API error (check browser console)

**Solutions:**
```bash
# Check API directly
curl http://localhost:8000/api/v1/positions/open

# If empty: Add a position via API or dashboard
# If error: Check API server logs
```

#### Issue 4: Mode Switch Not Working

**Symptoms:**
- Switch mode in Settings
- Dashboard still uses old URL

**Solution:**
```bash
# Restart dashboard
# (Session state override requires restart for full effect)

streamlit run src/ui.py --server.port 8503

# Or use environment variable method
API_BASE_URL=http://VM_EXTERNAL_IP:8000/api/v1 streamlit run src/ui.py --server.port 8503
```

#### Issue 5: Charts Not Displaying

**Symptoms:**
- Position details page loads
- Chart area is blank

**Causes:**
- Insufficient data for chart
- Plotly not loaded

**Solutions:**
```bash
# Check browser console for errors
# Refresh page (Ctrl+R or Cmd+R)
# Clear browser cache

# Verify position has OHLCV data
curl http://localhost:8000/api/v1/positions/{id}
```

#### Issue 6: CORS_ORIGINS Pydantic Settings Error

**Symptoms:**
```
pydantic_settings.sources.SettingsError: error parsing value for field "cors_origins" 
from source "DotEnvSettingsSource"
```

**Traceback:**
```
File "src/config.py", line 441, in <module>
    settings = Settings()
File "pydantic_settings/main.py", line 72, in __init__
File "pydantic_settings/sources.py", line 254, in __call__
    raise SettingsError
```

**Causes:**
- `CORS_ORIGINS` in `.env` file uses JSON array format: `["http://localhost:8501","http://localhost:8000"]`
- `CORS_ORIGINS` environment variable set in shell session with old format
- pydantic-settings 2.x tries to parse `List[str]` fields as JSON, but comma-separated values aren't valid JSON

**Solutions:**

**Solution 1: Fix .env file (Recommended)**
```bash
# Edit .env file - change from JSON array to comma-separated
# Before:
CORS_ORIGINS=["http://localhost:8501","http://localhost:8000"]

# After:
CORS_ORIGINS=http://localhost:8501,http://localhost:8000
```

**Solution 2: Unset shell environment variable**
```bash
# Check if CORS_ORIGINS is set in shell
echo $CORS_ORIGINS

# If it shows the old JSON format, unset it
unset CORS_ORIGINS

# Restart dashboard
streamlit run src/ui.py --server.port 8503
```

**Solution 3: Fix config.py (Permanent fix)**
```python
# In src/config.py, change cors_origins field definition:

# Before:
cors_origins: List[str] = ["http://localhost:8501", "http://localhost:8000"]

# After:
cors_origins_str: str = "http://localhost:8501,http://localhost:8000"

@property
def cors_origins(self) -> List[str]:
    """Parse CORS origins from comma-separated string."""
    return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
```

**Prevention:**
- Always use comma-separated format for list fields in `.env`: `VAR=value1,value2,value3`
- Avoid JSON array format unless the field explicitly expects JSON
- Check shell environment variables don't override `.env` values

### 10.2 Performance Issues

#### Slow Dashboard

**Symptoms:**
- Dashboard takes >5 seconds to load
- Interactions feel sluggish

**Solutions:**
1. **Reduce auto-refresh frequency**
   - Disable auto-refresh in sidebar
   - Use manual refresh instead

2. **Clear browser cache**
   - Chrome: Ctrl+Shift+Delete
   - Safari: Cmd+Option+E

3. **Check API response time**
   ```bash
   time curl http://localhost:8000/api/v1/positions/open
   # Should be <1 second
   ```

4. **Reduce number of positions**
   - Close old positions
   - Archive historical data

### 10.3 Getting Help

**Logs Location:**
```
logs/monitor.log      # Monitoring logs
logs/telegram.log     # Telegram notifications
logs/data_fetch.log   # Data fetching logs
```

**Useful Commands:**
```bash
# View live logs
tail -f logs/monitor.log

# Check API status
curl http://localhost:8000/health

# Test Telegram
curl -X POST http://localhost:8000/api/v1/positions/scheduler/test-alert
```

---

## 11. Security Considerations

### 11.1 Current Security Status

| Aspect | Status | Risk Level |
|--------|--------|------------|
| **VM IP Exposure** | ✅ Hidden in `.env` | Low |
| **API Authentication** | 🔴 None | **HIGH** |
| **Firewall** | 🔴 Open to internet | Medium |
| **Dashboard Auth** | ✅ Local only | Low |
| **Database Access** | ✅ SSH tunnel only | Low |

### 11.2 Known Vulnerabilities

#### 1. No API Authentication

**Risk:** Anyone who knows your VM IP can:
- View all your positions
- Add fake positions
- Close your positions
- Delete positions

**Mitigation (Planned):**
- Add API key authentication (Task 4)
- Require `X-API-Key` header for sensitive endpoints

#### 2. Open Firewall

**Risk:** Port 8000 accessible from anywhere

**Mitigation (Optional):**
- Restrict firewall to your home IP (Task 5)
- Use VPN for remote access

### 11.3 Best Practices

#### DO:
- ✅ Keep `.env` file private (never commit)
- ✅ Use strong `SECRET_KEY` (32+ characters)
- ✅ Restrict firewall to your IP if possible
- ✅ Rotate API keys periodically
- ✅ Monitor logs for suspicious activity

#### DON'T:
- ❌ Deploy dashboard publicly without authentication
- ❌ Share your VM IP publicly
- ❌ Use weak passwords or API keys
- ❌ Commit `.env` to git
- ❌ Leave unused ports open

### 11.4 Security Checklist

Before deploying to production:

- [ ] VM IP stored in `.env` (not in git)
- [ ] API authentication implemented (Task 4)
- [ ] Firewall restricted to your IP (Task 5)
- [ ] Strong `SECRET_KEY` generated
- [ ] Telegram bot token secured
- [ ] Database backups configured
- [ ] Log rotation enabled
- [ ] HTTPS configured (if exposing dashboard)

---

## Appendix A: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `R` | Refresh dashboard |
| `Ctrl+R` | Browser refresh |
| `Ctrl+Shift+R` | Hard refresh (clear cache) |

## Appendix B: Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `API_BASE_URL` | Dashboard API connection | `http://localhost:8000/api/v1` | No |
| `VM_EXTERNAL_IP` | Google Cloud VM IP | None | For production |
| `TELEGRAM_BOT_TOKEN` | Telegram bot | None | For alerts |
| `TELEGRAM_CHAT_ID` | Telegram user | None | For alerts |

## Appendix C: API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/positions/open` | GET | List open positions |
| `/api/v1/positions` | GET | List all positions |
| `/api/v1/positions/{id}` | GET | Get position details |
| `/api/v1/positions/open` | POST | Add new position |
| `/api/v1/positions/{id}/close` | POST | Close position |
| `/api/v1/positions/{id}` | DELETE | Delete position |
| `/api/v1/positions/scheduler/status` | GET | Scheduler status |
| `/api/v1/positions/scheduler/test-alert` | POST | Test Telegram |
| `/health` | GET | Health check |

---

**Document Version:** 1.0.0  
**Last Updated:** March 5, 2026  
**Maintained By:** TA-DSS Development Team
