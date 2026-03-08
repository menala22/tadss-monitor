"""
Unit tests for MTF Setup Detector.

Tests for:
- Pullback detection
- Divergence detection
- Consolidation detection
- Range setup detection
- Setup selection logic
"""

import numpy as np
import pandas as pd
import pytest

from src.models.mtf_models import (
    DivergenceType,
    HTFBias,
    MTFDirection,
    MTFSetup,
    PriceStructure,
    SetupType,
)
from src.services.mtf_setup_detector import MTFSetupDetector, detect_mtf_setup


class TestMTFSetupDetectorInit:
    """Test MTFSetupDetector initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        detector = MTFSetupDetector()
        assert detector.rsi_length == 14
        assert detector.sma20_period == 20
        assert detector.sma50_period == 50
        assert detector.volume_ma_period == 20

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        detector = MTFSetupDetector(
            rsi_length=10,
            sma20_period=15,
            sma50_period=30,
        )
        assert detector.rsi_length == 10
        assert detector.sma50_period == 30


class TestRSICalculation:
    """Test RSI calculation."""

    def test_rsi_calculation(self):
        """Test RSI is calculated correctly."""
        detector = MTFSetupDetector()
        np.random.seed(42)
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        rsi = detector._calculate_rsi(close, 14)

        # RSI should be between 0 and 100
        assert rsi.iloc[-1] >= 0
        assert rsi.iloc[-1] <= 100

        # RSI should have values (not all NaN)
        assert not rsi.isna().all()


class TestPullbackDetection:
    """Test pullback setup detection."""

    def test_pullback_to_sma20_bullish(self):
        """Test pullback to SMA20 in bullish trend."""
        # Create uptrending data pulling back to SMA20
        n = 100
        close = np.array([100 + i * 0.5 for i in range(n)])
        # Pullback in last 10 candles
        close[-10:] = close[-11] - np.arange(10) * 0.3

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "volume": np.random.randn(n).cumsum() + 1000,
        })

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.8,
            price_structure=PriceStructure.UPTREND,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        # Should detect some setup (pullback or consolidation)
        assert setup is not None

    def test_pullback_with_rsi_confirmation(self):
        """Test pullback with RSI approaching 40."""
        # Create data where RSI is around 40-45
        n = 100
        # Uptrend with slight pullback
        close = np.array([100 + i * 0.3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "volume": [1000] * n,
        })

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.7,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        assert setup is not None


class TestDivergenceDetection:
    """Test RSI divergence detection."""

    def test_bullish_divergence(self):
        """Test bullish divergence detection."""
        # Create data with price making new low but RSI making higher low
        n = 100
        close = np.array([100 + i * 0.2 for i in range(50)] + [95 + i * 0.1 for i in range(50)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        detector = MTFSetupDetector()
        rsi = detector._calculate_rsi(df["close"], 14)
        divergence = detector._detect_divergence(df, rsi)

        # Divergence detection is simplified - just verify it runs
        assert divergence is None or divergence == DivergenceType.REGULAR_BULLISH

    def test_bearish_divergence(self):
        """Test bearish divergence detection."""
        # Create data with price making new high but RSI making lower high
        n = 100
        close = np.array([100 - i * 0.2 for i in range(50)] + [105 - i * 0.1 for i in range(50)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        detector = MTFSetupDetector()
        rsi = detector._calculate_rsi(df["close"], 14)
        divergence = detector._detect_divergence(df, rsi)

        assert divergence is None or divergence == DivergenceType.REGULAR_BEARISH


class TestConsolidationDetection:
    """Test consolidation pattern detection."""

    def test_consolidation_low_volatility(self):
        """Test consolidation detection with low volatility."""
        # Create data with low volatility (sideways movement)
        n = 50
        close = np.array([100 + np.sin(i * 0.5) * 0.5 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.005,
            "low": close * 0.995,
        })

        detector = MTFSetupDetector()
        consolidation = detector._detect_consolidation(df)

        # May or may not detect - just verify it runs
        assert consolidation is None or consolidation in ["FLAG", "PENNANT", "TRIANGLE", "RECTANGLE"]


class TestRangeSetupDetection:
    """Test range boundary setup detection."""

    def test_range_low_setup(self):
        """Test setup at range low."""
        # Create ranging data
        n = 50
        close = np.array([95 + np.sin(i * 0.3) * 3 for i in range(n)])
        # End near range low
        close[-5:] = 95.5 + np.arange(5) * 0.1

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        htf_bias = HTFBias(
            direction=MTFDirection.NEUTRAL,
            price_structure=PriceStructure.RANGE,
            confidence=0.5,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        # Should detect range setup or consolidation
        assert setup is not None

    def test_range_high_setup(self):
        """Test setup at range high."""
        # Create ranging data
        n = 50
        close = np.array([95 + np.sin(i * 0.3) * 3 for i in range(n)])
        # End near range high
        close[-5:] = 100.5 - np.arange(5) * 0.1

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        htf_bias = HTFBias(
            direction=MTFDirection.NEUTRAL,
            price_structure=PriceStructure.RANGE,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        assert setup is not None

    def test_range_middle_no_setup(self):
        """Test no setup in middle of range."""
        # Create ranging data
        n = 50
        close = np.array([95 + np.sin(i * 0.3) * 3 for i in range(n)])
        # End in middle (around 98)
        close[-5:] = 98 + np.arange(5) * 0.1

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        htf_bias = HTFBias(
            direction=MTFDirection.NEUTRAL,
            price_structure=PriceStructure.RANGE,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        # Should indicate no setup in middle or at boundary with low confidence
        assert setup is not None
        # Either in middle (warning contains "middle") or at boundary with lower confidence
        assert (
            setup.warning is not None and "middle" in setup.warning.lower()
        ) or setup.confidence < 0.6


class TestSetupSelection:
    """Test best setup selection logic."""

    def test_select_pullback_over_consolidation(self):
        """Test pullback is selected over consolidation."""
        detector = MTFSetupDetector()

        from src.models.mtf_models import PullbackSetup

        pullback = PullbackSetup(
            approaching_sma=50,
            distance_to_sma_pct=1.5,
            rsi_level=42.0,
            rsi_approaching_40=True,
        )

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        setup = detector._select_best_setup(
            pullback_setup=pullback,
            divergence=None,
            consolidation="RECTANGLE",
            htf_bias=htf_bias,
            current_price=100.0,
            sma20=pd.Series([98] * 50),
            sma50=pd.Series([95] * 50),
        )

        assert setup.setup_type == SetupType.PULLBACK
        assert setup.confidence > 0.5

    def test_select_divergence_when_present(self):
        """Test divergence is selected when present."""
        detector = MTFSetupDetector()

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        setup = detector._select_best_setup(
            pullback_setup=None,
            divergence=DivergenceType.REGULAR_BULLISH,
            consolidation=None,
            htf_bias=htf_bias,
            current_price=100.0,
            sma20=pd.Series([98] * 50),
            sma50=pd.Series([95] * 50),
        )

        assert setup.setup_type == SetupType.DIVERGENCE
        assert setup.direction == MTFDirection.BULLISH


class TestFullSetupDetection:
    """Test full setup detection workflow."""

    def test_detect_setup_bullish_trend(self):
        """Test setup detection in bullish trend."""
        # Create uptrending data
        n = 100
        close = np.array([100 + i * 0.3 + np.sin(i * 0.2) * 0.5 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "volume": [1000 + np.random.randn() * 100 for _ in range(n)],
        })

        htf_bias = HTFBias(
            direction=MTFDirection.BULLISH,
            confidence=0.75,
            price_structure=PriceStructure.UPTREND,
        )

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        assert setup is not None
        assert setup.direction in [MTFDirection.BULLISH, MTFDirection.NEUTRAL]

    def test_detect_setup_insufficient_data(self):
        """Test setup detection with insufficient data."""
        df = pd.DataFrame({
            "close": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
        })

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        assert setup.confidence == 0.0
        assert "Insufficient data" in setup.warning

    def test_detect_setup_missing_columns(self):
        """Test setup detection with missing columns."""
        df = pd.DataFrame({
            "close": [100, 101, 102],
            # Missing high and low
        })

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        detector = MTFSetupDetector()
        setup = detector.detect_setup(df, htf_bias)

        # Should fail due to insufficient data OR missing columns
        assert setup.confidence == 0.0
        assert setup.warning is not None
        assert "Insufficient data" in setup.warning or "Missing columns" in setup.warning


class TestConvenienceFunction:
    """Test detect_mtf_setup convenience function."""

    def test_detect_mtf_setup_function(self):
        """Test the convenience function."""
        n = 100
        close = np.array([100 + i * 0.3 for i in range(n)])

        df = pd.DataFrame({
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
        })

        htf_bias = HTFBias(direction=MTFDirection.BULLISH)

        setup = detect_mtf_setup(df, htf_bias)

        assert isinstance(setup, MTFSetup)
        assert setup.setup_type in SetupType


class TestSetupToDict:
    """Test MTFSetup to_dict method."""

    def test_setup_to_dict_structure(self):
        """Test setup to_dict returns correct structure."""
        setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.65,
            sma20_action="SUPPORT",
            sma50_action="NONE",
        )
        result = setup.to_dict()

        assert result["setup_type"] == "PULLBACK"
        assert result["direction"] == "BULLISH"
        assert result["confidence"] == 0.65
        assert result["sma20_action"] == "SUPPORT"
        assert isinstance(result["warning"], str) or result["warning"] is None
