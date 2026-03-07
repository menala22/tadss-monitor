# BULLISH vs BEARISH Signal Definition

## 📊 Overview

The system defines **BULLISH** and **BEARISH** at **two levels**:

1. **Individual Indicator Level** - Each of the 6 indicators
2. **Overall Position Level** - Majority vote across all indicators

---

## 🎯 Level 1: Individual Indicator Signals

### 6 Technical Indicators Analyzed

| Indicator | Symbol | BULLISH When | BEARISH When |
|-----------|--------|--------------|--------------|
| **EMA 10** | MA10 | Close > EMA(10) | Close < EMA(10) |
| **EMA 20** | MA20 | Close > EMA(20) | Close < EMA(20) |
| **EMA 50** | MA50 | Close > EMA(50) | Close < EMA(50) |
| **MACD** | MACD | Histogram > 0 | Histogram < 0 |
| **RSI** | RSI | RSI > 50 | RSI < 50 |
| **OTT** | OTT | Trend = 1 (uptrend) | Trend = -1 (downtrend) |

---

### 1. Moving Averages (EMA 10, 20, 50)

**Logic:** Price position relative to moving average

```python
# For each EMA period (10, 20, 50)
if close_price > EMA_value:
    signal = "BULLISH"   # Price above average = bullish
elif close_price < EMA_value:
    signal = "BEARISH"   # Price below average = bearish
else:
    signal = "NEUTRAL"   # Price exactly at average (rare)
```

**Example:**
```
BTCUSD at $67,500
EMA(10) = $66,800 → BULLISH ✅ (price above)
EMA(20) = $66,300 → BULLISH ✅ (price above)
EMA(50) = $67,800 → BEARISH ❌ (price below)
```

**Special States:**
- **OVERBOUGHT** - RSI > 70 (extreme bullish, may reverse)
- **OVERSOLD** - RSI < 30 (extreme bearish, may bounce)

---

### 2. MACD (Moving Average Convergence Divergence)

**Logic:** Momentum based on histogram

```python
macd_histogram = MACD_line - Signal_line

if macd_histogram > 0:
    signal = "BULLISH"   # Positive momentum
elif macd_histogram < 0:
    signal = "BEARISH"   # Negative momentum
else:
    signal = "NEUTRAL"   # Zero momentum
```

**Example:**
```
MACD Line: 125.4
Signal Line: 110.2
Histogram: +15.2 → BULLISH ✅ (positive momentum)
```

**Why Histogram?**
- Histogram > 0: MACD line above signal line = upward momentum
- Histogram < 0: MACD line below signal line = downward momentum

---

### 3. RSI (Relative Strength Index)

**Logic:** Momentum with zones

```python
if RSI > 70:
    signal = "OVERBOUGHT"  # Very bullish, may reverse
elif RSI > 50:
    signal = "BULLISH"     # Bullish momentum
elif RSI == 50:
    signal = "NEUTRAL"     # Neutral
elif RSI < 30:
    signal = "OVERSOLD"    # Very bearish, may bounce
else:  # RSI < 50
    signal = "BEARISH"     # Bearish momentum
```

**RSI Zones:**
```
0    30    50    70   100
|----|----|----|----|
OVERSOLD  NEUTRAL  OVERBOUGHT
  ❌        ➖        ⚠️
```

**Example:**
```
RSI = 65 → BULLISH ✅ (above 50, below 70)
RSI = 75 → OVERBOUGHT ⚠️ (above 70, very bullish)
RSI = 25 → OVERSOLD ❌ (below 30, very bearish)
```

---

### 4. OTT (Optimized Trend Tracker)

**Logic:** Trend direction from OTT algorithm

```python
ott_trend = get_ott_trend()  # Returns: 1, 0, or -1

if ott_trend == 1:
    signal = "BULLISH"   # Uptrend
elif ott_trend == -1:
    signal = "BEARISH"   # Downtrend
else:
    signal = "NEUTRAL"   # No clear trend
```

**OTT Trend Calculation:**
- Trend = 1: MAvg above trailing stop = uptrend
- Trend = -1: MAvg below trailing stop = downtrend

**Example:**
```
OTT Trend: 1 → BULLISH ✅ (uptrend)
OTT Trend: -1 → BEARISH ❌ (downtrend)
```

---

## 🎯 Level 2: Overall Position Status

### Majority Vote System

After calculating all 6 individual signals, the system uses **majority voting**:

```python
def _determine_overall_status(signal_states):
    # Count signals
    bullish_count = 0
    bearish_count = 0
    
    signal_keys = ["MA10", "MA20", "MA50", "MACD", "RSI", "OTT"]
    
    for key in signal_keys:
        status = signal_states[key]
        if status in ["BULLISH", "OVERBOUGHT"]:
            bullish_count += 1
        elif status in ["BEARISH", "OVERSOLD"]:
            bearish_count += 1
    
    # Majority wins
    if bullish_count > bearish_count:
        return "BULLISH"
    elif bearish_count > bullish_count:
        return "BEARISH"
    else:
        return "NEUTRAL"  # Tie (e.g., 3-3)
```

---

### Examples

#### Example 1: Strong Bullish

```
Indicator Signals:
MA10:  BULLISH ✅
MA20:  BULLISH ✅
MA50:  BULLISH ✅
MACD:  BULLISH ✅
RSI:   BULLISH ✅
OTT:   BULLISH ✅

Count: 6 bullish, 0 bearish
Result: BULLISH (100% aligned)
```

#### Example 2: Mixed Signals

```
Indicator Signals:
MA10:  BULLISH ✅
MA20:  BULLISH ✅
MA50:  BEARISH ❌
MACD:  BEARISH ❌
RSI:   BULLISH ✅
OTT:   BEARISH ❌

Count: 3 bullish, 3 bearish
Result: NEUTRAL (tie - market unclear)
```

#### Example 3: Bearish with Overbought RSI

```
Indicator Signals:
MA10:  BEARISH ❌
MA20:  BEARISH ❌
MA50:  BEARISH ❌
MACD:  BEARISH ❌
RSI:   OVERSOLD ❌ (counts as bearish)
OTT:   BEARISH ❌

Count: 0 bullish, 6 bearish
Result: BEARISH (100% against position)
```

---

## 📊 Signal Counting Rules

### What Counts as BULLISH?

| Signal State | Counts As | Reason |
|--------------|-----------|--------|
| `BULLISH` | +1 bullish | Direct bullish signal |
| `OVERBOUGHT` | +1 bullish | Still bullish (just extreme) |
| `BEARISH` | +0 | Not bullish |
| `OVERSOLD` | +0 | Bearish |
| `NEUTRAL` | +0 | No opinion |

### What Counts as BEARISH?

| Signal State | Counts As | Reason |
|--------------|-----------|--------|
| `BEARISH` | +1 bearish | Direct bearish signal |
| `OVERSOLD` | +1 bearish | Still bearish (just extreme) |
| `BULLISH` | +0 | Not bearish |
| `OVERBOUGHT` | +0 | Bullish |
| `NEUTRAL` | +0 | No opinion |

---

## 🎯 Complete Flow Example

### Input: BTCUSD LONG Position

**Step 1: Fetch Market Data**
```
Current Price: $67,500
```

**Step 2: Calculate Indicators**
```
EMA(10): $66,800
EMA(20): $66,300
EMA(50): $67,800
MACD Histogram: +15.2
RSI: 58
OTT Trend: 1 (uptrend)
```

**Step 3: Generate Individual Signals**
```python
MA10:  $67,500 > $66,800 → BULLISH ✅
MA20:  $67,500 > $66,300 → BULLISH ✅
MA50:  $67,500 < $67,800 → BEARISH ❌
MACD:  +15.2 > 0 → BULLISH ✅
RSI:   58 > 50 → BULLISH ✅
OTT:   Trend=1 → BULLISH ✅
```

**Step 4: Count Signals**
```
Bullish: 5 (MA10, MA20, MACD, RSI, OTT)
Bearish: 1 (MA50)
```

**Step 5: Determine Overall Status**
```
5 > 1 → BULLISH
```

**Step 6: Check for Alert**
```python
previous_status = "BEARISH"  # From last check
current_status = "BULLISH"   # New status

if current_status != previous_status:
    # SEND ALERT! 🚨
    "Status changed: BEARISH → BULLISH"
```

---

## 📈 Code Locations

### Individual Signal Generation

**File:** `src/services/technical_analyzer.py`

**Function:** `generate_signal_states()` (Line ~516)

```python
# EMA signals (line ~580)
if close_price > ema_value:
    signals[signal_name] = SignalState.BULLISH
elif close_price < ema_value:
    signals[signal_name] = SignalState.BEARISH

# MACD signal (line ~605)
if macd_hist > 0:
    signals["MACD"] = SignalState.BULLISH
elif macd_hist < 0:
    signals["MACD"] = SignalState.BEARISH

# RSI signal (line ~620)
if rsi_value > 50:
    signals["RSI"] = SignalState.BULLISH
elif rsi_value < 50:
    signals["RSI"] = SignalState.BEARISH

# OTT signal (line ~645)
if ott_trend == 1:
    signals["OTT"] = SignalState.BULLISH
elif ott_trend == -1:
    signals["OTT"] = SignalState.BEARISH
```

### Overall Status Determination

**File:** `src/monitor.py`

**Function:** `_determine_overall_status()` (Line ~178)

```python
bullish_count = 0
bearish_count = 0

for key in ["MA10", "MA20", "MA50", "MACD", "RSI", "OTT"]:
    status = signal_states.get(key)
    if status in ["BULLISH", "OVERBOUGHT"]:
        bullish_count += 1
    elif status in ["BEARISH", "OVERSOLD"]:
        bearish_count += 1

if bullish_count > bearish_count:
    return "BULLISH"
elif bearish_count > bullish_count:
    return "BEARISH"
else:
    return "NEUTRAL"
```

---

## 🎯 Special Cases

### Case 1: Insufficient Data

When indicators can't be calculated (not enough historical data):

```python
signal = "NEUTRAL"  # Doesn't count toward bullish or bearish
```

**Example:**
```
New position with only 20 candles:
MA10:  BULLISH ✅
MA20:  NEUTRAL ➖ (not enough data)
MA50:  NEUTRAL ➖ (not enough data)
MACD:  BULLISH ✅
RSI:   NEUTRAL ➖ (not enough data)
OTT:   BULLISH ✅

Count: 3 bullish, 0 bearish, 3 neutral
Result: BULLISH (3 > 0)
```

### Case 2: RSI Extremes

RSI overbought/oversold still counts toward the direction:

```python
RSI = 75 → OVERBOUGHT (counts as +1 bullish)
RSI = 25 → OVERSOLD (counts as +1 bearish)
```

**Why?** Even though extreme, the momentum is still in that direction.

### Case 3: All Neutral

```python
All indicators: NEUTRAL

Count: 0 bullish, 0 bearish
Result: NEUTRAL
```

---

## 📊 Summary Table

| Level | What It Measures | How It's Calculated |
|-------|------------------|---------------------|
| **Individual** | Each indicator's view | Price vs indicator value |
| **Overall** | Market consensus | Majority vote (6 indicators) |

### Individual Signal Rules

| Indicator | BULLISH | BEARISH |
|-----------|---------|---------|
| MA10/20/50 | Close > EMA | Close < EMA |
| MACD | Histogram > 0 | Histogram < 0 |
| RSI | RSI > 50 | RSI < 50 |
| OTT | Trend = 1 | Trend = -1 |

### Overall Status Rules

| Bullish Count | Bearish Count | Overall Status |
|---------------|---------------|----------------|
| > Bearish | < Bullish | **BULLISH** |
| < Bullish | > Bearish | **BEARISH** |
| = Bearish | = Bullish | **NEUTRAL** |

---

## 🔍 Testing

### View Individual Signals

```python
from src.services.technical_analyzer import TechnicalAnalyzer

analyzer = TechnicalAnalyzer()
df = fetcher.get_ohlcv("BTCUSD", "h4", limit=100)
df = analyzer.calculate_indicators(df)

signals = analyzer.generate_signal_states(df)
print(signals)
# Output:
# {
#   'MA10': 'BULLISH',
#   'MA20': 'BULLISH',
#   'MA50': 'BEARISH',
#   'MACD': 'BULLISH',
#   'RSI': 'BULLISH',
#   'OTT': 'BULLISH',
#   'values': {...}
# }
```

### View Overall Status

```python
from src.monitor import PositionMonitor

monitor = PositionMonitor()
overall = monitor._determine_overall_status(signals)
print(overall)
# Output: "BULLISH" (5 > 1)
```

---

**Questions?** Check the code:
- Individual signals: `src/services/technical_analyzer.py:516`
- Overall status: `src/monitor.py:178`
