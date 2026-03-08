# MTF Analysis Logic - Complete Documentation

**Date:** 2026-03-08
**Version:** 1.0
**Purpose:** Detailed explanation of MTF analysis logic, decision-making, and risk management

---

## Table of Contents

1. [Overview](#overview)
2. [HTF Bias Detection Logic](#1-htf-bias-detection-logic)
3. [MTF Setup Detection Logic](#2-mtf-setup-detection-logic)
4. [LTF Entry Signal Logic](#3-ltf-entry-signal-logic)
5. [Alignment Scoring Logic](#4-alignment-scoring-logic)
6. [Stop Loss Calculation](#5-stop-loss-calculation)
7. [Take Profit Target Calculation](#6-take-profit-target-calculation)
8. [Complete Example](#7-complete-example)

---

## Overview

### MTF Framework Philosophy

The Multi-Timeframe (MTF) analysis framework is built on a **top-down approach**:

```
HTF (Higher Timeframe) → Directional Bias
    ↓
MTF (Middle Timeframe) → Setup Identification  
    ↓
LTF (Lower Timeframe) → Entry Signal
    ↓
Alignment Score → Trade Decision
```

### Timeframe Configuration by Trading Style

| Style | HTF | MTF | LTF | Hold Time |
|-------|-----|-----|-----|-----------|
| POSITION | Monthly | Weekly | Daily | Weeks-Months |
| **SWING** | **Weekly** | **Daily** | **4H** | **3-10 days** |
| INTRADAY | Daily | 4H | 1H | Hours |
| DAY | 4H | 1H | 15M | Minutes-Hours |
| SCALPING | 1H | 15M | 5M | Seconds-Minutes |

---

## 1. HTF Bias Detection Logic

**File:** `src/services/mtf_bias_detector.py`

### Purpose
Determine the **directional bias** using structural tools only (no oscillators).

### Why Structural Tools Only?
- Oscillators (RSI, MACD) **lag too much** on HTF
- Price structure and moving averages provide **clearer directional bias**
- HTF sets the **context** for all lower timeframe decisions

---

### Step-by-Step Logic

#### Step 1: Find Swing Points

```python
# Swing High: high higher than N candles before and after
# Swing Low: low lower than N candles before and after
window = 5  # Default

for i in range(window, len(df) - window):
    # Check swing high
    if df['high'][i] > max(df['high'][i-window:i]) and 
       df['high'][i] > max(df['high'][i+1:i+window+1]):
        → Swing HIGH detected
    
    # Check swing low
    if df['low'][i] < min(df['low'][i-window:i]) and 
       df['low'][i] < min(df['low'][i+1:i+window+1]):
        → Swing LOW detected
```

**Swing Strength Calculation:**
```python
strength = min(1.0, (left_diff + right_diff) * 10)
# left_diff = how much higher/lower than left neighbors
# right_diff = how much higher/lower than right neighbors
```

---

#### Step 2: Detect Price Structure

**Logic:**
```python
# UPTREND (HH/HL): At least 2 HH and 2 HL in recent swings
if hh_count >= 2 and hl_count >= 2:
    → PriceStructure.UPTREND

# DOWNTREND (LH/LL): At least 2 LH and 2 LL in recent swings  
if lh_count >= 2 and ll_count >= 2:
    → PriceStructure.DOWNTREND

# Otherwise
→ PriceStructure.RANGE
```

**Why 2+ sequences?**
- Single HH/HL could be noise
- **2+ confirmed sequences** = established trend
- Reduces false signals in choppy markets

---

#### Step 3: Calculate Moving Averages

```python
SMA_50 = close_price.rolling(50).mean()
SMA_200 = close_price.rolling(200).mean()
```

**Why SMA 50/200?**
- **50 SMA:** Captures medium-term trend (institutional reference)
- **200 SMA:** Long-term trend benchmark (widely watched)
- **Simple** (not exponential) = smoother, less whipsaws

**Note:** For crypto/forex, consider EMA 20/50 instead (faster reaction)

---

#### Step 4: Determine SMA Slopes

```python
# Compare last 10 SMA values
slope = (SMA[-1] - SMA[-10]) / SMA[-10]

if slope > 0.005:   # > 0.5% increase
    → SMA_Slope.UP
elif slope < -0.005:  # < 0.5% decrease
    → SMA_Slope.DOWN
else:
    → SMA_Slope.FLAT
```

**Why 10-period lookback?**
- Smooths out short-term noise
- Captures meaningful trend changes
- 0.5% threshold filters flat/choppy conditions

---

#### Step 5: Check Price Position vs SMAs

```python
diff_pct = (current_price - SMA_value) / SMA_value

if diff_pct > 0.005:    # > 0.5% above
    → PriceVsSMA.ABOVE
elif diff_pct < -0.005:  # > 0.5% below
    → PriceVsSMA.BELOW
else:
    → PriceVsSMA.AT  # Within 0.5%
```

**Why 0.5% threshold?**
- Accounts for normal volatility
- Avoids constant flipping between ABOVE/AT/BELOW
- Provides clear categorization

---

#### Step 6: Identify Key S/R Levels

```python
# Group swing points by price proximity (within 1%)
for swing in swings:
    if abs(swing.price - group_avg) / group_avg < 0.01:
        → Add to group

# Create levels from groups
for group in price_groups:
    avg_price = average of group
    touch_count = number of swings in group
    strength = max strength from group
    
    # Determine strength
    if touch_count >= 3 or max_strength >= 0.8:
        → LevelStrength.STRONG
    elif touch_count >= 2 or max_strength >= 0.6:
        → LevelStrength.MEDIUM
    else:
        → LevelStrength.WEAK
```

**Why group by 1%?**
- Accounts for wicks/overshoots
- Identifies **zones** not exact prices
- More practical for real trading

---

#### Step 7: Determine Direction & Confidence

**Scoring System (Weighted):**

| Factor | Weight | Bullish Points | Bearish Points |
|--------|--------|----------------|----------------|
| Price Structure (HH/HL or LH/LL) | 40% | +0.4 | +0.4 |
| SMA50 Slope | 20% | +0.2 | +0.2 |
| SMA200 Slope | 15% | +0.15 | +0.15 |
| Price vs SMA50 | 15% | +0.15 | +0.15 |
| Price vs SMA200 | 10% | +0.10 | +0.10 |
| **Total** | **100%** | **1.0** | **1.0** |

**Logic:**
```python
bullish_score = 0.0
bearish_score = 0.0

# Price structure (40%)
if price_structure == UPTREND:
    bullish_score += 0.4
elif price_structure == DOWNTREND:
    bearish_score += 0.4

# SMA50 slope (20%)
if sma50_slope == UP:
    bullish_score += 0.2
elif sma50_slope == DOWN:
    bearish_score += 0.2

# ... (repeat for all factors)

# Determine direction
if bullish_score > bearish_score:
    → Direction = BULLISH, Confidence = bullish_score
elif bearish_score > bullish_score:
    → Direction = BEARISH, Confidence = bearish_score
else:
    → Direction = NEUTRAL, Confidence = 0.0
```

**Why Weighted Scoring?**
- **Price structure most important** (40%) = price action is king
- **SMA slopes secondary** (35% combined) = trend confirmation
- **Price position** (25% combined) = momentum check
- **Confidence score** = quantifies conviction

---

### Output Example

```python
HTFBias(
    direction=MTFDirection.BULLISH,
    confidence=0.65,  # 65% confidence
    price_structure=PriceStructure.UPTREND,  # HH/HL
    sma50_slope=SMASlope.UP,
    price_vs_sma50=PriceVsSMA.ABOVE,
    price_vs_sma200=PriceVsSMA.AT,
    key_levels=[
        SupportResistanceLevel(
            price=65000,
            level_type=LevelType.SUPPORT,
            strength=LevelStrength.STRONG
        ),
        SupportResistanceLevel(
            price=72000,
            level_type=LevelType.RESISTANCE,
            strength=LevelStrength.MEDIUM
        )
    ],
    swing_sequence=[...last 6 swings...]
)
```

---

## 2. MTF Setup Detection Logic

**File:** `src/services/mtf_setup_detector.py`

### Purpose
Identify **tradeable setups** within the HTF bias direction.

### Setup Types

| Setup Type | Description | Confidence |
|------------|-------------|------------|
| **PULLBACK** | Pullback to SMA20/50 in trend | 0.5-0.8 |
| **DIVERGENCE** | RSI divergence at key level | 0.6 |
| **BREAKOUT** | Breakout from consolidation | 0.5-0.7 |
| **CONSOLIDATION** | Flag/pennant/triangle | 0.4 |
| **RANGE_LOW/HIGH** | Range boundary setup | 0.5-0.6 |

---

### Pullback Detection Logic

**Why Pullbacks?**
- Trade **with the trend** at better prices
- Higher probability than counter-trend trades
- Better R:R (tighter stops)

**Criteria:**
```python
# 1. Price approaching SMA20 or SMA50
dist_20 = abs(price - SMA20) / SMA20
if dist_20 < 0.02:  # Within 2%
    → approaching_sma = 20

dist_50 = abs(price - SMA50) / SMA50
if dist_50 < 0.03:  # Within 3%
    → approaching_sma = 50

# 2. RSI condition (based on HTF direction)
if htf_direction == BULLISH:
    # In uptrend, RSI should be 35-50 (pullback but not broken)
    rsi_approaching_40 = (35 <= current_rsi <= 50)
elif htf_direction == BEARISH:
    # In downtrend, RSI should be 50-65 (rally but not broken)
    rsi_approaching_40 = (50 <= current_rsi <= 65)

# 3. Volume declining (healthy pullback)
if recent_volume < volume_ma:
    → volume_declining = True
```

**Confidence Calculation:**
```python
confidence = 0.5  # Base

if rsi_approaching_40:
    confidence += 0.2  # RSI confirms

if volume_declining:
    confidence += 0.1  # Volume confirms

→ Max confidence = 0.8
```

---

### Divergence Detection Logic

**Why Divergence?**
- Early warning of **momentum shift**
- High-probability reversal signal
- Works well at key S/R levels

**Logic:**
```python
# Bullish Divergence
if price_makes_new_low and RSI_makes_higher_low:
    → DivergenceType.REGULAR_BULLISH

# Bearish Divergence
if price_makes_new_high and RSI_makes_lower_high:
    → DivergenceType.REGULAR_BEARISH
```

**Confidence:** 0.6 (fixed)
- Divergence alone = moderate confidence
- **Divergence at HTF level** = high confidence (requires manual confirmation)

---

### Range Protocol Logic

**When HTF is RANGE:**
```python
# Identify range boundaries
range_low = recent_support
range_high = recent_resistance

# Check if price at boundary
if price at range_low (within 1%):
    → Setup = RANGE_LOW, Direction = BULLISH, Confidence = 0.5-0.6
elif price at range_high (within 1%):
    → Setup = RANGE_HIGH, Direction = BEARISH, Confidence = 0.5-0.6
else:
    → No setup (price in middle third)
```

**Why Range Protocol?**
- Different strategy for ranging vs trending markets
- Buy low, sell high (not buy breakout)
- Avoids whipsaws in range-bound conditions

---

### Output Example

```python
MTFSetup(
    setup_type=SetupType.PULLBACK,
    direction=MTFDirection.BULLISH,
    confidence=0.70,
    sma20_action="SUPPORT",
    sma50_action="NONE",
    rsi_divergence=None,
    pullback_details=PullbackSetup(
        approaching_sma=20,
        distance_to_sma_pct=0.36,
        rsi_level=49.2,
        rsi_approaching_40=True,
        volume_declining=True
    )
)
```

---

## 3. LTF Entry Signal Logic

**File:** `src/services/mtf_entry_finder.py`

### Purpose
Find **precise entry points** with tight stop losses.

### Entry Criteria (All Must Align)

1. ✅ LTF trend aligns with HTF direction
2. ✅ Price reclaims 20 EMA after pullback
3. ✅ Reversal candlestick pattern
4. ✅ RSI turns from key level

---

### Candlestick Pattern Detection

**Patterns Detected:**

#### 1. Engulfing Pattern
```python
# Bullish Engulfing
if current_close > current_open and  # Current is bullish
   prev_close < prev_open and       # Previous was bearish
   current_open <= prev_close and   # Opens at/below prev close
   current_close >= prev_open:      # Closes at/above prev open
    → ENGULFING pattern
```

**Why it works:** Complete reversal of previous candle's sentiment

---

#### 2. Hammer Pattern
```python
curr_body = abs(close - open)
curr_lower_wick = min(open, close) - low
curr_upper_wick = high - max(open, close)

if curr_lower_wick >= 2 * curr_body and  # Lower wick 2x body
   curr_upper_wick <= curr_body * 0.5:    # Small upper wick
    → HAMMER pattern
```

**Why it works:** Sellers pushed down, buyers rejected and closed high

---

#### 3. Pinbar Pattern
```python
if curr_upper_wick >= 3 * curr_body and  # Upper wick 3x body
   curr_lower_wick <= curr_body:          # Little/no lower wick
    → BEARISH PINBAR

if curr_lower_wick >= 3 * curr_body and  # Lower wick 3x body
   curr_upper_wick <= curr_body:          # Little/no upper wick
    → BULLISH PINBAR
```

**Why it works:** Extreme rejection at one end of range

---

#### 4. Inside Bar
```python
if current_high <= prev_high and
   current_low >= prev_low:
    → INSIDE_BAR pattern
```

**Why it works:** Consolidation before continuation/breakout

---

### EMA 20 Reclaim Logic

**Why EMA 20?**
- Faster than SMA, reacts to recent price
- Dynamic support/resistance
- Widely watched by traders

**Logic:**
```python
# For LONG entry
for i in range(2, 5):  # Check last 2-5 candles
    if prev_price < prev_EMA and   # Was below EMA
       current_price > current_EMA:  # Now above EMA
        → EMA_RECLAIM = True

# For SHORT entry (inverse)
if prev_price > prev_EMA and
   current_price < current_EMA:
    → EMA_RECLAIM = True
```

**Why check multiple candles?**
- Confirms the reclaim is sustained
- Avoids false breakouts
- Shows momentum shift

---

### RSI Turn Logic

**Logic:**
```python
# For LONG: RSI turns up from oversold (< 40)
if prev_rsi < 40 and current_rsi > prev_rsi:
    → RSI_TURN = UP_FROM_OVERSOLD

# For SHORT: RSI turns down from overbought (> 60)
if prev_rsi > 60 and current_rsi < prev_rsi:
    → RSI_TURN = DOWN_FROM_OVERBOUGHT
```

**Why 40/60 instead of 30/70?**
- **More sensitive** for entry timing
- Catches turns earlier
- Works better in trending markets (RSI can stay 40-60 in trends)

---

### Signal Priority

If multiple signals present:
```python
if candle_pattern != NONE:
    → Use candle_pattern as signal_type
elif ema_reclaim:
    → Use BREAKOUT as signal_type
else:
    → No signal
```

**Priority Order:**
1. Candlestick pattern (most reliable)
2. EMA reclaim (momentum shift)
3. RSI turn (confirmation only)

---

### Output Example

```python
LTFEntry(
    signal_type=EntrySignalType.INSIDE_BAR,
    direction=MTFDirection.BULLISH,
    ema20_reclaim=True,
    rsi_turning=RSITurn.UP_FROM_OVERSOLD,
    entry_price=67292.20,
    stop_loss=66234.56,
    confirmation_candle_close=67292.20
)
```

---

## 4. Alignment Scoring Logic

**File:** `src/services/mtf_alignment_scorer.py`

### Alignment Score Calculation

```python
alignment_score = 0

# HTF counts as 1 if not NEUTRAL
if htf_bias.direction != NEUTRAL:
    alignment_score += 1

# MTF counts as 1 if aligned with HTF
if mtf_setup.direction != NEUTRAL:
    if mtf_setup.direction == htf_bias.direction:
        alignment_score += 1

# LTF counts as 1 if aligned with HTF
if ltf_entry is not None and ltf_entry.direction != NEUTRAL:
    if ltf_entry.direction == htf_bias.direction:
        alignment_score += 1

→ Max score = 3/3
```

---

### Quality Assessment

| Score | Quality | Meaning | Action |
|-------|---------|---------|--------|
| **3/3** | HIGHEST | All TFs aligned | Trade aggressively |
| **2/3** | GOOD | 2 TFs aligned | Standard risk |
| **1/3** | POOR | Only 1 TF aligned | Avoid or reduce size |
| **0/3** | AVOID | No alignment | Do not trade |

---

### Recommendation Logic

```python
# Check for timeframe conflicts
if htf_direction != mtf_direction and mtf_direction != NEUTRAL:
    → has_conflict = True

if has_conflict:
    → Recommendation = WAIT
elif alignment_score < 2:
    → Recommendation = AVOID
else:
    if htf_direction == BULLISH:
        → Recommendation = BUY
    else:
        → Recommendation = SELL
```

---

### R:R Calculation

```python
if ltf_entry and entry_price > 0 and stop_loss > 0:
    risk = abs(entry_price - stop_loss)
    
    # Initial target estimate (refined by target_calculator)
    if recommendation in (BUY, SELL):
        target_price = entry_price + (risk * 2.5 if BUY else -risk * 2.5)
        reward = abs(target_price - entry_price)
        rr_ratio = reward / risk
```

**Why 2.5x initial estimate?**
- Conservative starting point
- Actual target refined by target_calculator
- Ensures minimum 2:1 R:R for most trades

---

## 5. Stop Loss Calculation

**File:** `src/services/mtf_entry_finder.py`

### Logic

```python
lookback = min(10, len(df))  # Last 10 candles

if direction == "LONG":
    # Find recent swing low
    recent_low = df['low'].iloc[-lookback:].min()
    
    # Add buffer (0.5%)
    stop_loss = recent_low * 0.995
    
else:  # SHORT
    # Find recent swing high
    recent_high = df['high'].iloc[-lookback:].max()
    
    # Add buffer (0.5%)
    stop_loss = recent_high * 1.005
```

---

### Why This Method?

#### 1. **Structural Stop** (Not Arbitrary)
- Based on **recent price structure**
- Below/above visible support/resistance
- Makes logical sense (invalidation point)

#### 2. **10-Candle Lookback**
- Captures recent swing points
- Not too tight (avoids noise)
- Not too loose (maintains good R:R)

#### 3. **0.5% Buffer**
- Accounts for **wick overshoots**
- Avoids stop hunts
- Standard practice in crypto/forex

---

### Example Calculation

**LONG Trade on BTC/USDT:**
```
Entry: $67,292.20
Recent 10-candle low: $66,567.00

Stop Loss = $66,567.00 × 0.995
           = $66,234.56

Risk = $67,292.20 - $66,234.56
     = $1,057.64 (1.57%)
```

**Why 1.57% risk is acceptable:**
- Typical for swing trading
- Allows for normal volatility
- Still achieves good R:R with proper targets

---

## 6. Take Profit Target Calculation

**File:** `src/services/target_calculator.py`

### 5 Target Methods

---

#### Method 1: HTF S/R Level (Primary) ⭐

**When to Use:**
- Clear HTF support/resistance ahead
- Most common method (70% of cases)
- Highest confidence

**Logic:**
```python
# Find next S/R level in trade direction
for level in htf_bias.key_levels:
    if direction == "LONG" and 
       level.type == RESISTANCE and 
       level.price > entry_price:
        → target_price = level.price
        → confidence = 0.7
        break
    
    if direction == "SHORT" and 
       level.type == SUPPORT and 
       level.price < entry_price:
        → target_price = level.price
        → confidence = 0.7
        break
```

**Example:**
```
Entry: $67,292 (LONG)
Next HTF Resistance: $69,936

Target = $69,936
Reward = $69,936 - $67,292 = $2,644
R:R = $2,644 / $1,058 = 2.5:1
```

---

#### Method 2: Measured Move

**When to Use:**
- Classical patterns (flag, triangle, rectangle)
- Breakout from consolidation
- Clear pattern boundaries

**Logic by Pattern:**

**Flag Pattern:**
```python
# Flagpole = impulse move before flag
impulse_start = recent_low (for LONG)
breakout_level = flag_high

flagpole = breakout_level - impulse_start

target = entry_price + flagpole
```

**Rectangle Pattern:**
```python
rectangle_height = rectangle_high - rectangle_low

if LONG:
    target = rectangle_high + rectangle_height
else:
    target = rectangle_low - rectangle_height
```

**Confidence:** 0.5-0.6
- Pattern targets are estimates
- Works best on clean, well-defined patterns

---

#### Method 3: Fibonacci Extension

**When to Use:**
- Strong impulse moves
- No clear S/R levels ahead
- Trending markets

**Logic:**
```python
# Anchor to recent swing
lookback = 20 candles

if direction == "LONG":
    swing_low = recent_low
    swing_high = recent_high
    
    fib_1272 = swing_high + (swing_high - swing_low) × 0.272
    fib_1618 = swing_high + (swing_high - swing_low) × 0.618
    fib_2618 = swing_high + (swing_high - swing_low) × 1.618
    
    → target = fib_1618 (standard)
    
else:  # SHORT
    # Inverse calculation
```

**Fibonacci Levels:**
| Level | Description | Use Case |
|-------|-------------|----------|
| 1.272 | Conservative | Quick profits |
| **1.618** | **Standard** | **Primary target** |
| 2.618 | Extended | Runner position |

---

#### Method 4: ATR-Based Target

**When to Use:**
- No clear S/R levels
- High volatility
- Default fallback method

**Logic:**
```python
ATR = Average True Range (14-period)

if direction == "LONG":
    target = entry_price + (ATR × multiplier)
else:
    target = entry_price - (ATR × multiplier)

# Multiplier based on trading style
SWING: multiplier = 3.0
INTRADAY: multiplier = 2.0
POSITION: multiplier = 4.0-5.0
```

**Why ATR?**
- Adapts to **current volatility**
- Higher vol = wider targets
- Lower vol = tighter targets

---

#### Method 5: Prior Swing High/Low

**When to Use:**
- Counter-trend trades
- Range markets
- Quick scalp targets

**Logic:**
```python
if direction == "LONG":
    # Target prior swing high
    target = recent_swing_high
else:
    # Target prior swing low
    target = recent_swing_low
```

**Confidence:** 0.5
- Counter-trend = lower confidence
- Use for partial profits only

---

### Auto-Selection Logic

```python
# Priority 1: Classical pattern present
if setup.consolidation_pattern in ("FLAG", "TRIANGLE", "RECTANGLE"):
    → Use MEASURED_MOVE

# Priority 2: Clear HTF S/R ahead
if htf_bias.key_levels and clear_level_ahead():
    → Use SR_LEVEL

# Priority 3: Strong impulse
if is_strong_impulse():
    → Use FIBONACCI

# Priority 4: Range market
if htf_bias.price_structure == RANGE:
    → Use PRIOR_SWING

# Default
→ Use ATR
```

---

### Multiple Target Strategy

**Recommended Approach:**
```
Target 1 (T1): 25% position at 1.5:1 R:R
Target 2 (T2): 50% position at 2.5:1 R:R (primary)
Target 3 (T3): 25% position at 4:1+ R:R (runner)
```

**Management:**
- At T1: Move stop to breakeven
- At T2: Trail stop using ATR or structure
- At T3: Let runner continue with tight trail

---

## 7. Complete Example

### Scenario: BTC/USDT Swing Trade

---

#### Step 1: HTF Analysis (Weekly)

```python
# Swing Points Detected
- HIGH at $74,500 (strength: 0.82)
- LOW at $49,100 (strength: 1.00)
- HIGH at $98,200 (strength: 0.93)
- LOW at $80,677 (strength: 1.00)

# Price Structure
→ HH/HL sequence detected (UPTREND)

# Moving Averages
SMA50 = $65,432 (slope: UP)
SMA200 = $58,900 (slope: UP)
Price = $67,292 (ABOVE SMA50, ABOVE SMA200)

# Key Levels
Support: $65,000 (STRONG)
Resistance: $72,000 (MEDIUM)

# HTF Bias Calculation
Price Structure (UPTREND): +0.4 bullish
SMA50 Slope (UP): +0.2 bullish
SMA200 Slope (UP): +0.15 bullish
Price vs SMA50 (ABOVE): +0.15 bullish
Price vs SMA200 (ABOVE): +0.10 bullish

→ HTF Bias: BULLISH
→ Confidence: 0.85 (85%)
```

---

#### Step 2: MTF Analysis (Daily)

```python
# Current Conditions
Price = $67,292
SMA20 = $66,800
SMA50 = $64,500
RSI(14) = 49.2

# Pullback Detection
Distance to SMA20 = 0.74% (< 2% threshold) ✅
RSI in range 35-50 = 49.2 ✅
Volume declining = True ✅

# MTF Setup
→ Setup Type: PULLBACK
→ Direction: BULLISH (aligned with HTF)
→ Confidence: 0.5 + 0.2 (RSI) + 0.1 (volume) = 0.80
```

---

#### Step 3: LTF Analysis (4H)

```python
# Candlestick Pattern
Current candle: Inside bar (within previous range)
→ Pattern: INSIDE_BAR

# EMA Check
Previous candles: Below EMA20
Current candle: Above EMA20
→ EMA Reclaim: True

# RSI Check
Previous RSI: 38.5 (< 40)
Current RSI: 42.1 (> previous)
→ RSI Turn: UP_FROM_OVERSOLD

# Entry Signal
→ Signal: INSIDE_BAR
→ Direction: BULLISH
→ Entry Price: $67,292.20
```

---

#### Step 4: Stop Loss Calculation

```python
# Recent 10-candle low
recent_low = $66,567.00

# Add 0.5% buffer
stop_loss = $66,567.00 × 0.995
           = $66,234.56

# Risk
risk = $67,292.20 - $66,234.56
     = $1,057.64 (1.57%)
```

---

#### Step 5: Target Calculation

```python
# Auto-select method
# Priority 1: No pattern
# Priority 2: Clear HTF resistance ahead ✅
→ Use SR_LEVEL method

# Next HTF resistance
target_price = $69,936

# Reward
reward = $69,936 - $67,292 = $2,644

# R:R Ratio
rr_ratio = $2,644 / $1,058 = 2.5:1
```

---

#### Step 6: Alignment Scoring

```python
# Alignment Count
HTF: BULLISH ✅ (+1)
MTF: BULLISH (aligned) ✅ (+1)
LTF: BULLISH (aligned) ✅ (+1)

→ Alignment Score: 3/3
→ Quality: HIGHEST

# Recommendation
→ BUY (all conditions met)
```

---

#### Step 7: Trade Summary

```python
╔═══════════════════════════════════════════════════════════╗
║         BTC/USDT — MTF TRADE SETUP (SWING)                ║
╠═══════════════════════════════════════════════════════════╣
║  Signal: BUY                                              ║
║  Quality: HIGHEST         (3/3 aligned)                   ║
║  Confidence: High                                         ║
╠═══════════════════════════════════════════════════════════╣
║  ENTRY:           $67,292.20                              ║
║  STOP LOSS:       $66,234.56                              ║
║  TARGET:          $69,936.00                              ║
╠═══════════════════════════════════════════════════════════╣
║  RISK:            $1,057.64 (1.57%)                       ║
║  REWARD:          $2,643.80 (3.93%)                       ║
║  R:R RATIO:       2.50:1                                  ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Summary Tables

### Decision Flow

| Step | Question | If Yes | If No |
|------|----------|--------|-------|
| 1 | HTF bias clear? | Proceed to MTF | WAIT (no bias) |
| 2 | MTF setup in direction? | Proceed to LTF | WAIT (no setup) |
| 3 | LTF entry signal? | Calculate risk | WAIT (no entry) |
| 4 | R:R ≥ 2.0? | Trade | SKIP (poor R:R) |
| 5 | Alignment ≥ 2/3? | Full size | Reduce size or skip |

---

### Confidence Levels

| Component | Confidence Range | Interpretation |
|-----------|------------------|----------------|
| **HTF Bias** | 0.6-0.8 | Strong trend |
| | 0.4-0.6 | Moderate trend |
| | < 0.4 | Weak/range |
| **MTF Setup** | 0.7-0.8 | Optimal pullback |
| | 0.5-0.7 | Standard setup |
| | < 0.5 | Weak setup |
| **Alignment** | 3/3 | Highest quality |
| | 2/3 | Good quality |
| | < 2/3 | Avoid |

---

### Risk Management Rules

| Rule | Value | Reason |
|------|-------|--------|
| **Max Risk per Trade** | 1-2% of account | Survive losing streaks |
| **Minimum R:R** | 2.0:1 | Profitable with 40% win rate |
| **Stop Loss Type** | Structural (below swing) | Logical invalidation |
| **Stop Buffer** | 0.5% | Avoid wick stops |
| **Target Method Priority** | S/R > Pattern > Fib > ATR | Highest probability first |

---

**End of Documentation**
