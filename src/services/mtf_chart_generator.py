"""
MTF Chart Generator for Multi-Timeframe Analysis Reports.

Generates professional trading charts with annotations for:
- HTF bias analysis (price structure, SMAs, key levels)
- MTF setup detection (pullback, RSI, SMA zones)
- LTF entry signals (candlestick patterns, EMA reclaim)
- Multi-timeframe alignment visualization

Output: PNG images for Markdown reports or interactive Plotly HTML.

Example:
    >>> from src.services.mtf_chart_generator import MTFChartGenerator
    >>> generator = MTFChartGenerator()
    >>> generator.generate_htf_chart(
    ...     df=htf_data,
    ...     htf_bias=htf_bias,
    ...     pair='BTC/USDT',
    ...     timeframe='1w',
    ...     save_path='charts/btc-htf-analysis.png'
    ... )
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

from src.models.mtf_models import (
    HTFBias,
    LTFEntry,
    MTFAlignment,
    MTFDirection,
    MTFSetup,
    PriceStructure,
    SetupType,
    EntrySignalType,
)

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """
    Configuration for chart generation.
    
    Attributes:
        width: Figure width in inches (default 14).
        height: Figure height in inches (default 10).
        dpi: Dots per inch for saved images (default 100).
        style: Matplotlib style (default 'seaborn-v0_8-darkgrid').
        save_format: Image format (default 'png').
        bullish_color: Color for bullish elements (default green #2ecc71).
        bearish_color: Color for bearish elements (default red #e74c3c).
        neutral_color: Color for neutral elements (default gray #95a5a6).
        sma50_color: Color for 50-period MA (default blue #3498db).
        sma200_color: Color for 200-period MA (default orange #e67e22).
        entry_color: Color for entry markers (default purple #9b59b6).
    """
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
    
    Attributes:
        config: Chart configuration object.
    
    Example:
        >>> generator = MTFChartGenerator()
        >>> chart_path = generator.generate_htf_chart(
        ...     df=htf_df,
        ...     htf_bias=htf_bias,
        ...     pair='BTC/USDT',
        ...     timeframe='1w',
        ...     save_path='charts/btc-htf.png'
        ... )
    """
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize chart generator.
        
        Args:
            config: Chart configuration. Uses defaults if None.
        """
        self.config = config or ChartConfig()
        
        # Try to use seaborn style, fallback to default
        try:
            plt.style.use(self.config.style)
        except (OSError, IOError):
            plt.style.use('default')
            logger.debug("Using default matplotlib style")
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to lowercase.
        
        Args:
            df: Input DataFrame.
        
        Returns:
            DataFrame with lowercase column names.
        """
        df_copy = df.copy()
        df_copy.columns = df_copy.columns.str.lower()
        return df_copy
    
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
        - Price line chart (or candlestick if preferred)
        - SMA 50 and SMA 200 (if available)
        - Key support/resistance levels
        - Swing points with markers
        - Bias annotation box with metrics
        
        Args:
            df: OHLCV DataFrame for HTF timeframe.
            htf_bias: HTF bias analysis results from HTFBiasDetector.
            pair: Trading pair symbol (e.g., 'BTC/USDT').
            timeframe: HTF timeframe (e.g., '1w', '1d').
            save_path: File path to save chart image.
            show_sma50: Show 50-period SMA if available.
            show_sma200: Show 200-period SMA if available.
        
        Returns:
            Path to saved chart image.
        
        Example:
            >>> chart_path = generator.generate_htf_chart(
            ...     df=weekly_df,
            ...     htf_bias=htf_result,
            ...     pair='BTC/USDT',
            ...     timeframe='1w',
            ...     save_path='charts/btc-weekly-htf.png'
            ... )
        """
        logger.info(f"Generating HTF chart for {pair} ({timeframe})")

        # Standardize column names (handle both 'close' and 'Close')
        df_std = self._standardize_columns(df)

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(self.config.width, self.config.height),
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )

        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine price color based on bias
        price_color = (
            self.config.bullish_color
            if htf_bias.direction == MTFDirection.BULLISH
            else self.config.bearish_color
        )

        # Plot price
        if 'close' in df_std.columns:
            ax1.plot(
                df_std.index, df_std['close'],
                linewidth=2,
                color=price_color,
                label='Close Price',
                zorder=5
            )

        # Plot SMAs
        sma50 = None
        sma200 = None

        if show_sma50 and len(df_std) >= 50:
            sma50 = df_std['close'].rolling(50).mean()
            ax1.plot(
                df_std.index, sma50, 
                linewidth=1.5, 
                color=self.config.sma50_color,
                label=f'SMA 50 ({sma50.iloc[-1]:,.2f})',
                zorder=3
            )
        
        if show_sma200 and len(df_std) >= 200:
            sma200 = df_std['close'].rolling(200).mean()
            ax1.plot(
                df_std.index, sma200, 
                linewidth=1.5, 
                color=self.config.sma200_color,
                label=f'SMA 200 ({sma200.iloc[-1]:,.2f})',
                zorder=3
            )
        
        # Plot key levels (top 3)
        for i, level in enumerate(htf_bias.key_levels[:3]):
            level_color = (
                self.config.bullish_color 
                if level.level_type.value == 'SUPPORT' 
                else self.config.bearish_color
            )
            ax1.axhline(
                y=level.price,
                color=level_color,
                linestyle='--',
                linewidth=1.5,
                alpha=0.7,
                label=f'{level.level_type.value}: {level.price:,.2f}',
                zorder=2
            )
        
        # Plot swing points (last 6)
        for swing in htf_bias.swing_sequence[-6:]:
            marker = 'v' if swing.swing_type == 'HIGH' else '^'
            color = 'red' if swing.swing_type == 'HIGH' else 'green'
            
            # Parse timestamp
            try:
                timestamp = pd.to_datetime(swing.timestamp)
            except:
                timestamp = df_std.index[-1]

            ax1.scatter(
                timestamp, swing.price,
                marker=marker,
                s=250,
                color=color,
                edgecolors='black',
                linewidths=1.5,
                zorder=10,
                label=f'{swing.swing_type}: {swing.price:,.2f}'
            )
        
        # Add bias annotation box
        self._add_bias_annotation(
            ax=ax1,
            bias=htf_bias,
            pair=pair,
            timeframe=timeframe,
            current_price=df_std['close'].iloc[-1] if 'close' in df_std.columns else 0
        )
        
        # Configure axes
        ax1.set_title(
            f'{pair} — HTF Analysis ({timeframe})', 
            fontsize=16, 
            fontweight='bold',
            pad=15
        )
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # Plot volume (if available)
        if 'volume' in df_std.columns and 'open' in df_std.columns:
            colors = [
                self.config.bullish_color if c >= o else self.config.bearish_color
                for c, o in zip(df_std['close'], df_std['open'])
            ]
            ax2.bar(
                df_std.index,
                df_std['volume'],
                color=colors,
                alpha=0.6,
                label='Volume',
                width=1
            )
            ax2.set_ylabel('Volume', fontsize=12)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(
            save_path,
            dpi=self.config.dpi,
            bbox_inches='tight',
            facecolor='white',
            edgecolor='none'
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
        - RSI panel (14-period)
        - Pullback zone highlighting (if applicable)
        - Setup annotation with confidence

        Args:
            df: OHLCV DataFrame for MTF timeframe.
            mtf_setup: MTF setup analysis results from MTFSetupDetector.
            pair: Trading pair symbol.
            timeframe: MTF timeframe.
            save_path: File path to save chart image.

        Returns:
            Path to saved chart image.
        """
        logger.info(f"Generating MTF chart for {pair} ({timeframe})")

        # Standardize column names
        df_std = self._standardize_columns(df)

        fig, (ax1, ax2, ax3) = plt.subplots(
            3, 1,
            figsize=(self.config.width, self.config.height),
            gridspec_kw={'height_ratios': [3, 1, 1]},
            sharex=True
        )

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine price color
        price_color = (
            self.config.bullish_color
            if mtf_setup.direction == MTFDirection.BULLISH
            else self.config.bearish_color
        )

        # Panel 1: Price with SMAs
        if 'close' in df_std.columns:
            ax1.plot(
                df_std.index, df_std['close'],
                linewidth=2,
                color=price_color,
                label='Close',
                zorder=5
            )

        # Plot SMAs
        sma20 = df_std['close'].rolling(20).mean()
        sma50 = df_std['close'].rolling(50).mean()

        ax1.plot(
            df_std.index, sma20,
            linewidth=1.5,
            color='#3498db',
            label=f'SMA 20 ({sma20.iloc[-1]:,.2f})',
            zorder=3
        )

        ax1.plot(
            df_std.index, sma50,
            linewidth=1.5,
            color='#e67e22',
            label=f'SMA 50 ({sma50.iloc[-1]:,.2f})',
            zorder=3
        )

        # Highlight pullback zone
        if mtf_setup.pullback_details and mtf_setup.pullback_details.approaching_sma:
            pb = mtf_setup.pullback_details
            current_price = df_std['close'].iloc[-1]
            sma_value = sma20.iloc[-1] if pb.approaching_sma == 20 else sma50.iloc[-1]

            # Draw zone around SMA (±1%)
            ax1.axhspan(
                sma_value * 0.99, sma_value * 1.01,
                alpha=0.3,
                color='yellow',
                label=f'Pullback Zone (SMA{pb.approaching_sma})',
                zorder=1
            )

        ax1.set_title(
            f'{pair} — MTF Setup ({timeframe})',
            fontsize=16,
            fontweight='bold',
            pad=15
        )
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')

        # Panel 2: RSI
        if 'close' in df_std.columns:
            rsi = self._calculate_rsi(df_std['close'], 14)
            ax2.plot(df_std.index, rsi, linewidth=1.5, color='purple', label='RSI(14)', zorder=5)
            ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=70, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=30, color='green', linestyle='--', linewidth=1, alpha=0.5)
            ax2.fill_between(df_std.index, 30, 70, alpha=0.1, color='gray')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.3, linestyle='--')

        # Panel 3: Volume
        if 'volume' in df_std.columns and 'open' in df_std.columns:
            colors = [
                self.config.bullish_color if c >= o else self.config.bearish_color
                for c, o in zip(df_std['close'], df_std['open'])
            ]
            ax3.bar(
                df_std.index,
                df_std['volume'],
                color=colors,
                alpha=0.6,
                width=1
            )
            ax3.set_ylabel('Volume', fontsize=12)
            ax3.grid(True, alpha=0.3, linestyle='--')
        
        # Add setup annotation
        self._add_setup_annotation(
            ax=ax1,
            setup=mtf_setup,
            timeframe=timeframe
        )
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(
            save_path, 
            dpi=self.config.dpi, 
            bbox_inches='tight', 
            facecolor='white',
            edgecolor='none'
        )
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
        target_price: Optional[float] = None,
    ) -> str:
        """
        Generate LTF entry signal chart.

        Features:
        - Price with EMA 20
        - Entry point marker
        - Stop loss level
        - Target level (if provided)
        - Signal type annotation

        Args:
            df: OHLCV DataFrame for LTF timeframe.
            ltf_entry: LTF entry signal results from LTFEntryFinder.
            pair: Trading pair symbol.
            timeframe: LTF timeframe.
            save_path: File path to save chart image.
            target_price: Target price level (optional).

        Returns:
            Path to saved chart image.
        """
        logger.info(f"Generating LTF chart for {pair} ({timeframe})")

        # Standardize column names
        df_std = self._standardize_columns(df)

        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(self.config.width, self.config.height * 0.8),
            gridspec_kw={'height_ratios': [3, 1]},
            sharex=True
        )

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine price color
        price_color = (
            self.config.bullish_color
            if ltf_entry.direction == MTFDirection.BULLISH
            else self.config.bearish_color
        )

        # Plot price
        if 'close' in df_std.columns:
            ax1.plot(
                df_std.index, df_std['close'],
                linewidth=2,
                color=price_color,
                label='Close',
                zorder=5
            )

        # Plot EMA 20
        ema20 = df_std['close'].ewm(span=20, adjust=False).mean()
        ax1.plot(
            df_std.index, ema20,
            linewidth=1.5,
            color=self.config.entry_color,
            label=f'EMA 20 ({ema20.iloc[-1]:,.2f})',
            zorder=3
        )

        # Mark entry point
        if ltf_entry.entry_price > 0:
            entry_marker_color = (
                'green' if ltf_entry.direction == MTFDirection.BULLISH else 'red'
            )
            ax1.scatter(
                df_std.index[-1], ltf_entry.entry_price,
                marker='o',
                s=300,
                color=entry_marker_color,
                edgecolors='black',
                linewidths=2,
                zorder=10,
                label=f'Entry: {ltf_entry.entry_price:,.2f}'
            )

        # Mark stop loss
        if ltf_entry.stop_loss > 0:
            ax1.axhline(
                y=ltf_entry.stop_loss,
                color='red',
                linestyle='--',
                linewidth=2.5,
                label=f'Stop Loss: {ltf_entry.stop_loss:,.2f}',
                zorder=8
            )

        # Mark target
        if target_price and target_price > 0:
            ax1.axhline(
                y=target_price,
                color='green',
                linestyle='--',
                linewidth=2.5,
                label=f'Target: {target_price:,.2f}',
                zorder=8
            )

        ax1.set_title(
            f'{pair} — LTF Entry ({timeframe}) — {ltf_entry.signal_type.value}',
            fontsize=16,
            fontweight='bold',
            pad=15
        )
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')

        # Panel 2: RSI
        if 'close' in df_std.columns:
            rsi = self._calculate_rsi(df_std['close'], 14)
            ax2.plot(df_std.index, rsi, linewidth=1.5, color='purple', label='RSI(14)', zorder=5)
            ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            ax2.axhline(y=40, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Oversold')
            ax2.axhline(y=60, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Overbought')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(
            save_path, 
            dpi=self.config.dpi, 
            bbox_inches='tight', 
            facecolor='white',
            edgecolor='none'
        )
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
        - Color-coded by direction (green=bullish, red=bearish, gray=neutral)
        - Confidence bars for each timeframe
        - Alignment score and recommendation display
        
        Args:
            alignment: Full MTF alignment results from MTFAnalyzer.
            pair: Trading pair symbol.
            save_path: File path to save chart image.
        
        Returns:
            Path to saved chart image.
        """
        logger.info(f"Generating alignment chart for {pair}")
        
        fig, axes = plt.subplots(
            3, 1,
            figsize=(self.config.width, self.config.height * 0.8),
            sharex=False
        )
        
        # Ensure axes is a 2D array
        if len(axes.shape) == 1:
            axes = axes.reshape(3, 1)
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # HTF Panel
        self._plot_tf_panel(
            ax=axes[0, 0] if len(axes.shape) == 2 else axes[0],
            title=f"HTF — {alignment.htf_bias.price_structure.value}",
            direction=alignment.htf_bias.direction,
            confidence=alignment.htf_bias.confidence,
            details=[
                f"Structure: {alignment.htf_bias.price_structure.value}",
                f"SMA50 Slope: {alignment.htf_bias.sma50_slope.value}",
                f"Price vs SMA50: {alignment.htf_bias.price_vs_sma50.value}",
                f"Confidence: {alignment.htf_bias.confidence:.2f}",
            ],
            color_idx=0
        )
        
        # MTF Panel
        self._plot_tf_panel(
            ax=axes[1, 0] if len(axes.shape) == 2 else axes[1],
            title=f"MTF — {alignment.mtf_setup.setup_type.value}",
            direction=alignment.mtf_setup.direction,
            confidence=alignment.mtf_setup.confidence,
            details=[
                f"Setup: {alignment.mtf_setup.setup_type.value}",
                f"Direction: {alignment.mtf_setup.direction.value}",
                f"Confidence: {alignment.mtf_setup.confidence:.2f}",
            ],
            color_idx=1
        )
        
        # LTF Panel
        ltf_signal = (
            alignment.ltf_entry.signal_type.value
            if alignment.ltf_entry
            else 'No Signal'
        )
        ltf_direction = (
            alignment.ltf_entry.direction
            if alignment.ltf_entry
            else MTFDirection.NEUTRAL
        )

        self._plot_tf_panel(
            ax=axes[2, 0] if len(axes.shape) == 2 else axes[2],
            title=f"LTF — {ltf_signal}",
            direction=ltf_direction,
            confidence=0.0,  # LTF doesn't have confidence score
            details=[
                f"Signal: {ltf_signal}",
                f"Entry: ${alignment.ltf_entry.entry_price:,.2f}"
                    if alignment.ltf_entry and alignment.ltf_entry.entry_price
                    else "No Entry",
                f"Stop: ${alignment.ltf_entry.stop_loss:,.2f}"
                    if alignment.ltf_entry and alignment.ltf_entry.stop_loss
                    else "N/A",
            ],
            color_idx=2
        )
        
        # Add overall alignment score as suptitle
        fig.suptitle(
            f'{pair} — MTF Alignment: {alignment.alignment_score}/3 | '
            f'Quality: {alignment.quality.value} | '
            f'Signal: {alignment.recommendation.value}',
            fontsize=18,
            fontweight='bold',
            y=1.02
        )
        
        plt.tight_layout()
        plt.savefig(
            save_path, 
            dpi=self.config.dpi, 
            bbox_inches='tight', 
            facecolor='white',
            edgecolor='none'
        )
        plt.close(fig)
        
        logger.info(f"Alignment chart saved to {save_path}")
        return save_path
    
    def _plot_tf_panel(
        self,
        ax,
        title: str,
        direction: MTFDirection,
        confidence: float,
        details: List[str],
        color_idx: int
    ):
        """
        Plot single timeframe panel for alignment chart.
        
        Args:
            ax: Matplotlib axes object.
            title: Panel title (timeframe and setup type).
            direction: MTFDirection enum value.
            confidence: Confidence score (0.0-1.0).
            details: List of detail strings to display.
            color_idx: Index for color selection (unused, kept for compatibility).
        """
        colors = [
            self.config.bullish_color,  # Green for bullish
            self.config.bearish_color,  # Red for bearish
            self.config.neutral_color,  # Gray for neutral
        ]
        
        # Determine color based on direction
        if direction == MTFDirection.BULLISH:
            color = colors[0]
        elif direction == MTFDirection.BEARISH:
            color = colors[1]
        else:
            color = colors[2]
        
        # Create horizontal confidence bar
        ax.barh([0], [confidence * 100], color=color, alpha=0.7, height=0.5)
        ax.set_xlim(0, 100)
        ax.set_yticks([])
        ax.set_xlabel('Confidence (%)', fontsize=10)
        
        # Add title
        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        
        # Add details as text
        for i, detail in enumerate(details):
            ax.text(
                0.02, -0.3 - (i * 0.25),
                detail,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )
        
        ax.grid(True, alpha=0.3, linestyle='--', axis='x')
    
    def _add_bias_annotation(
        self, 
        ax, 
        bias: HTFBias, 
        pair: str, 
        timeframe: str, 
        current_price: float
    ):
        """
        Add bias annotation box to HTF chart.
        
        Args:
            ax: Matplotlib axes object.
            bias: HTFBias object with analysis results.
            pair: Trading pair symbol.
            timeframe: HTF timeframe.
            current_price: Current market price.
        """
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
    
    def _add_setup_annotation(
        self, 
        ax, 
        setup: MTFSetup, 
        timeframe: str
    ):
        """
        Add setup annotation box to MTF chart.
        
        Args:
            ax: Matplotlib axes object.
            setup: MTFSetup object with setup details.
            timeframe: MTF timeframe.
        """
        textstr = (
            f'Setup: {setup.setup_type.value}\n'
            f'Direction: {setup.direction.value}\n'
            f'Confidence: {setup.confidence:.2f}'
        )
        
        if setup.pullback_details:
            pb = setup.pullback_details
            textstr += (
                f'\nPullback to SMA{pb.approaching_sma}\n'
                f'Distance: {pb.distance_to_sma_pct:.2f}%\n'
                f'RSI: {pb.rsi_level:.1f}'
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
    
    def _calculate_rsi(self, series: pd.Series, length: int) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            series: Price series (close prices).
            length: RSI calculation period (default 14).
        
        Returns:
            RSI series (0-100 scale).
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(100)


# Convenience functions
def generate_htf_chart(
    df: pd.DataFrame,
    htf_bias: HTFBias,
    pair: str,
    timeframe: str,
    save_path: str,
) -> str:
    """
    Convenience function to generate HTF chart.
    
    Args:
        df: OHLCV DataFrame.
        htf_bias: HTF bias analysis.
        pair: Trading pair.
        timeframe: HTF timeframe.
        save_path: Path to save chart.
    
    Returns:
        Path to saved chart.
    """
    generator = MTFChartGenerator()
    return generator.generate_htf_chart(df, htf_bias, pair, timeframe, save_path)


def generate_mtf_chart(
    df: pd.DataFrame,
    mtf_setup: MTFSetup,
    pair: str,
    timeframe: str,
    save_path: str,
) -> str:
    """
    Convenience function to generate MTF chart.
    
    Args:
        df: OHLCV DataFrame.
        mtf_setup: MTF setup analysis.
        pair: Trading pair.
        timeframe: MTF timeframe.
        save_path: Path to save chart.
    
    Returns:
        Path to saved chart.
    """
    generator = MTFChartGenerator()
    return generator.generate_mtf_chart(df, mtf_setup, pair, timeframe, save_path)


def generate_ltf_chart(
    df: pd.DataFrame,
    ltf_entry: LTFEntry,
    pair: str,
    timeframe: str,
    save_path: str,
    target_price: Optional[float] = None,
) -> str:
    """
    Convenience function to generate LTF chart.
    
    Args:
        df: OHLCV DataFrame.
        ltf_entry: LTF entry signal.
        pair: Trading pair.
        timeframe: LTF timeframe.
        save_path: Path to save chart.
        target_price: Target price level (optional).
    
    Returns:
        Path to saved chart.
    """
    generator = MTFChartGenerator()
    return generator.generate_ltf_chart(
        df, ltf_entry, pair, timeframe, save_path, target_price
    )


def generate_alignment_chart(
    alignment: MTFAlignment,
    pair: str,
    save_path: str,
) -> str:
    """
    Convenience function to generate alignment chart.
    
    Args:
        alignment: Full MTF alignment.
        pair: Trading pair.
        save_path: Path to save chart.
    
    Returns:
        Path to saved chart.
    """
    generator = MTFChartGenerator()
    return generator.generate_alignment_chart(alignment, pair, save_path)
