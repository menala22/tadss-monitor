# MTF Report with Charts - Implementation Guide

**Date:** 2026-03-08
**Status:** Implementation Plan

---

## Executive Summary

Yes, you **can** show charts in Markdown files! Here are your options:

### Option 1: Markdown + Embedded Images (Recommended ⭐)
- Generate PNG charts with Matplotlib/Plotly
- Embed as base64 or save as files
- Reference in Markdown: `![Chart](charts/btc-htf-analysis.png)`
- **Pros:** Simple, works everywhere, GitHub renders automatically
- **Cons:** Static images, no interactivity

### Option 2: HTML Report with Interactive Charts
- Generate full HTML report with Plotly interactive charts
- Zoom, pan, hover tooltips
- **Pros:** Professional, interactive, beautiful
- **Cons:** Larger file size, requires browser

### Option 3: Streamlit Dashboard (You Already Have!)
- Create MTF report page in your existing Streamlit app
- **Pros:** Interactive, real-time, no extra work
- **Cons:** Requires running Streamlit server

---

## Recommendation: Hybrid Approach

**Best of Both Worlds:**
1. **Generate PNG charts** for Markdown reports (quick viewing)
2. **Generate HTML report** with interactive Plotly charts (deep analysis)
3. **Link to Streamlit dashboard** for live exploration

---

## Implementation: Option 1 (Markdown + PNG Charts)

### Step 1: Create Chart Generator Service

Create `src/services/mtf_chart_generator.py`:

```python
"""
MTF Chart Generator for Multi-Timeframe Analysis Reports.

Generates professional trading charts with annotations for:
- HTF bias analysis (price structure, SMAs, key levels)
- MTF setup detection (pullback, RSI, SMA zones)
- LTF entry signals (candlestick patterns, EMA reclaim)

Output: PNG images for Markdown reports, or interactive Plotly HTML.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

from src.models.mtf_models import HTFBias, MTFSetup, LTFEntry, MTFAlignment

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    width: int = 14
    height: int = 10
    dpi: int = 100
    style: str = 'seaborn-v0_8-darkgrid'
    save_format: str = 'png'
    
    # Colors
    bullish_color: str = '#2ecc71'  # Green
    bearish_color: str = '#e74c3c'  # Red
    neutral_color: str = '#95a5a6'  # Gray
    sma50_color: str = '#3498db'    # Blue
    sma200_color: str = '#e67e22'   # Orange
    entry_color: str = '#9b59b6'    # Purple


class MTFChartGenerator:
    """
    Generate professional MTF analysis charts.
    
    Creates annotated charts for HTF, MTF, and LTF analysis
    with automatic layout and professional styling.
    
    Example:
        >>> generator = MTFChartGenerator()
        >>> generator.generate_htf_chart(
        ...     df=htf_data,
        ...     htf_bias=htf_bias,
        ...     save_path='charts/btc-htf-analysis.png'
        ... )
    """
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize chart generator.
        
        Args:
            config: Chart configuration. Uses defaults if None.
        """
        self.config = config or ChartConfig()
        plt.style.use(self.config.style)
    
    def generate_htf_chart(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
        pair: str,
        timeframe: str,
        save_path: str,
        show_sma50: bool = True,
        show_sma200: bool = True,
    ) -> str:
        """
        Generate HTF bias analysis chart.
        
        Features:
        - Candlestick or line chart
        - SMA 50 and SMA 200 (if available)
        - Key support/resistance levels
        - Swing points
        - Bias annotation box
        
        Args:
            df: OHLCV DataFrame for HTF.
            htf_bias: HTF bias analysis results.
            pair: Trading pair symbol.
            timeframe: HTF timeframe (e.g., '1w', '1d').
            save_path: Path to save chart image.
            show_sma50: Show 50-period SMA.
            show_sma200: Show 200-period SMA.
        
        Returns:
            Path to saved chart.
        """
        logger.info(f"Generating HTF chart for {pair} ({timeframe})")
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1, 
            figsize=(self.config.width, self.config.height),
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )
        
        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Plot price
        if 'close' in df.columns:
            ax1.plot(df.index, df['close'], 
                    linewidth=2, 
                    color=self.config.bullish_color 
                    if htf_bias.direction.value == 'BULLISH' 
                    else self.config.bearish_color,
                    label='Close Price')
        
        # Plot SMAs
        if show_sma50 and len(df) >= 50:
            sma50 = df['close'].rolling(50).mean()
            ax1.plot(df.index, sma50, 
                    linewidth=1.5, 
                    color=self.config.sma50_color,
                    label=f'SMA 50 ({sma50.iloc[-1]:,.2f})')
        
        if show_sma200 and len(df) >= 200:
            sma200 = df['close'].rolling(200).mean()
            ax1.plot(df.index, sma200, 
                    linewidth=1.5, 
                    color=self.config.sma200_color,
                    label=f'SMA 200 ({sma200.iloc[-1]:,.2f})')
        
        # Plot key levels
        for level in htf_bias.key_levels[:3]:  # Top 3 levels
            ax1.axhline(
                y=level.price,
                color=self.config.neutral_color,
                linestyle='--',
                linewidth=1,
                alpha=0.7,
                label=f'{level.level_type.value}: {level.price:,.2f}'
            )
        
        # Plot swing points
        for swing in htf_bias.swing_sequence[-6:]:  # Last 6 swings
            marker = 'v' if swing.swing_type == 'HIGH' else '^'
            ax1.scatter(
                swing.timestamp, swing.price,
                marker=marker,
                s=200,
                color='red' if swing.swing_type == 'HIGH' else 'green',
                zorder=5,
                label=f'{swing.swing_type}: {swing.price:,.2f}'
            )
        
        # Add bias annotation box
        self._add_bias_annotation(
            ax=ax1,
            bias=htf_bias,
            pair=pair,
            timeframe=timeframe,
            current_price=df['close'].iloc[-1] if 'close' in df.columns else 0
        )
        
        # Configure axes
        ax1.set_title(f'{pair} - HTF Analysis ({timeframe})', 
                     fontsize=16, fontweight='bold')
        ax1.set_ylabel('Price', fontsize=12)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Plot volume (if available)
        if 'volume' in df.columns:
            ax2.bar(
                df.index, 
                df['volume'],
                color=[self.config.bullish_color if c >= o else self.config.bearish_color 
                      for c, o in zip(df['close'], df['open'])],
                alpha=0.5,
                label='Volume'
            )
            ax2.set_ylabel('Volume', fontsize=12)
            ax2.legend(loc='upper left')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(
            save_path,
            dpi=self.config.dpi,
            bbox_inches='tight',
            facecolor='white'
        )
        plt.close(fig)
        
        logger.info(f"HTF chart saved to {save_path}")
        return save_path
    
    def generate_mtf_chart(
        self,
        df: pd.DataFrame,
        mtf_setup: MTFSetup,
        pair: str,
        timeframe: str,
        save_path: str,
    ) -> str:
        """
        Generate MTF setup analysis chart.
        
        Features:
        - Price with SMA 20 and SMA 50
        - RSI panel
        - Pullback zone highlighting
        - Setup annotation
        
        Args:
            df: OHLCV DataFrame for MTF.
            mtf_setup: MTF setup analysis results.
            pair: Trading pair symbol.
            timeframe: MTF timeframe.
            save_path: Path to save chart image.
        
        Returns:
            Path to saved chart.
        """
        logger.info(f"Generating MTF chart for {pair} ({timeframe})")
        
        fig, (ax1, ax2, ax3) = plt.subplots(
            3, 1,
            figsize=(self.config.width, self.config.height),
            gridspec_kw={'height_ratios': [3, 1, 1]},
            sharex=True
        )
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Panel 1: Price with SMAs
        if 'close' in df.columns:
            ax1.plot(df.index, df['close'], 
                    linewidth=2, 
                    color=self.config.bullish_color 
                    if mtf_setup.direction.value == 'BULLISH' 
                    else self.config.bearish_color,
                    label='Close')
        
        # Plot SMAs
        sma20 = df['close'].rolling(20).mean()
        sma50 = df['close'].rolling(50).mean()
        
        ax1.plot(df.index, sma20, 
                linewidth=1.5, 
                color='#3498db',
                label=f'SMA 20 ({sma20.iloc[-1]:,.2f})')
        
        ax1.plot(df.index, sma50, 
                linewidth=1.5, 
                color='#e67e22',
                label=f'SMA 50 ({sma50.iloc[-1]:,.2f})')
        
        # Highlight pullback zone
        if mtf_setup.pullback_details:
            pb = mtf_setup.pullback_details
            current_price = df['close'].iloc[-1]
            sma_value = sma20.iloc[-1] if pb.approaching_sma == 20 else sma50.iloc[-1]
            
            # Draw zone around SMA
            ax1.axhspan(
                sma_value * 0.99, sma_value * 1.01,
                alpha=0.2,
                color='yellow',
                label=f'Pullback Zone (SMA{pb.approaching_sma})'
            )
        
        ax1.set_title(f'{pair} - MTF Setup ({timeframe})', 
                     fontsize=16, fontweight='bold')
        ax1.set_ylabel('Price', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Panel 2: RSI
        if 'close' in df.columns:
            rsi = self._calculate_rsi(df['close'], 14)
            ax2.plot(df.index, rsi, linewidth=1.5, color='purple', label='RSI(14)')
            ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=70, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=30, color='green', linestyle='--', linewidth=1, alpha=0.5)
            ax2.fill_between(df.index, 30, 70, alpha=0.1, color='gray')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)
        
        # Panel 3: Volume
        if 'volume' in df.columns:
            ax3.bar(
                df.index, 
                df['volume'],
                color=[self.config.bullish_color if c >= o else self.config.bearish_color 
                      for c, o in zip(df['close'], df['open'])],
                alpha=0.5
            )
            ax3.set_ylabel('Volume', fontsize=12)
            ax3.grid(True, alpha=0.3)
        
        # Add setup annotation
        self._add_setup_annotation(
            ax=ax1,
            setup=mtf_setup,
            timeframe=timeframe
        )
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        logger.info(f"MTF chart saved to {save_path}")
        return save_path
    
    def generate_ltf_chart(
        self,
        df: pd.DataFrame,
        ltf_entry: LTFEntry,
        pair: str,
        timeframe: str,
        save_path: str,
    ) -> str:
        """
        Generate LTF entry signal chart.
        
        Features:
        - Candlestick or line chart
        - EMA 20
        - Entry point annotation
        - Stop loss and target levels
        - Signal type annotation
        
        Args:
            df: OHLCV DataFrame for LTF.
            ltf_entry: LTF entry signal results.
            pair: Trading pair symbol.
            timeframe: LTF timeframe.
            save_path: Path to save chart image.
        
        Returns:
            Path to saved chart.
        """
        logger.info(f"Generating LTF chart for {pair} ({timeframe})")
        
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(self.config.width, self.config.height),
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Plot price
        if 'close' in df.columns:
            ax1.plot(df.index, df['close'], 
                    linewidth=2, 
                    color=self.config.bullish_color 
                    if ltf_entry.direction.value == 'BULLISH' 
                    else self.config.bearish_color,
                    label='Close')
        
        # Plot EMA 20
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ax1.plot(df.index, ema20, 
                linewidth=1.5, 
                color='#9b59b6',
                label=f'EMA 20 ({ema20.iloc[-1]:,.2f})')
        
        # Mark entry point
        if ltf_entry.entry_price > 0:
            ax1.scatter(
                df.index[-1], ltf_entry.entry_price,
                marker='o',
                s=300,
                color='green' if ltf_entry.direction.value == 'BULLISH' else 'red',
                zorder=10,
                label=f'Entry: {ltf_entry.entry_price:,.2f}'
            )
        
        # Mark stop loss
        if ltf_entry.stop_loss > 0:
            ax1.axhline(
                y=ltf_entry.stop_loss,
                color='red',
                linestyle='--',
                linewidth=2,
                label=f'Stop: {ltf_entry.stop_loss:,.2f}'
            )
        
        # Mark target (if available from alignment)
        # (Would need to pass target parameter)
        
        ax1.set_title(f'{pair} - LTF Entry ({timeframe}) - {ltf_entry.signal_type.value}', 
                     fontsize=16, fontweight='bold')
        ax1.set_ylabel('Price', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Panel 2: RSI
        if 'close' in df.columns:
            rsi = self._calculate_rsi(df['close'], 14)
            ax2.plot(df.index, rsi, linewidth=1.5, color='purple', label='RSI(14)')
            ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=40, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Oversold')
            ax2.axhline(y=60, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Overbought')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        logger.info(f"LTF chart saved to {save_path}")
        return save_path
    
    def generate_alignment_chart(
        self,
        alignment: MTFAlignment,
        pair: str,
        save_path: str,
    ) -> str:
        """
        Generate multi-timeframe alignment visualization.
        
        Features:
        - 3-panel layout (HTF, MTF, LTF)
        - Color-coded by direction
        - Alignment score display
        - Recommendation summary
        
        Args:
            alignment: Full MTF alignment results.
            pair: Trading pair symbol.
            save_path: Path to save chart image.
        
        Returns:
            Path to saved chart.
        """
        logger.info(f"Generating alignment chart for {pair}")
        
        fig, axes = plt.subplots(
            3, 1,
            figsize=(self.config.width, self.config.height * 0.8),
            sharex=False
        )
        
        if len(axes.shape) == 1:
            axes = axes.reshape(3, 1)
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # HTF Panel
        self._plot_tf_panel(
            ax=axes[0],
            title=f"HTF ({alignment.htf_bias.price_structure.value})",
            direction=alignment.htf_bias.direction,
            confidence=alignment.htf_bias.confidence,
            details=[
                f"Structure: {alignment.htf_bias.price_structure.value}",
                f"SMA50: {alignment.htf_bias.sma50_slope.value}",
                f"Price vs SMA50: {alignment.htf_bias.price_vs_sma50.value}",
            ],
            color_idx=0
        )
        
        # MTF Panel
        self._plot_tf_panel(
            ax=axes[1],
            title=f"MTF ({alignment.mtf_setup.setup_type.value})",
            direction=alignment.mtf_setup.direction,
            confidence=alignment.mtf_setup.confidence,
            details=[
                f"Setup: {alignment.mtf_setup.setup_type.value}",
                f"RSI: {alignment.mtf_setup.pullback_details.rsi_level if alignment.mtf_setup.pullback_details else 'N/A'}",
            ],
            color_idx=1
        )
        
        # LTF Panel
        self._plot_tf_panel(
            ax=axes[2],
            title=f"LTF ({alignment.ltf_entry.signal_type.value if alignment.ltf_entry else 'No Signal'})",
            direction=alignment.ltf_entry.direction if alignment.ltf_entry else None,
            confidence=0.0,
            details=[
                f"Signal: {alignment.ltf_entry.signal_type.value if alignment.ltf_entry else 'None'}",
                f"Entry: ${alignment.ltf_entry.entry_price:,.2f}" if alignment.ltf_entry and alignment.ltf_entry.entry_price else "No Entry",
            ],
            color_idx=2
        )
        
        # Add overall alignment score
        fig.suptitle(
            f'{pair} - MTF Alignment: {alignment.alignment_score}/3 | '
            f'Quality: {alignment.quality.value} | '
            f'Signal: {alignment.recommendation.value}',
            fontsize=18,
            fontweight='bold',
            y=1.02
        )
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        logger.info(f"Alignment chart saved to {save_path}")
        return save_path
    
    def _plot_tf_panel(
        self,
        ax,
        title: str,
        direction,
        confidence: float,
        details: List[str],
        color_idx: int
    ):
        """Plot single timeframe panel for alignment chart."""
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']  # Green, Red, Gray
        
        # Determine color based on direction
        if direction and direction.value in ['BULLISH', 'LONG']:
            color = colors[0]
        elif direction and direction.value in ['BEARISH', 'SHORT']:
            color = colors[1]
        else:
            color = colors[2]
        
        # Create horizontal bar
        ax.barh([0], [confidence * 100], color=color, alpha=0.7, height=0.5)
        ax.set_xlim(0, 100)
        ax.set_yticks([])
        ax.set_xlabel('Confidence', fontsize=10)
        
        # Add title
        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        # Add details
        for i, detail in enumerate(details):
            ax.text(
                0.02, -0.3 - (i * 0.3),
                detail,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                family='monospace'
            )
    
    def _add_bias_annotation(self, ax, bias: HTFBias, pair: str, timeframe: str, current_price: float):
        """Add bias annotation box to chart."""
        textstr = (
            f'HTF Bias: {bias.direction.value}\n'
            f'Confidence: {bias.confidence:.2f}\n'
            f'Structure: {bias.price_structure.value}\n'
            f'Price: ${current_price:,.2f}'
        )
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(
            0.02, 0.98, textstr,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment='top',
            bbox=props,
            family='monospace'
        )
    
    def _add_setup_annotation(self, ax, setup: MTFSetup, timeframe: str):
        """Add setup annotation box to chart."""
        textstr = (
            f'Setup: {setup.setup_type.value}\n'
            f'Direction: {setup.direction.value}\n'
            f'Confidence: {setup.confidence:.2f}'
        )
        
        if setup.pullback_details:
            pb = setup.pullback_details
            textstr += f'\nPullback to SMA{pb.approaching_sma}\nRSI: {pb.rsi_level:.1f}'
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(
            0.02, 0.98, textstr,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment='top',
            bbox=props,
            family='monospace'
        )
    
    def _calculate_rsi(self, series: pd.Series, length: int) -> pd.Series:
        """Calculate RSI."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(100)
```

---

### Step 2: Update Report Generator

Modify `scripts/generate_mtf_report.py` to generate charts:

```python
#!/usr/bin/env python3
"""
MTF Analysis Report Generator with Charts

Generates a detailed Multi-Timeframe Analysis report with:
- PNG charts for HTF, MTF, LTF analysis
- Interactive Plotly HTML report (optional)
- Markdown report with embedded images

Usage:
    python scripts/generate_mtf_report.py BTC/USDT SWING BALANCED
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetcher import DataFetcher
from src.services.mtf_alignment_scorer import MTFAnalyzer
from src.services.mtf_chart_generator import MTFChartGenerator, ChartConfig
from src.models.mtf_models import (
    MTFTimeframeConfig,
    TradingStyle,
    IndicatorProfile,
)

def generate_charts(
    pair: str,
    data: dict,
    alignment,
    output_dir: Path,
) -> dict:
    """
    Generate all charts for MTF analysis.
    
    Args:
        pair: Trading pair.
        data: Dictionary with htf, mtf, ltf DataFrames.
        alignment: MTFAlignment object.
        output_dir: Directory to save charts.
    
    Returns:
        Dictionary with chart file paths.
    """
    print("\n📊 Generating charts...")
    
    chart_gen = MTFChartGenerator()
    chart_paths = {}
    
    # HTF Chart
    htf_chart_path = output_dir / f"{pair.replace('/', '')}-htf-analysis.png"
    chart_gen.generate_htf_chart(
        df=data['htf'],
        htf_bias=alignment.htf_bias,
        pair=pair,
        timeframe=config.htf_timeframe,
        save_path=str(htf_chart_path),
    )
    chart_paths['htf'] = htf_chart_path
    print(f"  ✓ HTF chart: {htf_chart_path}")
    
    # MTF Chart
    mtf_chart_path = output_dir / f"{pair.replace('/', '')}-mtf-setup.png"
    chart_gen.generate_mtf_chart(
        df=data['mtf'],
        mtf_setup=alignment.mtf_setup,
        pair=pair,
        timeframe=config.mtf_timeframe,
        save_path=str(mtf_chart_path),
    )
    chart_paths['mtf'] = mtf_chart_path
    print(f"  ✓ MTF chart: {mtf_chart_path}")
    
    # LTF Chart (if entry signal exists)
    if alignment.ltf_entry and alignment.ltf_entry.entry_price > 0:
        ltf_chart_path = output_dir / f"{pair.replace('/', '')}-ltf-entry.png"
        chart_gen.generate_ltf_chart(
            df=data['ltf'],
            ltf_entry=alignment.ltf_entry,
            pair=pair,
            timeframe=config.ltf_timeframe,
            save_path=str(ltf_chart_path),
        )
        chart_paths['ltf'] = ltf_chart_path
        print(f"  ✓ LTF chart: {ltf_chart_path}")
    
    # Alignment Chart
    alignment_chart_path = output_dir / f"{pair.replace('/', '')}-alignment.png"
    chart_gen.generate_alignment_chart(
        alignment=alignment,
        pair=pair,
        save_path=str(alignment_chart_path),
    )
    chart_paths['alignment'] = alignment_chart_path
    print(f"  ✓ Alignment chart: {alignment_chart_path}")
    
    return chart_paths
```

---

### Step 3: Embed Charts in Markdown Report

Update the report template to include charts:

```python
def generate_report(
    pair: str,
    trading_style: str,
    alignment,
    data: dict,
    chart_paths: dict,  # NEW
) -> str:
    """Generate markdown report with embedded charts."""
    
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Build report with charts
    report = f"""# MTF Analysis Report: {pair} ({trading_style.title()} Trading)

**Generated:** {now}
**Trading Style:** {trading_style.upper()}
**Analysis Type:** Multi-Timeframe Framework (Real-Time Data)

---

## ⚠️ Disclaimer

This report is for **educational and informational purposes only**.
It does not constitute financial advice.

---

## 🎯 Executive Summary

| Metric | Value |
|--------|-------|
| **Pair** | {pair} |
| **Overall Signal** | {alignment.recommendation.value} |
| **Alignment Score** | {alignment.alignment_score}/3 ({alignment.quality.value}) |
"""

    # Add alignment chart
    if 'alignment' in chart_paths:
        report += f"""
## 📊 Multi-Timeframe Alignment

![MTF Alignment]({chart_paths['alignment'].name})

*Figure 1: Timeframe alignment visualization. Green = Bullish, Red = Bearish.*

---

"""

    # Add HTF section with chart
    report += f"""
## 1. Higher Timeframe ({config.htf_timeframe}) — Directional Bias

![HTF Analysis]({chart_paths['htf'].name})

*Figure 2: HTF bias analysis showing price structure, SMAs, and key levels.*

### 1.1 Price Structure

**Structure Type:** {alignment.htf_bias.price_structure.value}

"""

    # Add swing points table
    if alignment.htf_bias.swing_sequence:
        report += "**Recent Swing Points:**\n"
        report += "| Type | Price | Strength |\n"
        report += "|------|-------|----------|\n"
        for swing in alignment.htf_bias.swing_sequence[-6:]:
            report += f"| {swing.swing_type} | ${swing.price:,.2f} | {swing.strength:.2f} |\n"

    # Add MTF section with chart
    report += f"""
## 2. Middle Timeframe ({config.mtf_timeframe}) — Setup Identification

![MTF Setup]({chart_paths['mtf'].name})

*Figure 3: MTF setup detection showing pullback zones and RSI.*

### 2.1 Setup Details

**Setup Type:** {alignment.mtf_setup.setup_type.value}
**Direction:** {alignment.mtf_setup.direction.value}
**Confidence:** {alignment.mtf_setup.confidence:.2f}

"""

    # Add LTF section with chart (if available)
    if 'ltf' in chart_paths:
        report += f"""
## 3. Lower Timeframe ({config.ltf_timeframe}) — Entry Signal

![LTF Entry]({chart_paths['ltf'].name})

*Figure 4: LTF entry signal showing entry point, stop loss, and target.*

### 3.1 Entry Details

**Signal Type:** {alignment.ltf_entry.signal_type.value}
**Entry Price:** ${alignment.ltf_entry.entry_price:,.2f}
**Stop Loss:** ${alignment.ltf_entry.stop_loss:,.2f}

"""

    # Continue with rest of report...
    
    return report
```

---

## Output Example

Your Markdown report will now include:

```markdown
# MTF Analysis Report: BTC/USDT (Swing Trading)

**Generated:** 2026-03-08 12:00:00 UTC

---

## 🎯 Executive Summary

| Metric | Value |
|--------|-------|
| **Pair** | BTC/USDT |
| **Signal** | BUY |
| **Alignment** | 3/3 (HIGHEST) |

---

## 📊 Multi-Timeframe Alignment

![MTF Alignment](charts/btcusdt-alignment.png)

*Figure 1: Timeframe alignment visualization.*

---

## 1. Higher Timeframe (w1) — Directional Bias

![HTF Analysis](charts/btcusdt-htf-analysis.png)

*Figure 2: HTF bias analysis showing price structure, SMAs, and key levels.*

### 1.1 Price Structure
...
```

---

## Option 2: Interactive HTML Report with Plotly

If you want **interactive charts** (zoom, pan, hover), use Plotly instead:

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_interactive_htf_chart(df, htf_bias, pair, timeframe, save_path):
    """Generate interactive Plotly chart."""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{pair} - HTF Analysis ({timeframe})', 'Volume')
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC'
        ),
        row=1, col=1
    )
    
    # Add SMAs
    sma50 = df['close'].rolling(50).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index, y=sma50,
            mode='lines', name='SMA 50',
            line=dict(color='blue', width=1.5)
        ),
        row=1, col=1
    )
    
    # Add annotations
    fig.add_annotation(
        x=df.index[-1], y=df['close'].iloc[-1],
        text=f"Bias: {htf_bias.direction.value}",
        showarrow=True,
        arrowhead=2,
        bgcolor="white",
        bordercolor="black"
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        title=f"{pair} - MTF HTF Analysis",
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # Save as interactive HTML
    fig.write_html(save_path)
    
    return save_path
```

**Output:** Interactive HTML file that opens in browser with zoom/pan/hover.

---

## File Structure

After implementation, your reports folder will look like:

```
docs/reports/
├── BTCUSDT-mtf-analysis-swing-20260308.md
├── charts/
│   ├── BTCUSDT-htf-analysis.png
│   ├── BTCUSDT-mtf-setup.png
│   ├── BTCUSDT-ltf-entry.png
│   └── BTCUSDT-alignment.png
└── html/
    └── BTCUSDT-mtf-analysis-swing-20260308.html  (optional interactive)
```

---

## Usage

```bash
# Generate report with charts
python scripts/generate_mtf_report.py BTC/USDT SWING BALANCED

# Output:
# - Markdown report with embedded PNG charts
# - Optional: Interactive HTML report
```

---

## Next Steps

1. ✅ **Create `mtf_chart_generator.py`** (chart generation service)
2. ✅ **Update `generate_mtf_report.py`** (integrate chart generation)
3. ✅ **Update report template** (embed charts in Markdown)
4. ✅ **Test with real data** (generate sample report)
5. 🔄 **Optional:** Add Plotly interactive HTML version

---

**Ready to implement?** I can create the full `mtf_chart_generator.py` file for you now!
