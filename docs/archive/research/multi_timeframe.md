# Strategy: Multi-Timeframe Analysis (MTF)
_Last updated: 2026-03-07_

## Overview
Multi-timeframe analysis (MTF) is the practice of analyzing multiple timeframes simultaneously to align the higher timeframe trend with lower timeframe entry precision. It is not a standalone strategy but a **framework** applied on top of any strategy.

**Core premise**: Higher timeframes determine direction; lower timeframes determine entry timing. Trading with all timeframes aligned produces the highest-probability trades.

---

## The Timeframe Hierarchy

### Top-Down Approach
Always start from the highest relevant timeframe and work down:

| Timeframe Layer | Role | Examples |
|----------------|------|---------|
| Higher (HTF) | Directional bias | Weekly → Daily |
| Middle (MTF) | Setup identification | Daily → 4H |
| Lower (LTF) | Entry timing | 4H → 1H → 15M |

### Common Timeframe Combinations
| Trading Style | Bias TF | Setup TF | Entry TF |
|--------------|---------|---------|---------|
| Position trading | Monthly | Weekly | Daily |
| Swing trading | Weekly | Daily | 4H |
| Intraday swing | Daily | 4H | 1H |
| Day trading | 4H | 1H | 15M or 5M |
| Scalping | 1H | 15M | 1–5M |

**General rule**: Entry timeframe should be 4–6× smaller than setup timeframe.

---

## Indicator Assignment by Timeframe Role

Indicators serve different purposes at each timeframe layer. Applying the wrong indicator to the wrong layer is a common source of poor decisions.

**Rule**: Oscillators belong on lower timeframes for entry timing. Higher timeframes use structural tools (MAs, S/R) for bias — oscillators lag too much at HTF and generate false signals.

### HTF — Directional Bias Indicators
| Indicator | Settings | Purpose |
|-----------|----------|---------|
| 50 SMA | Standard | Slope and price position determine medium-term trend direction |
| 200 SMA | Standard | Defines the secular trend; price above = bull regime, below = bear regime |
| Price structure | — | HH/HL or LH/LL sequence (minimum 2 confirmed swings — see Trend Definition below) |
| Volume | — | Confirms trend validity; declining volume on trend moves signals exhaustion |

**Do not use RSI, MACD, or Stochastic on the HTF for bias decisions.** These oscillators whipsaw on weekly/monthly charts and add noise, not signal.

### MTF — Setup Identification Indicators
| Indicator | Settings | Purpose |
|-----------|----------|---------|
| 20 SMA | Standard | Dynamic support/resistance during pullbacks in trending markets |
| 50 SMA | Standard | Key institutional level; pullbacks to 50 SMA in an uptrend are high-probability setups |
| RSI | 14 | Use for divergence detection only — not overbought/oversold levels |
| Volume | — | Must confirm breakouts; low-volume breakouts are suspect |

**RSI divergence on MTF**: when price makes a new high/low but RSI does not confirm, it signals momentum deterioration. This is a setup filter, not an entry trigger.

### LTF — Entry Timing Indicators
| Indicator | Settings | Purpose |
|-----------|----------|---------|
| Price action | — | Primary entry signal: candlestick patterns (engulfing, hammer, pin bar) at key levels |
| RSI | 14 | Entry timing: enter longs when RSI turns up from oversold (<40) at MTF support; shorts from overbought (>60) at MTF resistance |
| 20 EMA | Standard | Dynamic micro-trend direction; price reclaiming 20 EMA confirms LTF trend resumption |

**Keep LTF analysis simple.** The setup is already defined on MTF — the LTF job is only to find the lowest-risk entry point within that setup.

---

## The MTF Framework

### Step 1: Higher Timeframe Bias
Determine the dominant trend on the HTF using MAs and price structure:
- Is price making HH/HL (bullish) or LH/LL (bearish)? Require minimum 2 confirmed swing sequences.
- Is price above or below the 50 SMA and 200 SMA?
- Is the 50 SMA sloping up (bullish) or down (bearish)?
- Where is price relative to key HTF S/R levels?
- **Decision**: bullish bias, bearish bias, or no bias (HTF in range — see Range Protocol below)

**Only trade in the direction of the HTF bias.**

### Step 2: Middle Timeframe Setup
On the setup timeframe, look for a tradeable setup in the HTF direction:
- A pullback in an uptrend approaching MTF support (20 SMA or 50 SMA)
- RSI(14) divergence signaling momentum exhaustion against the HTF trend
- A consolidation pattern (flag, pennant, triangle) in the trend direction
- A breakout setup from a defined range, confirmed with volume

### Step 3: Lower Timeframe Entry
Once the setup is identified, drop to the LTF for a precise entry:
- Wait for LTF trend to align with HTF (LTF uptrend resuming in HTF uptrend)
- Price reclaims the 20 EMA on the LTF after a pullback
- Look for LTF reversal candle (engulfing, hammer, pin bar) at the MTF setup level
- RSI(14) on LTF turns up from below 40 (long) or down from above 60 (short)
- Enter on LTF confirmation → set stop at LTF structure → define target before entry (see Target Methods)

**Benefit of LTF entry**: much tighter stop loss (based on LTF swing low) with a larger target (MTF/HTF), dramatically improving R:R.

---

## Trend Definition

A trend is not confirmed by a single swing. Use these minimum criteria:

**Uptrend confirmed**: 2 sequential HH/HL pairs visible on the timeframe being assessed. The second HL must hold above the first HL. Any close below the most recent HL invalidates the uptrend.

**Downtrend confirmed**: 2 sequential LH/LL pairs visible. Any close above the most recent LH invalidates the downtrend.

**Trend invalidation**: A single decisive close beyond the prior swing structure (not a wick) is sufficient to call the trend broken. Do not require a second violation — act on the first structural break.

---

## Target Methods

Define the target **before** entry. Never leave targets open-ended. Use one primary method and one confirming method per trade.

### Method 1: Next HTF S/R Level (Primary)
The default target is the next significant S/R level on the setup or HTF chart. Identify it before entry. Do not move the target after the trade is open unless the original level is clearly eliminated.

### Method 2: Measured Move / Pattern Target
Classical chart patterns provide objective price targets:
- **Bull flag**: flagpole length projected from breakout point
- **Ascending triangle**: triangle height projected from breakout
- **Inverse H&S**: head-to-neckline distance projected above neckline
- **Double bottom**: trough-to-neckline distance projected above neckline

Use the pattern target as a minimum objective. If HTF S/R sits below the pattern target, use the S/R level instead.

### Method 3: Fibonacci Extension
After a confirmed impulsive move (Wave 1 of a new trend), apply Fibonacci extensions to project Wave 3/5 targets:
- **1.272 extension**: conservative target, suitable for partial profit-taking
- **1.618 extension**: standard measured-move target
- **2.618 extension**: extended target in a strong trend; only trail into this level, do not set as a fixed target

*Anchor the Fibonacci tool from the swing low to swing high of the impulse (for uptrends), then from the retracement low.*

### Method 4: ATR-Based Target
Use Average True Range (ATR, 14 periods) on the setup timeframe to set a volatility-adjusted target:
- **Minimum target**: 2× ATR from entry
- **Standard target**: 3× ATR from entry
- **Extended target**: 4–5× ATR only in strong-trend, all-3-TF-aligned setups

ATR targets are most useful when S/R levels are absent or too far away, and for short-term day-trading setups where pattern targets are impractical.

### Method 5: Prior Swing High/Low (Structural Target)
In a trending market, the most recent prior swing high (for longs) or swing low (for shorts) is a natural profit target. Price frequently revisits prior swing extremes before continuing. This is the most conservative of all target methods and appropriate when:
- Entering counter-trend or in a range
- Volatility is elevated and a conservative target is warranted
- Using a wide stop that requires a closer target to maintain minimum 2:1 R:R

### Target Priority Guide
| Situation | Preferred Method |
|-----------|----------------|
| Clear HTF S/R ahead | HTF S/R Level (Method 1) |
| Classical pattern present | Measured Move (Method 2) |
| Strong new impulse starting | Fibonacci Extension (Method 3) |
| No clear S/R; high volatility | ATR-Based (Method 4) |
| Counter-trend or range trade | Prior Swing High/Low (Method 5) |
| All-3-TF aligned, strong trend | Combine Methods 2 + 3; trail into target |

**Partial profit-taking**: in high-conviction setups, consider taking 50% off at Method 5 (prior swing) and trailing the remainder toward Methods 1–3.

---

## Timeframe Alignment Score
For a trade to be taken, require alignment across at least 2 of 3 timeframes:

| Alignment | Trade Quality |
|-----------|--------------|
| All 3 TFs bullish | Highest quality — trade aggressively |
| 2 of 3 bullish | Good quality — trade with standard risk |
| 1 of 3 bullish | Poor quality — avoid or reduce size |
| 0 of 3 bullish | Do not trade long |

**When HTF and MTF conflict**: do not trade until LTF confirms HTF direction. Require all 3 TFs to align before entering. If alignment does not materialize, pass on the trade entirely.

---

## Range Protocol (HTF No-Bias Condition)

When the HTF is in a range (no confirmed HH/HL or LH/LL sequence; price oscillating between defined levels), the trend-following MTF framework does not apply. Switch to the following protocol:

**Range boundaries**: Identify the HTF range high and range low. These are the only levels that matter until one is broken.

**Tradeable setups inside a range**:
- Long at range low support with LTF reversal confirmation; target is range midpoint or range high
- Short at range high resistance with LTF reversal confirmation; target is range midpoint or range low
- Do not trade in the middle third of the range — risk/reward is insufficient

**Breakout from range**:
- A decisive HTF close above range high (with volume) re-activates the bullish trend-following framework
- A decisive HTF close below range low re-activates the bearish framework
- Do not anticipate the breakout — wait for the confirmed close

**False breakout filter**: require the breakout candle to close in the top 25% of its range (bullish) or bottom 25% (bearish). A close in the middle of the candle after a breakout attempt is a warning of a false break.

---

## MTF Divergence (Warning)

When timeframes conflict, the following rules apply:

| Conflict | Action |
|----------|--------|
| HTF bullish, MTF bearish | Wait for MTF to turn bullish before entry; do not force trades |
| HTF bullish, MTF bearish, LTF bullish | Require all 3 to align; pass if MTF does not confirm |
| Price at HTF support, but MTF RSI diverging (price new low, RSI higher low) | This is a bullish divergence signal — treat as a setup, not a warning |
| Price at HTF support, MTF RSI confirming (both making new lows) | No divergence — no setup; wait or stand aside |
| HTF and MTF conflicting with no resolution | Range is likely forming; switch to Range Protocol above |

Conflicting signals are not automatically negative — RSI divergence at HTF support is a high-probability setup. Read the conflict carefully before deciding to stand aside.

---

## Common MTF Patterns

### HTF Support + LTF Reversal
1. Weekly chart: price at major support; 50 SMA sloping up and holding
2. Daily chart: price forming a base; RSI(14) showing bullish divergence (price new low, RSI higher low)
3. 4H chart: bullish engulfing or hammer forms at the daily support; RSI turns up from below 40

**Entry**: Buy on 4H confirmation candle close
**Stop**: Below 4H swing low (tight, within the daily support zone)
**Target**: Next weekly resistance level (Method 1); confirm with Fibonacci 1.618 extension (Method 3)

### HTF Trend + MTF Pullback + LTF Entry
1. Daily: strong uptrend (2+ HH/HL confirmed), price pulling back toward 50 SMA
2. 4H: price at the 50 SMA, forming higher lows; RSI(14) approaching 40 without breaking it
3. 1H: price reclaims 20 EMA; bullish breakout from a small consolidation; RSI turns up

**Entry**: 1H breakout candle close above consolidation high
**Stop**: Below 1H swing low
**Target**: Daily prior high (Method 5) for first partial; Fibonacci 1.618 extension (Method 3) for remainder

### Converging Levels Across Timeframes
When the same price area appears as support/resistance on multiple timeframes, it is extremely significant:
- Weekly S/R + Daily S/R at the same level = very strong zone
- Add a Fibonacci level at the same area = exceptional confluence
- Add ATR measurement confirming the zone is within a 2:1+ R:R = trade with full size

---

## Practical Checklist for Every Trade
Before entering, answer all of the following:

1. ✅ What is the HTF trend direction? (2+ confirmed HH/HL or LH/LL sequences)
2. ✅ Is the HTF using 50/200 SMA for MA confirmation?
3. ✅ Is the setup timeframe in alignment with the HTF?
4. ✅ Is there MTF RSI divergence or a pattern setup confirming the trade direction?
5. ✅ Is there a clear entry signal on the LTF? (Candle pattern + 20 EMA reclaim + RSI timing)
6. ✅ Is the stop at a LTF structure level (specific price, not arbitrary)?
7. ✅ Is the target defined before entry using a named method (S/R, measured move, Fib, ATR, or prior swing)?
8. ✅ What is the R:R? (Minimum 2:1 required)
9. ✅ Is this a range environment? If yes, is the Range Protocol being followed instead?

If any answer is "no" or "unclear", do not take the trade.
