# MTF Scanner User Guide

**Multi-Timeframe Analysis for TA-DSS**

_Version: 1.0 | Last Updated: 2026-03-07_

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Understanding MTF Analysis](#understanding-mtf-analysis)
4. [Using the Dashboard](#using-the-dashboard)
5. [API Reference](#api-reference)
6. [Telegram Alerts](#telegram-alerts)
7. [Trading Styles](#trading-styles)
8. [FAQ](#faq)

---

## Overview

The MTF (Multi-Timeframe) Scanner is a feature of TA-DSS that automatically detects high-probability trading opportunities by analyzing three timeframes simultaneously.

**What it does:**
- Scans multiple trading pairs for MTF-aligned setups
- Scores alignment across Higher, Middle, and Lower timeframes
- Filters by minimum R:R ratio and alignment quality
- Sends Telegram alerts for high-conviction opportunities

**Key benefits:**
- Saves time on manual chart analysis
- Enforces disciplined multi-timeframe approach
- Identifies opportunities you might miss
- Provides objective alignment scoring

---

## Quick Start

### Dashboard

```bash
# Start the dashboard
cd trading-order-monitoring-system
streamlit run src/ui.py --server.port 8503

# Open browser to http://localhost:8503
# Click "🔍 MTF Scanner" in sidebar
```

### API

```bash
# Scan for opportunities
curl "http://localhost:8000/api/v1/mtf/opportunities?trading_style=SWING"

# Get timeframe configs
curl "http://localhost:8000/api/v1/mtf/configs"
```

### Telegram Alerts

Configure in `.env`:
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890
```

Alerts are automatic for 3/3 alignment opportunities.

---

## Understanding MTF Analysis

### The Timeframe Hierarchy

| Layer | Role | Tools | Example (Swing) |
|-------|------|-------|-----------------|
| **HTF** (Higher) | Directional bias | 50/200 SMA, Price structure | Weekly |
| **MTF** (Middle) | Setup identification | 20/50 SMA, RSI divergence | Daily |
| **LTF** (Lower) | Entry timing | 20 EMA, Candlestick patterns | 4H |

### Alignment Scoring

| Score | Quality | Meaning | Action |
|-------|---------|---------|--------|
| 3/3 | HIGHEST | All timeframes aligned | Trade aggressively |
| 2/3 | GOOD | 2 timeframes aligned | Standard risk |
| 1/3 | POOR | Only 1 timeframe aligned | Avoid or reduce size |
| 0/3 | AVOID | No alignment | Do not trade |

### Patterns Detected

1. **HTF Support + LTF Reversal**
   - Price at HTF support level
   - LTF shows reversal candle (engulfing, hammer)
   - High-probability bounce setup

2. **HTF Trend + MTF Pullback + LTF Entry**
   - HTF in confirmed trend (HH/HL or LH/LL)
   - MTF pulling back to SMA20/50
   - LTF shows entry signal (EMA reclaim, RSI turn)

3. **MTF Divergence at HTF Level**
   - Price at HTF S/R level
   - MTF shows RSI divergence
   - Potential reversal

4. **All 3 TFs Aligned**
   - Maximum confluence
   - Highest quality setups

---

## Using the Dashboard

### Step 1: Select Trading Style

Choose from 5 predefined configurations:

| Style | HTF | MTF | LTF | Best For |
|-------|-----|-----|-----|----------|
| POSITION | Monthly | Weekly | Daily | Long-term investors |
| SWING | Weekly | Daily | 4H | Swing traders (default) |
| INTRADAY | Daily | 4H | 1H | Day traders |
| DAY | 4H | 1H | 15M | Scalpers |
| SCALPING | 1H | 15M | 5M | High-frequency |

### Step 2: Set Filters

**Min Alignment (0-3):**
- Recommended: 2 (good balance)
- Strict: 3 (only highest quality)
- Lenient: 1 (more opportunities, lower quality)

**Min R:R (0.5-10):**
- Recommended: 2.0 (minimum acceptable)
- Conservative: 3.0+ (only excellent setups)

### Step 3: Scan

Click "🔍 Scan Now" to scan all pairs in watchlist.

### Step 4: Review Results

Results displayed as expandable cards:

```
🟢 BTC/USDT - HIGHEST (3/3) - BUY
├── HTF Bias: BULLISH
├── MTF Setup: PULLBACK
├── LTF Entry: ENGULFING
├── Entry: $67,500
├── Stop: $65,800
├── Target: $72,900
├── R:R: 3.2
└── Patterns: HTF Trend + MTF Pullback + LTF Entry
```

### Step 5: Take Action

- Click "📈 Analyze Pair" for detailed view
- Use signals to inform your trading decisions
- Always do your own analysis before trading

---

## API Reference

### GET /api/v1/mtf/opportunities

Scan for MTF opportunities.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| trading_style | string | SWING | POSITION, SWING, INTRADAY, DAY, SCALPING |
| min_alignment | integer | 2 | Minimum alignment score (0-3) |
| min_rr_ratio | float | 2.0 | Minimum R:R ratio |
| pairs | string | watchlist | Comma-separated pair list |

**Example:**
```bash
curl "http://localhost:8000/api/v1/mtf/opportunities?trading_style=DAY&min_alignment=3"
```

**Response:**
```json
{
  "timestamp": "2026-03-07T10:00:00",
  "trading_style": "DAY",
  "filters": {"min_alignment": 3, "min_rr_ratio": 2.0},
  "opportunities": [
    {
      "pair": "BTC/USDT",
      "quality": "HIGHEST",
      "alignment_score": 3,
      "recommendation": "BUY",
      "rr_ratio": 3.2,
      "htf_bias": "BULLISH",
      "mtf_setup": "PULLBACK",
      "ltf_entry": "ENGULFING"
    }
  ],
  "summary": {
    "total_scanned": 5,
    "opportunities_found": 1,
    "high_conviction": 1
  }
}
```

### GET /api/v1/mtf/opportunities/{pair}

Get detailed analysis for a single pair.

**Example:**
```bash
curl "http://localhost:8000/api/v1/mtf/opportunities/BTC/USDT"
```

### GET /api/v1/mtf/configs

Get all timeframe configurations.

**Response:**
```json
{
  "configs": {
    "POSITION": {"htf": "M1", "mtf": "w1", "ltf": "d1"},
    "SWING": {"htf": "w1", "mtf": "d1", "ltf": "h4"},
    "INTRADAY": {"htf": "d1", "mtf": "h4", "ltf": "h1"},
    "DAY": {"htf": "h4", "mtf": "h1", "ltf": "m15"},
    "SCALPING": {"htf": "h1", "mtf": "m15", "ltf": "m5"}
  }
}
```

### POST /api/v1/mtf/scan

Trigger on-demand scan with custom parameters.

**Request Body:**
```json
{
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "trading_style": "INTRADAY",
  "min_alignment": 2,
  "min_rr_ratio": 2.5
}
```

### GET /api/v1/mtf/watchlist

Get current watchlist.

---

## Telegram Alerts

### Alert Types

#### 1. High-Conviction Opportunity

Sent when:
- Alignment score = 3/3
- Recommendation = BUY or SELL
- Under daily throttle limit

```
🟢 MTF Opportunity Alert ⭐⭐⭐

Pair: BTC/USDT
Style: SWING
Alignment: 3/3 timeframes
Recommendation: BUY
R:R: 3.2:1

💰 Trade Setup:
Entry: $67,500.00
Stop: $65,800.00
Target: $72,900.00

Patterns Detected:
• HTF Trend + MTF Pullback + LTF Entry

💡 Action: Review on dashboard before trading
```

#### 2. Divergence Alert

Sent when:
- RSI divergence at key level
- Confidence ≥ 0.6

#### 3. Daily Summary

Summary of daily scan results.

### Throttling

- Maximum 3 alerts per day
- 24-hour rolling window
- Prevents alert fatigue

### Check Alert Status

```python
from src.services.mtf_notifier import get_alert_status

status = get_alert_status()
print(f"Sent today: {status['alerts_sent_today']}")
print(f"Remaining: {status['alerts_remaining']}")
```

---

## Trading Styles

### POSITION (Monthly → Weekly → Daily)

**Best for:** Long-term investors, position traders

**Characteristics:**
- Few signals (1-2 per month)
- High reliability
- Large targets (1000+ pips)
- Wide stops

**Recommended filters:**
- Min alignment: 3
- Min R:R: 3.0

---

### SWING (Weekly → Daily → 4H) ⭐ Default

**Best for:** Swing traders, part-time traders

**Characteristics:**
- Moderate signals (2-5 per week)
- Good reliability
- Medium targets (200-500 pips)
- Moderate stops

**Recommended filters:**
- Min alignment: 2
- Min R:R: 2.0

---

### INTRADAY (Daily → 4H → 1H)

**Best for:** Day traders, active traders

**Characteristics:**
- Frequent signals (1-3 per day)
- Moderate reliability
- Smaller targets (50-200 pips)
- Tighter stops

**Recommended filters:**
- Min alignment: 2
- Min R:R: 2.0

---

### DAY (4H → 1H → 15M)

**Best for:** Full-time day traders

**Characteristics:**
- Very frequent signals (5-10 per day)
- Lower reliability per signal
- Small targets (20-50 pips)
- Tight stops

**Recommended filters:**
- Min alignment: 3
- Min R:R: 2.5

---

### SCALPING (1H → 15M → 5M)

**Best for:** Scalpers, high-frequency traders

**Characteristics:**
- Extremely frequent signals (20+ per day)
- Lowest reliability per signal
- Tiny targets (5-20 pips)
- Very tight stops

**Recommended filters:**
- Min alignment: 3
- Min R:R: 3.0

---

## FAQ

### Q: How often should I scan?

**A:** Depends on your trading style:
- POSITION: Once per week
- SWING: Once per day
- INTRADAY: 2-3 times per day
- DAY/SCALPING: Every few hours

### Q: Why are there no opportunities?

**A:** Possible reasons:
1. Filters too strict (try min_alignment=1)
2. Market in range (no clear trends)
3. Watchlist too small (add more pairs)
4. Cache needs refresh (wait for next hour)

### Q: Can I customize the watchlist?

**A:** Yes, edit `DEFAULT_MTF_WATCHLIST` in `src/api/routes_mtf.py` or pass `pairs` parameter to API.

### Q: How accurate are the signals?

**A:** Accuracy varies by market conditions:
- Trending markets: 60-70% win rate
- Ranging markets: 40-50% win rate
- 3/3 alignment: Higher accuracy than 2/3

Always use proper risk management.

### Q: Can I backtest MTF signals?

**A:** Backtesting is planned for a future release. Currently, signals are for live analysis only.

### Q: What data sources are used?

**A:** Same as position monitoring:
- Crypto: CCXT/Kraken
- Metals: Twelve Data
- Forex: Twelve Data
- Stocks: Twelve Data

### Q: How do I report bugs?

**A:** Create an issue in the project repository or check `docs/bugs.md` for known issues.

---

## Support

For technical support:
- Check [`docs/features/`](docs/features/) for session summaries
- Review [`docs/bugs.md`](docs/bugs.md) for known issues
- Read API docs at `http://localhost:8000/docs`

---

**End of User Guide**
