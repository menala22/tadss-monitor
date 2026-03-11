"""
MTF Interactive Chart Generator with Plotly

Generates beautiful, interactive HTML reports with Plotly charts.
Features:
- Zoom, pan, hover tooltips
- Professional candlestick charts
- Multiple panels (price, volume, indicators)
- Standalone HTML file (no dependencies)

Usage:
    from src.services.mtf_chart_generator_plotly import MTFChartGeneratorPlotly
    generator = MTFChartGeneratorPlotly()
    generator.generate_full_report(
        pair='BTC/USDT',
        alignment=alignment,
        data=data,
        config=config,
        save_path='reports/btc-mtf-analysis.html'
    )
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.models.mtf_models import HTFBias, LTFEntry, MTFAlignment, MTFDirection, MTFSetup

logger = logging.getLogger(__name__)


class MTFChartGeneratorPlotly:
    """
    Generate interactive MTF analysis charts with Plotly.
    
    Creates professional, interactive HTML reports with:
    - Candlestick charts
    - Moving averages
    - Volume panels
    - RSI indicators
    - Annotations and labels
    """
    
    def __init__(self):
        """Initialize Plotly chart generator."""
        self.colors = {
            'bullish': '#2ecc71',
            'bearish': '#e74c3c',
            'neutral': '#95a5a6',
            'sma50': '#3498db',
            'sma200': '#e67e22',
            'ema20': '#9b59b6',
            'background': '#ffffff',
            'grid': '#f0f0f0',
        }
    
    def generate_full_report(
        self,
        pair: str,
        alignment: MTFAlignment,
        data: dict,
        config,
        save_path: str,
    ) -> str:
        """
        Generate complete interactive HTML report.
        
        Args:
            pair: Trading pair symbol.
            alignment: MTF alignment results.
            data: Dictionary with htf, mtf, ltf DataFrames.
            config: MTF timeframe configuration.
            save_path: Path to save HTML report.
        
        Returns:
            Path to saved HTML file.
        """
        logger.info(f"Generating interactive HTML report for {pair}")
        
        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=False,
            vertical_spacing=0.08,
            row_heights=[0.25, 0.25, 0.25, 0.25],
            subplot_titles=[
                f'HTF ({config.htf_timeframe}) - {alignment.htf_bias.direction.value}',
                f'MTF ({config.mtf_timeframe}) - {alignment.mtf_setup.setup_type.value}',
                f'LTF ({config.ltf_timeframe}) - Entry Signal',
                f'Alignment Overview - Score: {alignment.alignment_score}/3'
            ]
        )
        
        # Standardize column names
        htf_df = self._standardize_columns(data['htf'])
        mtf_df = self._standardize_columns(data['mtf'])
        ltf_df = self._standardize_columns(data['ltf'])
        
        # HTF Panel - Candlestick with SMAs
        self._add_htf_panel(fig, htf_df, alignment.htf_bias, row=1)
        
        # MTF Panel - Candlestick with SMAs and RSI
        self._add_mtf_panel(fig, mtf_df, alignment.mtf_setup, row=2)
        
        # LTF Panel - Candlestick with entry markers
        self._add_ltf_panel(fig, ltf_df, alignment.ltf_entry, alignment.target, row=3)
        
        # Alignment Panel - Visual overview
        self._add_alignment_panel(fig, alignment, row=4)
        
        # Update layout
        fig.update_layout(
            height=1200,
            title_text=f'<b>{pair} - MTF Analysis Report</b><br>Style: {config.trading_style.value} | Signal: {alignment.recommendation.value} | Quality: {alignment.quality.value}',
            title_font_size=20,
            showlegend=True,
            legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)'),
            hovermode='x unified',
            template='plotly_white',
        )
        
        # Update x-axis
        fig.update_xaxes(
            rangeslider_visible=False,
            tickformat='%Y-%m-%d',
        )
        
        # Save as HTML
        fig.write_html(
            save_path,
            include_plotlyjs=True,
            full_html=True,
            config={
                'scrollZoom': True,
                'displayModeBar': True,
                'modeBarButtonsToAdd': ['drawline', 'eraseshape'],
            }
        )
        
        logger.info(f"Interactive HTML report saved to {save_path}")
        return save_path
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to lowercase."""
        df_copy = df.copy()
        df_copy.columns = df_copy.columns.str.lower()
        return df_copy
    
    def _add_htf_panel(self, fig, df: pd.DataFrame, htf_bias: HTFBias, row: int):
        """Add HTF candlestick chart with SMAs."""
        
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='OHLC',
                increasing_line_color=self.colors['bullish'],
                decreasing_line_color=self.colors['bearish'],
            ),
            row=row, col=1
        )
        
        # Add SMA 50 if available
        if len(df) >= 50:
            sma50 = df['close'].rolling(50).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=sma50,
                    mode='lines', name='SMA 50',
                    line=dict(color=self.colors['sma50'], width=2)
                ),
                row=row, col=1
            )
        
        # Add SMA 200 if available
        if len(df) >= 200:
            sma200 = df['close'].rolling(200).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=sma200,
                    mode='lines', name='SMA 200',
                    line=dict(color=self.colors['sma200'], width=2)
                ),
                row=row, col=1
            )
        
        # Add bias annotation
        fig.add_annotation(
            x=df.index[-1], y=df['close'].iloc[-1],
            text=f"Bias: {htf_bias.direction.value}<br>Conf: {htf_bias.confidence:.2f}",
            showarrow=True,
            arrowhead=2,
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            row=row, col=1
        )
    
    def _add_mtf_panel(self, fig, df: pd.DataFrame, mtf_setup: MTFSetup, row: int):
        """Add MTF candlestick chart with SMAs and RSI."""
        
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='MTF OHLC',
                increasing_line_color=self.colors['bullish'],
                decreasing_line_color=self.colors['bearish'],
                xaxis='x2', yaxis='y2'
            ),
            row=row, col=1
        )
        
        # Add SMA 20 and 50
        sma20 = df['close'].rolling(20).mean()
        sma50 = df['close'].rolling(50).mean()
        
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma20,
                mode='lines', name='SMA 20',
                line=dict(color=self.colors['sma50'], width=2),
                xaxis='x2', yaxis='y2'
            ),
            row=row, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma50,
                mode='lines', name='SMA 50',
                line=dict(color=self.colors['sma200'], width=2),
                xaxis='x2', yaxis='y2'
            ),
            row=row, col=1
        )
        
        # Highlight pullback zone if applicable
        if mtf_setup.pullback_details and mtf_setup.pullback_details.approaching_sma:
            pb = mtf_setup.pullback_details
            sma_value = sma20.iloc[-1] if pb.approaching_sma == 20 else sma50.iloc[-1]
            
            fig.add_hrect(
                y0=sma_value * 0.99, y1=sma_value * 1.01,
                fillcolor="yellow", opacity=0.3,
                annotation_text=f"Pullback Zone (SMA{pb.approaching_sma})",
                annotation_position="top",
                row=row, col=1
            )
    
    def _add_ltf_panel(self, fig, df: pd.DataFrame, ltf_entry: Optional[LTFEntry], target, row: int):
        """Add LTF candlestick chart with entry markers."""
        
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='LTF OHLC',
                increasing_line_color=self.colors['bullish'],
                decreasing_line_color=self.colors['bearish'],
                xaxis='x3', yaxis='y3'
            ),
            row=row, col=1
        )
        
        # Add EMA 20
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=ema20,
                mode='lines', name='EMA 20',
                line=dict(color=self.colors['ema20'], width=2, dash='dot'),
                xaxis='x3', yaxis='y3'
            ),
            row=row, col=1
        )
        
        # Add entry marker if exists
        if ltf_entry and ltf_entry.entry_price > 0:
            # Entry point
            fig.add_scatter(
                x=[df.index[-1]], y=[ltf_entry.entry_price],
                mode='markers', name='Entry',
                marker=dict(color='green', size=15, symbol='circle'),
                xaxis='x3', yaxis='y3'
            )
            
            # Stop loss line
            fig.add_hline(
                y=ltf_entry.stop_loss,
                line_dash='dash', line_color='red', line_width=2,
                annotation_text='Stop Loss',
                row=row, col=1
            )
            
            # Target line
            if target and target.target_price:
                fig.add_hline(
                    y=target.target_price,
                    line_dash='dash', line_color='green', line_width=2,
                    annotation_text='Target',
                    row=row, col=1
                )
    
    def _add_alignment_panel(self, fig, alignment: MTFAlignment, row: int):
        """Add alignment overview panel."""
        
        # Create bar chart for alignment
        timeframes = ['HTF', 'MTF', 'LTF']
        confidences = [
            alignment.htf_bias.confidence,
            alignment.mtf_setup.confidence,
            0.0  # LTF doesn't have confidence
        ]
        
        colors = []
        for direction in [
            alignment.htf_bias.direction,
            alignment.mtf_setup.direction,
            alignment.ltf_entry.direction if alignment.ltf_entry else MTFDirection.NEUTRAL
        ]:
            if direction == MTFDirection.BULLISH:
                colors.append(self.colors['bullish'])
            elif direction == MTFDirection.BEARISH:
                colors.append(self.colors['bearish'])
            else:
                colors.append(self.colors['neutral'])
        
        fig.add_trace(
            go.Bar(
                x=timeframes,
                y=confidences,
                marker_color=colors,
                name='Confidence',
                text=[f'{c:.2f}' for c in confidences],
                textposition='auto',
                xaxis='x4', yaxis='y4'
            ),
            row=row, col=1
        )
        
        # Add alignment score annotation
        fig.add_annotation(
            x=1.5, y=0.5,
            text=f'<b>Alignment Score: {alignment.alignment_score}/3</b><br>Quality: {alignment.quality.value}<br>Signal: {alignment.recommendation.value}',
            showarrow=False,
            font_size=16,
            align='center',
            row=row, col=1
        )
        
        fig.update_yaxes(range=[0, 1.2], row=row, col=1)


def generate_interactive_report(
    pair: str,
    alignment: MTFAlignment,
    data: dict,
    config,
    save_dir: str,
) -> str:
    """
    Convenience function to generate interactive HTML report.
    
    Args:
        pair: Trading pair.
        alignment: MTF alignment.
        data: OHLCV data dictionary.
        config: MTF config.
        save_dir: Directory to save report.
    
    Returns:
        Path to saved HTML file.
    """
    generator = MTFChartGeneratorPlotly()
    
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    filename = f"{pair.replace('/', '')}-mtf-analysis-interactive-{date_str}.html"
    save_path = Path(save_dir) / filename
    
    return generator.generate_full_report(
        pair=pair,
        alignment=alignment,
        data=data,
        config=config,
        save_path=str(save_path)
    )
