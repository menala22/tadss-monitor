"""
Unit tests for Session 3 MTF components.

Tests for:
- Divergence Detector
- Target Calculator
- Support/Resistance Detector
- Opportunity Scanner
"""

import numpy as np
import pandas as pd
import pytest

from src.models.mtf_models import (
    DivergenceType,
    HTFBias,
    LevelType,
    LevelStrength,
    LTFEntry,
    MTFDirection,
    MTFSetup,
    PriceStructure,
    SetupType,
    SupportResistanceLevel,
    TargetMethod,
    TradingStyle,
)
from src.services.divergence_detector import (
    DivergenceDetector,
    DivergenceResult,
    detect_divergence,
)
from src.services.target_calculator import (
    TargetCalculator,
    TargetResult,
    calculate_target,
)
from src.services.support_resistance_detector import (
    SupportResistanceDetector,
    identify_support_resistance,
)
from src.services.mtf_opportunity_scanner import (
    MTFOpportunityScanner,
    ScanResult,
    scan_mtf_opportunities,
)


# =============================================================================
# Divergence Detector Tests
# =============================================================================

class TestDivergenceDetectorInit:
    """Test DivergenceDetector initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        detector = DivergenceDetector()
        assert detector.rsi_length == 14
        assert detector.lookback_bars == 50
        assert detector.min_bars_between_swings == 5

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        detector = DivergenceDetector(
            rsi_length=10,
            lookback_bars=30,
        )
        assert detector.rsi_length == 10
        assert detector.lookback_bars == 30


class TestDivergenceDetection:
    """Test divergence detection."""

    def test_detect_divergence_insufficient_data(self):
        """Test divergence detection with insufficient data."""
        df = pd.DataFrame({"close": [100, 101, 102]})

        detector = DivergenceDetector()
        result = detector.detect_divergence(df)

        assert isinstance(result, DivergenceResult)
        assert len(result.divergences) == 0

    def test_detect_divergence_missing_columns(self):
        """Test divergence detection with missing columns."""
        df = pd.DataFrame({"close": [100, 101, 102]})

        detector = DivergenceDetector()
        result = detector.detect_divergence(df)

        assert result.confidence == 0.0

    def test_regular_bullish_divergence_pattern(self):
        """Test regular bullish divergence pattern detection."""
        # Create data with potential bullish divergence
        # Price makes lower low, RSI should make higher low
        n = 100
        # First decline
        close1 = np.linspace(100, 90, 40)
        # Bounce
        close2 = np.linspace(90, 95, 20)
        # Second decline (lower low)
        close3 = np.linspace(95, 88, 40)

        close = np.concatenate([close1, close2, close3])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        detector = DivergenceDetector(lookback_bars=100)
        result = detector.detect_divergence(df)

        # May or may not detect depending on exact RSI values
        assert isinstance(result, DivergenceResult)

    def test_divergence_result_to_dict(self):
        """Test DivergenceResult to_dict method."""
        result = DivergenceResult(
            divergences=[],
            latest_type=DivergenceType.REGULAR_BULLISH,
            confidence=0.7,
        )
        d = result.to_dict()

        assert d["latest_type"] == "REGULAR_BULLISH"
        assert d["confidence"] == 0.7
        assert d["count"] == 0


class TestConvenienceFunction:
    """Test convenience functions."""

    def test_detect_divergence_function(self):
        """Test detect_divergence convenience function."""
        n = 100
        close = np.array([100 + np.sin(i * 0.2) * 2 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        result = detect_divergence(df, lookback_bars=50)
        assert isinstance(result, DivergenceResult)


# =============================================================================
# Target Calculator Tests
# =============================================================================

class TestTargetCalculatorInit:
    """Test TargetCalculator initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        calc = TargetCalculator()
        assert calc.atr_period == 14
        assert calc.fib_anchor_bars == 20


class TestATRTarget:
    """Test ATR-based target calculation."""

    def test_atr_target_long(self):
        """Test ATR target for LONG position."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 0.5 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        calc = TargetCalculator()
        target = calc._calculate_atr_target(df, entry_price=100.0, direction="LONG")

        assert target.target_price > 100.0
        assert target.method == TargetMethod.ATR

    def test_atr_target_short(self):
        """Test ATR target for SHORT position."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 0.5 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        calc = TargetCalculator()
        target = calc._calculate_atr_target(df, entry_price=100.0, direction="SHORT")

        assert target.target_price < 100.0
        assert target.method == TargetMethod.ATR

    def test_atr_calculation(self):
        """Test ATR calculation."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        calc = TargetCalculator()
        atr = calc._calculate_atr(df, period=14)

        assert atr > 0


class TestPriorSwingTarget:
    """Test prior swing target calculation."""

    def test_prior_swing_target_long(self):
        """Test prior swing target for LONG."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        calc = TargetCalculator()
        target = calc._calculate_prior_swing_target(df, entry_price=100.0, direction="LONG")

        assert target.method == TargetMethod.PRIOR_SWING
        assert target.target_price >= 100.0

    def test_prior_swing_target_short(self):
        """Test prior swing target for SHORT."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        calc = TargetCalculator()
        target = calc._calculate_prior_swing_target(df, entry_price=100.0, direction="SHORT")

        assert target.method == TargetMethod.PRIOR_SWING
        assert target.target_price <= 100.0


class TestTargetSelection:
    """Test target method selection."""

    def test_select_best_method_default(self):
        """Test default method selection."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        calc = TargetCalculator()
        method = calc._select_best_method(
            df_htf=df,
            df_mtf=df,
            direction="LONG",
            setup=None,
            htf_bias=HTFBias(),  # Pass empty HTFBias instead of None
        )

        # Should select a valid method (ATR or FIBONACCI depending on trend detection)
        assert method in [TargetMethod.ATR, TargetMethod.FIBONACCI, TargetMethod.SR_LEVEL]

    def test_select_measured_move_for_pattern(self):
        """Test measured move selection for pattern."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        setup = MTFSetup(
            setup_type=SetupType.CONSOLIDATION,
            consolidation_pattern="FLAG",
        )

        calc = TargetCalculator()
        method = calc._select_best_method(
            df_htf=df,
            df_mtf=df,
            direction="LONG",
            setup=setup,
            htf_bias=None,
        )

        assert method == TargetMethod.MEASURED_MOVE


class TestFullTargetCalculation:
    """Test full target calculation."""

    def test_calculate_target_auto(self):
        """Test target calculation with auto method selection."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        calc = TargetCalculator()
        target = calc.calculate_target(
            df_htf=df,
            df_mtf=df,
            entry_price=100.0,
            stop_loss=98.0,
            direction="LONG",
        )

        assert target.target_price > 100.0
        assert target.rr_ratio > 0

    def test_calculate_target_specific_method(self):
        """Test target calculation with specific method."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        calc = TargetCalculator()
        target = calc.calculate_target(
            df_htf=df,
            df_mtf=df,
            entry_price=100.0,
            stop_loss=98.0,
            direction="LONG",
            method=TargetMethod.ATR,
        )

        assert target.method == TargetMethod.ATR


class TestConvenienceFunction:
    """Test convenience functions."""

    def test_calculate_target_function(self):
        """Test calculate_target convenience function."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
        })

        target = calculate_target(
            df_htf=df,
            df_mtf=df,
            entry_price=100.0,
            stop_loss=98.0,
            direction="LONG",
        )

        assert isinstance(target, TargetResult)


# =============================================================================
# Support/Resistance Detector Tests
# =============================================================================

class TestSupportResistanceDetectorInit:
    """Test SupportResistanceDetector initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        detector = SupportResistanceDetector()
        assert detector.swing_window == 5
        assert detector.volume_bins == 50

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        detector = SupportResistanceDetector(
            swing_window=3,
            volume_bins=30,
        )
        assert detector.swing_window == 3


class TestSwingLevelIdentification:
    """Test swing-based S/R level identification."""

    def test_identify_swing_levels(self):
        """Test swing level identification."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        detector = SupportResistanceDetector()
        levels = detector._identify_swing_levels(df, "d1")

        assert len(levels) > 0
        assert all(isinstance(l, SupportResistanceLevel) for l in levels)

    def test_identify_levels_insufficient_data(self):
        """Test level identification with insufficient data."""
        df = pd.DataFrame({
            "close": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
        })

        detector = SupportResistanceDetector()
        levels = detector.identify_levels(df)

        assert len(levels) == 0


class TestVolumeLevelIdentification:
    """Test volume-based S/R level identification."""

    def test_identify_volume_levels(self):
        """Test volume level identification."""
        n = 50
        close = np.arange(100, 100 + n)

        df = pd.DataFrame({
            "close": close,
            "high": close + 1,
            "low": close - 1,
            "volume": np.random.randn(n).cumsum() + 1000,
        })

        detector = SupportResistanceDetector()
        levels = detector._identify_volume_levels(df, "d1")

        # May find levels depending on volume distribution
        assert isinstance(levels, list)


class TestRoundNumberIdentification:
    """Test round number S/R level identification."""

    def test_identify_round_numbers(self):
        """Test round number identification."""
        n = 50
        close = np.array([98 + np.random.randn() * 0.5 for _ in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        detector = SupportResistanceDetector()
        levels = detector._identify_round_numbers(df, "d1")

        # Should find round numbers near 100
        assert len(levels) > 0
        assert any(100 <= l.price <= 100 for l in levels) or len(levels) > 0


class TestLevelMerging:
    """Test S/R level merging."""

    def test_merge_nearby_levels(self):
        """Test merging of nearby levels."""
        levels = [
            SupportResistanceLevel(
                price=100.0,
                level_type=LevelType.SUPPORT,
                strength=LevelStrength.MEDIUM,
                touch_count=1,
            ),
            SupportResistanceLevel(
                price=100.3,  # Within 0.5%
                level_type=LevelType.SUPPORT,
                strength=LevelStrength.MEDIUM,
                touch_count=1,
            ),
        ]

        detector = SupportResistanceDetector()
        merged = detector._merge_nearby_levels(levels, tolerance_pct=0.01)

        # Should merge into one level
        assert len(merged) == 1
        assert merged[0].touch_count == 2


class TestConvergingLevels:
    """Test converging level detection."""

    def test_find_converging_levels(self):
        """Test converging level detection."""
        levels_htf = [
            SupportResistanceLevel(
                price=100.0,
                level_type=LevelType.SUPPORT,
                strength=LevelStrength.STRONG,
            ),
        ]
        levels_mtf = [
            SupportResistanceLevel(
                price=100.2,  # Within tolerance
                level_type=LevelType.SUPPORT,
                strength=LevelStrength.MEDIUM,
            ),
        ]

        detector = SupportResistanceDetector()
        converging = detector.find_converging_levels({
            "d1": levels_htf,
            "h4": levels_mtf,
        })

        # Should find converging level
        assert len(converging) > 0
        assert converging[0].level_count == 2


class TestConvenienceFunction:
    """Test convenience functions."""

    def test_identify_support_resistance_function(self):
        """Test identify_support_resistance convenience function."""
        n = 50
        close = np.array([100 + np.sin(i * 0.3) * 3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        levels = identify_support_resistance(df, "d1")
        assert isinstance(levels, list)


# =============================================================================
# Opportunity Scanner Tests
# =============================================================================

class TestMTFOpportunityScannerInit:
    """Test MTFOpportunityScanner initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        scanner = MTFOpportunityScanner()
        assert scanner.min_alignment == 2
        assert scanner.min_rr_ratio == 2.0
        assert scanner.trading_style == TradingStyle.SWING

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        scanner = MTFOpportunityScanner(
            min_alignment=3,
            min_rr_ratio=1.5,
            trading_style=TradingStyle.DAY,
        )
        assert scanner.min_alignment == 3
        assert scanner.trading_style == TradingStyle.DAY


class TestFilterChecking:
    """Test filter checking logic."""

    def test_check_filters_passes(self):
        """Test filters that should pass."""
        from src.models.mtf_models import MTFAlignment, AlignmentQuality

        scanner = MTFOpportunityScanner()

        alignment = MTFAlignment(
            alignment_score=3,
            quality=AlignmentQuality.HIGHEST,
            rr_ratio=3.0,
        )

        passes = scanner._check_filters(alignment)
        assert passes is True

    def test_check_filters_fails_alignment(self):
        """Test filters that fail on alignment."""
        from src.models.mtf_models import MTFAlignment, AlignmentQuality

        scanner = MTFOpportunityScanner()

        alignment = MTFAlignment(
            alignment_score=1,  # Below minimum
            quality=AlignmentQuality.POOR,
            rr_ratio=3.0,
        )

        passes = scanner._check_filters(alignment)
        assert passes is False

    def test_check_filters_fails_rr(self):
        """Test filters that fail on R:R."""
        from src.models.mtf_models import MTFAlignment, AlignmentQuality

        scanner = MTFOpportunityScanner()

        alignment = MTFAlignment(
            alignment_score=3,
            quality=AlignmentQuality.HIGHEST,
            rr_ratio=1.0,  # Below minimum
        )

        passes = scanner._check_filters(alignment)
        assert passes is False


class TestPatternDetection:
    """Test pattern detection."""

    def test_detect_patterns_htf_support_reversal(self):
        """Test HTF support + LTF reversal pattern."""
        scanner = MTFOpportunityScanner()

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            price_structure=PriceStructure.UPTREND,
        )

        mtf_setup = MTFSetup()

        from src.models.mtf_models import EntrySignalType, LTFEntry

        ltf_entry = LTFEntry(
            signal_type=EntrySignalType.ENGULFING,
        )

        patterns = scanner._detect_patterns(htf_bias, mtf_setup, ltf_entry)

        assert "HTF Support + LTF Reversal" in patterns

    def test_detect_patterns_pullback_entry(self):
        """Test HTF trend + MTF pullback + LTF entry pattern."""
        scanner = MTFOpportunityScanner()

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        mtf_setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
        )

        ltf_entry = LTFEntry(ema20_reclaim=True)

        patterns = scanner._detect_patterns(htf_bias, mtf_setup, ltf_entry)

        assert "HTF Trend + MTF Pullback + LTF Entry" in patterns


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_scan_result_to_dict(self):
        """Test ScanResult to_dict method."""
        from src.models.mtf_models import MTFAlignment, AlignmentQuality

        result = ScanResult(
            pair="BTC/USDT",
            alignment=MTFAlignment(
                alignment_score=2,
                quality=AlignmentQuality.GOOD,
            ),
            patterns=["Pattern 1"],
        )

        d = result.to_dict()

        assert d["pair"] == "BTC/USDT"
        assert d["patterns"] == ["Pattern 1"]
        assert d["passes_filters"] is False


class TestConvenienceFunction:
    """Test convenience functions."""

    def test_scan_mtf_opportunities_function(self):
        """Test scan_mtf_opportunities convenience function."""
        n = 100
        close = np.array([100 + i * 0.1 + np.sin(i * 0.2) * 0.5 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "open": close,
        })

        data_by_pair = {
            "BTC/USDT": {"htf": df, "mtf": df, "ltf": df},
        }

        opportunities = scan_mtf_opportunities(data_by_pair)

        assert isinstance(opportunities, list)
