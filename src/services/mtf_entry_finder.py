"""
Lower Timeframe (LTF) Entry Finder for MTF Analysis.

This module finds precise entry signals on the lower timeframe,
following the MTF framework from multi_timeframe.md.

Entry Criteria (all must align):
- LTF trend aligns with HTF direction
- Price reclaims 20 EMA after pullback
- Reversal candle pattern (engulfing, hammer, pinbar)
- RSI(14) turns up from <40 (long) or down from >60 (short)
"""

import logging
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    EntrySignalType,
    LTFEntry,
    MTFDirection,
    MTFSetup,
    RSITurn,
    SetupType,
)

logger = logging.getLogger(__name__)


class LTFEntryFinder:
    """
    Find precise entry signals on lower timeframe.

    The LTF entry finds the optimal entry point within the MTF setup
    with tight stop loss based on LTF structure.

    Attributes:
        ema20_period: 20 EMA period for trend confirmation.
        rsi_length: RSI calculation period (default 14).
        rsi_oversold: RSI oversold threshold (default 40 for entry).
        rsi_overbought: RSI overbought threshold (default 60 for entry).
    """

    def __init__(
        self,
        ema20_period: int = 20,
        rsi_length: int = 14,
        rsi_oversold: float = 40.0,
        rsi_overbought: float = 60.0,
    ):
        """
        Initialize LTF entry finder.

        Args:
            ema20_period: 20 EMA period.
            rsi_length: RSI calculation period.
            rsi_oversold: RSI oversold threshold for long entries.
            rsi_overbought: RSI overbought threshold for short entries.
        """
        self.ema20_period = ema20_period
        self.rsi_length = rsi_length
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def find_entry(
        self,
        df: pd.DataFrame,
        setup: MTFSetup,
        direction: Literal["LONG", "SHORT"],
    ) -> Optional[LTFEntry]:
        """
        Find entry signal in setup direction.

        Returns entry signal with:
        - Entry price (on confirmation candle close)
        - Stop loss (below LTF swing low)
        - Signal type (candle pattern)

        Args:
            df: DataFrame with OHLCV data.
            setup: MTF setup to enter from.
            direction: LONG or SHORT.

        Returns:
            LTFEntry object if signal found, None otherwise.

        Example:
            >>> finder = LTFEntryFinder()
            >>> setup = MTFSetup(setup_type=SetupType.PULLBACK, ...)
            >>> entry = finder.find_entry(ohlcv_df, setup, "LONG")
            >>> if entry:
            ...     print(f"Entry: {entry.entry_price}, Stop: {entry.stop_loss}")
        """
        if df.empty or len(df) < self.ema20_period:
            logger.warning(f"Insufficient data for LTF entry (need {self.ema20_period} candles)")
            return None

        # Ensure required columns exist
        df = df.copy()
        required_cols = {"close", "high", "low", "open"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            logger.warning(f"Missing columns for LTF entry: {required_cols - available_cols}")
            return None

        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})

        # Calculate indicators
        ema20 = df["close"].ewm(span=self.ema20_period, adjust=False).mean()
        rsi = self._calculate_rsi(df["close"], self.rsi_length)

        # Check for candlestick pattern
        candle_pattern = self._detect_candlestick_pattern(df)

        # Check EMA20 reclaim
        ema20_reclaim = self._check_ema20_reclaim(df, ema20, direction)

        # Check RSI turn
        rsi_turn = self._check_rsi_turn(df, rsi, direction)

        # Determine if we have a valid entry signal
        # Require at least: candle pattern OR (EMA reclaim + RSI turn)
        has_signal = (
            candle_pattern != EntrySignalType.NONE or
            (ema20_reclaim and rsi_turn != RSITurn.NONE)
        )

        if not has_signal:
            return None

        # Calculate entry and stop loss
        current_close = df["close"].iloc[-1]
        current_high = df["high"].iloc[-1]
        current_low = df["low"].iloc[-1]
        current_timestamp = df.index[-1]  # Get timestamp of confirmation candle

        # Entry price: close of confirmation candle
        entry_price = current_close

        # Stop loss: below/above recent swing
        stop_loss = self._calculate_stop_loss(df, direction)

        # Determine signal type priority
        if candle_pattern != EntrySignalType.NONE:
            signal_type = candle_pattern
        elif ema20_reclaim:
            signal_type = EntrySignalType.BREAKOUT
        else:
            signal_type = EntrySignalType.NONE

        # Determine direction enum
        entry_direction = MTFDirection.BULLISH if direction == "LONG" else MTFDirection.BEARISH

        return LTFEntry(
            signal_type=signal_type,
            direction=entry_direction,
            ema20_reclaim=ema20_reclaim,
            rsi_turning=rsi_turn,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            confirmation_candle_close=float(current_close),
            confirmation_candle_timestamp=current_timestamp,  # NEW: Capture timestamp
        )

    def _calculate_rsi(self, series: pd.Series, length: int) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).

        Args:
            series: Price series (close).
            length: RSI period.

        Returns:
            RSI series.
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()

        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(100)  # loss == 0 means all gains → RSI = 100
        return rsi

    def _detect_candlestick_pattern(
        self,
        df: pd.DataFrame,
    ) -> EntrySignalType:
        """
        Detect reversal candlestick patterns.

        Patterns detected:
        - ENGULFING: Current candle engulfs previous
        - HAMMER: Small body, long lower wick (2x body)
        - PINBAR: Small body, long wick on one side
        - INSIDE_BAR: Current candle within previous range

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            EntrySignalType enum value.
        """
        if len(df) < 2:
            return EntrySignalType.NONE

        # Get current and previous candle data
        curr_open = df["open"].iloc[-1]
        curr_high = df["high"].iloc[-1]
        curr_low = df["low"].iloc[-1]
        curr_close = df["close"].iloc[-1]

        prev_open = df["open"].iloc[-2]
        prev_high = df["high"].iloc[-2]
        prev_low = df["low"].iloc[-2]
        prev_close = df["close"].iloc[-2]

        # Calculate body and wicks
        curr_body = abs(curr_close - curr_open)
        curr_upper_wick = curr_high - max(curr_open, curr_close)
        curr_lower_wick = min(curr_open, curr_close) - curr_low

        prev_body = abs(prev_close - prev_open)

        # Avoid division by zero
        if curr_body == 0:
            curr_body = 0.0001
        if prev_body == 0:
            prev_body = 0.0001

        # Engulfing pattern
        # Bullish engulfing: current body engulfs previous body, current is bullish
        if curr_close > curr_open and prev_close < prev_open:
            if curr_open <= prev_close and curr_close >= prev_open:
                logger.debug("Bullish engulfing pattern detected")
                return EntrySignalType.ENGULFING

        # Bearish engulfing: current body engulfs previous body, current is bearish
        if curr_close < curr_open and prev_close > prev_open:
            if curr_open >= prev_close and curr_close <= prev_open:
                logger.debug("Bearish engulfing pattern detected")
                return EntrySignalType.ENGULFING

        # Hammer pattern: small body, long lower wick (2x body), little upper wick
        if curr_lower_wick >= 2 * curr_body and curr_upper_wick <= curr_body * 0.5:
            logger.debug("Hammer pattern detected")
            return EntrySignalType.HAMMER

        # Pinbar: small body, long wick on one side (3x body)
        if curr_upper_wick >= 3 * curr_body and curr_lower_wick <= curr_body:
            logger.debug("Bearish pinbar detected")
            return EntrySignalType.PINBAR
        if curr_lower_wick >= 3 * curr_body and curr_upper_wick <= curr_body:
            logger.debug("Bullish pinbar detected")
            return EntrySignalType.PINBAR

        # Inside bar: current candle within previous range
        if curr_high <= prev_high and curr_low >= prev_low:
            logger.debug("Inside bar detected")
            return EntrySignalType.INSIDE_BAR

        return EntrySignalType.NONE

    def _check_ema20_reclaim(
        self,
        df: pd.DataFrame,
        ema20: pd.Series,
        direction: Literal["LONG", "SHORT"],
    ) -> bool:
        """
        Check if price reclaimed 20 EMA after pullback.

        For LONG: price was below EMA, now above
        For SHORT: price was above EMA, now below

        Args:
            df: DataFrame with OHLCV data.
            ema20: 20 EMA series.
            direction: LONG or SHORT.

        Returns:
            True if EMA reclaimed, False otherwise.
        """
        if len(df) < 5:
            return False

        current_price = df["close"].iloc[-1]
        current_ema = ema20.iloc[-1]

        if pd.isna(current_ema):
            return False

        # Check previous candles (last 2-5)
        for i in range(2, min(6, len(df))):
            prev_price = df["close"].iloc[-i]
            prev_ema = ema20.iloc[-i]

            if pd.isna(prev_ema):
                continue

            if direction == "LONG":
                # Was below EMA, now above
                if prev_price < prev_ema and current_price > current_ema:
                    logger.debug("EMA20 reclaim (bullish) detected")
                    return True
            else:  # SHORT
                # Was above EMA, now below
                if prev_price > prev_ema and current_price < current_ema:
                    logger.debug("EMA20 reclaim (bearish) detected")
                    return True

        return False

    def _check_rsi_turn(
        self,
        df: pd.DataFrame,
        rsi: pd.Series,
        direction: Literal["LONG", "SHORT"],
    ) -> RSITurn:
        """
        Check RSI turning from key levels.

        Long: RSI turns up from below 40 (oversold)
        Short: RSI turns down from above 60 (overbought)

        Args:
            df: DataFrame with OHLCV data.
            rsi: RSI series.
            direction: LONG or SHORT.

        Returns:
            RSITurn enum value.
        """
        if len(rsi) < 3:
            return RSITurn.NONE

        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        prev2_rsi = rsi.iloc[-3]

        if pd.isna(current_rsi) or pd.isna(prev_rsi) or pd.isna(prev2_rsi):
            return RSITurn.NONE

        if direction == "LONG":
            # Check if RSI was oversold and turning up
            if prev_rsi < self.rsi_oversold and current_rsi > prev_rsi:
                logger.debug(f"RSI turning up from oversold ({prev_rsi:.1f} → {current_rsi:.1f})")
                return RSITurn.UP_FROM_OVERSOLD

        else:  # SHORT
            # Check if RSI was overbought and turning down
            if prev_rsi > self.rsi_overbought and current_rsi < prev_rsi:
                logger.debug(f"RSI turning down from overbought ({prev_rsi:.1f} → {current_rsi:.1f})")
                return RSITurn.DOWN_FROM_OVERBOUGHT

        return RSITurn.NONE

    def _calculate_stop_loss(
        self,
        df: pd.DataFrame,
        direction: Literal["LONG", "SHORT"],
    ) -> float:
        """
        Calculate stop loss at LTF structure level.

        For LONG: below recent swing low
        For SHORT: above recent swing high

        Args:
            df: DataFrame with OHLCV data.
            direction: LONG or SHORT.

        Returns:
            Stop loss price.
        """
        lookback = min(10, len(df))

        if direction == "LONG":
            # Find recent swing low
            recent_low = df["low"].iloc[-lookback:].min()
            # Add small buffer (0.5%)
            stop_loss = recent_low * 0.995
        else:  # SHORT
            # Find recent swing high
            recent_high = df["high"].iloc[-lookback:].max()
            # Add small buffer (0.5%)
            stop_loss = recent_high * 1.005

        return float(stop_loss)


def find_ltf_entry(
    df: pd.DataFrame,
    setup: MTFSetup,
    direction: Literal["LONG", "SHORT"],
    ema20_period: int = 20,
) -> Optional[LTFEntry]:
    """
    Convenience function to find LTF entry signal.

    Args:
        df: DataFrame with OHLCV data.
        setup: MTF setup.
        direction: LONG or SHORT.
        ema20_period: 20 EMA period.

    Returns:
        LTFEntry object if signal found.

    Example:
        >>> from src.data_fetcher import fetch_ohlcv
        >>> df = fetch_ohlcv('BTC/USDT', '1h')
        >>> setup = MTFSetup(setup_type=SetupType.PULLBACK, ...)
        >>> entry = find_ltf_entry(df, setup, "LONG")
        >>> if entry:
        ...     print(f"Entry: {entry.entry_price}, Stop: {entry.stop_loss}")
    """
    finder = LTFEntryFinder(ema20_period=ema20_period)
    return finder.find_entry(df, setup, direction)
