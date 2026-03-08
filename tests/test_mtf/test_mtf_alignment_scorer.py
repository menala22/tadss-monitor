"""
Unit tests for MTF Alignment Scorer and MTF Analyzer.

Tests for:
- Alignment scoring
- Quality determination
- Recommendation logic
- Full MTF analysis workflow
"""

import numpy as np
import pandas as pd
import pytest

from src.models.mtf_models import (
    HTFBias,
    LTFEntry,
    MTFAlignment,
    MTFDirection,
    MTFSetup,
    MTFTimeframeConfig,
    PriceStructure,
    Recommendation,
    SetupType,
    TradingStyle,
    AlignmentQuality,
)
from src.services.mtf_alignment_scorer import (
    MTFAlignmentScorer,
    MTFAnalyzer,
    analyze_mtf,
)


class TestMTFAlignmentScorerInit:
    """Test MTFAlignmentScorer initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        scorer = MTFAlignmentScorer()
        assert scorer.min_rr_ratio == 2.0
        assert scorer.require_all_3_for_highest is True

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        scorer = MTFAlignmentScorer(min_rr_ratio=1.5)
        assert scorer.min_rr_ratio == 1.5


class TestAlignmentScoring:
    """Test alignment scoring logic."""

    def test_score_3_3_aligned_bullish(self):
        """Test scoring when all 3 TFs are bullish."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.8,
            price_structure=PriceStructure.UPTREND,
        )

        mtf_setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        ltf_entry = LTFEntry(
            signal_type="ENGULFING",
            direction=MTFDirection.BULLISH,
            entry_price=100.0,
            stop_loss=98.0,
        )

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.alignment_score == 3
        assert alignment.quality == AlignmentQuality.HIGHEST
        # Recommendation should be BUY or WAIT (WAIT if R:R not met)
        assert alignment.recommendation in [Recommendation.BUY, Recommendation.WAIT]

    def test_score_2_3_aligned(self):
        """Test scoring when 2 of 3 TFs are aligned."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        mtf_setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.6,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.NEUTRAL,  # Not aligned
        )

        alignment = scorer.score_alignment(
            pair="ETH/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.alignment_score == 2
        assert alignment.quality == AlignmentQuality.GOOD

    def test_score_1_3_aligned(self):
        """Test scoring when only 1 TF is aligned."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.6,
        )

        mtf_setup = MTFSetup(
            direction=MTFDirection.NEUTRAL,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.NEUTRAL,
        )

        alignment = scorer.score_alignment(
            pair="SOL/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.alignment_score == 1
        assert alignment.quality == AlignmentQuality.POOR
        assert alignment.recommendation == Recommendation.AVOID

    def test_score_0_3_aligned(self):
        """Test scoring when 0 TFs are aligned (all neutral)."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.NEUTRAL,
            confidence=0.0,
        )

        mtf_setup = MTFSetup(
            direction=MTFDirection.NEUTRAL,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.NEUTRAL,
        )

        alignment = scorer.score_alignment(
            pair="XAU/USD",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.alignment_score == 0
        assert alignment.quality == AlignmentQuality.AVOID
        assert alignment.recommendation == Recommendation.AVOID


class TestTimeframeConflictDetection:
    """Test timeframe conflict detection."""

    def test_conflict_htf_mtf_disagree(self):
        """Test conflict when HTF and MTF disagree."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        mtf_setup = MTFSetup(
            direction=MTFDirection.BEARISH,  # Conflicting
            confidence=0.6,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.BULLISH,
        )

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.recommendation == Recommendation.WAIT
        assert "conflict" in alignment.notes.lower() or "⚠️" in alignment.notes

    def test_no_conflict_all_aligned(self):
        """Test no conflict when all TFs aligned."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.8,
        )

        mtf_setup = MTFSetup(
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.BULLISH,
        )

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert alignment.recommendation == Recommendation.BUY


class TestRRatioCalculation:
    """Test R:R ratio calculation."""

    def test_rr_ratio_calculation(self):
        """Test R:R ratio is calculated correctly."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.8,
        )

        mtf_setup = MTFSetup(
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        ltf_entry = LTFEntry(
            direction=MTFDirection.BULLISH,
            entry_price=100.0,
            stop_loss=95.0,  # Risk = 5
        )

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        # Should have target and R:R calculated
        if alignment.target:
            assert alignment.target.target_price > ltf_entry.entry_price
            assert alignment.rr_ratio > 0


class TestNotesGeneration:
    """Test analysis notes generation."""

    def test_notes_include_htf_bias(self):
        """Test notes include HTF bias."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            price_structure=PriceStructure.UPTREND,
        )

        mtf_setup = MTFSetup()
        ltf_entry = LTFEntry()

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert "HTF" in alignment.notes
        assert "BULLISH" in alignment.notes or "UPTREND" in alignment.notes

    def test_notes_include_mtf_setup(self):
        """Test notes include MTF setup."""
        scorer = MTFAlignmentScorer()

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        mtf_setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
        )

        ltf_entry = LTFEntry()

        alignment = scorer.score_alignment(
            pair="BTC/USDT",
            htf_bias=htf_bias,
            mtf_setup=mtf_setup,
            ltf_entry=ltf_entry,
        )

        assert "MTF" in alignment.notes
        assert "PULLBACK" in alignment.notes


class TestMTFAnalyzer:
    """Test MTFAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test MTFAnalyzer initialization."""
        config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
        analyzer = MTFAnalyzer(config)

        assert analyzer.config == config
        assert analyzer.htf_detector is None  # Lazy loaded
        assert analyzer.mtf_detector is None
        assert analyzer.ltf_finder is None

    def test_analyze_pair(self):
        """Test full MTF analysis."""
        config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
        analyzer = MTFAnalyzer(config)

        # Create sample data
        n = 250
        close = np.array([100 + i * 0.2 + np.sin(i * 0.1) * 0.5 for i in range(n)])

        htf_data = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "open": close,
        })

        mtf_data = htf_data.copy()
        ltf_data = htf_data.copy()

        alignment = analyzer.analyze_pair(
            pair="BTC/USDT",
            htf_data=htf_data,
            mtf_data=mtf_data,
            ltf_data=ltf_data,
        )

        assert isinstance(alignment, MTFAlignment)
        assert alignment.pair == "BTC/USDT"
        assert alignment.alignment_score >= 0
        assert alignment.alignment_score <= 3


class TestConvenienceFunction:
    """Test analyze_mtf convenience function."""

    def test_analyze_mtf_function(self):
        """Test the convenience function."""
        # Create sample data
        n = 250
        close = np.array([100 + i * 0.2 for i in range(n)])

        htf_data = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "open": close,
        })

        mtf_data = htf_data.copy()
        ltf_data = htf_data.copy()

        result = analyze_mtf(
            pair="BTC/USDT",
            htf_data=htf_data,
            mtf_data=mtf_data,
            ltf_data=ltf_data,
            trading_style=TradingStyle.SWING,
        )

        assert isinstance(result, MTFAlignment)


class TestAlignmentToDict:
    """Test MTFAlignment to_dict method."""

    def test_alignment_to_dict_structure(self):
        """Test alignment to_dict returns correct structure."""
        alignment = MTFAlignment(
            pair="BTC/USDT",
            htf_bias=HTFBias(direction=MTFDirection.BULLISH, confidence=0.8),
            mtf_setup=MTFSetup(direction=MTFDirection.BULLISH, confidence=0.7),
            ltf_entry=LTFEntry(direction=MTFDirection.BULLISH),
            alignment_score=3,
            quality=AlignmentQuality.HIGHEST,
            recommendation=Recommendation.BUY,
        )

        result = alignment.to_dict()

        assert result["pair"] == "BTC/USDT"
        assert result["alignment_score"] == 3
        assert result["quality"] == "HIGHEST"
        assert result["recommendation"] == "BUY"
        assert "htf_bias" in result
        assert "mtf_setup" in result
        assert "ltf_entry" in result


class TestTradingStyleConfigs:
    """Test trading style configurations."""

    def test_swing_config(self):
        """Test swing trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.SWING)
        assert config.htf_timeframe == "w1"
        assert config.mtf_timeframe == "d1"
        assert config.ltf_timeframe == "h4"

    def test_intraday_config(self):
        """Test intraday trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.INTRADAY)
        assert config.htf_timeframe == "d1"
        assert config.mtf_timeframe == "h4"
        assert config.ltf_timeframe == "h1"

    def test_day_config(self):
        """Test day trading configuration."""
        config = MTFTimeframeConfig.get_config(TradingStyle.DAY)
        assert config.htf_timeframe == "h4"
        assert config.mtf_timeframe == "h1"
        assert config.ltf_timeframe == "m15"
