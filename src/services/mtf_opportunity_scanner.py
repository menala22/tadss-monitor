"""
MTF Opportunity Scanner for Multi-Timeframe Analysis.

This module scans multiple pairs for MTF-aligned trading opportunities,
following the MTF framework from multi_timeframe.md.

Patterns Scanned:
1. HTF Support + LTF Reversal
2. HTF Trend + MTF Pullback + LTF Entry
3. Converging Levels Across Timeframes
4. MTF Divergence at HTF Support/Resistance
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.models.mtf_models import (
    HTFBias,
    LTFEntry,
    MTFAlignment,
    MTFDirection,
    MTFSetup,
    MTFTimeframeConfig,
    MTFOpportunity,
    PriceStructure,
    Recommendation,
    SetupType,
    TradingStyle,
)
from src.services.mtf_alignment_scorer import MTFAnalyzer, MTFAlignmentScorer
from src.services.mtf_bias_detector import HTFBiasDetector
from src.services.mtf_entry_finder import LTFEntryFinder
from src.services.mtf_setup_detector import MTFSetupDetector
from src.services.divergence_detector import DivergenceDetector, DivergenceResult
from src.services.support_resistance_detector import (
    SupportResistanceDetector,
    SupportResistanceLevel,
)

logger = logging.getLogger(__name__)

# Candle limits per role — HTF needs more history for EMA/swing detection.
ROLE_LIMITS: Dict[str, int] = {"htf": 250, "mtf": 150, "ltf": 100}


def load_pair_data_from_universal(
    pair: str,
    config: "MTFTimeframeConfig",
    db: Session,
) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load HTF/MTF/LTF DataFrames for a pair from ohlcv_universal table (read-only).

    Single authoritative implementation used by both the API scanner and the
    report script, so both always analyse the same data.

    Args:
        pair: Trading pair symbol (e.g. 'XAU/USD').
        config: MTF timeframe configuration.
        db: SQLAlchemy database session.

    Returns:
        {"htf": df, "mtf": df, "ltf": df} or None if any timeframe has <10 candles.
    """
    from src.models.ohlcv_universal_model import OHLCVUniversal

    roles = [
        ("htf", config.htf_timeframe),
        ("mtf", config.mtf_timeframe),
        ("ltf", config.ltf_timeframe),
    ]
    result: Dict[str, pd.DataFrame] = {}

    for role, internal_tf in roles:
        limit = ROLE_LIMITS[role]

        candles = (
            db.query(OHLCVUniversal)
            .filter(
                OHLCVUniversal.symbol == pair,
                OHLCVUniversal.timeframe == internal_tf,
            )
            .order_by(OHLCVUniversal.timestamp.desc())
            .limit(limit)
            .all()
        )

        if not candles or len(candles) < 10:
            logger.info(
                f"No data in ohlcv_universal for {pair} {internal_tf} — "
                "waiting for prefetch job"
            )
            return None

        df = pd.DataFrame([c.to_dict() for c in candles])
        df = df.sort_values("timestamp").reset_index(drop=True)
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]]

        result[role] = df

    return result


@dataclass
class ScanResult:
    """
    Result of opportunity scan for a single pair.

    Attributes:
        pair: Trading pair symbol.
        alignment: Full MTF alignment analysis.
        patterns: List of detected patterns.
        divergence: Divergence detection result.
        key_levels: Key S/R levels.
        passes_filters: Whether opportunity meets criteria.
    """

    pair: str
    alignment: MTFAlignment
    patterns: List[str] = field(default_factory=list)
    divergence: Optional[DivergenceResult] = None
    key_levels: List[SupportResistanceLevel] = field(default_factory=list)
    passes_filters: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "pair": self.pair,
            "alignment": self.alignment.to_dict(),
            "patterns": self.patterns,
            "divergence": self.divergence.to_dict() if self.divergence else None,
            "key_levels": [
                {"price": l.price, "type": l.level_type.value, "strength": l.strength.value}
                for l in self.key_levels
            ],
            "passes_filters": self.passes_filters,
        }


class MTFOpportunityScanner:
    """
    Scan multiple pairs for MTF-aligned opportunities.

    The scanner runs full MTF analysis on each pair and filters
    for high-probability setups meeting minimum criteria.

    Attributes:
        min_alignment: Minimum alignment score (0-3, default 2).
        min_rr_ratio: Minimum R:R ratio (default 2.0).
        require_no_conflict: Require no timeframe conflicts.
        trading_style: Trading style configuration.
    """

    def __init__(
        self,
        min_alignment: int = 2,
        min_rr_ratio: float = 2.0,
        require_no_conflict: bool = True,
        trading_style: TradingStyle = TradingStyle.SWING,
    ):
        """
        Initialize opportunity scanner.

        Args:
            min_alignment: Minimum alignment score required.
            min_rr_ratio: Minimum R:R ratio required.
            require_no_conflict: Require no timeframe conflicts.
            trading_style: Trading style configuration.
        """
        self.min_alignment = min_alignment
        self.min_rr_ratio = min_rr_ratio
        self.require_no_conflict = require_no_conflict
        self.trading_style = trading_style

        # Initialize components
        self.config = MTFTimeframeConfig.get_config(trading_style)
        self.analyzer = MTFAnalyzer(self.config)
        self.scorer = MTFAlignmentScorer(min_rr_ratio=min_rr_ratio)
        self.divergence_detector = DivergenceDetector()
        self.sr_detector = SupportResistanceDetector()

    def scan_opportunities(
        self,
        data_by_pair: Dict[str, Dict[str, pd.DataFrame]],
        min_alignment: Optional[int] = None,
        min_rr_ratio: Optional[float] = None,
    ) -> List[MTFOpportunity]:
        """
        Scan all pairs and return opportunities.

        Args:
            data_by_pair: Dict of pair → {htf, mtf, ltf} DataFrames.
            min_alignment: Override minimum alignment score.
            min_rr_ratio: Override minimum R:R ratio.

        Returns:
            List of MTFOpportunity objects meeting criteria.

        Example:
            >>> scanner = MTFOpportunityScanner()
            >>> data = {
            ...     "BTC/USDT": {"htf": htf_df, "mtf": mtf_df, "ltf": ltf_df},
            ...     "ETH/USDT": {"htf": htf_df, "mtf": mtf_df, "ltf": ltf_df},
            ... }
            >>> opportunities = scanner.scan_opportunities(data)
            >>> for opp in opportunities:
            ...     print(f"{opp.pair}: {opp.alignment.quality.value}")
        """
        opportunities = []

        for pair, data in data_by_pair.items():
            htf_data = data.get("htf")
            mtf_data = data.get("mtf")
            ltf_data = data.get("ltf")

            if htf_data is None or mtf_data is None or ltf_data is None:
                logger.warning(f"Missing data for pair {pair}")
                continue

            # Run full MTF analysis
            alignment = self.analyzer.analyze_pair(
                pair=pair,
                htf_data=htf_data,
                mtf_data=mtf_data,
                ltf_data=ltf_data,
            )

            # Check filters
            passes_filters = self._check_filters(
                alignment=alignment,
                min_alignment=min_alignment or self.min_alignment,
                min_rr_ratio=min_rr_ratio or self.min_rr_ratio,
            )

            if passes_filters:
                opportunities.append(MTFOpportunity(
                    alignment=alignment,
                    passes_filters=True,
                    min_alignment_met=alignment.alignment_score >= (min_alignment or self.min_alignment),
                    min_rr_met=alignment.rr_ratio >= (min_rr_ratio or self.min_rr_ratio),
                    no_conflicts=True,
                ))
            else:
                opportunities.append(MTFOpportunity(
                    alignment=alignment,
                    passes_filters=False,
                    min_alignment_met=alignment.alignment_score >= (min_alignment or self.min_alignment),
                    min_rr_met=alignment.rr_ratio >= (min_rr_ratio or self.min_rr_ratio),
                    no_conflicts=alignment.recommendation != Recommendation.WAIT,
                ))

        # Sort by quality and alignment score
        opportunities.sort(
            key=lambda x: (
                {"HIGHEST": 4, "GOOD": 3, "POOR": 2, "AVOID": 1}.get(
                    x.alignment.quality.value, 0
                ),
                x.alignment.alignment_score,
            ),
            reverse=True,
        )

        logger.info(
            f"Scan complete: {sum(1 for o in opportunities if o.passes_filters)} "
            f"opportunities out of {len(opportunities)} pairs"
        )

        return opportunities

    def scan_pair_detailed(
        self,
        pair: str,
        htf_data: pd.DataFrame,
        mtf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
    ) -> ScanResult:
        """
        Scan single pair with detailed pattern detection.

        Args:
            pair: Trading pair symbol.
            htf_data: HTF OHLCV data.
            mtf_data: MTF OHLCV data.
            ltf_data: LTF OHLCV data.

        Returns:
            ScanResult with full analysis.
        """
        # Run base MTF analysis
        alignment = self.analyzer.analyze_pair(
            pair=pair,
            htf_data=htf_data,
            mtf_data=mtf_data,
            ltf_data=ltf_data,
        )

        # Detect patterns
        patterns = self._detect_patterns(
            htf_bias=alignment.htf_bias,
            mtf_setup=alignment.mtf_setup,
            ltf_entry=alignment.ltf_entry,
        )

        # Detect divergence on MTF
        divergence = self.divergence_detector.detect_divergence(mtf_data)

        # Identify key levels on HTF
        key_levels = self.sr_detector.identify_levels(htf_data, self.config.htf_timeframe)

        # Check filters
        passes_filters = self._check_filters(alignment)

        return ScanResult(
            pair=pair,
            alignment=alignment,
            patterns=patterns,
            divergence=divergence if divergence.divergences else None,
            key_levels=key_levels[:5],  # Top 5 levels
            passes_filters=passes_filters,
        )

    def _check_filters(
        self,
        alignment: MTFAlignment,
        min_alignment: Optional[int] = None,
        min_rr_ratio: Optional[float] = None,
    ) -> bool:
        """
        Check if alignment meets filter criteria.

        Args:
            alignment: MTF alignment to check.
            min_alignment: Minimum alignment score.
            min_rr_ratio: Minimum R:R ratio.

        Returns:
            True if passes all filters.
        """
        min_align = min_alignment or self.min_alignment
        min_rr = min_rr_ratio or self.min_rr_ratio

        # Check alignment score
        if alignment.alignment_score < min_align:
            return False

        # Check R:R ratio
        if alignment.rr_ratio < min_rr:
            return False

        # Check timeframe conflicts
        if self.require_no_conflict and alignment.recommendation == Recommendation.WAIT:
            return False

        return True

    def _detect_patterns(
        self,
        htf_bias: HTFBias,
        mtf_setup: MTFSetup,
        ltf_entry: LTFEntry,
    ) -> List[str]:
        """
        Detect specific MTF patterns.

        Patterns:
        1. HTF Support + LTF Reversal
        2. HTF Trend + MTF Pullback + LTF Entry
        3. Converging Levels (from key_levels)
        4. MTF Divergence at HTF S/R

        Args:
            htf_bias: HTF bias assessment.
            mtf_setup: MTF setup.
            ltf_entry: LTF entry signal.

        Returns:
            List of detected pattern names.
        """
        patterns = []

        # Pattern 1: HTF Support + LTF Reversal
        if (
            htf_bias.direction == MTFDirection.BULLISH
            and htf_bias.price_structure == PriceStructure.UPTREND
            and ltf_entry.signal_type.value in ("ENGULFING", "HAMMER", "PINBAR")
        ):
            patterns.append("HTF Support + LTF Reversal")

        if (
            htf_bias.direction == MTFDirection.BEARISH
            and htf_bias.price_structure == PriceStructure.DOWNTREND
            and ltf_entry.signal_type.value in ("ENGULFING", "HAMMER", "PINBAR")
        ):
            patterns.append("HTF Resistance + LTF Reversal")

        # Pattern 2: HTF Trend + MTF Pullback + LTF Entry
        if (
            htf_bias.direction != MTFDirection.NEUTRAL
            and mtf_setup.setup_type == SetupType.PULLBACK
            and ltf_entry.ema20_reclaim
        ):
            patterns.append("HTF Trend + MTF Pullback + LTF Entry")

        # Pattern 3: Divergence at S/R
        if mtf_setup.rsi_divergence and htf_bias.key_levels:
            patterns.append("MTF Divergence at HTF Level")

        # Pattern 4: All 3 TFs aligned
        if alignment_score := (
            (1 if htf_bias.direction != MTFDirection.NEUTRAL else 0)
            + (1 if mtf_setup.direction == htf_bias.direction else 0)
            + (1 if ltf_entry.direction == htf_bias.direction else 0)
        ) == 3:
            patterns.append("All 3 TFs Aligned")

        return patterns

    def get_high_conviction_opportunities(
        self,
        data_by_pair: Dict[str, Dict[str, pd.DataFrame]],
    ) -> List[MTFOpportunity]:
        """
        Get only highest conviction opportunities (3/3 alignment).

        Args:
            data_by_pair: Dict of pair → {htf, mtf, ltf} DataFrames.

        Returns:
            List of high-conviction MTFOpportunity objects.
        """
        opportunities = self.scan_opportunities(
            data_by_pair,
            min_alignment=3,
            min_rr_ratio=2.0,
        )

        return [o for o in opportunities if o.passes_filters]


def scan_mtf_opportunities(
    data_by_pair: Dict[str, Dict[str, pd.DataFrame]],
    trading_style: TradingStyle = TradingStyle.SWING,
    min_alignment: int = 2,
    min_rr_ratio: float = 2.0,
) -> List[MTFOpportunity]:
    """
    Convenience function to scan for MTF opportunities.

    Args:
        data_by_pair: Dict of pair → {htf, mtf, ltf} DataFrames.
        trading_style: Trading style configuration.
        min_alignment: Minimum alignment score.
        min_rr_ratio: Minimum R:R ratio.

    Returns:
        List of MTFOpportunity objects.
    """
    scanner = MTFOpportunityScanner(
        min_alignment=min_alignment,
        min_rr_ratio=min_rr_ratio,
        trading_style=trading_style,
    )
    return scanner.scan_opportunities(data_by_pair)
