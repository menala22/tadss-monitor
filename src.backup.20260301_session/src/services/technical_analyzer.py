"""
Technical Analysis Service for TA-DSS.

This module provides technical indicator calculation and signal generation
using pandas_ta for positions in the monitoring system.

All calculations are vectorized using Pandas for optimal performance.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class SignalState(str, Enum):
    """Possible signal states for technical indicators."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    OVERBOUGHT = "OVERBOUGHT"
    OVERSOLD = "OVERSOLD"


class PositionType(str, Enum):
    """Position direction."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class TechnicalSignal:
    """Represents a technical analysis signal for a position."""

    pair: str
    position_type: PositionType
    timeframe: str
    current_price: float
    indicators: dict[str, Any] = field(default_factory=dict)
    signal_states: dict[str, SignalState] = field(default_factory=dict)
    overall_signal: SignalState = SignalState.NEUTRAL
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    confidence_score: float = 0.0
    warning: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert signal to dictionary for API response."""
        # Handle new signal_states format with 'values' key
        signal_states_dict = {}
        values_dict = {}
        
        for k, v in self.signal_states.items():
            if k == 'values':
                values_dict = v
            elif isinstance(v, SignalState):
                signal_states_dict[k] = v.value
            else:
                signal_states_dict[k] = v
        
        return {
            "pair": self.pair,
            "position_type": self.position_type.value,
            "timeframe": self.timeframe,
            "current_price": self.current_price,
            "indicators": self.indicators,
            "signal_states": signal_states_dict,
            "indicator_values": values_dict,
            "overall_signal": self.overall_signal.value,
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "neutral_count": self.neutral_count,
            "confidence_score": round(self.confidence_score, 2),
            "warning": self.warning,
        }


class TechnicalAnalyzer:
    """
    Technical analysis engine for trading positions.

    Calculates technical indicators using pandas_ta and generates
    trading signals based on configurable rules.

    Attributes:
        ema_periods: List of EMA periods to calculate.
        rsi_length: RSI calculation period.
        macd_fast: MACD fast period.
        macd_slow: MACD slow period.
        macd_signal: MACD signal period.
        rsi_overbought: RSI overbought threshold.
        rsi_oversold: RSI oversold threshold.
    """

    def __init__(
        self,
        ema_periods: list[int] | None = None,
        rsi_length: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ):
        """
        Initialize the technical analyzer.

        Args:
            ema_periods: List of EMA periods. Defaults to [10, 20, 50].
            rsi_length: RSI calculation period. Defaults to 14.
            macd_fast: MACD fast period. Defaults to 12.
            macd_slow: MACD slow period. Defaults to 26.
            macd_signal: MACD signal period. Defaults to 9.
            rsi_overbought: RSI overbought threshold. Defaults to 70.
            rsi_oversold: RSI oversold threshold. Defaults to 30.
        """
        self.ema_periods = ema_periods or [10, 20, 50]
        self.rsi_length = rsi_length
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLCV data.

        This method adds the following columns to the DataFrame:
        - EMA 10, 20, 50
        - MACD (12, 26, 9) with histogram
        - RSI (14)

        Args:
            df: DataFrame with OHLCV data. Must contain 'close' column.
                Optional: 'open', 'high', 'low', 'volume'.

        Returns:
            DataFrame with added indicator columns.

        Raises:
            ValueError: If required columns are missing.
        """
        if df.empty:
            raise ValueError("Cannot calculate indicators on empty DataFrame")

        if "close" not in df.columns and "Close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' or 'Close' column")

        # Work on a copy to avoid modifying original
        df = df.copy()

        # Standardize column names (ensure lowercase)
        df = df.rename(columns={col: col.lower() for col in df.columns})

        # Ensure close is numeric
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        # Calculate EMAs
        for period in self.ema_periods:
            col_name = f"EMA_{period}"
            df[col_name] = ta.ema(df["close"], length=period)

        # Calculate MACD (12, 26, 9)
        # Handle case where pandas_ta returns None (insufficient data)
        macd = ta.macd(
            df["close"],
            fast=self.macd_fast,
            slow=self.macd_slow,
            signal=self.macd_signal,
        )
        if macd is not None:
            # Merge MACD columns
            for col in macd.columns:
                df[col] = macd[col]
        else:
            # Add NaN columns for insufficient data
            macd_prefix = f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
            df[f"{macd_prefix}"] = np.nan
            df[f"{macd_prefix}h"] = np.nan
            df[f"{macd_prefix}s"] = np.nan
            logger.debug("MACD returned None - insufficient data")

        # Calculate RSI (14)
        # Handle case where pandas_ta returns None (insufficient data)
        rsi = ta.rsi(df["close"], length=self.rsi_length)
        if rsi is not None:
            df["RSI"] = rsi
        else:
            df["RSI"] = np.nan
            logger.debug("RSI returned None - insufficient data")

        logger.debug(
            f"Calculated indicators: EMA{self.ema_periods}, "
            f"MACD({self.macd_fast},{self.macd_slow},{self.macd_signal}), "
            f"RSI({self.rsi_length})"
        )

        return df

    def generate_signal_states(
        self,
        df: pd.DataFrame
    ) -> dict[str, Any]:
        """
        Generate signal states for each technical indicator.

        Evaluates the latest row of the DataFrame and returns the signal
        state for each indicator based on the following rules:

        - MA (10/20/50): BULLISH if Close > MA, BEARISH if Close < MA
        - MACD: BULLISH if Histogram > 0, BEARISH if Histogram < 0
        - RSI: BULLISH if RSI > 50, BEARISH if RSI < 50
               OVERBOUGHT if RSI > 70, OVERSOLD if RSI < 30

        Handles insufficient data gracefully by returning 'NEUTRAL' or None
        when indicators cannot be calculated.

        Args:
            df: DataFrame with calculated indicator columns.

        Returns:
            Dictionary with signal states and indicator values:
            {
                'MA10': 'BULLISH',
                'MA20': 'BULLISH',
                'MA50': 'BEARISH',
                'MACD': 'BULLISH',
                'RSI': 'NEUTRAL',
                'values': {
                    'RSI': 55.4,
                    'MACD_hist': 1.2,
                    'EMA_10': 45000.0,
                    'EMA_20': 44800.0,
                    'EMA_50': 45500.0,
                }
            }

        Example:
            >>> df = analyzer.calculate_indicators(ohlcv_df)
            >>> signals = analyzer.generate_signal_states(df)
            >>> print(signals['MA10'])
            'BULLISH'
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for signal generation")
            return {
                'MA10': SignalState.NEUTRAL,
                'MA20': SignalState.NEUTRAL,
                'MA50': SignalState.NEUTRAL,
                'MACD': SignalState.NEUTRAL,
                'RSI': SignalState.NEUTRAL,
                'values': {},
            }

        # Get the latest row
        latest = df.iloc[-1]
        close_price = latest.get("close", 0)

        signals = {}
        values = {}

        # Evaluate EMAs (MA10, MA20, MA50)
        ema_map = {10: 'MA10', 20: 'MA20', 50: 'MA50'}
        for period, signal_name in ema_map.items():
            col_name = f"EMA_{period}"
            ema_value = latest.get(col_name)

            # Handle insufficient data (NaN values)
            if ema_value is None or pd.isna(ema_value):
                signals[signal_name] = SignalState.NEUTRAL
                values[signal_name.replace('MA', 'EMA_')] = None
                logger.debug(f"{col_name} is NaN - insufficient data")
            elif close_price > ema_value:
                signals[signal_name] = SignalState.BULLISH
                values[signal_name.replace('MA', 'EMA_')] = float(ema_value)
            elif close_price < ema_value:
                signals[signal_name] = SignalState.BEARISH
                values[signal_name.replace('MA', 'EMA_')] = float(ema_value)
            else:
                signals[signal_name] = SignalState.NEUTRAL
                values[signal_name.replace('MA', 'EMA_')] = float(ema_value)

        # Evaluate MACD Histogram
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        macd_hist = latest.get(macd_hist_col)

        # Handle insufficient data for MACD
        if macd_hist is None or pd.isna(macd_hist):
            signals["MACD"] = SignalState.NEUTRAL
            values["MACD_hist"] = None
            logger.debug("MACD histogram is NaN - insufficient data")
        elif macd_hist > 0:
            signals["MACD"] = SignalState.BULLISH
            values["MACD_hist"] = float(macd_hist)
        elif macd_hist < 0:
            signals["MACD"] = SignalState.BEARISH
            values["MACD_hist"] = float(macd_hist)
        else:
            signals["MACD"] = SignalState.NEUTRAL
            values["MACD_hist"] = 0.0

        # Evaluate RSI
        rsi_value = latest.get("RSI")

        # Handle insufficient data for RSI
        if rsi_value is None or pd.isna(rsi_value):
            signals["RSI"] = SignalState.NEUTRAL
            values["RSI"] = None
            logger.debug("RSI is NaN - insufficient data")
        elif rsi_value >= self.rsi_overbought:
            signals["RSI"] = SignalState.OVERBOUGHT
            values["RSI"] = float(rsi_value)
        elif rsi_value <= self.rsi_oversold:
            signals["RSI"] = SignalState.OVERSOLD
            values["RSI"] = float(rsi_value)
        elif rsi_value > 50:
            signals["RSI"] = SignalState.BULLISH
            values["RSI"] = float(rsi_value)
        elif rsi_value < 50:
            signals["RSI"] = SignalState.BEARISH
            values["RSI"] = float(rsi_value)
        else:
            signals["RSI"] = SignalState.NEUTRAL
            values["RSI"] = 50.0

        # Add values dictionary to result
        signals['values'] = values

        return signals

    def calculate_overall_signal(
        self,
        signal_states: dict[str, Any],
        position_type: PositionType,
    ) -> tuple[SignalState, float, dict[str, int]]:
        """
        Calculate overall signal and confidence score.

        Aggregates individual indicator signals into an overall signal
        and calculates a confidence score based on signal agreement.

        Args:
            signal_states: Dictionary of indicator signals (from generate_signal_states).
            position_type: The position direction (LONG or SHORT).

        Returns:
            Tuple of (overall_signal, confidence_score, counts_dict) where:
            - overall_signal: Aggregated signal state
            - confidence_score: 0.0 to 1.0 indicating signal strength
            - counts_dict: {'bullish': n, 'bearish': n, 'neutral': n}
        """
        counts = {"bullish": 0, "bearish": 0, "neutral": 0}

        # Only count actual signal keys (exclude 'values')
        signal_keys = ['MA10', 'MA20', 'MA50', 'MACD', 'RSI']

        for key in signal_keys:
            state = signal_states.get(key)
            if state is None:
                continue
            if state in (SignalState.BULLISH, SignalState.OVERBOUGHT):
                counts["bullish"] += 1
            elif state in (SignalState.BEARISH, SignalState.OVERSOLD):
                counts["bearish"] += 1
            else:
                counts["neutral"] += 1

        total = sum(counts.values())
        if total == 0:
            return SignalState.NEUTRAL, 0.0, counts

        # Determine dominant signal
        if counts["bullish"] > counts["bearish"]:
            dominant = SignalState.BULLISH
        elif counts["bearish"] > counts["bullish"]:
            dominant = SignalState.BEARISH
        else:
            dominant = SignalState.NEUTRAL

        # Calculate confidence score (0.0 to 1.0)
        # Based on agreement ratio and neutral reduction
        agreement_ratio = max(counts["bullish"], counts["bearish"]) / total
        neutral_penalty = counts["neutral"] / total * 0.5
        confidence = max(0.0, min(1.0, agreement_ratio - neutral_penalty))

        return dominant, confidence, counts

    def analyze_position(
        self,
        df: pd.DataFrame,
        pair: str,
        position_type: PositionType,
        timeframe: str,
    ) -> TechnicalSignal:
        """
        Perform complete technical analysis for a position.

        This is the main entry point for analyzing a trading position.
        It calculates indicators, generates signals, and produces an
        overall assessment with confidence score.

        Args:
            df: OHLCV DataFrame with at least 'close' column.
            pair: Trading pair symbol (e.g., 'BTCUSD').
            position_type: Position direction (LONG or SHORT).
            timeframe: Analysis timeframe (e.g., 'h4', 'd1').

        Returns:
            TechnicalSignal object with complete analysis results.

        Example:
            analyzer = TechnicalAnalyzer()
            df = market_data.fetch_ohlcv('BTCUSD', 'h4', limit=100)
            signal = analyzer.analyze_position(df, 'BTCUSD', PositionType.LONG, 'h4')
            print(signal.to_dict())
        """
        # Calculate indicators
        df_with_indicators = self.calculate_indicators(df)

        # Get current price
        current_price = float(df_with_indicators["close"].iloc[-1])

        # Generate signal states
        signal_states = self.generate_signal_states(df_with_indicators)

        # Calculate overall signal
        overall_signal, confidence, counts = self.calculate_overall_signal(
            signal_states, position_type
        )

        # Check for warning conditions
        warning = self._check_warnings(signal_states, position_type)

        # Extract indicator values for response
        latest = df_with_indicators.iloc[-1]
        indicators = {
            "current_price": current_price,
            "EMA_10": float(latest.get("EMA_10", 0)) if latest.get("EMA_10") is not None else None,
            "EMA_20": float(latest.get("EMA_20", 0)) if latest.get("EMA_20") is not None else None,
            "EMA_50": float(latest.get("EMA_50", 0)) if latest.get("EMA_50") is not None else None,
            "MACD": float(latest.get(f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}", 0))
            if latest.get(f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}") is not None
            else None,
            "MACD_histogram": float(latest.get(f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}", 0))
            if latest.get(f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}") is not None
            else None,
            "RSI": float(latest.get("RSI", 0)) if latest.get("RSI") is not None else None,
        }

        return TechnicalSignal(
            pair=pair,
            position_type=position_type,
            timeframe=timeframe,
            current_price=current_price,
            indicators=indicators,
            signal_states=signal_states,
            overall_signal=overall_signal,
            bullish_count=counts["bullish"],
            bearish_count=counts["bearish"],
            neutral_count=counts["neutral"],
            confidence_score=confidence,
            warning=warning,
        )

    def _check_warnings(
        self,
        signal_states: dict[str, Any],
        position_type: PositionType,
    ) -> Optional[str]:
        """
        Check for warning conditions based on signals and position.

        Args:
            signal_states: Dictionary of indicator signals (from generate_signal_states).
            position_type: Position direction.

        Returns:
            Warning message string or None if no warnings.
        """
        warnings = []

        # Check for overbought/oversold conditions
        rsi_state = signal_states.get("RSI")
        if rsi_state == SignalState.OVERBOUGHT:
            if position_type == PositionType.LONG:
                warnings.append("RSI overbought - consider taking profits on LONG")
        elif rsi_state == SignalState.OVERSOLD:
            if position_type == PositionType.SHORT:
                warnings.append("RSI oversold - consider covering SHORT")

        # Check for strong divergence (all MAs against position)
        # Use new signal names: MA10, MA20, MA50
        ma_signals = [
            signal_states.get("MA10"),
            signal_states.get("MA20"),
            signal_states.get("MA50"),
        ]
        ma_signals = [s for s in ma_signals if s is not None]

        if position_type == PositionType.LONG:
            if all(s == SignalState.BEARISH for s in ma_signals):
                warnings.append("All EMAs bearish - strong downtrend vs LONG position")
        elif position_type == PositionType.SHORT:
            if all(s == SignalState.BULLISH for s in ma_signals):
                warnings.append("All EMAs bullish - strong uptrend vs SHORT position")

        # Check MACD divergence
        macd_state = signal_states.get("MACD")
        if position_type == PositionType.LONG and macd_state == SignalState.BEARISH:
            warnings.append("MACD bearish divergence on LONG position")
        elif position_type == PositionType.SHORT and macd_state == SignalState.BULLISH:
            warnings.append("MACD bullish divergence on SHORT position")

        return "; ".join(warnings) if warnings else None

    def get_indicator_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Get a summary of all calculated indicators.

        Args:
            df: DataFrame with calculated indicator columns.

        Returns:
            Dictionary with latest indicator values and interpretations.
        """
        latest = df.iloc[-1]
        close_price = latest["close"]

        summary = {
            "price": {
                "current": float(close_price),
            },
            "moving_averages": {},
            "momentum": {},
        }

        # EMA summary
        for period in self.ema_periods:
            col_name = f"EMA_{period}"
            ema_value = float(latest[col_name]) if col_name in latest else None
            summary["moving_averages"][f"EMA_{period}"] = {
                "value": ema_value,
                "distance_pct": round((close_price - ema_value) / ema_value * 100, 2)
                if ema_value and not pd.isna(ema_value)
                else None,
            }

        # MACD summary
        macd_col = f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        summary["momentum"]["MACD"] = {
            "value": float(latest[macd_col]) if macd_col in latest else None,
            "histogram": float(latest[macd_hist_col]) if macd_hist_col in latest else None,
        }

        # RSI summary
        summary["momentum"]["RSI"] = {
            "value": float(latest["RSI"]) if "RSI" in latest else None,
            "interpretation": self._interpret_rsi(latest.get("RSI")),
        }

        return summary

    def _interpret_rsi(self, rsi_value: Optional[float]) -> str:
        """
        Get human-readable RSI interpretation.

        Args:
            rsi_value: RSI value.

        Returns:
            Interpretation string.
        """
        if rsi_value is None or pd.isna(rsi_value):
            return "N/A"
        elif rsi_value >= self.rsi_overbought:
            return "Overbought"
        elif rsi_value <= self.rsi_oversold:
            return "Oversold"
        elif rsi_value > 50:
            return "Bullish"
        elif rsi_value < 50:
            return "Bearish"
        else:
            return "Neutral"
