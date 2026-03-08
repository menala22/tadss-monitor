"""
Unit tests for MTF data models.

Tests for:
- MTFTimeframeConfig
- HTFBias, MTFSetup, LTFEntry
- MTFAlignment
- Helper functions
"""

import pytest
from datetime import datetime

from src.models.mtf_models import (
    MTFDirection,
    PriceStructure,
    SMASlope,
    PriceVsSMA,
    SetupType,
    EntrySignalType,
    RSITurn,
    AlignmentQuality,
    Recommendation,
    DivergenceType,
    TargetMethod,
    LevelType,
    LevelStrength,
    TradingStyle,
    SwingPoint,
    SupportResistanceLevel,
    HTFBias,
    MTFSetup,
    LTFEntry,
    TargetResult,
    MTFAlignment,
    MTFTimeframeConfig,
    PullbackSetup,
    determine_alignment_quality,
    determine_recommendation,
    check_timeframe_conflict,
)


class TestMTFDirection:
    """Test MTFDirection enum."""

    def test_direction_values(self):
        """Test enum values exist."""
        assert MTFDirection.BULLISH.value == "BULLISH"
        assert MTFDirection.BEARISH.value == "BEARISH"
        assert MTFDirection.NEUTRAL.value == "NEUTRAL"


class TestSwingPoint:
    """Test SwingPoint dataclass."""

    def test_swing_point_creation(self):
        """Test creating a swing point."""
        swing = SwingPoint(
            price=45000.0,
            index=100,
            timestamp="2026-03-07T10:00:00",
            swing_type="HIGH",
            strength=0.8,
        )
        assert swing.price == 45000.0
        assert swing.swing_type == "HIGH"
        assert swing.strength == 0.8


class TestSupportResistanceLevel:
    """Test SupportResistanceLevel dataclass."""

    def test_support_level_creation(self):
        """Test creating a support level."""
        level = SupportResistanceLevel(
            price=44000.0,
            level_type=LevelType.SUPPORT,
            strength=LevelStrength.STRONG,
            touch_count=3,
        )
        assert level.price == 44000.0
        assert level.level_type == LevelType.SUPPORT
        assert level.strength == LevelStrength.STRONG
        assert level.touch_count == 3


class TestHTFBias:
    """Test HTFBias dataclass."""

    def test_htf_bias_default_values(self):
        """Test HTFBias default values."""
        bias = HTFBias()
        assert bias.direction == MTFDirection.NEUTRAL
        assert bias.confidence == 0.0
        assert bias.price_structure == PriceStructure.RANGE
        assert bias.sma50_slope == SMASlope.FLAT

    def test_htf_bias_bullish(self):
        """Test bullish HTFBias."""
        bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.85,
            price_structure=PriceStructure.UPTREND,
            sma50_slope=SMASlope.UP,
            price_vs_sma50=PriceVsSMA.ABOVE,
            price_vs_sma200=PriceVsSMA.ABOVE,
        )
        assert bias.direction == MTFDirection.BULLISH
        assert bias.confidence == 0.85

    def test_htf_bias_to_dict(self):
        """Test HTFBias to_dict method."""
        bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.75,
            price_structure=PriceStructure.UPTREND,
        )
        result = bias.to_dict()
        assert result["direction"] == "BULLISH"
        assert result["confidence"] == 0.75
        assert result["price_structure"] == "HH/HL"


class TestMTFSetup:
    """Test MTFSetup dataclass."""

    def test_mtf_setup_default_values(self):
        """Test MTFSetup default values."""
        setup = MTFSetup()
        assert setup.setup_type == SetupType.CONSOLIDATION
        assert setup.direction == MTFDirection.NEUTRAL
        assert setup.confidence == 0.0

    def test_mtf_setup_pullback(self):
        """Test pullback setup."""
        pullback = PullbackSetup(
            approaching_sma=50,
            distance_to_sma_pct=0.02,
            rsi_level=42.0,
            rsi_approaching_40=True,
        )
        setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.7,
            pullback_details=pullback,
        )
        assert setup.setup_type == SetupType.PULLBACK
        assert setup.pullback_details.approaching_sma == 50

    def test_mtf_setup_to_dict(self):
        """Test MTFSetup to_dict method."""
        setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.65,
        )
        result = setup.to_dict()
        assert result["setup_type"] == "PULLBACK"
        assert result["direction"] == "BULLISH"
        assert result["confidence"] == 0.65


class TestLTFEntry:
    """Test LTFEntry dataclass."""

    def test_ltf_entry_default_values(self):
        """Test LTFEntry default values."""
        entry = LTFEntry()
        assert entry.signal_type == EntrySignalType.NONE
        assert entry.direction == MTFDirection.NEUTRAL
        assert entry.ema20_reclaim is False

    def test_ltf_entry_bullish_engulfing(self):
        """Test bullish engulfing entry."""
        entry = LTFEntry(
            signal_type=EntrySignalType.ENGULFING,
            direction=MTFDirection.BULLISH,
            ema20_reclaim=True,
            rsi_turning=RSITurn.UP_FROM_OVERSOLD,
            entry_price=45100.0,
            stop_loss=44800.0,
        )
        assert entry.signal_type == EntrySignalType.ENGULFING
        assert entry.ema20_reclaim is True
        assert entry.rsi_turning == RSITurn.UP_FROM_OVERSOLD

    def test_ltf_entry_to_dict(self):
        """Test LTFEntry to_dict method."""
        entry = LTFEntry(
            signal_type=EntrySignalType.HAMMER,
            direction=MTFDirection.BULLISH,
            entry_price=45100.0,
            stop_loss=44800.0,
        )
        result = entry.to_dict()
        assert result["signal_type"] == "HAMMER"
        assert result["entry_price"] == 45100.0


class TestTargetResult:
    """Test TargetResult dataclass."""

    def test_target_result_creation(self):
        """Test TargetResult creation."""
        target = TargetResult(
            target_price=46000.0,
            method=TargetMethod.SR_LEVEL,
            confidence=0.8,
            rr_ratio=2.5,
            description="Next HTF resistance level",
        )
        assert target.target_price == 46000.0
        assert target.method == TargetMethod.SR_LEVEL
        assert target.rr_ratio == 2.5


class TestMTFAlignment:
    """Test MTFAlignment dataclass."""

    def test_mtf_alignment_default_values(self):
        """Test MTFAlignment default values."""
        alignment = MTFAlignment()
        assert alignment.alignment_score == 0
        assert alignment.quality == AlignmentQuality.AVOID
        assert alignment.recommendation == Recommendation.AVOID

    def test_mtf_alignment_bullish(self):
        """Test bullish MTF alignment."""
        alignment = MTFAlignment(
            pair="BTC/USDT",
            htf_bias=HTFBias(direction=MTFDirection.BULLISH, confidence=0.8),
            mtf_setup=MTFSetup(direction=MTFDirection.BULLISH, confidence=0.7),
            ltf_entry=LTFEntry(direction=MTFDirection.BULLISH),
            alignment_score=3,
            alignment_pct=100.0,
            quality=AlignmentQuality.HIGHEST,
            recommendation=Recommendation.BUY,
            rr_ratio=2.5,
        )
        assert alignment.pair == "BTC/USDT"
        assert alignment.alignment_score == 3
        assert alignment.quality == AlignmentQuality.HIGHEST
        assert alignment.recommendation == Recommendation.BUY

    def test_mtf_alignment_to_dict(self):
        """Test MTFAlignment to_dict method."""
        alignment = MTFAlignment(
            pair="ETH/USDT",
            alignment_score=2,
            quality=AlignmentQuality.GOOD,
        )
        result = alignment.to_dict()
        assert result["pair"] == "ETH/USDT"
        assert result["alignment_score"] == 2
        assert result["quality"] == "GOOD"


class TestMTFTimeframeConfig:
    """Test MTFTimeframeConfig dataclass."""

    def test_get_swing_config(self):
        """Test swing trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
        assert config.trading_style == TradingStyle.SWING
        assert config.htf_timeframe == "w1"
        assert config.mtf_timeframe == "d1"
        assert config.ltf_timeframe == "h4"

    def test_get_intraday_config(self):
        """Test intraday trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.INTRADAY)
        assert config.htf_timeframe == "d1"
        assert config.mtf_timeframe == "h4"
        assert config.ltf_timeframe == "h1"

    def test_get_day_config(self):
        """Test day trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.DAY)
        assert config.htf_timeframe == "h4"
        assert config.mtf_timeframe == "h1"
        assert config.ltf_timeframe == "m15"

    def test_get_all_configs(self):
        """Test get_all_configs method."""
        configs = MTFTimeframeConfig.get_all_configs()
        assert "SWING" in configs
        assert "INTRADAY" in configs
        assert "DAY" in configs
        assert configs["SWING"]["htf"] == "w1"

    def test_config_to_dict(self):
        """Test config to_dict method."""
        config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
        result = config.to_dict()
        assert result["trading_style"] == "SWING"
        assert result["htf_timeframe"] == "w1"


class TestHelperFunctions:
    """Test MTF helper functions."""

    def test_determine_alignment_quality_3(self):
        """Test alignment quality for score 3."""
        quality = determine_alignment_quality(3)
        assert quality == AlignmentQuality.HIGHEST

    def test_determine_alignment_quality_2(self):
        """Test alignment quality for score 2."""
        quality = determine_alignment_quality(2)
        assert quality == AlignmentQuality.GOOD

    def test_determine_alignment_quality_1(self):
        """Test alignment quality for score 1."""
        quality = determine_alignment_quality(1)
        assert quality == AlignmentQuality.POOR

    def test_determine_alignment_quality_0(self):
        """Test alignment quality for score 0."""
        quality = determine_alignment_quality(0)
        assert quality == AlignmentQuality.AVOID

    def test_determine_recommendation_bullish_3(self):
        """Test recommendation for 3/3 bullish alignment."""
        rec = determine_recommendation(
            alignment_score=3,
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.BULLISH,
            ltf_direction=MTFDirection.BULLISH,
        )
        assert rec == Recommendation.BUY

    def test_determine_recommendation_bearish_3(self):
        """Test recommendation for 3/3 bearish alignment."""
        rec = determine_recommendation(
            alignment_score=3,
            htf_direction=MTFDirection.BEARISH,
            mtf_direction=MTFDirection.BEARISH,
            ltf_direction=MTFDirection.BEARISH,
        )
        assert rec == Recommendation.SELL

    def test_determine_recommendation_score_2(self):
        """Test recommendation for score 2 (wait)."""
        rec = determine_recommendation(
            alignment_score=2,
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.BULLISH,
            ltf_direction=MTFDirection.NEUTRAL,
        )
        assert rec == Recommendation.WAIT

    def test_determine_recommendation_score_1(self):
        """Test recommendation for score 1 (avoid)."""
        rec = determine_recommendation(
            alignment_score=1,
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.NEUTRAL,
            ltf_direction=MTFDirection.NEUTRAL,
        )
        assert rec == Recommendation.AVOID

    def test_check_timeframe_conflict_no_conflict(self):
        """Test no conflict when all aligned."""
        has_conflict, message = check_timeframe_conflict(
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.BULLISH,
            ltf_direction=MTFDirection.BULLISH,
        )
        assert has_conflict is False
        assert message is None

    def test_check_timeframe_conflict_htf_mtf(self):
        """Test conflict when HTF and MTF disagree."""
        has_conflict, message = check_timeframe_conflict(
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.BEARISH,
            ltf_direction=MTFDirection.BULLISH,
        )
        assert has_conflict is True
        assert "HTF bullish, MTF bearish" in message

    def test_check_timeframe_conflict_all_different(self):
        """Test conflict when all three differ."""
        has_conflict, message = check_timeframe_conflict(
            htf_direction=MTFDirection.BULLISH,
            mtf_direction=MTFDirection.BEARISH,
            ltf_direction=MTFDirection.NEUTRAL,
        )
        assert has_conflict is True
