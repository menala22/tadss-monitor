#!/usr/bin/env python3
"""
MTF Analysis Report Generator - UPGRADED SYSTEM

Generates a detailed Multi-Timeframe Analysis report for a given trading pair.
Fetches real-time data and calculates all MTF metrics with upgraded 4-layer system.

UPGRADED Features (NEW):
- Layer 1: MTF Context Classification (ADX, ATR, EMA distance)
- Layer 2: Context-Gated Setup Detection
- Layer 3: Pullback Quality Scoring (multi-factor)
- Layer 4: Weighted Alignment & Position Sizing

Legacy Features:
- Full MTF analysis (HTF bias, MTF setup, LTF entry)
- Markdown report with analysis results
- Data quality checks

Usage:
    python scripts/generate_mtf_report.py BTC/USDT SWING
    python scripts/generate_mtf_report.py ETH/USDT INTRADAY

Output:
    docs/reports/{pair}-mtf-analysis-{style}-{date}.md
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetcher import DataFetcher
from src.services.mtf_alignment_scorer import MTFAnalyzer
from src.services.mtf_bias_detector import HTFBiasDetector
from src.services.mtf_setup_detector import MTFSetupDetector
from src.services.mtf_entry_finder import LTFEntryFinder
from src.services.divergence_detector import DivergenceDetector
from src.services.target_calculator import TargetCalculator
from src.services.support_resistance_detector import SupportResistanceDetector
from src.services.data_quality_checker import check_data_quality
from src.models.mtf_models import (
    MTFTimeframeConfig,
    TradingStyle,
    MTFDirection,
    AlignmentQuality,
    DataQualityReport,
    DataQualityStatus,
)


def fetch_real_data(pair: str, config: MTFTimeframeConfig) -> dict:
    """
    Fetch real OHLCV data for all 3 timeframes.

    Auto-selects best data source:
    - Crypto (BTC, ETH) → CCXT/Kraken (free, more history)
    - Metals (XAG, XAU) → Gate.io (swap contracts)

    Args:
        pair: Trading pair (e.g., 'BTC/USDT').
        config: MTF timeframe configuration.

    Returns:
        Dictionary with htf, mtf, ltf DataFrames.
    """
    print(f"📡 Fetching data for {pair}...")
    print(f"  HTF: {config.htf_timeframe} ({config.trading_style.value})")
    print(f"  MTF: {config.mtf_timeframe}")
    print(f"  LTF: {config.ltf_timeframe}")

    # Auto-select data source based on pair
    pair_upper = pair.upper().replace('/', '').replace('-', '').replace('_', '')

    if pair_upper.startswith(('BTC', 'ETH', 'SOL', 'XRP', 'ADA')):
        source = 'ccxt'
        print(f"  Source: CCXT/Kraken (crypto)")
    elif pair_upper.startswith(('XAG', 'XAU')):
        source = 'gateio'
        print(f"  Source: Gate.io (metals swap)")
    else:
        source = 'gateio'  # Default to gateio
        print(f"  Source: Gate.io")

    fetcher = DataFetcher(source=source)

    # Map internal timeframes to API format
    tf_map = {
        'm1': '1m', 'm5': '5m', 'm15': '15m', 'm30': '30m',
        'h1': '1h', 'h2': '2h', 'h4': '4h', 'h6': '6h', 'h8': '8h', 'h12': '12h',
        'd1': '1d', 'd3': '3d', 'd5': '5d',
        'w1': '1w', 'M1': '1M',
    }

    htf_tf = tf_map.get(config.htf_timeframe, '1d')
    mtf_tf = tf_map.get(config.mtf_timeframe, '4h')
    ltf_tf = tf_map.get(config.ltf_timeframe, '1h')

    # Fetch data with increased limits for HTF
    print(f"  Fetching HTF ({htf_tf})... need 200+ candles for full analysis")
    htf_df = fetcher.get_ohlcv(pair, htf_tf, limit=500)  # Max for historical

    print(f"  Fetching MTF ({mtf_tf})...")
    mtf_df = fetcher.get_ohlcv(pair, mtf_tf, limit=200)

    print(f"  Fetching LTF ({ltf_tf})...")
    ltf_df = fetcher.get_ohlcv(pair, ltf_tf, limit=500)

    print(f"  ✓ HTF: {len(htf_df)} candles {'✓' if len(htf_df) >= 200 else '⚠️ Need 200+ for full SMA analysis'}")
    print(f"  ✓ MTF: {len(mtf_df)} candles")
    print(f"  ✓ LTF: {len(ltf_df)} candles")

    return {
        'htf': htf_df,
        'mtf': mtf_df,
        'ltf': ltf_df,
    }


def generate_report(
    pair: str,
    trading_style: str,
    alignment,
    data: dict,
    config: MTFTimeframeConfig,
    quality_report: Optional[DataQualityReport] = None,
) -> str:
    """
    Generate markdown report from analysis results.

    Args:
        pair: Trading pair.
        trading_style: Trading style name.
        alignment: MTFAlignment object.
        data: Dictionary with OHLCV DataFrames.
        config: MTF timeframe configuration.
        quality_report: Data quality report (optional).

    Returns:
        Markdown report content with data quality dashboard.
    """
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    # Extract values
    htf_bias = alignment.htf_bias
    mtf_setup = alignment.mtf_setup
    ltf_entry = alignment.ltf_entry

    # Get current prices (handle column name variations)
    def get_close(df):
        if df is None or df.empty:
            return 0
        # Handle both 'close' and 'Close' column names
        close_col = 'close' if 'close' in df.columns else 'Close'
        return df[close_col].iloc[-1]

    htf_close = get_close(data['htf'])
    mtf_close = get_close(data['mtf'])
    ltf_close = get_close(data['ltf'])

    # Build report
    report = f"""# MTF Analysis Report: {pair} ({trading_style.title()} Trading)

**Generated:** {now}  
**Trading Style:** {trading_style.upper()}  
**Analysis Type:** Multi-Timeframe Framework (Real-Time Data)  
**Data Source:** CCXT/Kraken (Crypto), Twelve Data (Metals/Forex)

---

## ⚠️ Disclaimer

This report is generated for **educational and informational purposes only**. 
It does not constitute financial advice. Always do your own research before trading.

Past performance does not guarantee future results. Trading involves substantial risk.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Pair** | {pair} |
| **Overall Signal** | {alignment.recommendation.value} |
| **Alignment Score** | {alignment.alignment_score}/3 ({alignment.quality.value}) |
| **HTF Close** | ${htf_close:,.2f} |
| **MTF Close** | ${mtf_close:,.2f} |
| **LTF Close** | ${ltf_close:,.2f} |
"""

    # Add entry/stop/target if available
    if ltf_entry.entry_price:
        report += f"""| **Entry Price** | ${ltf_entry.entry_price:,.2f} |
| **Stop Loss** | ${ltf_entry.stop_loss:,.2f} |
| **Target Price** | ${alignment.target.target_price:,.2f} |
| **R:R Ratio** | {alignment.rr_ratio:.2f}:1 |
"""

    report += f"""| **Confidence** | {'High' if alignment.rr_ratio > 0 else 'Pending'} |

"""

    # Add UPGRADED SYSTEM section (NEW)
    report += f"""
---

## 🆙 Upgraded MTF System Analysis

### Layer 1: Market Context

| Metric | Value |
|--------|-------|
| **Context** | {alignment.mtf_setup.mtf_context.value if alignment.mtf_setup.mtf_context else 'N/A'} |
"""

    # Add ADX and distance if available
    if alignment.mtf_setup.mtf_context_result:
        ctx_result = alignment.mtf_setup.mtf_context_result
        report += f"| **ADX** | {ctx_result.adx:.2f} |\n"
        report += f"| **Distance from EMA** | {ctx_result.distance_from_ema_atr:.2f} ATR |\n"
        report += f"| **ATR** | {ctx_result.atr:.2f} |\n"
    
    report += "\n"
    
    # Add reasoning
    if alignment.mtf_setup.mtf_context_result and alignment.mtf_setup.mtf_context_result.reasoning:
        report += f"**Assessment:** {alignment.mtf_setup.mtf_context_result.reasoning}\n\n"
    
    report += """#### Context Classification Rationale (Audit Trail)

The context classification is based on the following decision tree:

"""

    # Add detailed context rationale
    if alignment.mtf_setup.mtf_context_result:
        ctx_result = alignment.mtf_setup.mtf_context_result
        
        # ADX interpretation
        if ctx_result.adx > 25:
            adx_interpretation = f"**ADX = {ctx_result.adx:.2f}** (> 25) → **Trending market** — directional bias confirmed"
        elif ctx_result.adx < 20:
            adx_interpretation = f"**ADX = {ctx_result.adx:.2f}** (< 20) → **Ranging market** — no clear trend"
        else:
            adx_interpretation = f"**ADX = {ctx_result.adx:.2f}** (20-25) → **Transition zone** — market deciding direction"
        
        report += f"**Step 1: Trend Strength (ADX)**\n"
        report += f"- {adx_interpretation}\n\n"
        
        # Distance interpretation
        dist = abs(ctx_result.distance_from_ema_atr)
        direction = "above" if ctx_result.distance_from_ema_atr > 0 else "below"
        
        if dist > 3.0:
            dist_interpretation = f"**Distance = {dist:.2f} ATR** (> 3.0 ATR {direction} EMA21) → **Overextended** — price stretched from mean"
        elif dist < 1.5:
            dist_interpretation = f"**Distance = {dist:.2f} ATR** (< 1.5 ATR {direction} EMA21) → **Pullback zone** — price near moving average"
        else:
            dist_interpretation = f"**Distance = {dist:.2f} ATR** (1.5-3.0 ATR {direction} EMA21) → **Normal trend space** — neither extended nor pulling back"
        
        report += f"**Step 2: Price Position (ATR-Normalized Distance)**\n"
        report += f"- {dist_interpretation}\n\n"
        
        # Final classification
        report += f"**Step 3: Context Assignment**\n"
        report += f"- ADX + Distance combined → **{ctx_result.context.value}**\n"
        report += f"- **Implication:** "
        
        if ctx_result.context == 'TRENDING_PULLBACK':
            report += "Pullback setups are valid. Look for entries near EMA with declining volume.\n"
        elif ctx_result.context == 'TRENDING_EXTENSION':
            report += "NO setups valid. Wait for price to pull back to EMA before considering entries.\n"
        elif ctx_result.context == 'BREAKING_OUT':
            report += "Breakout setups valid. Look for volume confirmation and momentum.\n"
        elif ctx_result.context == 'CONSOLIDATING':
            report += "Range setups only or wait. Avoid trend-following strategies.\n"
        elif ctx_result.context == 'REVERSING':
            report += "Divergence/reversal setups valid. Watch for structure breaks.\n"
        
        report += "\n**Educational Note:** This context-first approach prevents false setups. For example, if the market is in TRENDING_EXTENSION, no setups will fire regardless of other signals — you wait for a better entry.\n\n"
    else:
        report += "*Context classification details not available*\n\n"

    # Layer 3: Pullback Quality Score
    if alignment.mtf_setup.pullback_quality_score:
        qs = alignment.mtf_setup.pullback_quality_score
        quality_emoji = "✅" if qs.total_score >= 0.6 else "⚠️" if qs.total_score >= 0.4 else "❌"
        
        report += f"""
### Layer 3: Pullback Quality Score {quality_emoji}

| Factor | Score | Weight |
|--------|-------|--------|
| **Total Score** | {qs.total_score:.2f} | 100% |
| Distance to EMA | {qs.distance_score:.2f} | 25% |
| RSI Compression | {qs.rsi_score:.2f} | 20% |
| Volume Profile | {qs.volume_score:.2f} | 25% |
| Level Confluence | {qs.confluence_score:.2f} | 20% |
| Candle Structure | {qs.structure_score:.2f} | 10% |

**Quality Reasons:**
"""
        for reason in qs.reasons:
            report += f"- {reason}\n"
        report += "\n"
    else:
        report += """
### Layer 3: Pullback Quality Score ⚠️

*No pullback quality score available - either no pullback setup or context doesn't allow pullbacks*

"""

    # Layer 4: Weighted Alignment & Position Sizing
    report += f"""
### Layer 4: Weighted Alignment & Position Sizing

| Metric | Value | Action |
|--------|-------|--------|
| **Weighted Score** | {alignment.weighted_score:.2f} | {'✅ High' if alignment.weighted_score >= 0.75 else '⚠️ Moderate' if alignment.weighted_score >= 0.50 else '❌ Low'} |
| **Position Size** | {alignment.position_size_pct:.0f}% of base risk | {'Full size' if alignment.position_size_pct >= 100 else 'Standard' if alignment.position_size_pct >= 75 else 'Reduced' if alignment.position_size_pct >= 50 else 'No trade'} |
| **Legacy Score** | {alignment.alignment_score}/3 | {alignment.quality.value} |

"""

    # Add data quality dashboard if available
    if quality_report:
        status_emoji = {
            DataQualityStatus.PASS: "✅",
            DataQualityStatus.WARNING: "⚠️",
            DataQualityStatus.FAIL: "❌",
        }
        
        report += f"""
## 📊 Data Quality Check

**Overall Status:** {status_emoji.get(quality_report.overall_status, "❓")} {quality_report.overall_status.value}

| Timeframe | Candles | Required | Status | Freshness |
|-----------|---------|----------|--------|-----------|
| **HTF** ({quality_report.htf_quality.timeframe}) | {quality_report.htf_quality.candle_count} | {quality_report.htf_quality.required_count} | {status_emoji.get(quality_report.htf_quality.status, "")} {quality_report.htf_quality.status.value} | {quality_report.htf_quality.freshness_hours:.1f}h old |
| **MTF** ({quality_report.mtf_quality.timeframe}) | {quality_report.mtf_quality.candle_count} | {quality_report.mtf_quality.required_count} | {status_emoji.get(quality_report.mtf_quality.status, "")} {quality_report.mtf_quality.status.value} | {quality_report.mtf_quality.freshness_hours:.1f}h old |
| **LTF** ({quality_report.ltf_quality.timeframe}) | {quality_report.ltf_quality.candle_count} | {quality_report.ltf_quality.required_count} | {status_emoji.get(quality_report.ltf_quality.status, "")} {quality_report.ltf_quality.status.value} | {quality_report.ltf_quality.freshness_hours:.1f}h old |

**Assessment:** {quality_report.summary}

"""
        
        # Add warnings if data quality is not PASS
        if quality_report.overall_status != DataQualityStatus.PASS:
            report += f"""
> [!WARNING]
> **Data Quality Warning:** {quality_report.summary}
> 
"""
            if quality_report.recommendations:
                report += "**Recommendations:**\n"
                for i, rec in enumerate(quality_report.recommendations[:3], 1):
                    report += f"{i}. {rec}\n"
                report += "\n"
        
        # Add MTF readiness warning
        if not quality_report.is_mtf_ready:
            report += f"""
> [!IMPORTANT]
> **MTF Analysis Not Recommended:** Insufficient data for reliable MTF analysis.
> The signals below may be unreliable due to data quality issues.
>
"""

    report += f"""
## Timeframe Configuration ({trading_style.title()})

| Layer | Timeframe | Role | Indicators |
|-------|-----------|------|------------|
| **HTF** | {config.htf_timeframe} | Directional Bias | 50 EMA, 200 EMA, Price Structure, ADX |
| **MTF** | {config.mtf_timeframe} | Setup Identification | 21 EMA, 50 EMA, RSI(14), ATR |
| **LTF** | {config.ltf_timeframe} | Entry Timing | 20 EMA, Candlestick Patterns, RSI(14) |

---
"""

    report += f"""
## 1. Higher Timeframe ({config.htf_timeframe}) — Directional Bias

### 1.1 Price Structure

**Structure Type:** {htf_bias.price_structure.value}

"""

    # Add swing sequence
    if htf_bias.swing_sequence:
        report += "**Recent Swing Points:**\n"
        report += "| Type | Price | Strength |\n"
        report += "|------|-------|----------|\n"
        for swing in htf_bias.swing_sequence[-6:]:
            report += f"| {swing.swing_type} | ${swing.price:,.2f} | {swing.strength:.2f} |\n"

    report += f"""
### 1.2 Moving Averages

| MA | Value | Price Position | Slope |
|----|-------|----------------|-------|
| 50 EMA | ${htf_bias.ema20_value:,.2f} | {htf_bias.price_vs_sma50.value} | {htf_bias.ema20_slope.value} |
| 200 EMA | ${htf_bias.ema50_value:,.2f} | {htf_bias.price_vs_sma200.value} | {htf_bias.ema50_slope.value} |

*Note: Using EMA (Exponential Moving Average) for faster response to price changes. Legacy field names (50/200) kept for consistency.*

### 1.3 Key Levels

"""

    if htf_bias.key_levels:
        report += "| Type | Price | Strength |\n"
        report += "|------|-------|----------|\n"
        for level in htf_bias.key_levels[:5]:
            report += f"| {level.level_type.value} | ${level.price:,.2f} | {level.strength.value} |\n"

    report += f"""
### 1.4 HTF Bias Result

```
HTF ({config.htf_timeframe}) Bias: {htf_bias.direction.value}
Confidence: {htf_bias.confidence:.2f}
Price Structure: {htf_bias.price_structure.value}
```

---

## 2. MidTF (Middle Timeframe: {config.mtf_timeframe}) — Setup Identification

### 2.1 Setup Details

**Setup Type:** {mtf_setup.setup_type.value}
**Direction:** {mtf_setup.direction.value}
**Confidence:** {mtf_setup.confidence:.2f}

"""

    if mtf_setup.pullback_details:
        pb = mtf_setup.pullback_details
        report += f"""**Pullback Details:**
- Approaching EMA: {pb.approaching_sma}
- Distance to EMA: {pb.distance_to_sma_pct:.2f}%
- RSI Level: {pb.rsi_level:.1f}
"""

    if mtf_setup.rsi_divergence:
        report += f"\n**Divergence:** {mtf_setup.rsi_divergence.value}\n"

    report += f"""
### 2.2 MTF Setup Result

```
MTF ({config.mtf_timeframe}) Setup: {mtf_setup.setup_type.value}
Confidence: {mtf_setup.confidence:.2f}
Direction: {mtf_setup.direction.value}
```

---

## 3. Lower Timeframe ({config.ltf_timeframe}) — Entry Signal

### 3.1 Entry Details

**Signal Type:** {ltf_entry.signal_type.value}  
**Direction:** {ltf_entry.direction.value}  
**EMA20 Reclaim:** {'Yes ✓' if ltf_entry.ema20_reclaim else 'No ✗'}  
**RSI Turn:** {ltf_entry.rsi_turning.value}

"""

    if ltf_entry.entry_price:
        report += f"""### 3.2 Trade Parameters

| Parameter | Value |
|-----------|-------|
| Entry Price | ${ltf_entry.entry_price:,.2f} |
| Stop Loss | ${ltf_entry.stop_loss:,.2f} |
| Risk | ${ltf_entry.entry_price - ltf_entry.stop_loss:,.2f} ({(ltf_entry.entry_price - ltf_entry.stop_loss) / ltf_entry.entry_price * 100:.2f}%) |
"""

    if alignment.target:
        report += f"""| Target | ${alignment.target.target_price:,.2f} |
| Reward | ${alignment.target.target_price - ltf_entry.entry_price:,.2f} ({(alignment.target.target_price - ltf_entry.entry_price) / ltf_entry.entry_price * 100:.2f}%) |
| R:R Ratio | {alignment.rr_ratio:.2f}:1 |

#### Target Calculation Rationale

**Method:** {alignment.target.method.value}

**Calculation Details:**
- **Entry:** ${ltf_entry.entry_price:,.2f}
- **Stop Loss:** ${ltf_entry.stop_loss:,.2f}
- **Risk:** ${ltf_entry.entry_price - ltf_entry.stop_loss:,.2f} per unit
- **Target:** ${alignment.target.target_price:,.2f}
- **Reward:** ${alignment.target.target_price - ltf_entry.entry_price:,.2f} per unit
- **R:R Ratio:** {alignment.rr_ratio:.2f}:1

**Reasoning:** {alignment.target.description if alignment.target.description else 'Target calculated based on technical levels'}

**Confidence:** {'✅ High' if alignment.target.confidence >= 0.7 else '⚠️ Moderate' if alignment.target.confidence >= 0.5 else '❌ Low'} ({alignment.target.confidence:.0%})

"""

    report += f"""
### 3.3 LTF Entry Result

```
LTF ({config.ltf_timeframe}) Entry: {ltf_entry.signal_type.value}
Entry Price: ${ltf_entry.entry_price:,.2f}
Stop Loss: ${ltf_entry.stop_loss:,.2f}
```

---

## 4. Alignment Scoring

### 4.1 Timeframe Alignment

| Timeframe | Direction | Confidence | Aligned? |
|-----------|-----------|------------|----------|
| HTF ({config.htf_timeframe}) | {htf_bias.direction.value} | {htf_bias.confidence:.2f} | {'✅' if htf_bias.direction != MTFDirection.NEUTRAL else '❌'} |
| MTF ({config.mtf_timeframe}) | {mtf_setup.direction.value} | {mtf_setup.confidence:.2f} | {'✅' if mtf_setup.direction == htf_bias.direction else '❌'} |
| LTF ({config.ltf_timeframe}) | {ltf_entry.direction.value} | — | {'✅' if ltf_entry.direction == htf_bias.direction else '❌'} |

**Alignment Score: {alignment.alignment_score}/3**

### 4.2 Quality Assessment

```
Alignment Score: {alignment.alignment_score}/3
Quality: {alignment.quality.value}
Recommendation: {alignment.recommendation.value}
```

### 4.3 Patterns Detected

"""

    if alignment.notes:
        for pattern in alignment.notes.split(' | '):
            if 'Pattern' in pattern or 'TF' in pattern:
                report += f"- {pattern}\n"

    report += f"""
---

## 5. Final Trade Setup

```
╔═══════════════════════════════════════════════════════════╗
║         {pair} — MTF TRADE SETUP ({trading_style.upper()})            ║
╠═══════════════════════════════════════════════════════════╣
║  Signal: {alignment.recommendation.value:<54}║
║  Quality: {alignment.quality.value:<15} ({alignment.alignment_score}/3 aligned){' ' * 25}║
║  Confidence: {alignment.rr_ratio > 0 and 'High' or 'Pending':<46}║
╠═══════════════════════════════════════════════════════════╣
"""

    if ltf_entry.entry_price:
        report += f"""║  ENTRY:           ${ltf_entry.entry_price:>42,.2f}║
║  STOP LOSS:       ${ltf_entry.stop_loss:>42,.2f}║
║  TARGET:          ${alignment.target.target_price:>42,.2f}║
╠═══════════════════════════════════════════════════════════╣
║  RISK:            ${ltf_entry.entry_price - ltf_entry.stop_loss:>42,.2f}║
║  REWARD:          ${alignment.target.target_price - ltf_entry.entry_price:>42,.2f}║
║  R:R RATIO:       {alignment.rr_ratio:>42,.2f}:1║
"""

    report += f"""╚═══════════════════════════════════════════════════════════╝
```

---

## 6. Risk Warning

**This analysis is based on historical data and technical indicators. It does not:**

- Guarantee future performance
- Account for fundamental news or events
- Replace proper risk management
- Constitute financial advice

**Always:**
- Use proper position sizing (risk 1-2% per trade)
- Set stop losses and stick to them
- Do your own research
- Never trade more than you can afford to lose

---

## 7. Monitoring Checklist

### Before Entry:
- [ ] All 3 timeframes aligned?
- [ ] R:R ratio ≥ 2.0?
- [ ] No major news events scheduled?
- [ ] Position size calculated?

### After Entry:
- [ ] Stop loss set?
- [ ] Target levels defined?
- [ ] Monitoring plan in place?

---

**Report Generated by TA-DSS MTF Scanner**  
*Multi-Timeframe Analysis Framework v1.0*  
**Data is real-time. Analysis is automated. Trade at your own risk.**
"""

    return report


if __name__ == '__main__':
    # Parse arguments
    if len(sys.argv) < 2:
        pair = 'BTC/USDT'
        style = 'SWING'
    else:
        pair = sys.argv[1].upper()
        style = sys.argv[2].upper() if len(sys.argv) > 2 else 'SWING'

    print(f"🔍 MTF Analysis Report Generator")
    print(f"   Pair: {pair}")
    print(f"   Style: {style}")
    print("=" * 50)

    # Get configuration
    try:
        config = MTFTimeframeConfig.get_config(TradingStyle[style])
    except KeyError:
        print(f"❌ Invalid trading style: {style}")
        print(f"   Valid options: POSITION, SWING, INTRADAY, DAY, SCALPING")
        sys.exit(1)

    # Fetch real data
    try:
        data = fetch_real_data(pair, config)
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print(f"   Make sure you have API keys configured in .env")
        sys.exit(1)

    # Run MTF analysis
    print("\n📊 Running MTF analysis...")
    analyzer = MTFAnalyzer(config)
    alignment = analyzer.analyze_pair(
        pair=pair,
        htf_data=data['htf'],
        mtf_data=data['mtf'],
        ltf_data=data['ltf'],
    )

    print(f"   Signal: {alignment.recommendation.value}")
    print(f"   Alignment: {alignment.alignment_score}/3")
    print(f"   Quality: {alignment.quality.value}")
    
    # Print UPGRADED SYSTEM features (NEW)
    print("\n🆙 Upgraded System Analysis:")
    
    # Layer 1: Context
    if alignment.mtf_setup.mtf_context:
        ctx = alignment.mtf_setup.mtf_context
        print(f"   Layer 1 - Context: {ctx.value}")
        # Note: ADX and distance are in the context result, but we'd need to store that separately
        # For now, just show context
    else:
        print(f"   Layer 1 - Context: N/A")
    
    # Layer 3: Quality Score
    if alignment.mtf_setup.pullback_quality_score:
        qs = alignment.mtf_setup.pullback_quality_score
        print(f"   Layer 3 - Quality Score: {qs.total_score:.2f}")
        if qs.reasons:
            print(f"            Reasons: {qs.reasons[0]}")
    else:
        print(f"   Layer 3 - Quality Score: N/A (no pullback)")
    
    # Layer 4: Weighted Alignment & Position Sizing
    print(f"   Layer 4 - Weighted Score: {alignment.weighted_score:.2f}")
    print(f"            Position Size: {alignment.position_size_pct:.0f}% of base risk")
    
    # Show warning if insufficient data
    if alignment.alignment_score == 0 and alignment.htf_bias.confidence == 0:
        print("\n⚠️  Warning: Insufficient historical data for full analysis")
        print(f"   HTF needs 200+ candles for 50/200 SMA calculation")
        print(f"   Currently have: {len(data['htf'])} candles")
        print("\n💡 Tip: The MTF system needs more historical data.")
        print("   For production use, ensure your data provider supports")
        print("   fetching 200+ candles for the HTF timeframe.")

    # Check data quality
    print("\n🔍 Checking data quality...")
    quality_report = check_data_quality(
        htf_df=data['htf'],
        mtf_df=data['mtf'],
        ltf_df=data['ltf'],
        config=config,
    )
    print(f"   Overall: {quality_report.overall_status.value}")
    if quality_report.overall_status != DataQualityStatus.PASS:
        print(f"   ⚠️ {quality_report.summary}")
    else:
        print(f"   ✅ {quality_report.summary}")

    # Generate report
    print("\n📝 Generating report...")
    report = generate_report(pair, style, alignment, data, config, quality_report)

    # Save report
    report_dir = project_root / 'docs' / 'reports'
    report_dir.mkdir(exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')

    filename = f"{pair.replace('/', '')}-mtf-analysis-{style.lower()}-{date_str}.md"
    filepath = report_dir / filename

    with open(filepath, 'w') as f:
        f.write(report)

    print(f"\n✅ Report saved to: {filepath}")
    print(f"\n📈 Summary:")
    print(f"   Pair: {pair}")
    print(f"   Signal: {alignment.recommendation.value}")
    print(f"   Alignment: {alignment.alignment_score}/3 ({alignment.quality.value})")
    if alignment.ltf_entry.entry_price:
        print(f"   Entry: ${alignment.ltf_entry.entry_price:,.2f}")
        print(f"   Stop: ${alignment.ltf_entry.stop_loss:,.2f}")
        print(f"   Target: ${alignment.target.target_price:,.2f}")
        print(f"   R:R: {alignment.rr_ratio:.2f}:1")
