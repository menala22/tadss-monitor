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
        ott_period: OTT indicator period.
        ott_percent: OTT percentage for band calculation.
        ott_ma_type: Moving average type for OTT (VAR, EMA, SMA, etc.).
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
        ott_period: int = 2,
        ott_percent: float = 1.4,
        ott_ma_type: str = "VAR",
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
            ott_period: OTT indicator period. Defaults to 2.
            ott_percent: OTT percentage for band calculation. Defaults to 1.4.
            ott_ma_type: Moving average type for OTT. Defaults to "VAR".
        """
        self.ema_periods = ema_periods or [10, 20, 50]
        self.rsi_length = rsi_length
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.ott_period = ott_period
        self.ott_percent = ott_percent
        self.ott_ma_type = ott_ma_type

    # ========================================================================
    # OTT (Optimized Trend Tracker) Helper Functions
    # ========================================================================

    def _var_func(self, src: pd.Series, length: int) -> pd.Series:
        """
        Calculate Variable Moving Average (VAR) using CMO.

        The VAR adapts to market volatility using the Chande Momentum
        Oscillator to adjust the smoothing factor dynamically.

        Formula:
            valpha = 2 / (length + 1)
            vUD = sum of up moves (9 periods)
            vDD = sum of down moves (9 periods)
            vCMO = (vUD - vDD) / (vUD + vDD)
            VAR = valpha * |vCMO| * src + (1 - valpha * |vCMO|) * VAR[1]

        Args:
            src: Source price series (typically close).
            length: VAR period.

        Returns:
            VAR series.
        """
        valpha = 2 / (length + 1)

        # Calculate up and down moves
        vud1 = src.where(src > src.shift(1), 0) - src.shift(1).where(src > src.shift(1), 0)
        vud1 = vud1.clip(lower=0)

        vdd1 = src.shift(1).where(src < src.shift(1), 0) - src.where(src < src.shift(1), 0)
        vdd1 = vdd1.clip(lower=0)

        # Sum over 9 periods (as per Pine Script)
        vUD = vud1.rolling(window=9).sum()
        vDD = vdd1.rolling(window=9).sum()

        # Chande Momentum Oscillator
        vCMO = (vUD - vDD) / (vUD + vDD)
        vCMO = vCMO.fillna(0)

        # Calculate VAR using iterative approach
        VAR = pd.Series(index=src.index, dtype=float)
        VAR.iloc[0] = src.iloc[0]

        for i in range(1, len(src)):
            VAR.iloc[i] = valpha * abs(vCMO.iloc[i]) * src.iloc[i] + \
                          (1 - valpha * abs(vCMO.iloc[i])) * VAR.iloc[i - 1]

        return VAR

    def _wwma_func(self, src: pd.Series, length: int) -> pd.Series:
        """
        Calculate Wilder's Welles Moving Average (WWMA).

        Formula:
            WWMA = (1/length) * src + (1 - 1/length) * WWMA[1]

        Args:
            src: Source price series.
            length: WWMA period.

        Returns:
            WWMA series.
        """
        wwalpha = 1 / length
        WWMA = pd.Series(index=src.index, dtype=float)
        WWMA.iloc[0] = src.iloc[0]

        for i in range(1, len(src)):
            WWMA.iloc[i] = wwalpha * src.iloc[i] + (1 - wwalpha) * WWMA.iloc[i - 1]

        return WWMA

    def _zlema_func(self, src: pd.Series, length: int) -> pd.Series:
        """
        Calculate Zero Lag Exponential Moving Average (ZLEMA).

        ZLEMA reduces lag by adding the difference between current
        and lagged price to the source before applying EMA.

        Formula:
            lag = length / 2 (rounded)
            zxEMAData = src + (src - src[lag])
            ZLEMA = EMA(zxEMAData, length)

        Args:
            src: Source price series.
            length: ZLEMA period.

        Returns:
            ZLEMA series.
        """
        # Calculate lag (rounded to nearest integer)
        lag = int(round(length / 2))

        # Calculate zero-lag data
        zxEMAData = src + (src - src.shift(lag))

        # Apply EMA
        ZLEMA = ta.ema(zxEMAData, length=length)

        return ZLEMA

    def _tsf_func(self, src: pd.Series, length: int) -> pd.Series:
        """
        Calculate Time Series Forecast (TSF) using linear regression.

        TSF extends the linear regression line into the future by
        adding the slope to the current regression value.

        Formula:
            lrc = linreg(src, length, 0)
            lrc1 = linreg(src, length, 1)
            lrs = lrc - lrc1 (slope)
            TSF = lrc + lrs

        Args:
            src: Source price series.
            length: Linear regression period.

        Returns:
            TSF series.
        """
        # Linear regression with offset 0 and 1
        lrc = ta.linreg(src, period=length, offset=0)
        lrc1 = ta.linreg(src, period=length, offset=1)

        # Calculate slope
        lrs = lrc - lrc1

        # TSF = current regression + slope
        TSF = lrc + lrs

        return TSF

    def _get_ma(self, src: pd.Series, length: int) -> pd.Series:
        """
        Get moving average based on selected type.

        Supported types: SMA, EMA, WMA, TMA, VAR, WWMA, ZLEMA, TSF

        Args:
            src: Source price series.
            length: MA period.

        Returns:
            Moving average series.
        """
        if self.ott_ma_type == "SMA":
            return ta.sma(src, length=length)
        elif self.ott_ma_type == "EMA":
            return ta.ema(src, length=length)
        elif self.ott_ma_type == "WMA":
            return ta.wma(src, length=length)
        elif self.ott_ma_type == "TMA":
            # TMA = SMA of SMA
            half = int(length / 2)
            return ta.sma(ta.sma(src, length=half + 1), length=half + 1)
        elif self.ott_ma_type == "VAR":
            return self._var_func(src, length)
        elif self.ott_ma_type == "WWMA":
            return self._wwma_func(src, length)
        elif self.ott_ma_type == "ZLEMA":
            return self._zlema_func(src, length)
        elif self.ott_ma_type == "TSF":
            return self._tsf_func(src, length)
        else:
            # Default to VAR
            logger.warning(f"Unknown MA type '{self.ott_ma_type}', defaulting to VAR")
            return self._var_func(src, length)

    def _calculate_ott(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """
        Calculate Optimized Trend Tracker (OTT) indicator.

        The OTT is a trend-following indicator that provides dynamic
        support/resistance levels and trend direction signals.

        Formula:
            MAvg = selected moving average of source
            fark = MAvg * percent * 0.01
            longStop = MAvg - fark
            shortStop = MAvg + fark
            dir = trend direction (1 for up, -1 for down)
            MT = trailing stop level based on trend
            OTT = MT * (200 ± percent) / 200

        Args:
            df: DataFrame with OHLCV data (must have 'close' column).

        Returns:
            Dictionary with OTT results:
            {
                'OTT': OTT values,
                'MT': Trailing stop level,
                'Trend': Trend direction (1 or -1),
                'MAvg': Moving average used,
            }
        """
        src = df["close"]
        length = self.ott_period
        percent = self.ott_percent

        # Calculate base moving average
        MAvg = self._get_ma(src, length)

        # Calculate band offset (fark)
        fark = MAvg * percent * 0.01

        # Calculate initial long/short stops
        longStop = MAvg - fark
        shortStop = MAvg + fark

        # Calculate trailing stops with memory
        longStop_arr = pd.Series(index=src.index, dtype=float)
        shortStop_arr = pd.Series(index=src.index, dtype=float)

        longStop_arr.iloc[0] = longStop.iloc[0]
        shortStop_arr.iloc[0] = shortStop.iloc[0]

        for i in range(1, len(src)):
            # Long stop: max of current and previous (trailing)
            if MAvg.iloc[i] > longStop_arr.iloc[i - 1]:
                longStop_arr.iloc[i] = max(longStop.iloc[i], longStop_arr.iloc[i - 1])
            else:
                longStop_arr.iloc[i] = longStop.iloc[i]

            # Short stop: min of current and previous (trailing)
            if MAvg.iloc[i] < shortStop_arr.iloc[i - 1]:
                shortStop_arr.iloc[i] = min(shortStop.iloc[i], shortStop_arr.iloc[i - 1])
            else:
                shortStop_arr.iloc[i] = shortStop.iloc[i]

        # Calculate trend direction
        dir_arr = pd.Series(index=src.index, dtype=int)
        dir_arr.iloc[0] = 1

        for i in range(1, len(src)):
            prev_dir = dir_arr.iloc[i - 1]

            # Trend flips when MA crosses the opposite stop
            if prev_dir == -1 and MAvg.iloc[i] > shortStop_arr.iloc[i - 1]:
                dir_arr.iloc[i] = 1
            elif prev_dir == 1 and MAvg.iloc[i] < longStop_arr.iloc[i - 1]:
                dir_arr.iloc[i] = -1
            else:
                dir_arr.iloc[i] = prev_dir

        # Calculate MT (trailing stop level)
        MT = pd.Series(index=src.index, dtype=float)
        for i in range(len(src)):
            if dir_arr.iloc[i] == 1:
                MT.iloc[i] = longStop_arr.iloc[i]
            else:
                MT.iloc[i] = shortStop_arr.iloc[i]

        # Calculate OTT (offset from MT)
        OTT = pd.Series(index=src.index, dtype=float)
        for i in range(len(src)):
            if MAvg.iloc[i] > MT.iloc[i]:
                OTT.iloc[i] = MT.iloc[i] * (200 + percent) / 200
            else:
                OTT.iloc[i] = MT.iloc[i] * (200 - percent) / 200

        return {
            "OTT": OTT,
            "MT": MT,
            "Trend": dir_arr,
            "MAvg": MAvg,
        }

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLCV data.

        This method adds the following columns to the DataFrame:
        - EMA 10, 20, 50
        - MACD (12, 26, 9) with histogram
        - RSI (14)
        - OTT (Optimized Trend Tracker) with Trend and MT columns

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

        # Calculate OTT (Optimized Trend Tracker)
        try:
            ott_result = self._calculate_ott(df)
            df["OTT"] = ott_result["OTT"]
            df["OTT_MT"] = ott_result["MT"]
            df["OTT_Trend"] = ott_result["Trend"]
            df["OTT_MAvg"] = ott_result["MAvg"]
            logger.debug(
                f"Calculated OTT (period={self.ott_period}, percent={self.ott_percent}, "
                f"MA type={self.ott_ma_type})"
            )
        except Exception as e:
            logger.warning(f"OTT calculation failed: {e}")
            df["OTT"] = np.nan
            df["OTT_MT"] = np.nan
            df["OTT_Trend"] = np.nan
            df["OTT_MAvg"] = np.nan

        logger.debug(
            f"Calculated indicators: EMA{self.ema_periods}, "
            f"MACD({self.macd_fast},{self.macd_slow},{self.macd_signal}), "
            f"RSI({self.rsi_length}), OTT({self.ott_period})"
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
        - OTT: BULLISH if Trend == 1, BEARISH if Trend == -1

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
                'OTT': 'BULLISH',
                'values': {
                    'RSI': 55.4,
                    'MACD_hist': 1.2,
                    'EMA_10': 45000.0,
                    'EMA_20': 44800.0,
                    'EMA_50': 45500.0,
                    'OTT': 44900.0,
                    'OTT_Trend': 1,
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
                'OTT': SignalState.NEUTRAL,
                'values': {},
            }

        # Use confirmed close (second-to-last candle) to avoid incomplete candle signals
        # This ensures signals are based on closed, confirmed price action
        if len(df) >= 2:
            latest = df.iloc[-2]  # Last CONFIRMED candle (closed)
            current_candle = df.iloc[-1]  # Current (incomplete) candle
            logger.debug(f"Using confirmed close from candle index -2 (current: -1)")
        else:
            latest = df.iloc[-1]  # Fallback to last candle if only 1 candle
            current_candle = df.iloc[-1]
            logger.debug(f"Using last candle (insufficient data for confirmed close)")

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
            else:
                # Add stability threshold (0.3% buffer) to prevent flip-flopping
                stability_threshold = 0.003  # 0.3%
                price_diff_pct = (close_price - ema_value) / ema_value
                
                if price_diff_pct > stability_threshold:
                    signals[signal_name] = SignalState.BULLISH
                    values[signal_name.replace('MA', 'EMA_')] = float(ema_value)
                elif price_diff_pct < -stability_threshold:
                    signals[signal_name] = SignalState.BEARISH
                    values[signal_name.replace('MA', 'EMA_')] = float(ema_value)
                else:
                    # Price too close to EMA - maintain previous bias or use larger trend
                    # For stability, treat as slightly bullish if above, bearish if below
                    signals[signal_name] = SignalState.BULLISH if close_price >= ema_value else SignalState.BEARISH
                    values[signal_name.replace('MA', 'EMA_')] = float(ema_value)

        # Evaluate MACD Histogram
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        macd_hist = latest.get(macd_hist_col)

        # Handle insufficient data for MACD
        if macd_hist is None or pd.isna(macd_hist):
            signals["MACD"] = SignalState.NEUTRAL
            values["MACD_hist"] = None
            logger.debug("MACD histogram is NaN - insufficient data")
        else:
            # Add stability threshold to prevent flip-flopping near zero
            macd_threshold = 0.0001 * close_price  # Small threshold relative to price
            
            if macd_hist > macd_threshold:
                signals["MACD"] = SignalState.BULLISH
                values["MACD_hist"] = float(macd_hist)
            elif macd_hist < -macd_threshold:
                signals["MACD"] = SignalState.BEARISH
                values["MACD_hist"] = float(macd_hist)
            else:
                # Histogram too close to zero - use trend bias
                signals["MACD"] = SignalState.BULLISH if macd_hist >= 0 else SignalState.BEARISH
                values["MACD_hist"] = float(macd_hist)

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

        # Evaluate OTT (Optimized Trend Tracker)
        ott_trend = latest.get("OTT_Trend")
        ott_value = latest.get("OTT")
        ott_mt = latest.get("OTT_MT")

        # Handle insufficient data for OTT
        if ott_trend is None or pd.isna(ott_trend) or ott_value is None or pd.isna(ott_value):
            signals["OTT"] = SignalState.NEUTRAL
            values["OTT"] = None
            values["OTT_Trend"] = None
            values["OTT_MT"] = None
            logger.debug("OTT is NaN - insufficient data")
        else:
            values["OTT"] = float(ott_value)
            values["OTT_Trend"] = int(ott_trend)
            values["OTT_MT"] = float(ott_mt) if ott_mt is not None and not pd.isna(ott_mt) else None

            # OTT signal: Trend == 1 is BULLISH, Trend == -1 is BEARISH
            if ott_trend == 1:
                signals["OTT"] = SignalState.BULLISH
            elif ott_trend == -1:
                signals["OTT"] = SignalState.BEARISH
            else:
                signals["OTT"] = SignalState.NEUTRAL

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
        # Now includes OTT alongside MA10, MA20, MA50, MACD, RSI
        signal_keys = ['MA10', 'MA20', 'MA50', 'MACD', 'RSI', 'OTT']

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
            "OTT": float(latest.get("OTT", 0)) if latest.get("OTT") is not None else None,
            "OTT_MT": float(latest.get("OTT_MT", 0)) if latest.get("OTT_MT") is not None else None,
            "OTT_Trend": int(latest.get("OTT_Trend", 0)) if latest.get("OTT_Trend") is not None else None,
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

        # Check OTT trend reversal warning
        ott_state = signal_states.get("OTT")
        if ott_state is not None:
            if position_type == PositionType.LONG and ott_state == SignalState.BEARISH:
                warnings.append("OTT trend bearish - consider exiting LONG")
            elif position_type == PositionType.SHORT and ott_state == SignalState.BULLISH:
                warnings.append("OTT trend bullish - consider exiting SHORT")

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
            "trend": {},
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

        # OTT summary
        ott_value = float(latest["OTT"]) if "OTT" in latest and not pd.isna(latest["OTT"]) else None
        ott_trend = int(latest["OTT_Trend"]) if "OTT_Trend" in latest and not pd.isna(latest["OTT_Trend"]) else None
        ott_mt = float(latest["OTT_MT"]) if "OTT_MT" in latest and not pd.isna(latest["OTT_MT"]) else None
        
        summary["trend"]["OTT"] = {
            "value": ott_value,
            "trend": ott_trend,
            "mt": ott_mt,
            "interpretation": "BULLISH" if ott_trend == 1 else "BEARISH" if ott_trend == -1 else "NEUTRAL",
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
