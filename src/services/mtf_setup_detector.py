"""
MidTF (Middle Timeframe) Setup Detector for Multi-Timeframe (MTF) Analysis.

This module identifies tradeable setups on the middle timeframe (MidTF),
following the MTF framework from multi_timeframe.md.

Note: We use "MidTF" instead of "MTF" for the middle timeframe to avoid
confusion with "MTF" which refers to the overall Multi-Timeframe system.

UPGRADED SYSTEM (Layer 2): Context-Gated Setup Detection

Setup detection is now gated by MidTF context classification:
- TRENDING_PULLBACK: PULLBACK setups valid
- TRENDING_EXTENSION: NO setups (wait for pullback)
- BREAKING_OUT: BREAKOUT setups valid
- CONSOLIDATING: RANGE setups valid
- REVERSING: DIVERGENCE setups valid

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
    MTFContext,
    MTFDirection,
    MTFSetup,
    MTFContextResult,
    PriceStructure,
    PullbackSetup,
    PullbackQualityScore,
    SetupType,
    SupportResistanceLevel,
    VALID_SETUPS_BY_CONTEXT,
)
from src.services.mtf_bias_detector import HTFBiasDetector
from src.services.mtf_context_classifier import MTFContextClassifier, classify_mtf_context
from src.services.pullback_quality_scorer import PullbackQualityScorer, score_pullback_quality
from src.indicators.technical_indicators import compute_atr

logger = logging.getLogger(__name__)


class MTFSetupDetector:
    """
    Identify tradeable setups on MidTF (middle timeframe).

    The MidTF setup identifies the specific tradeable pattern within
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
        context_classifier: Optional[MTFContextClassifier] = None,
        quality_scorer: Optional[PullbackQualityScorer] = None,
    ):
        """
        Initialize MTF setup detector.

        Args:
            rsi_length: RSI calculation period.
            ema10_period: 10 EMA period.
            ema20_period: 20 EMA period.
            volume_ma_period: Volume moving average period.
            context_classifier: MTF context classifier (Layer 1).
            quality_scorer: Pullback quality scorer (Layer 3).
        """
        self.rsi_length = rsi_length
        self.ema10_period = ema10_period
        self.ema20_period = ema20_period
        self.volume_ma_period = volume_ma_period
        self.context_classifier = context_classifier or MTFContextClassifier()
        self.quality_scorer = quality_scorer or PullbackQualityScorer()

    def detect_setup(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
    ) -> MTFSetup:
        """
        Identify setup in direction of HTF bias.

        UPGRADED: Layer 2 - Context-Gated Setup Detection

        Steps:
        1. Classify MidTF context (Layer 1)
        2. Get valid setups for context from VALID_SETUPS_BY_CONTEXT
        3. If no valid setups (e.g., TRENDING_EXTENSION), return WAIT
        4. Only run detectors for valid setup types
        5. Score pullback quality if applicable (Layer 3)

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

        # LAYER 1: Classify MTF context
        context_result = self.context_classifier.classify(df, htf_bias)
        logger.info(f"MTF Context: {context_result.context.value} (ADX={context_result.adx:.1f}, Dist={context_result.distance_from_ema_atr:.2f} ATR)")

        # LAYER 2: Context-gated setup detection
        valid_setup_types = VALID_SETUPS_BY_CONTEXT.get(context_result.context, [])
        
        if not valid_setup_types:
            # No valid setups for this context - WAIT
            logger.info(f"No valid setups for context {context_result.context.value} - WAIT")
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=MTFDirection.NEUTRAL,
                confidence=0.0,
                mtf_context=context_result.context,
                warning=f"No valid setups for context {context_result.context.value}: {context_result.reasoning}",
            )

        logger.info(f"Valid setups for {context_result.context.value}: {[s.value for s in valid_setup_types]}")

        # Calculate indicators (using EMA instead of SMA)
        ema10 = df["close"].ewm(span=self.ema10_period, adjust=False).mean()
        ema20 = df["close"].ewm(span=self.ema20_period, adjust=False).mean()
        rsi = self._calculate_rsi(df["close"], self.rsi_length)

        # Add volume MA if volume exists
        volume_ma = None
        if "volume" in df.columns:
            volume_ma = df["volume"].rolling(window=self.volume_ma_period).mean()

        current_price = df["close"].iloc[-1]

        # Detect setups based on context
        pullback_setup = None
        divergence = None
        consolidation = None
        range_setup = None

        # Only run detectors for valid setup types
        if SetupType.PULLBACK in valid_setup_types:
            pullback_setup = self._detect_pullback(
                df=df,
                ema10=ema10,
                ema20=ema20,
                rsi=rsi,
                volume_ma=volume_ma,
                htf_direction=htf_bias.direction,
            )

        if SetupType.DIVERGENCE in valid_setup_types:
            divergence = self._detect_divergence(df, rsi)

        if SetupType.BREAKOUT in valid_setup_types or SetupType.CONSOLIDATION in valid_setup_types:
            consolidation = self._detect_consolidation(df)

        if SetupType.RANGE_LOW in valid_setup_types or SetupType.RANGE_HIGH in valid_setup_types:
            range_setup = self._detect_range_setup(df, htf_bias, current_price)

        # Determine best setup based on context and confidence
        return self._select_best_setup(
            pullback_setup=pullback_setup,
            divergence=divergence,
            consolidation=consolidation,
            range_setup=range_setup,
            htf_bias=htf_bias,
            current_price=current_price,
            ema10=ema10,
            ema20=ema20,
            context_result=context_result,
            df=df,
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
        range_setup: Optional[MTFSetup],
        htf_bias: HTFBias,
        current_price: float,
        ema10: pd.Series,
        ema20: pd.Series,
        context_result: MTFContextResult,
        df: pd.DataFrame,
    ) -> MTFSetup:
        """
        Select the best setup from detected patterns.

        UPGRADED: Includes context and pullback quality scoring.
        
        Priority:
        1. Pullback with RSI confirmation and quality score (highest confidence)
        2. Divergence at key level
        3. Range boundary setups
        4. Consolidation breakout
        5. Default to consolidation (no clear setup)

        Args:
            pullback_setup: Detected pullback setup.
            divergence: Detected divergence.
            consolidation: Detected consolidation pattern.
            range_setup: Detected range setup.
            htf_bias: HTF bias.
            current_price: Current price.
            ema10: 10 EMA series.
            ema20: 20 EMA series.
            context_result: MTF context classification result.
            df: DataFrame with OHLCV data.

        Returns:
            MTFSetup with best setup type, context, and quality score.
        """
        # Determine setup direction from HTF bias
        setup_direction = htf_bias.direction

        # Evaluate pullback (with Layer 3 quality scoring)
        if pullback_setup is not None:
            # LAYER 3: Score pullback quality
            atr = compute_atr(df, period=14).iloc[-1]
            quality_score = self.quality_scorer.score(df, htf_bias, atr)
            
            logger.info(f"Pullback quality score: {quality_score.total_score:.2f} - {quality_score.reasons}")

            # Base confidence from quality score
            confidence = 0.3 + (quality_score.total_score * 0.5)  # 0.3-0.8 range

            # Increase confidence if RSI confirms
            if pullback_setup.rsi_approaching_40:
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
                sma20_action=ema10_action,  # Legacy field name
                sma50_action=ema20_action,  # Legacy field name
                ema20_action=ema10_action,  # NEW: EMA20 action
                ema50_action=ema20_action,  # NEW: EMA50 action
                rsi_divergence=None,
                pullback_details=pullback_setup,
                mtf_context=context_result.context,  # Legacy: just enum
                mtf_context_result=context_result,  # NEW: full result with metrics
                pullback_quality_score=quality_score,
            )

        # Evaluate range setup
        if range_setup is not None:
            range_setup.mtf_context = context_result.context
            range_setup.mtf_context_result = context_result
            return range_setup

        # Evaluate divergence
        if divergence is not None:
            if divergence == DivergenceType.REGULAR_BULLISH:
                return MTFSetup(
                    setup_type=SetupType.DIVERGENCE,
                    direction=MTFDirection.BULLISH,
                    confidence=0.6,
                    rsi_divergence=divergence,
                    mtf_context=context_result.context,
                    mtf_context_result=context_result,
                )
            else:
                return MTFSetup(
                    setup_type=SetupType.DIVERGENCE,
                    direction=MTFDirection.BEARISH,
                    confidence=0.6,
                    rsi_divergence=divergence,
                    mtf_context=context_result.context,
                    mtf_context_result=context_result,
                )

        # Evaluate consolidation
        if consolidation is not None:
            return MTFSetup(
                setup_type=SetupType.CONSOLIDATION,
                direction=setup_direction,
                confidence=0.4,
                consolidation_pattern=consolidation,
                mtf_context=context_result.context,
                mtf_context_result=context_result,
            )

        # No clear setup
        return MTFSetup(
            setup_type=SetupType.CONSOLIDATION,
            direction=MTFDirection.NEUTRAL,
            confidence=0.0,
            mtf_context=context_result.context,
            mtf_context_result=context_result,
            warning=f"No clear MTF setup in {context_result.context.value} context",
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
