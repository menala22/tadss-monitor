"""
Higher Timeframe (HTF) Bias Detector for MTF Analysis.

This module detects the higher timeframe bias using price structure
and moving averages, following the MTF framework from multi_timeframe.md.

Key Rules:
- Use structural tools only (MA, price structure, S/R)
- Do NOT use oscillators (RSI, MACD) on HTF — they lag too much
- Require 2+ confirmed HH/HL or LH/LL sequences for trend confirmation
- A single decisive close beyond prior swing invalidates the trend

Note: Uses EMA 20/50 instead of SMA 50/200 for faster reaction time
and better suitability for crypto/forex 24/7 markets.
"""

import logging
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    HTFBias,
    MTFDirection,
    PriceStructure,
    PriceVsSMA,
    SMASlope,
    SupportResistanceLevel,
    SwingPoint,
    LevelType,
    LevelStrength,
)

logger = logging.getLogger(__name__)


class HTFBiasDetector:
    """
    Detect higher timeframe bias using price structure and EMAs.

    The HTF bias determines the directional bias for all trading decisions.
    Only trade in the direction of the HTF bias.

    Attributes:
        ema20_period: Period for 20 EMA (default 20).
        ema50_period: Period for 50 EMA (default 50).
        swing_window: Window size for swing point detection (default 5).
        min_swing_strength: Minimum strength for swing point inclusion (default 0.5).
    """

    def __init__(
        self,
        ema20_period: int = 20,
        ema50_period: int = 50,
        swing_window: int = 5,
        min_swing_strength: float = 0.5,
    ):
        """
        Initialize HTF bias detector.

        Args:
            ema20_period: Period for 20 EMA.
            ema50_period: Period for 50 EMA.
            swing_window: Window size for swing point detection.
            min_swing_strength: Minimum strength for swing points.
        """
        self.ema20_period = ema20_period
        self.ema50_period = ema50_period
        self.swing_window = swing_window
        self.min_swing_strength = min_swing_strength

    def detect_bias(self, df: pd.DataFrame) -> HTFBias:
        """
        Analyze HTF and return bias assessment.

        Steps:
        1. Identify swing highs/lows (require 2+ sequences)
        2. Calculate 20 EMA and 50 EMA
        3. Determine EMA slopes
        4. Check price position vs MAs
        5. Identify key S/R levels
        6. Return bias with confidence score

        Args:
            df: DataFrame with OHLCV data (must have 'close', 'high', 'low').

        Returns:
            HTFBias object with directional bias and confidence.

        Example:
            >>> detector = HTFBiasDetector()
            >>> bias = detector.detect_bias(ohlcv_df)
            >>> print(bias.direction)
            MTFDirection.BULLISH
        """
        if df.empty or len(df) < self.ema20_period:
            logger.warning(f"Insufficient data for HTF bias (need {self.ema20_period} candles, got {len(df)})")
            return HTFBias(
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                warning=f"Insufficient data: have {len(df)} candles, need {self.ema20_period}",
            )

        # Ensure required columns exist
        df = df.copy()
        required_cols = {"close", "high", "low"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            missing = required_cols - available_cols
            logger.error(f"Missing required columns: {missing}")
            return HTFBias(
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                warning=f"Missing columns: {missing}",
            )

        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})

        # Step 1: Find swing points
        swing_points = self._find_swing_points(df, window=self.swing_window)

        # Step 2: Detect price structure from swings
        price_structure = self._detect_price_structure(swing_points)

        # Step 3: Calculate EMAs
        ema20 = self._calculate_ema(df["close"], self.ema20_period)
        ema50 = self._calculate_ema(df["close"], self.ema50_period)

        # Step 4: Determine EMA slopes
        ema20_slope = self._calculate_sma_slope(ema20)
        ema50_slope = self._calculate_sma_slope(ema50)

        # Step 5: Check price position vs EMAs
        current_price = df["close"].iloc[-1]
        price_vs_ema20 = self._price_vs_sma(current_price, ema20.iloc[-1])
        price_vs_ema50 = self._price_vs_sma(current_price, ema50.iloc[-1])

        # Step 6: Identify key S/R levels
        key_levels = self._identify_key_levels(df, swing_points)

        # Step 7: Determine direction and confidence
        direction, confidence = self._determine_direction_and_confidence(
            price_structure=price_structure,
            sma50_slope=ema20_slope,  # Reusing parameter name for EMA slope
            sma200_slope=ema50_slope,  # Reusing parameter name for EMA slope
            price_vs_sma50=price_vs_ema20,  # Reusing parameter name for EMA
            price_vs_sma200=price_vs_ema50,  # Reusing parameter name for EMA
        )

        return HTFBias(
            direction=direction,
            confidence=confidence,
            price_structure=price_structure,
            sma50_slope=ema20_slope,
            price_vs_sma50=price_vs_ema20,
            price_vs_sma200=price_vs_ema50,
            key_levels=key_levels,
            swing_sequence=swing_points[-6:],  # Last 6 swings for context
        )

    def _find_swing_points(
        self,
        df: pd.DataFrame,
        window: int = 5,
    ) -> List[SwingPoint]:
        """
        Identify swing highs and lows using rolling window.

        A swing high is a high that is higher than the N candles before and after.
        A swing low is a low that is lower than the N candles before and after.

        Args:
            df: DataFrame with 'high' and 'low' columns.
            window: Number of candles on each side to compare.

        Returns:
            List of SwingPoint objects sorted by index.
        """
        swing_points = []

        # Need at least 2*window + 1 candles
        if len(df) < 2 * window + 1:
            logger.debug(f"Insufficient data for swing detection (need {2*window+1} candles)")
            return swing_points

        highs = df["high"].values
        lows = df["low"].values
        timestamps = df.index if hasattr(df.index, "tolist") else range(len(df))

        for i in range(window, len(df) - window):
            # Check for swing high
            left_highs = highs[i - window : i]
            right_highs = highs[i + 1 : i + window + 1]

            if len(left_highs) > 0 and len(right_highs) > 0:
                is_swing_high = (
                    highs[i] > left_highs.max() and
                    highs[i] > right_highs.max()
                )

                if is_swing_high:
                    # Calculate strength based on how much higher than neighbors
                    left_diff = (highs[i] - left_highs.max()) / highs[i]
                    right_diff = (highs[i] - right_highs.max()) / highs[i]
                    strength = min(1.0, (left_diff + right_diff) * 10)

                    if strength >= self.min_swing_strength:
                        swing_points.append(SwingPoint(
                            price=float(highs[i]),
                            index=i,
                            timestamp=str(timestamps[i]),
                            swing_type="HIGH",
                            strength=float(strength),
                        ))

            # Check for swing low
            left_lows = lows[i - window : i]
            right_lows = lows[i + 1 : i + window + 1]

            if len(left_lows) > 0 and len(right_lows) > 0:
                is_swing_low = (
                    lows[i] < left_lows.min() and
                    lows[i] < right_lows.min()
                )

                if is_swing_low:
                    # Calculate strength based on how much lower than neighbors
                    left_diff = (left_lows.min() - lows[i]) / lows[i]
                    right_diff = (right_lows.min() - lows[i]) / lows[i]
                    strength = min(1.0, (left_diff + right_diff) * 10)

                    if strength >= self.min_swing_strength:
                        swing_points.append(SwingPoint(
                            price=float(lows[i]),
                            index=i,
                            timestamp=str(timestamps[i]),
                            swing_type="LOW",
                            strength=float(strength),
                        ))

        logger.debug(f"Found {len(swing_points)} swing points")
        return swing_points

    def _detect_price_structure(
        self,
        swings: List[SwingPoint],
    ) -> PriceStructure:
        """
        Classify price structure from swing sequence.

        Uptrend: 2+ sequential HH/HL pairs, second HL > first HL
        Downtrend: 2+ sequential LH/LL pairs
        Range: oscillating between defined levels

        Args:
            swings: List of SwingPoint objects.

        Returns:
            PriceStructure enum value.
        """
        if len(swings) < 4:
            logger.debug("Insufficient swings for structure detection (need 4+)")
            return PriceStructure.RANGE

        # Separate highs and lows
        highs = [s for s in swings if s.swing_type == "HIGH"]
        lows = [s for s in swings if s.swing_type == "LOW"]

        # Need at least 2 highs and 2 lows
        if len(highs) < 2 or len(lows) < 2:
            return PriceStructure.RANGE

        # Check for uptrend (HH/HL sequence)
        # Sort by index to get chronological order
        highs_sorted = sorted(highs, key=lambda x: x.index)
        lows_sorted = sorted(lows, key=lambda x: x.index)

        # Check last 2-3 highs for HH pattern
        hh_count = 0
        for i in range(1, len(highs_sorted)):
            if highs_sorted[i].price > highs_sorted[i - 1].price:
                hh_count += 1

        # Check last 2-3 lows for HL pattern
        hl_count = 0
        for i in range(1, len(lows_sorted)):
            if lows_sorted[i].price > lows_sorted[i - 1].price:
                hl_count += 1

        # Check for downtrend (LH/LL sequence)
        lh_count = 0
        for i in range(1, len(highs_sorted)):
            if highs_sorted[i].price < highs_sorted[i - 1].price:
                lh_count += 1

        ll_count = 0
        for i in range(1, len(lows_sorted)):
            if lows_sorted[i].price < lows_sorted[i - 1].price:
                ll_count += 1

        # Determine structure
        # Uptrend: at least 2 HH and 2 HL in recent swings
        if hh_count >= 2 and hl_count >= 2:
            logger.debug("Price structure: UPTREND (HH/HL)")
            return PriceStructure.UPTREND

        # Downtrend: at least 2 LH and 2 LL in recent swings
        if lh_count >= 2 and ll_count >= 2:
            logger.debug("Price structure: DOWNTREND (LH/LL)")
            return PriceStructure.DOWNTREND

        # Otherwise, range
        logger.debug("Price structure: RANGE")
        return PriceStructure.RANGE

    def _calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average.

        Args:
            series: Price series.
            period: SMA period.

        Returns:
            SMA series.
        """
        return series.rolling(window=period).mean()

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            series: Price series.
            period: EMA period.

        Returns:
            EMA series.
        """
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_sma_slope(self, sma_series: pd.Series) -> SMASlope:
        """
        Determine SMA slope direction.

        Compares the last 10 SMA values to determine slope.

        Args:
            sma_series: SMA series.

        Returns:
            SMASlope enum value (UP, DOWN, FLAT).
        """
        if len(sma_series) < 10 or sma_series.iloc[-10:].isna().any():
            return SMASlope.FLAT

        # Calculate slope using linear regression
        last_10 = sma_series.iloc[-10:].values
        x = np.arange(10)

        # Simple slope calculation
        slope = (last_10[-1] - last_10[0]) / last_10[0]

        # Threshold for flat (0.5% change)
        threshold = 0.005

        if slope > threshold:
            return SMASlope.UP
        elif slope < -threshold:
            return SMASlope.DOWN
        else:
            return SMASlope.FLAT

    def _price_vs_sma(self, price: float, sma_value: float) -> PriceVsSMA:
        """
        Determine price position relative to SMA.

        Args:
            price: Current price.
            sma_value: SMA value.

        Returns:
            PriceVsSMA enum value.
        """
        if pd.isna(sma_value):
            return PriceVsSMA.BELOW

        diff_pct = (price - sma_value) / sma_value

        # Threshold for "AT" (within 0.5%)
        threshold = 0.005

        if diff_pct > threshold:
            return PriceVsSMA.ABOVE
        elif diff_pct < -threshold:
            return PriceVsSMA.BELOW
        else:
            return PriceVsSMA.AT

    def _identify_key_levels(
        self,
        df: pd.DataFrame,
        swings: List[SwingPoint],
    ) -> List[SupportResistanceLevel]:
        """
        Identify key support and resistance levels from swing points.

        Args:
            df: DataFrame with OHLCV data.
            swings: List of SwingPoint objects.

        Returns:
            List of SupportResistanceLevel objects.
        """
        if not swings:
            return []

        levels = []
        current_price = df["close"].iloc[-1]

        # Group swings by price proximity (within 1%)
        price_groups = []
        for swing in swings:
            grouped = False
            for group in price_groups:
                avg_price = sum(s.price for s in group) / len(group)
                if abs(swing.price - avg_price) / avg_price < 0.01:
                    group.append(swing)
                    grouped = True
                    break
            if not grouped:
                price_groups.append([swing])

        # Create levels from groups
        for group in price_groups:
            avg_price = sum(s.price for s in group) / len(group)
            touch_count = len(group)
            max_strength = max(s.strength for s in group)

            # Determine if support or resistance based on price position
            if avg_price < current_price:
                level_type = LevelType.SUPPORT
            else:
                level_type = LevelType.RESISTANCE

            # Determine strength
            if touch_count >= 3 or max_strength >= 0.8:
                strength = LevelStrength.STRONG
            elif touch_count >= 2 or max_strength >= 0.6:
                strength = LevelStrength.MEDIUM
            else:
                strength = LevelStrength.WEAK

            levels.append(SupportResistanceLevel(
                price=avg_price,
                level_type=level_type,
                strength=strength,
                touch_count=touch_count,
                last_tested=group[-1].timestamp,
            ))

        # Sort by strength and return top levels
        levels.sort(key=lambda x: (x.strength.value, x.touch_count), reverse=True)
        return levels[:5]  # Return top 5 levels

    def _determine_direction_and_confidence(
        self,
        price_structure: PriceStructure,
        sma50_slope: SMASlope,
        sma200_slope: SMASlope,
        price_vs_sma50: PriceVsSMA,
        price_vs_sma200: PriceVsSMA,
    ) -> Tuple[MTFDirection, float]:
        """
        Determine HTF direction and confidence score.

        Scoring:
        - Price structure (HH/HL or LH/LL): 40%
        - SMA50 slope: 20%
        - SMA200 slope: 15%
        - Price vs SMA50: 15%
        - Price vs SMA200: 10%

        Args:
            price_structure: Detected price structure.
            sma50_slope: 50 SMA slope.
            sma200_slope: 200 SMA slope.
            price_vs_sma50: Price position vs 50 SMA.
            price_vs_sma200: Price position vs 200 SMA.

        Returns:
            Tuple of (direction, confidence_score).
        """
        bullish_score = 0.0
        bearish_score = 0.0

        # Price structure (40%)
        if price_structure == PriceStructure.UPTREND:
            bullish_score += 0.4
        elif price_structure == PriceStructure.DOWNTREND:
            bearish_score += 0.4

        # SMA50 slope (20%)
        if sma50_slope == SMASlope.UP:
            bullish_score += 0.2
        elif sma50_slope == SMASlope.DOWN:
            bearish_score += 0.2

        # SMA200 slope (15%)
        if sma200_slope == SMASlope.UP:
            bullish_score += 0.15
        elif sma200_slope == SMASlope.DOWN:
            bearish_score += 0.15

        # Price vs SMA50 (15%)
        if price_vs_sma50 == PriceVsSMA.ABOVE:
            bullish_score += 0.15
        elif price_vs_sma50 == PriceVsSMA.BELOW:
            bearish_score += 0.15

        # Price vs SMA200 (10%)
        if price_vs_sma200 == PriceVsSMA.ABOVE:
            bullish_score += 0.10
        elif price_vs_sma200 == PriceVsSMA.BELOW:
            bearish_score += 0.10

        # Determine direction
        if bullish_score > bearish_score:
            direction = MTFDirection.BULLISH
            confidence = bullish_score
        elif bearish_score > bullish_score:
            direction = MTFDirection.BEARISH
            confidence = bearish_score
        else:
            direction = MTFDirection.NEUTRAL
            confidence = 0.0

        logger.debug(
            f"HTF bias: {direction.value} (confidence={confidence:.2f}, "
            f"bullish={bullish_score:.2f}, bearish={bearish_score:.2f})"
        )

        return direction, confidence


def detect_htf_bias(
    df: pd.DataFrame,
    sma50_period: int = 50,
    sma200_period: int = 200,
    swing_window: int = 5,
) -> HTFBias:
    """
    Convenience function to detect HTF bias.

    Args:
        df: DataFrame with OHLCV data.
        sma50_period: 50 SMA period.
        sma200_period: 200 SMA period.
        swing_window: Swing detection window.

    Returns:
        HTFBias object.

    Example:
        >>> from src.data_fetcher import fetch_ohlcv
        >>> df = fetch_ohlcv('BTC/USDT', '1d')
        >>> bias = detect_htf_bias(df)
        >>> print(f"HTF Bias: {bias.direction.value} ({bias.confidence:.2f})")
    """
    detector = HTFBiasDetector(
        sma50_period=sma50_period,
        sma200_period=sma200_period,
        swing_window=swing_window,
    )
    return detector.detect_bias(df)
