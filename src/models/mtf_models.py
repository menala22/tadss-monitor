"""
Data models for Multi-Timeframe (MTF) Analysis.

This module defines dataclasses and enums for representing multi-timeframe
analysis results, including bias assessments, setup identification, entry
signals, and alignment scoring.

MTF Framework:
- HTF (Higher Timeframe): Directional bias using 50/200 SMA + price structure
- MidTF (Middle Timeframe): Setup identification using 20/50 SMA + RSI divergence
- LTF (Lower Timeframe): Entry timing using price action + 20 EMA + RSI

Note: We use "MidTF" instead of "MTF" for the middle timeframe to avoid
confusion with "MTF" which refers to the overall Multi-Timeframe system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional


# =============================================================================
# ENUMS
# =============================================================================


class MTFDirection(str, Enum):
    """Direction enum for MTF analysis."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PriceStructure(str, Enum):
    """Price structure classification."""

    UPTREND = "HH/HL"  # Higher Highs / Higher Lows
    DOWNTREND = "LH/LL"  # Lower Highs / Lower Lows
    RANGE = "RANGE"


class SMASlope(str, Enum):
    """Simple Moving Average slope direction."""

    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class PriceVsSMA(str, Enum):
    """Price position relative to SMA."""

    ABOVE = "ABOVE"
    BELOW = "BELOW"
    AT = "AT"


class SetupType(str, Enum):
    """MTF setup type classification."""

    PULLBACK = "PULLBACK"
    BREAKOUT = "BREAKOUT"
    DIVERGENCE = "DIVERGENCE"
    CONSOLIDATION = "CONSOLIDATION"
    RANGE_LOW = "RANGE_LOW"
    RANGE_HIGH = "RANGE_HIGH"


class EntrySignalType(str, Enum):
    """LTF entry signal type."""

    ENGULFING = "ENGULFING"
    HAMMER = "HAMMER"
    PINBAR = "PINBAR"
    INSIDE_BAR = "INSIDE_BAR"
    BREAKOUT = "BREAKOUT"
    NONE = "NONE"


class RSITurn(str, Enum):
    """RSI turning direction from key levels."""

    UP_FROM_OVERSOLD = "UP_FROM_OVERSOLD"
    DOWN_FROM_OVERBOUGHT = "DOWN_FROM_OVERBOUGHT"
    NONE = "NONE"


class AlignmentQuality(str, Enum):
    """MTF alignment quality rating."""

    HIGHEST = "HIGHEST"  # 3/3 aligned
    GOOD = "GOOD"  # 2/3 aligned
    POOR = "POOR"  # 1/3 aligned
    AVOID = "AVOID"  # 0/3 aligned


class Recommendation(str, Enum):
    """Trade recommendation."""

    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    AVOID = "AVOID"


class DataQualityStatus(str, Enum):
    """Data quality status."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class MTFContext(str, Enum):
    """
    MTF market context classification.
    
    Context-first architecture: classify market state BEFORE running setup detection.
    Only valid setups for the classified context will be evaluated.
    """
    
    TRENDING_PULLBACK = "TRENDING_PULLBACK"      # In trend, pulling back to structure — setups valid
    TRENDING_EXTENSION = "TRENDING_EXTENSION"    # In trend, extended from MAs — WAIT, no setups
    BREAKING_OUT = "BREAKING_OUT"                # Consolidation resolving — breakout setups valid
    CONSOLIDATING = "CONSOLIDATING"              # Range-bound — range setups only or WAIT
    REVERSING = "REVERSING"                      # Structure breaking, trend change — divergence/reversal setups


@dataclass
class TimeframeDataQuality:
    """
    Data quality for a single timeframe.

    Attributes:
        timeframe: Timeframe name (e.g., '1w', '1d', '4h').
        candle_count: Number of candles available.
        required_count: Minimum candles needed for full analysis.
        is_sufficient: Whether candle count is sufficient.
        freshness_hours: Hours since last candle was fetched.
        max_freshness_hours: Maximum acceptable freshness for this TF.
        is_fresh: Whether data is fresh enough.
        status: Overall status (PASS/WARNING/FAIL).
        issues: List of quality issues.
    """
    timeframe: str
    candle_count: int
    required_count: int
    is_sufficient: bool
    freshness_hours: float
    max_freshness_hours: float
    is_fresh: bool
    status: DataQualityStatus
    issues: List[str] = field(default_factory=list)


@dataclass
class DataQualityReport:
    """
    Complete data quality report.

    Attributes:
        overall_status: Overall quality status.
        htf_quality: HTF data quality.
        mtf_quality: MTF data quality.
        ltf_quality: LTF data quality.
        has_conflicts: Any timeframe conflicts.
        is_mtf_ready: Whether MTF analysis can proceed.
        summary: Human-readable summary.
        recommendations: List of recommendations to improve quality.
    """
    overall_status: DataQualityStatus
    htf_quality: TimeframeDataQuality
    mtf_quality: TimeframeDataQuality
    ltf_quality: TimeframeDataQuality
    has_conflicts: bool
    is_mtf_ready: bool
    summary: str
    recommendations: List[str] = field(default_factory=list)


class DivergenceType(str, Enum):
    """RSI divergence type."""

    REGULAR_BULLISH = "REGULAR_BULLISH"
    REGULAR_BEARISH = "REGULAR_BEARISH"
    HIDDEN_BULLISH = "HIDDEN_BULLISH"
    HIDDEN_BEARISH = "HIDDEN_BEARISH"


class TargetMethod(str, Enum):
    """Profit target calculation method."""

    SR_LEVEL = "S/R"  # Next HTF S/R level
    MEASURED_MOVE = "MEASURED_MOVE"  # Pattern target
    FIBONACCI = "FIBONACCI"  # Fib extension
    ATR = "ATR"  # ATR-based
    PRIOR_SWING = "PRIOR_SWING"  # Prior swing high/low


class LevelType(str, Enum):
    """Support/Resistance level type."""

    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"


class LevelStrength(str, Enum):
    """S/R level strength classification."""

    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class TradingStyle(str, Enum):
    """Trading style for MTF timeframe configuration."""

    POSITION = "POSITION"  # Monthly → Weekly → Daily
    SWING = "SWING"  # Weekly → Daily → 4H
    INTRADAY = "INTRADAY"  # Daily → 4H → 1H
    DAY = "DAY"  # 4H → 1H → 15M
    SCALPING = "SCALPING"  # 1H → 15M → 1-5M


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SwingPoint:
    """
    Represents a swing high or low point.

    Attributes:
        price: Price at the swing point.
        index: Candle index where swing occurred.
        timestamp: Timestamp of the swing candle.
        swing_type: 'HIGH' or 'LOW'.
        strength: Strength score (0.0-1.0) based on surrounding candles.
    """

    price: float
    index: int
    timestamp: str
    swing_type: Literal["HIGH", "LOW"]
    strength: float = 1.0


@dataclass
class SupportResistanceLevel:
    """
    Represents a support or resistance level.

    Attributes:
        price: Price level.
        level_type: SUPPORT or RESISTANCE.
        strength: STRONG, MEDIUM, or WEAK.
        touch_count: Number of times price tested this level.
        timeframe_origin: Timeframe where level was identified.
        last_tested: Timestamp of last test.
    """

    price: float
    level_type: LevelType
    strength: LevelStrength = LevelStrength.MEDIUM
    touch_count: int = 1
    timeframe_origin: str = "unknown"
    last_tested: Optional[str] = None


@dataclass
class ConvergingLevel:
    """
    Represents a converging S/R level across multiple timeframes.

    Converging levels (same price on multiple TFs) are extremely
    significant and often act as strong support/resistance.

    Attributes:
        avg_price: Average price across converging levels.
        level_type: SUPPORT or RESISTANCE.
        strength: STRONG, MEDIUM, or WEAK.
        timeframes: List of timeframes where level appears.
        level_count: Number of individual levels converging.
    """

    avg_price: float
    level_type: LevelType
    strength: LevelStrength = LevelStrength.MEDIUM
    timeframes: List[str] = field(default_factory=list)
    level_count: int = 1


@dataclass
class HTFBias:
    """
    Higher Timeframe bias assessment.

    HTF analysis uses structural tools only (MA, price structure, S/R).
    Do NOT use oscillators (RSI, MACD) on HTF — they lag too much.

    Attributes:
        direction: BULLISH, BEARISH, or NEUTRAL.
        confidence: Confidence score 0.0-1.0.
        price_structure: HH/HL (uptrend), LH/LL (downtrend), or RANGE.
        sma50_slope: UP, DOWN, or FLAT.
        price_vs_sma50: ABOVE or BELOW.
        price_vs_sma200: ABOVE or BELOW.
        key_levels: List of significant S/R levels.
        swing_sequence: List of recent swing points confirming structure.
        warning: Optional warning message (e.g., "insufficient data").
    """

    direction: MTFDirection = MTFDirection.NEUTRAL
    confidence: float = 0.0
    price_structure: PriceStructure = PriceStructure.RANGE
    sma50_slope: SMASlope = SMASlope.FLAT  # Legacy: actually EMA20 slope
    price_vs_sma50: PriceVsSMA = PriceVsSMA.BELOW  # Legacy: actually price vs EMA20
    price_vs_sma200: PriceVsSMA = PriceVsSMA.BELOW  # Legacy: actually price vs EMA50
    ema20_value: Optional[float] = None  # NEW: Actual EMA20 value
    ema50_value: Optional[float] = None  # NEW: Actual EMA50 value
    ema20_slope: SMASlope = SMASlope.FLAT  # NEW: EMA20 slope
    ema50_slope: SMASlope = SMASlope.FLAT  # NEW: EMA50 slope
    key_levels: List[SupportResistanceLevel] = field(default_factory=list)
    swing_sequence: List[SwingPoint] = field(default_factory=list)
    warning: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "direction": self.direction.value,
            "confidence": round(self.confidence, 2),
            "price_structure": self.price_structure.value,
            "sma50_slope": self.sma50_slope.value,  # Legacy
            "price_vs_sma50": self.price_vs_sma50.value,  # Legacy
            "price_vs_sma200": self.price_vs_sma200.value,  # Legacy
            "ema20_value": round(self.ema20_value, 2) if self.ema20_value else None,  # NEW
            "ema50_value": round(self.ema50_value, 2) if self.ema50_value else None,  # NEW
            "ema20_slope": self.ema20_slope.value,  # NEW
            "ema50_slope": self.ema50_slope.value,  # NEW
            "key_levels": [
                {
                    "price": lvl.price,
                    "type": lvl.level_type.value,
                    "strength": lvl.strength.value,
                }
                for lvl in self.key_levels
            ],
            "swing_sequence": [
                {"price": sp.price, "type": sp.swing_type, "strength": sp.strength}
                for sp in self.swing_sequence
            ],
            "warning": self.warning,
        }


@dataclass
class PullbackSetup:
    """
    Details of a pullback setup on MTF.

    Attributes:
        approaching_sma: Which SMA price is approaching (20 or 50).
        distance_to_sma_pct: Distance from SMA as percentage.
        rsi_level: Current RSI value.
        rsi_approaching_40: Whether RSI is approaching 40 (in uptrend).
        volume_declining: Whether volume is declining during pullback.
    """

    approaching_sma: Literal[20, 50, None] = None
    distance_to_sma_pct: float = 0.0
    rsi_level: Optional[float] = None
    rsi_approaching_40: bool = False
    volume_declining: bool = False


@dataclass
class PullbackQualityScore:
    """
    Multi-factor pullback quality scoring result.
    
    Replaces flat confidence calculation with proper weighted scoring.
    
    Attributes:
        total_score: Overall quality score 0.0-1.0.
        distance_score: ATR-normalized distance to EMA score (25% weight).
        rsi_score: RSI compression zone score (20% weight).
        volume_score: Impulse vs pullback volume score (25% weight).
        confluence_score: HTF level confluence score (20% weight).
        structure_score: Candle structure score (10% weight).
        reasons: List of human-readable reasons for the score.
    """
    
    total_score: float = 0.0
    distance_score: float = 0.0
    rsi_score: float = 0.0
    volume_score: float = 0.0
    confluence_score: float = 0.0
    structure_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "total_score": round(self.total_score, 2),
            "distance_score": round(self.distance_score, 2),
            "rsi_score": round(self.rsi_score, 2),
            "volume_score": round(self.volume_score, 2),
            "confluence_score": round(self.confluence_score, 2),
            "structure_score": round(self.structure_score, 2),
            "reasons": self.reasons,
        }


@dataclass
class MTFContextResult:
    """
    MTF context classification result.
    
    Layer 1 of the upgraded MTF system.
    
    Attributes:
        context: Classified MTF context.
        confidence: Confidence score 0.0-1.0.
        adx: ADX value at classification.
        atr: ATR value at classification.
        distance_from_ema_atr: Distance from EMA21 in ATR units.
        reasoning: Human-readable explanation of classification.
    """
    
    context: MTFContext = MTFContext.CONSOLIDATING
    confidence: float = 0.0
    adx: float = 0.0
    atr: float = 0.0
    distance_from_ema_atr: float = 0.0
    reasoning: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "context": self.context.value,
            "confidence": round(self.confidence, 2),
            "adx": round(self.adx, 2),
            "atr": round(self.atr, 2),
            "distance_from_ema_atr": round(self.distance_from_ema_atr, 2),
            "reasoning": self.reasoning,
        }


# Setup validity mapping by context
# Layer 2: Context-gated setup detection
VALID_SETUPS_BY_CONTEXT = {
    MTFContext.TRENDING_PULLBACK: [SetupType.PULLBACK],
    MTFContext.TRENDING_EXTENSION: [],  # NO setups - wait for pullback
    MTFContext.BREAKING_OUT: [SetupType.BREAKOUT, SetupType.CONSOLIDATION],
    MTFContext.CONSOLIDATING: [SetupType.RANGE_LOW, SetupType.RANGE_HIGH],
    MTFContext.REVERSING: [SetupType.DIVERGENCE],
}


@dataclass
class MTFSetup:
    """
    MidTF (Middle Timeframe) setup identification.

    The MidTF analysis identifies tradeable setups in the direction of HTF bias.

    UPGRADED: Now uses EMA (Exponential Moving Average) instead of SMA for faster response.

    Attributes:
        setup_type: PULLBACK, BREAKOUT, DIVERGENCE, CONSOLIDATION, etc.
        direction: BULLISH or BEARISH.
        confidence: Confidence score 0.0-1.0.
        sma20_action: SUPPORT, RESISTANCE, or NONE. (Legacy - actually EMA20)
        sma50_action: SUPPORT, RESISTANCE, or NONE. (Legacy - actually EMA50)
        ema20_action: SUPPORT, RESISTANCE, or NONE. (NEW - EMA20 action)
        ema50_action: SUPPORT, RESISTANCE, or NONE. (NEW - EMA50 action)
        rsi_divergence: BULLISH, BEARISH, or None.
        volume_confirms: Whether volume confirms the setup.
        pullback_details: Optional pullback setup details.
        consolidation_pattern: Optional consolidation pattern type.
        warning: Optional warning message.
        mtf_context: MidTF market context (Layer 1 classification).
        pullback_quality_score: Multi-factor quality score (Layer 3).
    """

    setup_type: SetupType = SetupType.CONSOLIDATION
    direction: MTFDirection = MTFDirection.NEUTRAL
    confidence: float = 0.0
    sma20_action: Literal["SUPPORT", "RESISTANCE", "NONE"] = "NONE"  # Legacy field name (actually EMA20)
    sma50_action: Literal["SUPPORT", "RESISTANCE", "NONE"] = "NONE"  # Legacy field name (actually EMA50)
    ema20_action: Literal["SUPPORT", "RESISTANCE", "NONE"] = "NONE"  # NEW: EMA20 action
    ema50_action: Literal["SUPPORT", "RESISTANCE", "NONE"] = "NONE"  # NEW: EMA50 action
    rsi_divergence: Optional[DivergenceType] = None
    volume_confirms: bool = False
    pullback_details: Optional[PullbackSetup] = None
    consolidation_pattern: Optional[str] = None
    warning: Optional[str] = None
    mtf_context: Optional[MTFContext] = None  # Legacy: just the context enum
    mtf_context_result: Optional[MTFContextResult] = None  # NEW: full context result with metrics
    pullback_quality_score: Optional[PullbackQualityScore] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "setup_type": self.setup_type.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 2),
            "sma20_action": self.sma20_action,  # Legacy
            "sma50_action": self.sma50_action,  # Legacy
            "ema20_action": self.ema20_action,  # NEW
            "ema50_action": self.ema50_action,  # NEW
            "rsi_divergence": self.rsi_divergence.value if self.rsi_divergence else None,
            "volume_confirms": self.volume_confirms,
            "warning": self.warning,
            "mtf_context": self.mtf_context.value if self.mtf_context else None,  # Legacy
            "mtf_context_result": self.mtf_context_result.to_dict() if self.mtf_context_result else None,  # NEW
        }
        if self.pullback_details:
            result["pullback_details"] = {
                "approaching_sma": self.pullback_details.approaching_sma,
                "distance_to_sma_pct": round(self.pullback_details.distance_to_sma_pct, 2),
                "rsi_level": round(self.pullback_details.rsi_level, 2) if self.pullback_details.rsi_level else None,
            }
        if self.pullback_quality_score:
            result["pullback_quality_score"] = self.pullback_quality_score.to_dict()
        return result


@dataclass
class LTFEntry:
    """
    Lower Timeframe entry signal.

    LTF analysis finds precise entry points within the MTF setup.

    Attributes:
        signal_type: ENGULFING, HAMMER, PINBAR, BREAKOUT, or NONE.
        direction: BULLISH or BEARISH.
        ema20_reclaim: Whether price reclaimed 20 EMA after pullback.
        rsi_turning: RSI turning from key levels.
        entry_price: Suggested entry price (on confirmation candle close).
        stop_loss: Suggested stop loss level.
        confirmation_candle_close: Close price of confirmation candle.
        confirmation_candle_timestamp: Timestamp of confirmation candle.
        confidence: Confidence score 0.0-1.0 for LTF entry.
        warning: Optional warning message.
    """

    signal_type: EntrySignalType = EntrySignalType.NONE
    direction: MTFDirection = MTFDirection.NEUTRAL
    ema20_reclaim: bool = False
    rsi_turning: RSITurn = RSITurn.NONE
    entry_price: float = 0.0
    stop_loss: float = 0.0
    confirmation_candle_close: float = 0.0
    confirmation_candle_timestamp: Optional[datetime] = None
    confidence: float = 0.5
    warning: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "signal_type": self.signal_type.value,
            "direction": self.direction.value,
            "ema20_reclaim": self.ema20_reclaim,
            "rsi_turning": self.rsi_turning.value,
            "entry_price": round(self.entry_price, 4) if self.entry_price else None,
            "stop_loss": round(self.stop_loss, 4) if self.stop_loss else None,
            "confirmation_candle_close": round(self.confirmation_candle_close, 4) if self.confirmation_candle_close else None,
            "confirmation_candle_timestamp": self.confirmation_candle_timestamp.isoformat() if self.confirmation_candle_timestamp else None,
            "confidence": round(self.confidence, 2),
            "warning": self.warning,
        }


@dataclass
class TargetResult:
    """
    Profit target calculation result.

    Attributes:
        target_price: Calculated target price.
        method: TargetMethod used.
        confidence: Confidence score 0.0-1.0.
        rr_ratio: Risk:Reward ratio from entry to target.
        description: Human-readable description of the target.
    """

    target_price: float
    method: TargetMethod
    confidence: float = 0.5
    rr_ratio: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "target_price": round(self.target_price, 4),
            "method": self.method.value,
            "confidence": round(self.confidence, 2),
            "rr_ratio": round(self.rr_ratio, 2),
            "description": self.description,
        }


@dataclass
class DivergenceSignal:
    """
    RSI divergence signal.

    Attributes:
        divergence_type: REGULAR_BULLISH, REGULAR_BEARISH, etc.
        price_swing_1: First price swing point.
        price_swing_2: Second price swing point.
        rsi_swing_1: First RSI swing point.
        rsi_swing_2: Second RSI swing point.
        confidence: Confidence score 0.0-1.0.
        timestamp: When the divergence was detected.
    """

    divergence_type: DivergenceType
    price_swing_1: SwingPoint
    price_swing_2: SwingPoint
    rsi_swing_1: float
    rsi_swing_2: float
    confidence: float = 0.5
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "divergence_type": self.divergence_type.value,
            "price_swing_1": {"price": self.price_swing_1.price, "type": self.price_swing_1.swing_type},
            "price_swing_2": {"price": self.price_swing_2.price, "type": self.price_swing_2.swing_type},
            "rsi_swing_1": round(self.rsi_swing_1, 2),
            "rsi_swing_2": round(self.rsi_swing_2, 2),
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class MTFAlignment:
    """
    Combined multi-timeframe alignment score.

    This is the primary output of MTF (Multi-Timeframe) analysis, combining HTF bias,
    MidTF setup, and LTF entry into a single recommendation.

    Attributes:
        pair: Trading pair symbol.
        timestamp: Analysis timestamp.
        htf_bias: Higher timeframe bias assessment.
        mtf_setup: MidTF (middle timeframe) setup.
        ltf_entry: Lower timeframe entry signal.
        alignment_score: Count of aligned timeframes (0-3) - legacy binary scoring.
        alignment_pct: Percentage alignment (0-100).
        quality: HIGHEST, GOOD, POOR, or AVOID.
        recommendation: BUY, SELL, WAIT, or AVOID.
        target: Optional profit target.
        rr_ratio: Risk:Reward ratio.
        trading_style: Trading style configuration used.
        notes: Optional analysis notes.
        weighted_score: Confidence-weighted alignment score 0.0-1.0 (Layer 4).
        position_size_pct: Recommended position size as % of base risk.
    """

    pair: str = ""
    timestamp: str = ""
    htf_bias: HTFBias = field(default_factory=HTFBias)
    mtf_setup: MTFSetup = field(default_factory=MTFSetup)
    ltf_entry: LTFEntry = field(default_factory=LTFEntry)
    alignment_score: int = 0
    alignment_pct: float = 0.0
    quality: AlignmentQuality = AlignmentQuality.AVOID
    recommendation: Recommendation = Recommendation.AVOID
    target: Optional[TargetResult] = None
    rr_ratio: float = 0.0
    trading_style: TradingStyle = TradingStyle.SWING
    notes: str = ""
    weighted_score: float = 0.0
    position_size_pct: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "pair": self.pair,
            "timestamp": self.timestamp,
            "htf_bias": self.htf_bias.to_dict(),
            "mtf_setup": self.mtf_setup.to_dict(),
            "ltf_entry": self.ltf_entry.to_dict(),
            "alignment_score": self.alignment_score,
            "alignment_pct": round(self.alignment_pct, 1),
            "quality": self.quality.value,
            "recommendation": self.recommendation.value,
            "target": self.target.to_dict() if self.target else None,
            "rr_ratio": round(self.rr_ratio, 2),
            "trading_style": self.trading_style.value,
            "notes": self.notes,
            "weighted_score": round(self.weighted_score, 2),
            "position_size_pct": round(self.position_size_pct, 2),
        }


@dataclass
class MTFOpportunity:
    """
    A trading opportunity identified by MTF analysis.

    This is a filtered MTFAlignment that meets minimum criteria
    for presentation to the user.

    Attributes:
        alignment: Full MTF alignment analysis.
        passes_filters: Whether opportunity meets minimum criteria.
        min_alignment_met: Whether alignment score meets minimum.
        min_rr_met: Whether R:R meets minimum (2:1).
        no_conflicts: Whether timeframes are not in conflict.
    """

    alignment: MTFAlignment
    passes_filters: bool = False
    min_alignment_met: bool = False
    min_rr_met: bool = False
    no_conflicts: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = self.alignment.to_dict()
        result["filters"] = {
            "passes_filters": self.passes_filters,
            "min_alignment_met": self.min_alignment_met,
            "min_rr_met": self.min_rr_met,
            "no_conflicts": self.no_conflicts,
        }
        return result


# =============================================================================
# TIMEFRAME CONFIGURATIONS
# =============================================================================


@dataclass
class MTFTimeframeConfig:
    """
    Configuration for a 3-timeframe setup based on trading style.

    Class Attributes:
        trading_style: POSITION, SWING, INTRADAY, DAY, or SCALPING.
        htf_timeframe: Higher timeframe (directional bias).
        mtf_timeframe: MidTF (middle timeframe for setup identification).
        ltf_timeframe: Lower timeframe (entry timing).

    Common Timeframe Combinations:
        | Trading Style | HTF    | MidTF   | LTF      |
        |--------------|--------|---------|----------|
        | POSITION     | Monthly| Weekly  | Daily    |
        | SWING        | Weekly | Daily   | 4H       |
        | INTRADAY     | Daily  | 4H      | 1H       |
        | DAY          | 4H     | 1H      | 15M      |
        | SCALPING     | 1H     | 15M   | 1-5M     |

    General rule: Entry timeframe should be 4-6× smaller than setup timeframe.
    """

    trading_style: TradingStyle
    htf_timeframe: str
    mtf_timeframe: str
    ltf_timeframe: str

    # Predefined configurations
    CONFIGS = {
        TradingStyle.POSITION: ("M1", "w1", "d1"),
        TradingStyle.SWING: ("w1", "d1", "h4"),
        TradingStyle.INTRADAY: ("d1", "h4", "h1"),
        TradingStyle.DAY: ("h4", "h1", "m15"),
        TradingStyle.SCALPING: ("h1", "m15", "m5"),
    }

    @classmethod
    def get_config(cls, style: TradingStyle) -> "MTFTimeframeConfig":
        """
        Get MTF timeframe configuration for a trading style.

        Args:
            style: Trading style (POSITION, SWING, INTRADAY, DAY, SCALPING).

        Returns:
            MTFTimeframeConfig instance.

        Example:
            >>> config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
            >>> config.htf_timeframe
            'w1'
            >>> config.mtf_timeframe
            'd1'
            >>> config.ltf_timeframe
            'h4'
        """
        htf, mtf, ltf = cls.CONFIGS[style]
        return cls(
            trading_style=style,
            htf_timeframe=htf,
            mtf_timeframe=mtf,
            ltf_timeframe=ltf,
        )

    @classmethod
    def get_all_configs(cls) -> dict[str, dict[str, str]]:
        """
        Get all available MTF configurations.

        Returns:
            Dictionary of style name → timeframe dict.

        Example:
            >>> configs = MTFTimeframeConfig.get_all_configs()
            >>> configs['SWING']
            {'htf': 'w1', 'mtf': 'd1', 'ltf': 'h4'}
        """
        return {
            style.value: {
                "htf": cfg[0],
                "mtf": cfg[1],
                "ltf": cfg[2],
            }
            for style, cfg in cls.CONFIGS.items()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "trading_style": self.trading_style.value,
            "htf_timeframe": self.htf_timeframe,
            "mtf_timeframe": self.mtf_timeframe,
            "ltf_timeframe": self.ltf_timeframe,
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def determine_alignment_quality(score: int) -> AlignmentQuality:
    """
    Determine alignment quality from score.

    Args:
        score: Alignment score (0-3).

    Returns:
        AlignmentQuality enum value.

    Rules:
        - 3 = HIGHEST (trade aggressively)
        - 2 = GOOD (standard risk)
        - 1 = POOR (avoid or reduce size)
        - 0 = AVOID (do not trade)
    """
    quality_map = {
        3: AlignmentQuality.HIGHEST,
        2: AlignmentQuality.GOOD,
        1: AlignmentQuality.POOR,
        0: AlignmentQuality.AVOID,
    }
    return quality_map.get(score, AlignmentQuality.AVOID)


def determine_recommendation(
    alignment_score: int,
    htf_direction: MTFDirection,
    mtf_direction: MTFDirection,
    ltf_direction: MTFDirection,
) -> Recommendation:
    """
    Determine trade recommendation from alignment.

    Args:
        alignment_score: Count of aligned timeframes (0-3).
        htf_direction: HTF bias direction.
        mtf_direction: MTF setup direction.
        ltf_direction: LTF entry direction.

    Returns:
        Recommendation enum value.

    Rules:
        - All 3 aligned bullish = BUY (aggressive)
        - All 3 aligned bearish = SELL (aggressive)
        - 2 of 3 aligned = WAIT for full alignment
        - 0 or 1 aligned = AVOID
        - Conflicting directions = WAIT
    """
    if alignment_score < 2:
        return Recommendation.AVOID

    if alignment_score == 3:
        if htf_direction == MTFDirection.BULLISH:
            return Recommendation.BUY
        elif htf_direction == MTFDirection.BEARISH:
            return Recommendation.SELL

    # Score = 2 but not all aligned = WAIT
    return Recommendation.WAIT


def check_timeframe_conflict(
    htf_direction: MTFDirection,
    mtf_direction: MTFDirection,
    ltf_direction: MTFDirection,
) -> tuple[bool, Optional[str]]:
    """
    Check for timeframe conflicts.

    Args:
        htf_direction: HTF bias direction.
        mtf_direction: MTF setup direction.
        ltf_direction: LTF entry direction.

    Returns:
        Tuple of (has_conflict, conflict_message).

    Conflict Rules:
        - HTF bullish, MTF bearish = WAIT for MTF confirmation
        - HTF + MTF bullish, LTF bearish = WAIT for LTF confirmation
        - All 3 different = Range Protocol may apply
    """
    directions = [htf_direction, mtf_direction, ltf_direction]
    unique_directions = set(d for d in directions if d != MTFDirection.NEUTRAL)

    # All same (excluding NEUTRAL) = no conflict
    if len(unique_directions) <= 1:
        return False, None

    # Check specific conflicts
    if htf_direction == MTFDirection.BULLISH and mtf_direction == MTFDirection.BEARISH:
        return True, "HTF bullish, MTF bearish — wait for MTF confirmation"

    if htf_direction == MTFDirection.BEARISH and mtf_direction == MTFDirection.BULLISH:
        return True, "HTF bearish, MTF bullish — wait for MTF confirmation"

    if (
        htf_direction in (MTFDirection.BULLISH, MTFDirection.BEARISH)
        and mtf_direction == htf_direction
        and ltf_direction != htf_direction
        and ltf_direction != MTFDirection.NEUTRAL
    ):
        return True, f"HTF+MTF aligned, LTF conflicting — wait for LTF confirmation"

    # All 3 different
    if len(unique_directions) == 3:
        return True, "All timeframes conflicting — Range Protocol may apply"

    return False, None
