"""
MTF Context Classifier - Layer 1 of Upgraded MTF System.

This module classifies the market context BEFORE setup detection runs.
The context determines which setups are valid to evaluate.

Context Types:
- TRENDING_PULLBACK: In trend, pulling back to structure — setups valid
- TRENDING_EXTENSION: In trend, extended from MAs — WAIT, no setups
- BREAKING_OUT: Consolidation resolving — breakout setups valid
- CONSOLIDATING: Range-bound — range setups only or WAIT
- REVERSING: Structure breaking, trend change — divergence/reversal setups

Usage:
    classifier = MTFContextClassifier()
    context_result = classifier.classify(mtf_df, htf_bias)
    
    if context_result.context == MTFContext.TRENDING_EXTENSION:
        # No setups valid - wait for pullback
        return None
"""

import logging
from typing import Tuple

import pandas as pd

from src.indicators.technical_indicators import (
    compute_adx,
    compute_atr,
    compute_ema,
    normalize_by_atr,
)
from src.models.mtf_models import HTFBias, MTFContext, MTFContextResult

logger = logging.getLogger(__name__)


class MTFContextClassifier:
    """
    Classify MTF market context using ADX, ATR, and EMA distance.
    
    Layer 1 of the upgraded MTF system. Context classification happens
    BEFORE setup detection to gate which setups are valid.
    
    Attributes:
        adx_trend_threshold: ADX level above which market is trending (default 25).
        adx_range_threshold: ADX level below which market is ranging (default 20).
        ema_fast_span: Fast EMA period for distance calculation (default 21).
        ema_slow_span: Slow EMA period for trend confirmation (default 50).
        extension_threshold_atr: ATR multiple for overextended detection (default 3.0).
        pullback_threshold_atr: ATR multiple for pullback detection (default 1.5).
    """
    
    def __init__(
        self,
        adx_trend_threshold: float = 25.0,
        adx_range_threshold: float = 20.0,
        ema_fast_span: int = 21,
        ema_slow_span: int = 50,
        extension_threshold_atr: float = 3.0,
        pullback_threshold_atr: float = 1.5,
    ):
        """
        Initialize MTF context classifier.
        
        Args:
            adx_trend_threshold: ADX level for trending market.
            adx_range_threshold: ADX level for ranging market.
            ema_fast_span: Fast EMA period.
            ema_slow_span: Slow EMA period.
            extension_threshold_atr: ATR multiple for overextended detection.
            pullback_threshold_atr: ATR multiple for pullback detection.
        """
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_range_threshold = adx_range_threshold
        self.ema_fast_span = ema_fast_span
        self.ema_slow_span = ema_slow_span
        self.extension_threshold_atr = extension_threshold_atr
        self.pullback_threshold_atr = pullback_threshold_atr
    
    def classify(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
    ) -> MTFContextResult:
        """
        Classify MTF market context.
        
        Classification Logic:
        1. Calculate ADX, ATR, EMA21, EMA50
        2. Calculate ATR-normalized distance from EMA21
        3. Apply decision tree:
           - ADX > 25 (trending):
             - Distance < 1.5 ATR → TRENDING_PULLBACK
             - Distance > 3.0 ATR → TRENDING_EXTENSION
             - Otherwise → TRENDING_PULLBACK
           - ADX < 20 (ranging):
             - → CONSOLIDATING
           - ADX 20-25 (transition):
             - Check for breakout → BREAKING_OUT
             - Otherwise → CONSOLIDATING
        
        Args:
            df: DataFrame with OHLCV data.
            htf_bias: HTF bias assessment for trend direction.
        
        Returns:
            MTFContextResult with context classification and metrics.
        
        Example:
            >>> classifier = MTFContextClassifier()
            >>> result = classifier.classify(mtf_df, htf_bias)
            >>> print(f"Context: {result.context.value}")
            >>> print(f"ADX: {result.adx:.2f}, Distance: {result.distance_from_ema_atr:.2f} ATR")
        """
        if df.empty or len(df) < self.ema_slow_span:
            logger.warning(f"Insufficient data for context classification (need {self.ema_slow_span} candles)")
            return MTFContextResult(
                context=MTFContext.CONSOLIDATING,
                confidence=0.0,
                reasoning=f"Insufficient data: have {len(df)} candles, need {self.ema_slow_span}",
            )
        
        # Ensure required columns exist
        required_cols = {"high", "low", "close"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            logger.warning(f"Missing columns for context classification: {required_cols - available_cols}")
            return MTFContextResult(
                context=MTFContext.CONSOLIDATING,
                confidence=0.0,
                reasoning=f"Missing columns: {required_cols - available_cols}",
            )
        
        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})
        
        # Calculate indicators
        adx = compute_adx(df, period=14)
        atr = compute_atr(df, period=14)
        ema21 = compute_ema(df, column="close", span=self.ema_fast_span)
        ema50 = compute_ema(df, column="close", span=self.ema_slow_span)
        
        # Get current values
        current_adx = adx.iloc[-1]
        current_atr = atr.iloc[-1]
        current_ema21 = ema21.iloc[-1]
        current_ema50 = ema50.iloc[-1]
        current_price = df["close"].iloc[-1]
        
        # Handle NaN values
        if pd.isna(current_adx) or pd.isna(current_atr) or pd.isna(current_ema21):
            logger.warning("NaN values in indicator calculation")
            return MTFContextResult(
                context=MTFContext.CONSOLIDATING,
                confidence=0.0,
                reasoning="NaN values in indicator calculation",
            )
        
        # Calculate ATR-normalized distance from EMA21
        distance_from_ema_atr = normalize_by_atr(current_price, current_ema21, current_atr)
        
        # Classify context
        context, confidence, reasoning = self._classify_context(
            adx=current_adx,
            distance_atr=distance_from_ema_atr,
            price=current_price,
            ema21=current_ema21,
            ema50=current_ema50,
            atr=current_atr,
            df=df,
        )
        
        return MTFContextResult(
            context=context,
            confidence=confidence,
            adx=current_adx,
            atr=current_atr,
            distance_from_ema_atr=distance_from_ema_atr,
            reasoning=reasoning,
        )
    
    def _classify_context(
        self,
        adx: float,
        distance_atr: float,
        price: float,
        ema21: float,
        ema50: float,
        atr: float,
        df: pd.DataFrame,
    ) -> Tuple[MTFContext, float, str]:
        """
        Apply classification logic.
        
        Args:
            adx: Current ADX value.
            distance_atr: Distance from EMA21 in ATR units.
            price: Current price.
            ema21: Current EMA21 value.
            ema50: Current EMA50 value.
            atr: Current ATR value.
            df: Full DataFrame for additional analysis.
        
        Returns:
            Tuple of (context, confidence, reasoning).
        """
        # Trending market (ADX > 25)
        if adx > self.adx_trend_threshold:
            return self._classify_trending(
                distance_atr=distance_atr,
                price=price,
                ema21=ema21,
                ema50=ema50,
                atr=atr,
                adx=adx,
            )
        
        # Ranging market (ADX < 20)
        elif adx < self.adx_range_threshold:
            return self._classify_ranging(
                price=price,
                df=df,
                atr=atr,
                adx=adx,
            )
        
        # Transition zone (ADX 20-25)
        else:
            return self._classify_transition(
                price=price,
                df=df,
                atr=atr,
                adx=adx,
                distance_atr=distance_atr,
            )
    
    def _classify_trending(
        self,
        distance_atr: float,
        price: float,
        ema21: float,
        ema50: float,
        atr: float,
        adx: float,
    ) -> Tuple[MTFContext, float, str]:
        """
        Classify trending market context.
        
        Args:
            distance_atr: Distance from EMA21 in ATR units.
            price: Current price.
            ema21: Current EMA21 value.
            ema50: Current EMA50 value.
            atr: Current ATR value.
            adx: Current ADX value.
        
        Returns:
            Tuple of (context, confidence, reasoning).
        """
        abs_distance = abs(distance_atr)
        
        # Overextended trend (> 3 ATR from EMA21)
        if abs_distance > self.extension_threshold_atr:
            confidence = min(0.9, 0.5 + (abs_distance - self.extension_threshold_atr) * 0.1)
            return (
                MTFContext.TRENDING_EXTENSION,
                confidence,
                f"Trending (ADX={adx:.1f}), extended {abs_distance:.2f} ATR from EMA21 — WAIT for pullback",
            )
        
        # Pullback zone (< 1.5 ATR from EMA21)
        elif abs_distance < self.pullback_threshold_atr:
            # Higher confidence if closer to EMA
            proximity_score = 1.0 - (abs_distance / self.pullback_threshold_atr)
            confidence = 0.6 + (proximity_score * 0.3)
            
            direction = "bullish" if price > ema21 else "bearish"
            return (
                MTFContext.TRENDING_PULLBACK,
                confidence,
                f"Trending (ADX={adx:.1f}), pulling back to EMA21 ({abs_distance:.2f} ATR) — {direction} setups valid",
            )
        
        # Normal trend space (1.5-3.0 ATR)
        else:
            confidence = 0.7
            direction = "bullish" if price > ema21 else "bearish"
            return (
                MTFContext.TRENDING_PULLBACK,
                confidence,
                f"Trending (ADX={adx:.1f}), normal trend space ({abs_distance:.2f} ATR) — {direction} setups valid",
            )
    
    def _classify_ranging(
        self,
        price: float,
        df: pd.DataFrame,
        atr: float,
        adx: float,
    ) -> Tuple[MTFContext, float, str]:
        """
        Classify ranging market context.
        
        Args:
            price: Current price.
            df: Full DataFrame for range analysis.
            atr: Current ATR value.
            adx: Current ADX value.
        
        Returns:
            Tuple of (context, confidence, reasoning).
        """
        # Identify range boundaries
        lookback = 50
        recent_high = df["high"].iloc[-lookback:].max()
        recent_low = df["low"].iloc[-lookback:].min()
        range_mid = (recent_high + recent_low) / 2
        
        # Calculate position in range
        range_height = recent_high - recent_low
        if range_height > 0:
            position_in_range = (price - recent_low) / range_height
        else:
            position_in_range = 0.5
        
        # Check if at range boundary
        dist_to_high = (recent_high - price) / recent_high
        dist_to_low = (price - recent_low) / recent_low
        tolerance = 0.01  # 1% tolerance
        
        if dist_to_high < tolerance or dist_to_low < tolerance:
            confidence = 0.75
            boundary = "high" if dist_to_high < tolerance else "low"
            return (
                MTFContext.CONSOLIDATING,
                confidence,
                f"Ranging (ADX={adx:.1f}), at range {boundary} — range boundary setups valid",
            )
        
        # In middle of range
        elif 0.3 < position_in_range < 0.7:
            confidence = 0.8
            return (
                MTFContext.CONSOLIDATING,
                confidence,
                f"Ranging (ADX={adx:.1f}), in middle of range — WAIT or range setups only",
            )
        
        # Near boundary but not quite
        else:
            confidence = 0.65
            return (
                MTFContext.CONSOLIDATING,
                confidence,
                f"Ranging (ADX={adx:.1f}), near range boundary — watch for breakout",
            )
    
    def _classify_transition(
        self,
        price: float,
        df: pd.DataFrame,
        atr: float,
        adx: float,
        distance_atr: float,
    ) -> Tuple[MTFContext, float, str]:
        """
        Classify transition zone context (ADX 20-25).
        
        Args:
            price: Current price.
            df: Full DataFrame for breakout analysis.
            atr: Current ATR value.
            adx: Current ADX value.
            distance_atr: Distance from EMA21 in ATR units.
        
        Returns:
            Tuple of (context, confidence, reasoning).
        """
        # Check for breakout
        lookback = 30
        recent_high = df["high"].iloc[-lookback:].max()
        recent_low = df["low"].iloc[-lookback:].min()
        
        # Check if breaking range with momentum
        is_breaking_high = price > recent_high * 0.999
        is_breaking_low = price < recent_low * 1.001
        
        # Check volume for breakout confirmation
        recent_volume = df["volume"].iloc[-3:].mean()
        avg_volume = df["volume"].iloc[-lookback:-3].mean() if len(df) > lookback else recent_volume
        volume_confirms = recent_volume > avg_volume * 1.3
        
        if (is_breaking_high or is_breaking_low) and volume_confirms:
            confidence = 0.7
            direction = "high" if is_breaking_high else "low"
            return (
                MTFContext.BREAKING_OUT,
                confidence,
                f"Transition (ADX={adx:.1f}), breaking range {direction} with volume — breakout setups valid",
            )
        
        # No clear breakout
        elif abs(distance_atr) < 1.5:
            confidence = 0.6
            return (
                MTFContext.CONSOLIDATING,
                confidence,
                f"Transition (ADX={adx:.1f}), consolidating near EMA — WAIT for direction",
            )
        
        # Leaning towards trend
        else:
            confidence = 0.55
            direction = "bullish" if distance_atr > 0 else "bearish"
            return (
                MTFContext.TRENDING_PULLBACK,
                confidence,
                f"Transition (ADX={adx:.1f}), leaning {direction} — pullback setups valid",
            )


def classify_mtf_context(
    df: pd.DataFrame,
    htf_bias: HTFBias,
    **kwargs,
) -> MTFContextResult:
    """
    Convenience function to classify MTF context.
    
    Args:
        df: DataFrame with OHLCV data.
        htf_bias: HTF bias assessment.
        **kwargs: Additional arguments for MTFContextClassifier.
    
    Returns:
        MTFContextResult with classification.
    
    Example:
        >>> context = classify_mtf_context(mtf_df, htf_bias)
        >>> print(f"Context: {context.context.value}")
    """
    classifier = MTFContextClassifier(**kwargs)
    return classifier.classify(df, htf_bias)
