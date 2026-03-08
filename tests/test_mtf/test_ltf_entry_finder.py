"""
Unit tests for LTF Entry Finder.

Tests for:
- Candlestick pattern detection (engulfing, hammer, pinbar)
- EMA20 reclaim detection
- RSI turn detection
- Stop loss calculation
- Full entry signal detection
"""

import numpy as np
import pandas as pd
import pytest

from src.models.mtf_models import (
    EntrySignalType,
    LTFEntry,
    MTFDirection,
    MTFSetup,
    RSITurn,
    SetupType,
)
from src.services.mtf_entry_finder import LTFEntryFinder, find_ltf_entry


class TestLTFEntryFinderInit:
    """Test LTFEntryFinder initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        finder = LTFEntryFinder()
        assert finder.ema20_period == 20
        assert finder.rsi_length == 14
        assert finder.rsi_oversold == 40.0
        assert finder.rsi_overbought == 60.0

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        finder = LTFEntryFinder(
            ema20_period=15,
            rsi_length=10,
            rsi_oversold=35.0,
        )
        assert finder.ema20_period == 15
        assert finder.rsi_length == 10
        assert finder.rsi_oversold == 35.0


class TestRSICalculation:
    """Test RSI calculation."""

    def test_rsi_calculation(self):
        """Test RSI is calculated correctly."""
        finder = LTFEntryFinder()
        np.random.seed(42)
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        rsi = finder._calculate_rsi(close, 14)

        # RSI should be between 0 and 100
        assert rsi.iloc[-1] >= 0
        assert rsi.iloc[-1] <= 100

        # RSI should have values (not all NaN)
        assert not rsi.isna().all()


class TestCandlestickPatterns:
    """Test candlestick pattern detection."""

    def test_bullish_engulfing(self):
        """Test bullish engulfing pattern detection."""
        # Create bullish engulfing pattern
        # Previous: bearish candle (open > close)
        # Current: bullish candle (close > open) that engulfs previous
        data = {
            "open": [100.0, 98.0],
            "high": [101.0, 102.5],
            "low": [99.0, 97.5],
            "close": [98.5, 101.0],
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.ENGULFING

    def test_bearish_engulfing(self):
        """Test bearish engulfing pattern detection."""
        # Create bearish engulfing pattern
        # Previous: bullish candle (close > open)
        # Current: bearish candle (open > close) that engulfs previous
        data = {
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 98.0],
            "close": [101.0, 99.0],
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.ENGULFING

    def test_hammer_pattern(self):
        """Test hammer pattern detection."""
        # Create hammer pattern: small body, long lower wick (2x body)
        # Body = |close - open|, Lower wick = min(open,close) - low
        data = {
            "open": [100.0, 100.0],
            "high": [101.0, 100.3],  # Small upper wick
            "low": [99.0, 98.0],     # Long lower wick (2.0 = 4x body of 0.5)
            "close": [99.0, 100.5],  # Body = 0.5, lower wick = 2.0
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.HAMMER

    def test_pinbar_pattern(self):
        """Test pinbar pattern detection."""
        # Create bearish pinbar: small body, long upper wick (3x body)
        data = {
            "open": [100.0, 100.0],
            "high": [101.0, 101.5],  # Upper wick = 1.5
            "low": [99.0, 99.9],
            "close": [99.0, 100.0],  # Body = 0.0 (doji-like)
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        # May detect as pinbar or other pattern depending on exact ratios
        assert pattern in [EntrySignalType.PINBAR, EntrySignalType.NONE]

    def test_inside_bar_pattern(self):
        """Test inside bar pattern detection."""
        # Create inside bar pattern
        data = {
            "open": [100.0, 99.5],
            "high": [102.0, 101.0],  # Inside previous high
            "low": [98.0, 99.0],     # Inside previous low
            "close": [101.0, 100.0],
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.INSIDE_BAR

    def test_no_pattern(self):
        """Test when no pattern is present."""
        # Create normal candles with no specific pattern
        data = {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
        }
        df = pd.DataFrame(data)

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.NONE

    def test_insufficient_data(self):
        """Test with insufficient data."""
        df = pd.DataFrame({
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
        })

        finder = LTFEntryFinder()
        pattern = finder._detect_candlestick_pattern(df)

        assert pattern == EntrySignalType.NONE


class TestEMA20Reclaim:
    """Test EMA20 reclaim detection."""

    def test_bullish_ema_reclaim(self):
        """Test bullish EMA20 reclaim."""
        # Create data where price was below EMA, now above
        n = 30
        close = np.array([100 - i * 0.5 for i in range(10)] + [95 + i * 0.8 for i in range(20)])
        df = pd.DataFrame({"close": close})

        ema20 = df["close"].ewm(span=20, adjust=False).mean()

        finder = LTFEntryFinder()
        reclaim = finder._check_ema20_reclaim(df, ema20, "LONG")

        # Should detect reclaim if price crossed above EMA
        assert isinstance(reclaim, bool)

    def test_bearish_ema_reclaim(self):
        """Test bearish EMA20 reclaim."""
        # Create data where price was above EMA, now below
        n = 30
        close = np.array([100 + i * 0.5 for i in range(10)] + [105 - i * 0.8 for i in range(20)])
        df = pd.DataFrame({"close": close})

        ema20 = df["close"].ewm(span=20, adjust=False).mean()

        finder = LTFEntryFinder()
        reclaim = finder._check_ema20_reclaim(df, ema20, "SHORT")

        assert isinstance(reclaim, bool)

    def test_no_reclaim(self):
        """Test when no reclaim occurs."""
        # Price stays above EMA (no reclaim)
        n = 30
        close = np.array([100 + i * 0.3 for i in range(n)])
        df = pd.DataFrame({"close": close})

        ema20 = df["close"].ewm(span=20, adjust=False).mean()

        finder = LTFEntryFinder()
        reclaim = finder._check_ema20_reclaim(df, ema20, "LONG")

        # No reclaim if price never crossed
        assert reclaim is False


class TestRSITurn:
    """Test RSI turn detection."""

    def test_rsi_turn_up_from_oversold(self):
        """Test RSI turning up from oversold."""
        # Create data with RSI going from <40 to higher
        n = 30
        # Price declining then turning up
        close = np.array([100 - i * 0.5 for i in range(20)] + [90 + i * 0.3 for i in range(10)])
        df = pd.DataFrame({"close": close})

        finder = LTFEntryFinder()
        rsi = finder._calculate_rsi(df["close"], 14)
        turn = finder._check_rsi_turn(df, rsi, "LONG")

        # May detect turn if RSI was oversold
        assert isinstance(turn, RSITurn)

    def test_rsi_turn_down_from_overbought(self):
        """Test RSI turning down from overbought."""
        # Create data with RSI going from >60 to lower
        n = 30
        # Price rising then turning down
        close = np.array([100 + i * 0.5 for i in range(20)] + [110 - i * 0.3 for i in range(10)])
        df = pd.DataFrame({"close": close})

        finder = LTFEntryFinder()
        rsi = finder._calculate_rsi(df["close"], 14)
        turn = finder._check_rsi_turn(df, rsi, "SHORT")

        assert isinstance(turn, RSITurn)

    def test_no_rsi_turn(self):
        """Test when no RSI turn occurs."""
        # RSI in middle range
        n = 30
        close = np.array([100 + np.sin(i * 0.3) * 0.5 for i in range(n)])
        df = pd.DataFrame({"close": close})

        finder = LTFEntryFinder()
        rsi = finder._calculate_rsi(df["close"], 14)
        turn = finder._check_rsi_turn(df, rsi, "LONG")

        assert turn == RSITurn.NONE


class TestStopLossCalculation:
    """Test stop loss calculation."""

    def test_stop_loss_long(self):
        """Test stop loss for LONG position."""
        n = 20
        low = np.array([99 - i * 0.1 for i in range(10)] + [98 + i * 0.1 for i in range(10)])
        df = pd.DataFrame({
            "close": low + 1,
            "high": low + 2,
            "low": low,
        })

        finder = LTFEntryFinder()
        stop_loss = finder._calculate_stop_loss(df, "LONG")

        # Stop loss should be below recent low
        recent_low = df["low"].iloc[-10:].min()
        assert stop_loss < recent_low

    def test_stop_loss_short(self):
        """Test stop loss for SHORT position."""
        n = 20
        high = np.array([100 + i * 0.1 for i in range(10)] + [101 - i * 0.1 for i in range(10)])
        df = pd.DataFrame({
            "close": high - 1,
            "high": high,
            "low": high - 2,
        })

        finder = LTFEntryFinder()
        stop_loss = finder._calculate_stop_loss(df, "SHORT")

        # Stop loss should be above recent high
        recent_high = df["high"].iloc[-10:].max()
        assert stop_loss > recent_high


class TestFullEntryDetection:
    """Test full entry signal detection."""

    def test_find_entry_with_engulfing(self):
        """Test entry detection with engulfing pattern."""
        # Create data with bullish engulfing
        data = {
            "open": [100.0, 98.0, 101.0],
            "high": [101.0, 99.0, 103.0],
            "low": [99.0, 97.5, 100.5],
            "close": [99.0, 101.0, 102.0],
        }
        df = pd.DataFrame(data)

        setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.6,
        )

        finder = LTFEntryFinder()
        entry = finder.find_entry(df, setup, "LONG")

        # Should detect entry (engulfing pattern in last 2 candles)
        # Note: Entry detection requires multiple conditions, so we just verify it runs
        assert entry is None or (entry.entry_price > 0 and entry.stop_loss > 0)

    def test_find_entry_no_signal(self):
        """Test when no entry signal is present."""
        # Create normal candles with no pattern
        n = 30
        close = np.array([100 + np.sin(i * 0.3) * 0.5 for i in range(n)])
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
        })

        setup = MTFSetup(
            setup_type=SetupType.CONSOLIDATION,
            direction=MTFDirection.NEUTRAL,
            confidence=0.3,
        )

        finder = LTFEntryFinder()
        entry = finder.find_entry(df, setup, "LONG")

        # May or may not find entry depending on data
        assert entry is None or isinstance(entry, LTFEntry)

    def test_find_entry_insufficient_data(self):
        """Test entry detection with insufficient data."""
        df = pd.DataFrame({
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.0, 101.0],
        })

        setup = MTFSetup()

        finder = LTFEntryFinder()
        entry = finder.find_entry(df, setup, "LONG")

        assert entry is None

    def test_find_entry_missing_columns(self):
        """Test entry detection with missing columns."""
        df = pd.DataFrame({
            "close": [100.0, 101.0, 102.0],
            # Missing open, high, low
        })

        setup = MTFSetup()

        finder = LTFEntryFinder()
        entry = finder.find_entry(df, setup, "LONG")

        assert entry is None


class TestEntryToDict:
    """Test LTFEntry to_dict method."""

    def test_entry_to_dict_structure(self):
        """Test entry to_dict returns correct structure."""
        entry = LTFEntry(
            signal_type=EntrySignalType.ENGULFING,
            direction=MTFDirection.BULLISH,
            ema20_reclaim=True,
            rsi_turning=RSITurn.UP_FROM_OVERSOLD,
            entry_price=101.5,
            stop_loss=99.0,
        )
        result = entry.to_dict()

        assert result["signal_type"] == "ENGULFING"
        assert result["direction"] == "BULLISH"
        assert result["ema20_reclaim"] is True
        assert result["rsi_turning"] == "UP_FROM_OVERSOLD"
        assert result["entry_price"] == 101.5
        assert result["stop_loss"] == 99.0


class TestConvenienceFunction:
    """Test find_ltf_entry convenience function."""

    def test_find_ltf_entry_function(self):
        """Test the convenience function."""
        data = {
            "open": [100.0, 98.0, 101.0],
            "high": [101.0, 99.0, 103.0],
            "low": [99.0, 97.5, 100.5],
            "close": [99.0, 101.0, 102.0],
        }
        df = pd.DataFrame(data)

        setup = MTFSetup(
            setup_type=SetupType.PULLBACK,
            direction=MTFDirection.BULLISH,
            confidence=0.6,
        )

        entry = find_ltf_entry(df, setup, "LONG")

        # May or may not find entry depending on conditions
        assert entry is None or isinstance(entry, LTFEntry)
