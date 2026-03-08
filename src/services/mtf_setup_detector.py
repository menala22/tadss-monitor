"""
Middle Timeframe (MTF) Setup Detector for MTF Analysis.

This module identifies tradeable setups on the middle timeframe,
following the MTF framework from multi_timeframe.md.

Setup Types:
- PULLBACK: Pullback to EMA10/EMA20 in trending market
- DIVERGENCE: RSI divergence at key levels
- BREAKOUT: Breakout from consolidation with volume
- CONSOLIDATION: Flag, pennant, triangle patterns
- RANGE_LOW/RANGE_HIGH: Range boundary setups

Note: Uses EMA 10/20 instead of SMA 20/50 for faster reaction time
and better pullback detection in crypto/forex markets.
"""

import logging
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    DivergenceType,
    HTFBias,
    LevelType,
    MTFDirection,
    MTFSetup,
    PriceStructure,
    PullbackSetup,
    SetupType,
    SupportResistanceLevel,
)
from src.services.mtf_bias_detector import HTFBiasDetector

logger = logging.getLogger(__name__)


class MTFSetupDetector:
    """
    Identify tradeable setups on middle timeframe.

    The MTF setup identifies the specific tradeable pattern within
    the HTF bias direction.

    Attributes:
        rsi_length: RSI calculation period (default 14).
        ema10_period: 10 EMA period.
        ema20_period: 20 EMA period.
        volume_ma_period: Volume moving average period (default 20).
    """

    def __init__(
        self,
        rsi_length: int = 14,
        ema10_period: int = 10,
        ema20_period: int = 20,
        volume_ma_period: int = 20,
    ):
        """
        Initialize MTF setup detector.

        Args:
            rsi_length: RSI calculation period.
            ema10_period: 10 EMA period.
            ema20_period: 20 EMA period.
            volume_ma_period: Volume moving average period.
        """
        self.rsi_length = rsi_length
        self.ema10_period = ema10_period
        self.ema20_period = ema20_period
        self.volume_ma_period = volume_ma_period

    def detect_setup(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
    ) -> MTFSetup:
        """
        Identify setup in direction of HTF bias.

        If HTF bullish: look for pullback setups, bullish divergence
        If HTF bearish: look for rally setups, bearish divergence
        If HTF neutral (RANGE): use Range Protocol

        Args:
            df: DataFrame with OHLCV data.
            htf_bias: Higher timeframe bias assessment.

        Returns:
            MTFSetup object with setup type and confidence.

        Example:
            >>> detector = MTFSetupDetector()
            >>> htf_bias = HTFBias(direction=MTFDirection.BULLISH, ...)
            >>> setup = detector.detect_setup(ohlcv_df, htf_bias)
            >>> print(setup.setup_type)
            SetupType.PULLBACK
        """
        if df.empty or len(df) < self.ema20_period:
            logger.warning(f"Insufficient data for MTF setup (need {self.ema20_period} candles)")
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                warning=f"Insufficient data: have {len(df)} candles, need {self.ema20_period}",
            )

        # Ensure required columns exist
        df = df.copy()
        required_cols = {"close", "high", "low"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                warning=f"Missing columns: {required_cols - available_cols}",
            )

        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})

        # Calculate indicators (using EMA instead of SMA)
        ema10 = df["close"].ewm(span=self.ema10_period, adjust=False).mean()
        ema20 = df["close"].ewm(span=self.ema20_period, adjust=False).mean()
        rsi = self._calculate_rsi(df["close"], self.rsi_length)

        # Add volume MA if volume exists
        volume_ma = None
        if "volume" in df.columns:
            volume_ma = df["volume"].rolling(window=self.volume_ma_period).mean()

        current_price = df["close"].iloc[-1]

        # Check for range setup first
        if htf_bias.price_structure == PriceStructure.RANGE:
            return self._detect_range_setup(df, htf_bias, current_price)

        # Detect pullback setup
        pullback_setup = self._detect_pullback(
            df=df,
            ema10=ema10,
            ema20=ema20,
            rsi=rsi,
            volume_ma=volume_ma,
            htf_direction=htf_bias.direction,
        )

        # Detect divergence
        divergence = self._detect_divergence(df, rsi)

        # Detect consolidation/breakout
        consolidation = self._detect_consolidation(df)

        # Determine best setup based on confidence
        return self._select_best_setup(
            pullback_setup=pullback_setup,
            divergence=divergence,
            consolidation=consolidation,
            htf_bias=htf_bias,
            current_price=current_price,
            ema10=ema10,
            ema20=ema20,
        )

    def _calculate_rsi(self, series: pd.Series, length: int) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).

        Args:
            series: Price series (close).
            length: RSI period.

        Returns:
            RSI series.
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()

        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(100)  # loss == 0 means all gains → RSI = 100
        return rsi

    def _detect_pullback(
        self,
        df: pd.DataFrame,
        ema10: pd.Series,
        ema20: pd.Series,
        rsi: pd.Series,
        volume_ma: Optional[pd.Series],
        htf_direction: MTFDirection,
    ) -> Optional[PullbackSetup]:
        """
        Detect pullback to EMA.

        Criteria:
        - Price approaching 10 EMA or 20 EMA
        - RSI(14) approaching 40 (in uptrend) without breaking
        - Volume declining during pullback (healthy)

        Args:
            df: DataFrame with OHLCV data.
            ema10: 10 EMA series.
            ema20: 20 EMA series.
            rsi: RSI series.
            volume_ma: Volume moving average.
            htf_direction: HTF bias direction.

        Returns:
            PullbackSetup if detected, None otherwise.
        """
        current_price = df["close"].iloc[-1]
        current_ema10 = ema10.iloc[-1]
        current_ema20 = ema20.iloc[-1]
        current_rsi = rsi.iloc[-1]

        if pd.isna(current_ema10) or pd.isna(current_ema20) or pd.isna(current_rsi):
            return None

        # Determine which EMA price is approaching
        approaching_sma = None
        distance_to_sma_pct = 0.0

        # Check 10 EMA proximity
        dist_10 = abs(current_price - current_ema10) / current_ema10
        if dist_10 < 0.02:  # Within 2%
            approaching_sma = 10
            distance_to_sma_pct = dist_10 * 100

        # Check 20 EMA proximity (prefer if closer)
        dist_20 = abs(current_price - current_ema20) / current_ema20
        if dist_20 < 0.03 and dist_20 < dist_10:
            approaching_sma = 20
            distance_to_sma_pct = dist_20 * 100

        if approaching_sma is None:
            return None

        # Check RSI condition based on HTF direction
        rsi_approaching_40 = False
        if htf_direction == MTFDirection.BULLISH:
            # In uptrend, RSI should be approaching 40 from above
            rsi_approaching_40 = 35 <= current_rsi <= 50
        elif htf_direction == MTFDirection.BEARISH:
            # In downtrend, RSI should be approaching 60 from below
            rsi_approaching_40 = 50 <= current_rsi <= 65

        # Check volume declining (if available)
        volume_declining = False
        if volume_ma is not None and "volume" in df.columns:
            recent_volume = df["volume"].iloc[-5:].mean()
            if not pd.isna(volume_ma.iloc[-1]):
                volume_declining = recent_volume < volume_ma.iloc[-1]

        return PullbackSetup(
            approaching_sma=approaching_sma,
            distance_to_sma_pct=distance_to_sma_pct,
            rsi_level=float(current_rsi),
            rsi_approaching_40=rsi_approaching_40,
            volume_declining=volume_declining,
        )

    def _detect_divergence(
        self,
        df: pd.DataFrame,
        rsi: pd.Series,
    ) -> Optional[DivergenceType]:
        """
        Detect RSI divergence (simplified version).

        Bullish: price makes new low, RSI makes higher low
        Bearish: price makes new high, RSI makes lower high

        Note: Full divergence detection is in divergence_detector.py.
        This is a simplified version for MTF setup detection.

        Args:
            df: DataFrame with OHLCV data.
            rsi: RSI series.

        Returns:
            DivergenceType if detected, None otherwise.
        """
        if len(df) < 50:
            return None

        # Find recent price swings (last 20-50 candles)
        lookback = min(50, len(df))
        recent_high = df["high"].iloc[-lookback:].max()
        recent_low = df["low"].iloc[-lookback:].min()

        # Check if price made new high/low recently
        price_new_high = df["high"].iloc[-1] >= recent_high * 0.999
        price_new_low = df["low"].iloc[-1] <= recent_low * 1.001

        # Get RSI values at price extremes
        current_rsi = rsi.iloc[-1]
        rsi_lookback = rsi.iloc[-lookback:]
        rsi_high = rsi_lookback.max()
        rsi_low = rsi_lookback.min()

        # Bullish divergence: price new low, RSI not confirming
        if price_new_low and current_rsi > rsi_low * 1.02:
            logger.debug("Potential bullish divergence detected")
            return DivergenceType.REGULAR_BULLISH

        # Bearish divergence: price new high, RSI not confirming
        if price_new_high and current_rsi < rsi_high * 0.98:
            logger.debug("Potential bearish divergence detected")
            return DivergenceType.REGULAR_BEARISH

        return None

    def _detect_consolidation(
        self,
        df: pd.DataFrame,
    ) -> Optional[Literal["FLAG", "PENNANT", "TRIANGLE", "RECTANGLE"]]:
        """
        Detect consolidation patterns.

        Patterns:
        - FLAG: Parallel channel against trend
        - PENNANT: Converging triangle after strong move
        - TRIANGLE: Symmetrical, ascending, or descending
        - RECTANGLE: Horizontal support/resistance

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Pattern type if detected, None otherwise.
        """
        if len(df) < 20:
            return None

        # Simple consolidation detection: low volatility
        recent_closes = df["close"].iloc[-10:]
        volatility = recent_closes.std() / recent_closes.mean()

        # Check if volatility is significantly lower than recent history
        if len(df) >= 30:
            historical_volatility = df["close"].iloc[-30:-10].std() / df["close"].iloc[-30:-10].mean()
            if volatility < historical_volatility * 0.5:
                # Low volatility = potential consolidation
                # For now, classify as generic consolidation
                return "RECTANGLE"

        return None

    def _detect_range_setup(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
        current_price: float,
    ) -> MTFSetup:
        """
        Detect range boundary setups (Range Protocol).

        When HTF is in range, look for:
        - Long at range low support
        - Short at range high resistance

        Args:
            df: DataFrame with OHLCV data.
            htf_bias: HTF bias (should be RANGE).
            current_price: Current price.

        Returns:
            MTFSetup for range boundary.
        """
        # Identify range boundaries from HTF key levels
        range_low = None
        range_high = None

        for level in htf_bias.key_levels:
            if level.level_type == LevelType.SUPPORT:
                if range_low is None or level.price < range_low:
                    range_low = level.price
            elif level.level_type == LevelType.RESISTANCE:
                if range_high is None or level.price > range_high:
                    range_high = level.price

        # Fallback: use recent high/low
        if range_low is None or range_high is None:
            lookback = min(50, len(df))
            range_low = df["low"].iloc[-lookback:].min()
            range_high = df["high"].iloc[-lookback:].max()

        # Check if price is at range boundary
        dist_to_low = (current_price - range_low) / range_low
        dist_to_high = (range_high - current_price) / range_high

        tolerance = 0.01  # 1% tolerance

        if dist_to_low < tolerance:
            # At range low - potential long setup
            return MTFSetup(
                setup_type=SetupType.RANGE_LOW,
                direction=MTFDirection.BULLISH,
                confidence=0.6 if dist_to_low < 0.005 else 0.5,
                warning="Range Protocol: at support boundary",
            )
        elif dist_to_high < tolerance:
            # At range high - potential short setup
            return MTFSetup(
                setup_type=SetupType.RANGE_HIGH,
                direction=MTFDirection.BEARISH,
                confidence=0.6 if dist_to_high < 0.005 else 0.5,
                warning="Range Protocol: at resistance boundary",
            )
        else:
            # In middle of range - no setup
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                warning="Range Protocol: price in middle third, no setup",
            )

    def _select_best_setup(
        self,
        pullback_setup: Optional[PullbackSetup],
        divergence: Optional[DivergenceType],
        consolidation: Optional[str],
        htf_bias: HTFBias,
        current_price: float,
        ema10: pd.Series,
        ema20: pd.Series,
    ) -> MTFSetup:
        """
        Select the best setup from detected patterns.

        Priority:
        1. Pullback with RSI confirmation (highest confidence)
        2. Divergence at key level
        3. Consolidation breakout
        4. Default to consolidation (no clear setup)

        Args:
            pullback_setup: Detected pullback setup.
            divergence: Detected divergence.
            consolidation: Detected consolidation pattern.
            htf_bias: HTF bias.
            current_price: Current price.
            ema10: 10 EMA series.
            ema20: 20 EMA series.

        Returns:
            MTFSetup with best setup type.
        """
        # Determine setup direction from HTF bias
        setup_direction = htf_bias.direction

        # Evaluate pullback
        if pullback_setup is not None:
            confidence = 0.5

            # Increase confidence if RSI confirms
            if pullback_setup.rsi_approaching_40:
                confidence += 0.2

            # Increase confidence if volume confirms
            if pullback_setup.volume_declining:
                confidence += 0.1

            # Determine EMA action
            ema10_action = "NONE"
            ema20_action = "NONE"

            current_ema10 = ema10.iloc[-1]
            current_ema20 = ema20.iloc[-1]

            if not pd.isna(current_ema10):
                if setup_direction == MTFDirection.BULLISH and current_price > current_ema10:
                    ema10_action = "SUPPORT"
                elif setup_direction == MTFDirection.BEARISH and current_price < current_ema10:
                    ema10_action = "RESISTANCE"

            if not pd.isna(current_ema20):
                if setup_direction == MTFDirection.BULLISH and current_price > current_ema20:
                    ema20_action = "SUPPORT"
                elif setup_direction == MTFDirection.BEARISH and current_price < current_ema20:
                    ema20_action = "RESISTANCE"

            return MTFSetup(
                setup_type=SetupType.PULLBACK,
                direction=setup_direction,
                confidence=min(confidence, 0.9),
                sma20_action=ema10_action,  # Keeping field name for backwards compatibility
                sma50_action=ema20_action,  # Keeping field name for backwards compatibility
                rsi_divergence=None,
                pullback_details=pullback_setup,
            )

        # Evaluate divergence
        if divergence is not None:
            if divergence == DivergenceType.REGULAR_BULLISH:
                return MTFSetup(
                    setup_type=SetupType.DIVERGENCE,
                    direction=MTFDirection.BULLISH,
                    confidence=0.6,
                    rsi_divergence=divergence,
                )
            else:
                return MTFSetup(
                    setup_type=SetupType.DIVERGENCE,
                    direction=MTFDirection.BEARISH,
                    confidence=0.6,
                    rsi_divergence=divergence,
                )

        # Evaluate consolidation
        if consolidation is not None:
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=setup_direction,
                confidence=0.4,
                consolidation_pattern=consolidation,
            )

        # No clear setup
        return MTFSetup(
            setup_type=SetupType.CONSOLIDATION,
            direction=MTFDirection.NEUTRAL,
            confidence=0.0,
            warning="No clear MTF setup detected",
        )


def detect_mtf_setup(
    df: pd.DataFrame,
    htf_bias: HTFBias,
    rsi_length: int = 14,
) -> MTFSetup:
    """
    Convenience function to detect MTF setup.

    Args:
        df: DataFrame with OHLCV data.
        htf_bias: Higher timeframe bias.
        rsi_length: RSI period.

    Returns:
        MTFSetup object.

    Example:
        >>> from src.data_fetcher import fetch_ohlcv
        >>> df = fetch_ohlcv('BTC/USDT', '4h')
        >>> htf_bias = detect_htf_bias(daily_df)
        >>> setup = detect_mtf_setup(df, htf_bias)
        >>> print(f"Setup: {setup.setup_type.value} ({setup.confidence:.2f})")
    """
    detector = MTFSetupDetector(rsi_length=rsi_length)
    return detector.detect_setup(df, htf_bias)
