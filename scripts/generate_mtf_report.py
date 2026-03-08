#!/usr/bin/env python3
"""
MTF Analysis Report Generator with Charts

Generates a detailed Multi-Timeframe Analysis report for a given trading pair.
Fetches real-time data, calculates all MTF metrics, and generates professional charts.

Features:
- Full MTF analysis (HTF bias, MTF setup, LTF entry)
- Professional charts with annotations
- Markdown report with embedded images
- Optional interactive HTML report

Usage:
    python scripts/generate_mtf_report.py BTC/USDT SWING
    python scripts/generate_mtf_report.py ETH/USDT INTRADAY

Output:
    docs/reports/{pair}-mtf-analysis-{style}-{date}.md
    docs/reports/charts/{pair}-*.png (4 chart files)
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
from src.services.mtf_chart_generator import MTFChartGenerator, ChartConfig
from src.services.mtf_chart_generator_plotly import generate_interactive_report
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


def generate_charts(
    pair: str,
    data: dict,
    alignment,
    charts_dir: Path,
    config: MTFTimeframeConfig,
) -> Dict[str, Path]:
    """
    Generate all charts for MTF analysis.
    
    Creates 4 professional charts:
    1. HTF bias analysis (price structure, SMAs, key levels)
    2. MTF setup detection (pullback zones, RSI)
    3. LTF entry signal (entry point, stop, target)
    4. Multi-timeframe alignment overview
    
    Args:
        pair: Trading pair symbol.
        data: Dictionary with htf, mtf, ltf DataFrames.
        alignment: MTFAlignment object with analysis results.
        charts_dir: Directory to save chart images.
        config: MTF timeframe configuration.
    
    Returns:
        Dictionary mapping chart type to file path.
    """
    print("\n📊 Generating charts...")
    
    chart_gen = MTFChartGenerator()
    chart_paths = {}
    
    # Create charts directory
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # HTF Chart
        htf_chart_path = charts_dir / f"{pair.replace('/', '')}-htf-analysis.png"
        chart_gen.generate_htf_chart(
            df=data['htf'],
            htf_bias=alignment.htf_bias,
            pair=pair,
            timeframe=config.htf_timeframe,
            save_path=str(htf_chart_path),
            show_sma50=True,
            show_sma200=len(data['htf']) >= 200,  # Only if enough data
        )
        chart_paths['htf'] = htf_chart_path
        print(f"  ✓ HTF chart: {htf_chart_path.name}")
        
        # MTF Chart
        mtf_chart_path = charts_dir / f"{pair.replace('/', '')}-mtf-setup.png"
        chart_gen.generate_mtf_chart(
            df=data['mtf'],
            mtf_setup=alignment.mtf_setup,
            pair=pair,
            timeframe=config.mtf_timeframe,
            save_path=str(mtf_chart_path),
        )
        chart_paths['mtf'] = mtf_chart_path
        print(f"  ✓ MTF chart: {mtf_chart_path.name}")
        
        # LTF Chart (if entry signal exists)
        if alignment.ltf_entry and alignment.ltf_entry.entry_price > 0:
            ltf_chart_path = charts_dir / f"{pair.replace('/', '')}-ltf-entry.png"
            target_price = alignment.target.target_price if alignment.target else None
            chart_gen.generate_ltf_chart(
                df=data['ltf'],
                ltf_entry=alignment.ltf_entry,
                pair=pair,
                timeframe=config.ltf_timeframe,
                save_path=str(ltf_chart_path),
                target_price=target_price,
            )
            chart_paths['ltf'] = ltf_chart_path
            print(f"  ✓ LTF chart: {ltf_chart_path.name}")
        else:
            print(f"  ⚠️ Skipping LTF chart (no entry signal)")
        
        # Alignment Chart
        alignment_chart_path = charts_dir / f"{pair.replace('/', '')}-alignment.png"
        chart_gen.generate_alignment_chart(
            alignment=alignment,
            pair=pair,
            save_path=str(alignment_chart_path),
        )
        chart_paths['alignment'] = alignment_chart_path
        print(f"  ✓ Alignment chart: {alignment_chart_path.name}")
        
    except Exception as e:
        print(f"\n⚠️ Chart generation error: {e}")
        print(f"   Continuing with report generation (charts will be unavailable)")
    
    return chart_paths


def generate_report(
    pair: str,
    trading_style: str,
    alignment,
    data: dict,
    chart_paths: Optional[Dict[str, Path]] = None,
    quality_report: Optional[DataQualityReport] = None,
) -> str:
    """
    Generate markdown report from analysis results.
    
    Args:
        pair: Trading pair.
        trading_style: Trading style name.
        alignment: MTFAlignment object.
        data: Dictionary with OHLCV DataFrames.
        chart_paths: Dictionary mapping chart type to file path (optional).
        quality_report: Data quality report (optional).
    
    Returns:
        Markdown report content with embedded chart images and data quality dashboard.
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

    # Add alignment chart if available
    if chart_paths and 'alignment' in chart_paths:
        # Use relative path from report to charts directory
        report += f"""
## 📊 Multi-Timeframe Alignment

![MTF Alignment](charts/{chart_paths['alignment'].name})

*Figure 1: Timeframe alignment overview. Green = Bullish, Red = Bearish, Gray = Neutral.*

---

## Timeframe Configuration ({trading_style.title()})

| Layer | Timeframe | Role | Indicators |
|-------|-----------|------|------------|
| **HTF** | {config.htf_timeframe} | Directional Bias | 50 SMA, 200 SMA, Price Structure |
| **MTF** | {config.mtf_timeframe} | Setup Identification | 20 SMA, 50 SMA, RSI(14) |
| **LTF** | {config.ltf_timeframe} | Entry Timing | 20 EMA, Candlestick Patterns, RSI(14) |

---
"""
    else:
        report += f"""
---

## Timeframe Configuration ({trading_style.title()})

| Layer | Timeframe | Role | Indicators |
|-------|-----------|------|------------|
| **HTF** | {config.htf_timeframe} | Directional Bias | 50 SMA, 200 SMA, Price Structure |
| **MTF** | {config.mtf_timeframe} | Setup Identification | 20 SMA, 50 SMA, RSI(14) |
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
| 50 SMA | ${htf_close:,.2f} | {htf_bias.price_vs_sma50.value} | {htf_bias.sma50_slope.value} |
| 200 SMA | — | {htf_bias.price_vs_sma200.value} | — |

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

"""

    # Add HTF chart if available
    if chart_paths and 'htf' in chart_paths:
        report += f"""
![HTF Analysis](charts/{chart_paths['htf'].name})

*Figure 2: HTF bias analysis showing price structure, SMAs, and key levels.*

---
"""

    report += f"""
## 2. Middle Timeframe ({config.mtf_timeframe}) — Setup Identification

### 2.1 Setup Details

**Setup Type:** {mtf_setup.setup_type.value}  
**Direction:** {mtf_setup.direction.value}  
**Confidence:** {mtf_setup.confidence:.2f}

"""

    if mtf_setup.pullback_details:
        pb = mtf_setup.pullback_details
        report += f"""**Pullback Details:**
- Approaching SMA: {pb.approaching_sma}
- Distance to SMA: {pb.distance_to_sma_pct:.2f}%
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

"""

    # Add MTF chart if available
    if chart_paths and 'mtf' in chart_paths:
        report += f"""
![MTF Setup](charts/{chart_paths['mtf'].name})

*Figure 3: MTF setup detection showing pullback zones and RSI.*

---
"""

    report += f"""
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
"""

    report += f"""
### 3.3 LTF Entry Result

```
LTF ({config.ltf_timeframe}) Entry: {ltf_entry.signal_type.value}
Entry Price: ${ltf_entry.entry_price:,.2f}
Stop Loss: ${ltf_entry.stop_loss:,.2f}
```

"""

    # Add LTF chart if available
    if chart_paths and 'ltf' in chart_paths:
        report += f"""
![LTF Entry](charts/{chart_paths['ltf'].name})

*Figure 4: LTF entry signal showing entry point, stop loss, and target.*

---
"""

    report += f"""
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
    
    # Show warning if insufficient data
    if alignment.alignment_score == 0 and alignment.htf_bias.confidence == 0:
        print("\n⚠️  Warning: Insufficient historical data for full analysis")
        print(f"   HTF needs 200+ candles for 50/200 SMA calculation")
        print(f"   Currently have: {len(data['htf'])} candles")
        print("\n💡 Tip: The MTF system needs more historical data.")
        print("   For production use, ensure your data provider supports")
        print("   fetching 200+ candles for the HTF timeframe.")

    # Generate charts
    report_dir = project_root / 'docs' / 'reports'
    report_dir.mkdir(exist_ok=True)
    charts_dir = report_dir / 'charts'
    
    chart_paths = generate_charts(
        pair=pair,
        data=data,
        alignment=alignment,
        charts_dir=charts_dir,
        config=config,
    )
    
    # Generate interactive HTML report (Plotly)
    print("\n🌐 Generating interactive HTML report...")
    try:
        html_path = generate_interactive_report(
            pair=pair,
            alignment=alignment,
            data=data,
            config=config,
            save_dir=str(report_dir),
        )
        print(f"  ✓ HTML report: {Path(html_path).name}")
    except Exception as e:
        print(f"  ⚠️ HTML generation error: {e}")
        html_path = None

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
    report = generate_report(pair, style, alignment, data, chart_paths, quality_report)

    # Save report
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
