"""
Pullback Quality Scorer - Layer 3 of Upgraded MTF System.

This module scores pullback quality using multi-factor analysis:
- ATR-normalized distance to EMA (25% weight)
- RSI compression zone (20% weight)
- Impulse vs pullback volume comparison (25% weight)
- HTF level confluence (20% weight)
- Candle structure (10% weight)

This replaces the flat confidence calculation with proper weighted scoring.

Usage:
    scorer = PullbackQualityScorer()
    quality_score = scorer.score(mtf_df, htf_bias, atr)
    
    print(f"Quality Score: {quality_score.total_score:.2f}")
    print(f"Reasons: {quality_score.reasons}")
"""

import logging
from typing import List, Tuple

import pandas as pd

from src.indicators.technical_indicators import (
    compute_ema,
    compute_rsi,
    get_prior_impulse_volume,
    normalize_by_atr,
)
from src.models.mtf_models import HTFBias, MTFDirection, PullbackQualityScore

logger = logging.getLogger(__name__)


class PullbackQualityScorer:
    """
    Multi-factor pullback quality scoring.
    
    Layer 3 of the upgraded MTF system. Scores pullback quality on a
    scale of 0.0-1.0 based on five factors.
    
    Scoring Factors:
    1. Distance to EMA21 (25%): ATR-normalized distance
    2. RSI Compression (20%): RSI near target zone (42 bullish, 58 bearish)
    3. Volume Profile (25%): Pullback volume vs impulse volume
    4. Level Confluence (20%): Proximity to HTF support/resistance
    5. Candle Structure (10%): Orderly vs impulsive pullback
    
    Attributes:
        ema_span: EMA period for distance calculation (default 21).
        rsi_span: RSI period (default 14).
        rsi_bullish_target: RSI target for bullish pullback (default 42).
        rsi_bearish_target: RSI target for bearish pullback (default 58).
        volume_lookback: Lookback for pullback volume (default 5).
        impulse_lookback: Lookback for impulse volume (default 10).
    """
    
    def __init__(
        self,
        ema_span: int = 21,
        rsi_span: int = 14,
        rsi_bullish_target: float = 42.0,
        rsi_bearish_target: float = 58.0,
        volume_lookback: int = 5,
        impulse_lookback: int = 10,
    ):
        """
        Initialize pullback quality scorer.
        
        Args:
            ema_span: EMA period for distance calculation.
            rsi_span: RSI period.
            rsi_bullish_target: RSI target for bullish pullback.
            rsi_bearish_target: RSI target for bearish pullback.
            volume_lookback: Lookback for pullback volume.
            impulse_lookback: Lookback for impulse volume.
        """
        self.ema_span = ema_span
        self.rsi_span = rsi_span
        self.rsi_bullish_target = rsi_bullish_target
        self.rsi_bearish_target = rsi_bearish_target
        self.volume_lookback = volume_lookback
        self.impulse_lookback = impulse_lookback
    
    def score(
        self,
        df: pd.DataFrame,
        htf_bias: HTFBias,
        atr: float,
    ) -> PullbackQualityScore:
        """
        Score pullback quality.
        
        Args:
            df: DataFrame with OHLCV data.
            htf_bias: HTF bias assessment.
            atr: Current ATR value.
        
        Returns:
            PullbackQualityScore with total score and component scores.
        
        Example:
            >>> scorer = PullbackQualityScorer()
            >>> quality = scorer.score(mtf_df, htf_bias, atr)
            >>> if quality.total_score > 0.75:
            ...     print("High quality pullback")
        """
        if df.empty or len(df) < self.ema_span:
            logger.warning(f"Insufficient data for pullback scoring")
            return PullbackQualityScore(
                total_score=0.0,
                reasons=["Insufficient data for scoring"],
            )
        
        # Ensure required columns exist
        required_cols = {"high", "low", "close"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            logger.warning(f"Missing columns for pullback scoring: {required_cols - available_cols}")
            return PullbackQualityScore(
                total_score=0.0,
                reasons=[f"Missing columns: {required_cols - available_cols}"],
            )
        
        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})
        
        # Calculate indicators
        ema21 = compute_ema(df, column="close", span=self.ema_span)
        rsi = compute_rsi(df["close"], period=self.rsi_span)
        
        current_price = df["close"].iloc[-1]
        current_ema21 = ema21.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Handle NaN values
        if pd.isna(current_ema21) or pd.isna(current_rsi):
            logger.warning("NaN values in pullback scoring")
            return PullbackQualityScore(
                total_score=0.0,
                reasons=["NaN values in indicator calculation"],
            )
        
        # Score each factor
        distance_score = self._score_distance(current_price, current_ema21, atr)
        rsi_score = self._score_rsi(current_rsi, htf_bias.direction)
        volume_score = self._score_volume(df, htf_bias.direction)
        confluence_score = self._score_confluence(current_price, htf_bias, atr)
        structure_score = self._score_structure(df, htf_bias.direction)
        
        # Calculate weighted total
        total_score = (
            distance_score * 0.25 +
            rsi_score * 0.20 +
            volume_score * 0.25 +
            confluence_score * 0.20 +
            structure_score * 0.10
        )
        
        # Build reasons list
        reasons = self._build_reasons(
            distance_score=distance_score,
            rsi_score=rsi_score,
            volume_score=volume_score,
            confluence_score=confluence_score,
            structure_score=structure_score,
            price=current_price,
            ema21=current_ema21,
            rsi=current_rsi,
            atr=atr,
        )
        
        return PullbackQualityScore(
            total_score=min(total_score, 1.0),
            distance_score=distance_score,
            rsi_score=rsi_score,
            volume_score=volume_score,
            confluence_score=confluence_score,
            structure_score=structure_score,
            reasons=reasons,
        )
    
    def _score_distance(
        self,
        price: float,
        ema21: float,
        atr: float,
    ) -> float:
        """
        Score ATR-normalized distance to EMA21.
        
        Scoring:
        - < 0.5 ATR: 1.0 (excellent)
        - 0.5-1.0 ATR: 0.6 (good)
        - 1.0-1.5 ATR: 0.3 (fair)
        - > 1.5 ATR: 0.0 (poor)
        
        Args:
            price: Current price.
            ema21: Current EMA21 value.
            atr: Current ATR value.
        
        Returns:
            Score 0.0-1.0.
        """
        if atr <= 0:
            return 0.0
        
        distance_atr = abs(normalize_by_atr(price, ema21, atr))
        
        if distance_atr < 0.5:
            return 1.0
        elif distance_atr < 1.0:
            return 0.6
        elif distance_atr < 1.5:
            return 0.3
        else:
            return 0.0
    
    def _score_rsi(
        self,
        rsi: float,
        direction: MTFDirection,
    ) -> float:
        """
        Score RSI compression zone.
        
        Bullish pullback: target RSI 42 (approaching oversold but not broken)
        Bearish pullback: target RSI 58 (approaching overbought but not broken)
        
        Scoring: max(0, 1.0 - abs(rsi - target) * 0.05)
        
        Args:
            rsi: Current RSI value.
            direction: HTF bias direction.
        
        Returns:
            Score 0.0-1.0.
        """
        if direction == MTFDirection.BULLISH:
            target = self.rsi_bullish_target
        elif direction == MTFDirection.BEARISH:
            target = self.rsi_bearish_target
        else:
            return 0.0
        
        # Calculate score based on distance from target
        score = max(0, 1.0 - abs(rsi - target) * 0.05)
        return min(score, 1.0)
    
    def _score_volume(
        self,
        df: pd.DataFrame,
        direction: MTFDirection,
    ) -> float:
        """
        Score volume profile (impulse vs pullback).
        
        Healthy pullback: pullback volume < 60% of impulse volume
        Warning: pullback volume > 80% of impulse volume
        
        Scoring:
        - < 60%: 1.0 (excellent - healthy pullback)
        - 60-80%: 0.4 (fair - some distribution)
        - > 80%: 0.0 (poor - heavy distribution)
        
        Args:
            df: DataFrame with OHLCV data.
            direction: HTF bias direction.
        
        Returns:
            Score 0.0-1.0.
        """
        if "volume" not in df.columns:
            logger.warning("Volume data not available for scoring")
            return 0.5  # Neutral if no volume
        
        # Get impulse volume (volume during the prior directional move)
        impulse_vol = get_prior_impulse_volume(df, lookback=self.impulse_lookback)
        
        # Get pullback volume (recent average volume)
        pullback_vol = df["volume"].iloc[-self.volume_lookback:].mean()
        
        if impulse_vol <= 0:
            return 0.5  # Neutral if can't calculate
        
        # Calculate ratio
        volume_ratio = pullback_vol / impulse_vol
        
        # Score based on ratio
        if volume_ratio < 0.6:
            return 1.0
        elif volume_ratio < 0.8:
            return 0.4
        else:
            return 0.0
    
    def _score_confluence(
        self,
        price: float,
        htf_bias: HTFBias,
        atr: float,
    ) -> float:
        """
        Score HTF level confluence.
        
        Higher score if pullback is near HTF support/resistance level.
        
        Scoring:
        - < 0.5 ATR from level: 1.0 (excellent confluence)
        - 0.5-1.0 ATR from level: 0.5 (moderate confluence)
        - > 1.0 ATR from level: 0.0 (no confluence)
        
        Args:
            price: Current price.
            htf_bias: HTF bias with key levels.
            atr: Current ATR value.
        
        Returns:
            Score 0.0-1.0.
        """
        if not htf_bias.key_levels or atr <= 0:
            return 0.0
        
        # Find nearest HTF level
        min_distance_atr = float("inf")
        
        for level in htf_bias.key_levels:
            distance_atr = abs(normalize_by_atr(price, level.price, atr))
            min_distance_atr = min(min_distance_atr, distance_atr)
        
        # Score based on distance
        if min_distance_atr < 0.5:
            return 1.0
        elif min_distance_atr < 1.0:
            return 0.5
        else:
            return 0.0
    
    def _score_structure(
        self,
        df: pd.DataFrame,
        direction: MTFDirection,
    ) -> float:
        """
        Score candle structure at pullback.
        
        Good structure: orderly pullback without cascading candles
        Bad structure: impulsive move against the trend
        
        Scoring:
        - Orderly pullback: 1.0
        - Mixed structure: 0.5
        - Impulsive against trend: 0.0
        
        Args:
            df: DataFrame with OHLCV data.
            direction: HTF bias direction.
        
        Returns:
            Score 0.0-1.0.
        """
        if len(df) < 5:
            return 0.5  # Neutral if insufficient data
        
        lookback = min(5, len(df))
        recent = df.iloc[-lookback:]
        
        # Calculate candle bodies
        bodies = recent["close"] - recent["open"]
        
        if direction == MTFDirection.BULLISH:
            # In bullish pullback, we want small/negative candles but not cascading large red ones
            red_candles = bodies[bodies < 0]
            
            if len(red_candles) == 0:
                return 0.8  # No red candles - still consolidating
            
            # Check if red candles are getting larger (cascading)
            red_sizes = red_candles.abs()
            if len(red_sizes) > 1:
                if red_sizes.iloc[-1] > red_sizes.iloc[0] * 1.5:
                    return 0.0  # Cascading - bad
            
            # Check average red candle size vs recent average
            avg_body = bodies.abs().mean()
            avg_red = red_sizes.mean()
            
            if avg_red < avg_body * 0.8:
                return 1.0  # Orderly - red candles smaller than average
            else:
                return 0.5  # Mixed
        
        elif direction == MTFDirection.BEARISH:
            # In bearish pullback, we want small/positive candles but not cascading large green ones
            green_candles = bodies[bodies > 0]
            
            if len(green_candles) == 0:
                return 0.8  # No green candles - still consolidating
            
            # Check if green candles are getting larger (cascading)
            green_sizes = green_candles.abs()
            if len(green_sizes) > 1:
                if green_sizes.iloc[-1] > green_sizes.iloc[0] * 1.5:
                    return 0.0  # Cascading - bad
            
            # Check average green candle size vs recent average
            avg_body = bodies.abs().mean()
            avg_green = green_sizes.mean()
            
            if avg_green < avg_body * 0.8:
                return 1.0  # Orderly - green candles smaller than average
            else:
                return 0.5  # Mixed
        
        return 0.5  # Neutral for NEUTRAL direction
    
    def _build_reasons(
        self,
        distance_score: float,
        rsi_score: float,
        volume_score: float,
        confluence_score: float,
        structure_score: float,
        price: float,
        ema21: float,
        rsi: float,
        atr: float,
    ) -> List[str]:
        """
        Build human-readable reasons for the score.
        
        Args:
            distance_score: Distance component score.
            rsi_score: RSI component score.
            volume_score: Volume component score.
            confluence_score: Confluence component score.
            structure_score: Structure component score.
            price: Current price.
            ema21: Current EMA21 value.
            rsi: Current RSI value.
            atr: Current ATR value.
        
        Returns:
            List of reason strings.
        """
        reasons = []
        
        # Distance reason
        distance_atr = normalize_by_atr(price, ema21, atr)
        if distance_score >= 1.0:
            reasons.append(f"price at EMA21 ({abs(distance_atr):.2f} ATR) — high precision entry zone")
        elif distance_score >= 0.6:
            reasons.append(f"price near EMA21 ({abs(distance_atr):.2f} ATR)")
        elif distance_score >= 0.3:
            reasons.append(f"price approaching EMA21 ({abs(distance_atr):.2f} ATR)")
        else:
            reasons.append(f"price extended from EMA21 ({abs(distance_atr):.2f} ATR)")
        
        # RSI reason
        if rsi_score >= 0.8:
            reasons.append(f"RSI at optimal compression ({rsi:.1f})")
        elif rsi_score >= 0.5:
            reasons.append(f"RSI near compression zone ({rsi:.1f})")
        elif rsi_score > 0:
            reasons.append(f"RSI approaching compression ({rsi:.1f})")
        else:
            reasons.append(f"RSI outside compression zone ({rsi:.1f})")
        
        # Volume reason
        if volume_score >= 1.0:
            reasons.append("pullback volume significantly below impulse — healthy")
        elif volume_score >= 0.4:
            reasons.append("pullback volume moderating")
        else:
            reasons.append("pullback volume heavy — distribution likely")
        
        # Confluence reason
        if confluence_score >= 1.0:
            reasons.append("pullback confluent with HTF level")
        elif confluence_score >= 0.5:
            reasons.append("pullback near HTF level")
        else:
            reasons.append("no HTF level confluence")
        
        # Structure reason
        if structure_score >= 1.0:
            reasons.append("orderly pullback structure")
        elif structure_score >= 0.5:
            reasons.append("mixed pullback structure")
        else:
            reasons.append("cascading candles — impulsive pullback")
        
        return reasons


def score_pullback_quality(
    df: pd.DataFrame,
    htf_bias: HTFBias,
    atr: float,
    **kwargs,
) -> PullbackQualityScore:
    """
    Convenience function to score pullback quality.
    
    Args:
        df: DataFrame with OHLCV data.
        htf_bias: HTF bias assessment.
        atr: Current ATR value.
        **kwargs: Additional arguments for PullbackQualityScorer.
    
    Returns:
        PullbackQualityScore with scoring results.
    
    Example:
        >>> quality = score_pullback_quality(mtf_df, htf_bias, atr)
        >>> print(f"Score: {quality.total_score:.2f}")
    """
    scorer = PullbackQualityScorer(**kwargs)
    return scorer.score(df, htf_bias, atr)
