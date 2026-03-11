"""
MTF Alignment Scorer for Multi-Timeframe Analysis.

This module scores alignment across 3 timeframes and generates
trade recommendations, following the MTF framework from multi_timeframe.md.

UPGRADED SYSTEM (Layer 4): Weighted Alignment Scoring

Replaces binary 0-3 count with confidence-weighted scoring:
- HTF confidence × 50% (foundation - highest weight)
- MTF confidence × 35% (setup quality)
- LTF confidence × 15% (execution - lowest weight)

Position sizing based on weighted score:
- ≥ 0.75: 100% of base risk (full size)
- 0.60-0.74: 75% of base risk (standard)
- 0.50-0.59: 50% of base risk (reduced)
- < 0.50: 0% (no trade)
"""

import logging
from datetime import datetime
from typing import Literal, Optional, Tuple

import pandas as pd

from src.models.mtf_models import (
    HTFBias,
    LTFEntry,
    MTFAlignment,
    MTFContext,
    MTFDirection,
    MTFSetup,
    MTFTimeframeConfig,
    Recommendation,
    SetupType,
    TargetMethod,
    TargetResult,
    TradingStyle,
    check_timeframe_conflict,
    determine_alignment_quality,
    determine_recommendation,
)

logger = logging.getLogger(__name__)


class MTFAlignmentScorer:
    """
    Score alignment across 3 timeframes.

    The alignment scorer combines HTF bias, MTF setup, and LTF entry
    into a single recommendation with confidence score.

    Attributes:
        min_rr_ratio: Minimum R:R ratio for trade (default 2.0).
        require_all_3_for_highest: Require all 3 TFs for HIGHEST quality.
    """

    def __init__(
        self,
        min_rr_ratio: float = 2.0,
        require_all_3_for_highest: bool = True,
    ):
        """
        Initialize MTF alignment scorer.

        Args:
            min_rr_ratio: Minimum R:R ratio for trade recommendation.
            require_all_3_for_highest: Require 3/3 alignment for HIGHEST quality.
        """
        self.min_rr_ratio = min_rr_ratio
        self.require_all_3_for_highest = require_all_3_for_highest

    def score_alignment(
        self,
        pair: str,
        htf_bias: HTFBias,
        mtf_setup: MTFSetup,
        ltf_entry: Optional[LTFEntry],
        trading_style: TradingStyle = TradingStyle.SWING,
    ) -> MTFAlignment:
        """
        Calculate alignment score and quality rating.

        Returns full MTFAlignment object with:
        - alignment_score (0-3)
        - alignment_pct
        - quality rating
        - recommendation (BUY/SELL/WAIT/AVOID)

        Args:
            pair: Trading pair symbol.
            htf_bias: Higher timeframe bias assessment.
            mtf_setup: Middle timeframe setup.
            ltf_entry: Lower timeframe entry signal (optional).
            trading_style: Trading style configuration.

        Returns:
            MTFAlignment object with full analysis.

        Example:
            >>> scorer = MTFAlignmentScorer()
            >>> alignment = scorer.score_alignment(
            ...     "BTC/USDT", htf_bias, mtf_setup, ltf_entry
            ... )
            >>> print(f"Quality: {alignment.quality.value}, Rec: {alignment.recommendation.value}")
        """
        # Count aligned timeframes (legacy binary scoring)
        alignment_score = 0

        # HTF counts as 1 if not NEUTRAL
        if htf_bias.direction != MTFDirection.NEUTRAL:
            alignment_score += 1

        # MTF counts as 1 if aligned with HTF
        if mtf_setup.direction != MTFDirection.NEUTRAL:
            if mtf_setup.direction == htf_bias.direction:
                alignment_score += 1

        # LTF counts as 1 if aligned with HTF and MTF
        if ltf_entry is not None and ltf_entry.direction != MTFDirection.NEUTRAL:
            if ltf_entry.direction == htf_bias.direction:
                alignment_score += 1

        # Calculate alignment percentage
        max_score = 3 if ltf_entry is not None else 2
        alignment_pct = (alignment_score / max_score) * 100 if max_score > 0 else 0

        # LAYER 4: Calculate weighted alignment score (confidence-weighted)
        weighted_score = self._calculate_weighted_alignment(
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )
        
        logger.info(f"Weighted alignment score: {weighted_score:.2f}")

        # Determine quality (use both legacy and weighted)
        quality = determine_alignment_quality(alignment_score)

        # Check for timeframe conflicts
        has_conflict, conflict_message = check_timeframe_conflict(
            htf_direction=htf_bias.direction,
            mtf_direction=mtf_setup.direction,
            ltf_direction=ltf_entry.direction if ltf_entry else MTFDirection.NEUTRAL,
        )

        # Determine recommendation
        if has_conflict:
            recommendation = Recommendation.WAIT
        elif alignment_score < 2:
            recommendation = Recommendation.AVOID
        else:
            recommendation = determine_recommendation(
                alignment_score=alignment_score,
                htf_direction=htf_bias.direction,
                mtf_direction=mtf_setup.direction,
                ltf_direction=ltf_entry.direction if ltf_entry else MTFDirection.NEUTRAL,
            )

        # Calculate position size based on weighted score
        position_size_pct = self._get_position_size_pct(weighted_score)

        # Calculate R:R if entry exists
        rr_ratio = 0.0
        target = None
        if ltf_entry is not None and ltf_entry.entry_price > 0 and ltf_entry.stop_loss > 0:
            risk = abs(ltf_entry.entry_price - ltf_entry.stop_loss)
            if risk > 0:
                # Estimate target (will be refined by target_calculator.py)
                if recommendation in (Recommendation.BUY, Recommendation.SELL):
                    # Use 2.5x risk as initial target estimate
                    target_price = (
                        ltf_entry.entry_price + risk * 2.5
                        if recommendation == Recommendation.BUY
                        else ltf_entry.entry_price - risk * 2.5
                    )
                    reward = abs(target_price - ltf_entry.entry_price)
                    rr_ratio = reward / risk

                    target = TargetResult(
                        target_price=target_price,
                        method=TargetMethod.ATR,  # Placeholder
                        confidence=0.5,
                        rr_ratio=rr_ratio,
                        description=f"Estimated {rr_ratio:.1f}:1 R:R",
                    )

        # Build notes
        notes = self._build_notes(
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
            alignment_score=alignment_score,
            has_conflict=has_conflict,
            conflict_message=conflict_message,
        )

        return MTFAlignment(
            pair=pair,
            timestamp=datetime.utcnow().isoformat(),
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry or LTFEntry(),
            alignment_score=alignment_score,
            alignment_pct=alignment_pct,
            quality=quality,
            recommendation=recommendation,
            target=target,
            rr_ratio=rr_ratio,
            trading_style=trading_style,
            notes=notes,
            weighted_score=weighted_score,
            position_size_pct=position_size_pct,
        )

    def _build_notes(
        self,
        htf_bias: HTFBias,
        mtf_setup: MTFSetup,
        ltf_entry: Optional[LTFEntry],
        alignment_score: int,
        has_conflict: bool,
        conflict_message: Optional[str],
    ) -> str:
        """
        Build analysis notes.

        Args:
            htf_bias: HTF bias assessment.
            mtf_setup: MTF setup.
            ltf_entry: LTF entry signal.
            alignment_score: Alignment score (0-3).
            has_conflict: Whether timeframes conflict.
            conflict_message: Conflict description.

        Returns:
            Human-readable notes string.
        """
        notes = []

        # HTF note
        if htf_bias.direction != MTFDirection.NEUTRAL:
            notes.append(f"HTF: {htf_bias.direction.value} ({htf_bias.price_structure.value})")
        else:
            notes.append("HTF: NEUTRAL (no clear bias)")

        # MTF note
        if mtf_setup.setup_type == SetupType.PULLBACK and mtf_setup.pullback_details:
            sma = mtf_setup.pullback_details.approaching_sma
            notes.append(f"MTF: Pullback to SMA{sma}")
        elif mtf_setup.setup_type == SetupType.DIVERGENCE:
            notes.append(f"MTF: RSI divergence ({mtf_setup.direction.value})")
        elif mtf_setup.setup_type in (SetupType.RANGE_LOW, SetupType.RANGE_HIGH):
            notes.append(f"MTF: Range boundary ({mtf_setup.setup_type.value})")
        else:
            notes.append(f"MTF: {mtf_setup.setup_type.value}")

        # LTF note
        if ltf_entry is not None:
            signal_type = ltf_entry.signal_type
            # Handle both enum and string values
            signal_value = signal_type.value if hasattr(signal_type, 'value') else str(signal_type)
            if signal_type and signal_value != "NONE":
                notes.append(f"LTF: {signal_value} entry")
            else:
                notes.append("LTF: No clear entry signal")
        else:
            notes.append("LTF: Not analyzed")

        # Conflict note
        if has_conflict and conflict_message:
            notes.append(f"⚠️ {conflict_message}")

        # R:R note
        if alignment_score >= 2:
            notes.append("✓ Meets minimum alignment requirement")

        return " | ".join(notes)

    def _calculate_weighted_alignment(
        self,
        htf_bias: HTFBias,
        mtf_setup: MTFSetup,
        ltf_entry: Optional[LTFEntry],
    ) -> float:
        """
        Calculate confidence-weighted alignment score.
        
        LAYER 4: Weighted Alignment Scoring
        
        Replaces binary 0-3 count with confidence-weighted score:
        - HTF confidence × 50% (foundation - highest weight)
        - MTF confidence × 35% (setup quality)
        - LTF confidence × 15% (execution - lowest weight)
        
        Hard gate: All timeframes must be in same direction.
        
        Args:
            htf_bias: HTF bias assessment.
            mtf_setup: MTF setup.
            ltf_entry: LTF entry signal.
        
        Returns:
            Weighted alignment score 0.0-1.0.
        """
        if not mtf_setup or not ltf_entry:
            return 0.0
        
        # Hard gate: Check directional alignment first
        all_bullish = all(
            x.direction == MTFDirection.BULLISH 
            for x in [htf_bias, mtf_setup, ltf_entry]
        )
        all_bearish = all(
            x.direction == MTFDirection.BEARISH 
            for x in [htf_bias, mtf_setup, ltf_entry]
        )
        
        if not (all_bullish or all_bearish):
            return 0.0  # Misalignment = no trade
        
        # Weight by confidence with HTF carrying most weight
        weighted_score = (
            htf_bias.confidence * 0.50 +    # HTF is the foundation
            mtf_setup.confidence * 0.35 +   # MTF setup quality
            ltf_entry.confidence * 0.15     # LTF is execution only
        )
        
        return min(weighted_score, 1.0)

    def _get_position_size_pct(self, weighted_score: float) -> float:
        """
        Calculate position size percentage based on weighted alignment score.
        
        Position Sizing Rules:
        - ≥ 0.75: 100% of base risk (full size)
        - 0.60-0.74: 75% of base risk (standard)
        - 0.50-0.59: 50% of base risk (reduced)
        - < 0.50: 0% (no trade)
        
        Args:
            weighted_score: Weighted alignment score 0.0-1.0.
        
        Returns:
            Position size as percentage of base risk (0-100).
        """
        if weighted_score >= 0.75:
            return 100.0  # Full size
        elif weighted_score >= 0.60:
            return 75.0   # Standard size
        elif weighted_score >= 0.50:
            return 50.0   # Half size
        else:
            return 0.0    # No trade


class MTFAnalyzer:
    """
    Multi-timeframe analysis orchestrator.

    Coordinates analysis across 3 timeframes and produces
    alignment scores and trade recommendations.

    Attributes:
        config: MTF timeframe configuration.
        htf_detector: HTF bias detector.
        mtf_detector: MTF setup detector.
        ltf_finder: LTF entry finder.
        scorer: Alignment scorer.
    """

    def __init__(
        self,
        config: MTFTimeframeConfig,
        htf_detector=None,
        mtf_detector=None,
        ltf_finder=None,
        scorer=None,
    ):
        """
        Initialize MTF analyzer.

        Args:
            config: MTF timeframe configuration.
            htf_detector: HTFBiasDetector instance.
            mtf_detector: MTFSetupDetector instance.
            ltf_finder: LTFEntryFinder instance.
            scorer: MTFAlignmentScorer instance.
        """
        self.config = config
        self.htf_detector = htf_detector
        self.mtf_detector = mtf_detector
        self.ltf_finder = ltf_finder
        self.scorer = scorer or MTFAlignmentScorer()

    def analyze_pair(
        self,
        pair: str,
        htf_data: pd.DataFrame,
        mtf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
    ) -> MTFAlignment:
        """
        Run full MTF analysis on a single pair.

        Steps:
        1. Determine HTF bias from htf_data
        2. Identify MTF setup from mtf_data (using HTF bias)
        3. Find LTF entry from ltf_data (using MTF setup)
        4. Score alignment
        5. Return recommendation

        Args:
            pair: Trading pair symbol.
            htf_data: HTF OHLCV data.
            mtf_data: MTF OHLCV data.
            ltf_data: LTF OHLCV data.

        Returns:
            MTFAlignment object with full analysis.

        Example:
            >>> config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
            >>> analyzer = MTFAnalyzer(config)
            >>> htf_df = fetch_ohlcv('BTC/USDT', '1d')
            >>> mtf_df = fetch_ohlcv('BTC/USDT', '4h')
            >>> ltf_df = fetch_ohlcv('BTC/USDT', '1h')
            >>> result = analyzer.analyze_pair('BTC/USDT', htf_df, mtf_df, ltf_df)
            >>> print(f"Recommendation: {result.recommendation.value}")
        """
        # Lazy import to avoid circular dependencies
        if self.htf_detector is None:
            from src.services.mtf_bias_detector import HTFBiasDetector
            self.htf_detector = HTFBiasDetector()

        if self.mtf_detector is None:
            from src.services.mtf_setup_detector import MTFSetupDetector
            self.mtf_detector = MTFSetupDetector()

        if self.ltf_finder is None:
            from src.services.mtf_entry_finder import LTFEntryFinder
            self.ltf_finder = LTFEntryFinder()

        # Step 1: Determine HTF bias
        htf_bias = self.htf_detector.detect_bias(htf_data)
        logger.debug(f"HTF bias for {pair}: {htf_bias.direction.value} ({htf_bias.confidence:.2f})")

        # Step 2: Identify MTF setup
        mtf_setup = self.mtf_detector.detect_setup(mtf_data, htf_bias)
        logger.debug(f"MTF setup for {pair}: {mtf_setup.setup_type.value} ({mtf_setup.confidence:.2f})")

        # Step 3: Find LTF entry (if we have a setup)
        ltf_entry = None
        if mtf_setup.direction != MTFDirection.NEUTRAL and mtf_setup.confidence > 0.3:
            direction = "LONG" if mtf_setup.direction == MTFDirection.BULLISH else "SHORT"
            ltf_entry = self.ltf_finder.find_entry(ltf_data, mtf_setup, direction)
            if ltf_entry:
                logger.debug(f"LTF entry for {pair}: {ltf_entry.signal_type.value} @ {ltf_entry.entry_price}")

        # Step 4: Score alignment
        alignment = self.scorer.score_alignment(
            pair=pair,
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
            trading_style=self.config.trading_style,
        )

        # Step 5: Replace placeholder target with real TargetCalculator output
        if (
            alignment.ltf_entry
            and alignment.ltf_entry.entry_price > 0
            and alignment.ltf_entry.stop_loss > 0
            and alignment.recommendation in (Recommendation.BUY, Recommendation.SELL)
        ):
            direction = "LONG" if alignment.recommendation == Recommendation.BUY else "SHORT"
            try:
                from src.services.target_calculator import TargetCalculator
                real_target = TargetCalculator().calculate_target(
                    df_htf=htf_data,
                    df_mtf=mtf_data,
                    entry_price=alignment.ltf_entry.entry_price,
                    stop_loss=alignment.ltf_entry.stop_loss,
                    direction=direction,
                    htf_bias=htf_bias,
                    setup=mtf_setup,
                )
                alignment.target = real_target
                alignment.rr_ratio = real_target.rr_ratio
            except Exception as exc:
                logger.warning(f"TargetCalculator failed for {pair}, using placeholder: {exc}")

        logger.info(
            f"MTF analysis for {pair}: {alignment.quality.value}, "
            f"score={alignment.alignment_score}/3, rec={alignment.recommendation.value}"
        )

        return alignment


def analyze_mtf(
    pair: str,
    htf_data: pd.DataFrame,
    mtf_data: pd.DataFrame,
    ltf_data: pd.DataFrame,
    trading_style: TradingStyle = TradingStyle.SWING,
) -> MTFAlignment:
    """
    Convenience function for full MTF analysis.

    Args:
        pair: Trading pair symbol.
        htf_data: HTF OHLCV data.
        mtf_data: MTF OHLCV data.
        ltf_data: LTF OHLCV data.
        trading_style: Trading style configuration.

    Returns:
        MTFAlignment object.

    Example:
        >>> htf_df = fetch_ohlcv('BTC/USDT', '1d')
        >>> mtf_df = fetch_ohlcv('BTC/USDT', '4h')
        >>> ltf_df = fetch_ohlcv('BTC/USDT', '1h')
        >>> result = analyze_mtf('BTC/USDT', htf_df, mtf_df, ltf_df)
        >>> print(f"Quality: {result.quality.value}")
    """
    config = MTFTimeframeConfig.get_config(trading_style)
    analyzer = MTFAnalyzer(config)
    return analyzer.analyze_pair(pair, htf_data, mtf_data, ltf_data)
