"""
RSI Divergence Detector for MTF Analysis.

This module detects RSI divergence patterns across timeframes,
following the MTF framework from multi_timeframe.md.

Divergence Types:
- Regular Bullish: Price lower low, RSI higher low (reversal signal)
- Regular Bearish: Price higher high, RSI lower high (reversal signal)
- Hidden Bullish: Price higher low, RSI lower low (trend continuation)
- Hidden Bearish: Price lower high, RSI higher high (trend continuation)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    DivergenceSignal,
    DivergenceType,
    MTFDirection,
    SwingPoint,
)

logger = logging.getLogger(__name__)


@dataclass
class DivergenceZone:
    """
    Represents a price/RSI divergence zone.

    Attributes:
        price_swing: Swing point in price.
        rsi_value: RSI value at the swing point.
        timestamp: Timestamp of the swing.
        index: Candle index of the swing.
    """

    price_swing: SwingPoint
    rsi_value: float
    timestamp: str
    index: int


@dataclass
class DivergenceResult:
    """
    Result of divergence detection scan.

    Attributes:
        divergences: List of detected divergence signals.
        latest_type: Most recent divergence type (if any).
        latest_timestamp: Timestamp of latest divergence.
        confidence: Overall confidence score (0.0-1.0).
    """

    divergences: List[DivergenceSignal] = field(default_factory=list)
    latest_type: Optional[DivergenceType] = None
    latest_timestamp: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "divergences": [d.to_dict() for d in self.divergences],
            "latest_type": self.latest_type.value if self.latest_type else None,
            "latest_timestamp": self.latest_timestamp,
            "confidence": round(self.confidence, 2),
            "count": len(self.divergences),
        }


class DivergenceDetector:
    """
    Detect RSI divergence patterns.

    Divergence occurs when price and momentum (RSI) move in opposite directions,
    signaling potential trend reversal or continuation.

    Attributes:
        rsi_length: RSI calculation period (default 14).
        lookback_bars: Number of candles to look back for divergence (default 50).
        min_bars_between_swings: Minimum candles between swing points (default 5).
        tolerance_pct: Price/RSI comparison tolerance percentage (default 0.01).
    """

    def __init__(
        self,
        rsi_length: int = 14,
        lookback_bars: int = 50,
        min_bars_between_swings: int = 5,
        tolerance_pct: float = 0.01,
    ):
        """
        Initialize divergence detector.

        Args:
            rsi_length: RSI calculation period.
            lookback_bars: Number of candles to scan.
            min_bars_between_swings: Minimum separation between swings.
            tolerance_pct: Tolerance for comparing price/RSI levels.
        """
        self.rsi_length = rsi_length
        self.lookback_bars = lookback_bars
        self.min_bars_between_swings = min_bars_between_swings
        self.tolerance_pct = tolerance_pct

    def detect_divergence(
        self,
        df: pd.DataFrame,
        rsi_length: Optional[int] = None,
        lookback_bars: Optional[int] = None,
    ) -> DivergenceResult:
        """
        Scan for RSI divergence patterns.

        Returns list of divergence signals with:
        - Type (regular/hidden, bullish/bearish)
        - Price swing points
        - RSI swing points
        - Confidence score

        Args:
            df: DataFrame with OHLCV data (must have 'close', 'high', 'low').
            rsi_length: RSI period (overrides default).
            lookback_bars: Lookback period (overrides default).

        Returns:
            DivergenceResult object with detected divergences.

        Example:
            >>> detector = DivergenceDetector()
            >>> result = detector.detect_divergence(ohlcv_df)
            >>> if result.divergences:
            ...     print(f"Found {len(result.divergences)} divergences")
            ...     print(f"Latest: {result.latest_type.value}")
        """
        if df.empty or len(df) < self.rsi_length + 10:
            logger.warning("Insufficient data for divergence detection")
            return DivergenceResult()

        # Use overrides or defaults
        rsi_len = rsi_length or self.rsi_length
        lookback = lookback_bars or self.lookback_bars

        # Ensure required columns
        df = df.copy()
        required_cols = {"close", "high", "low"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            logger.warning(f"Missing columns for divergence: {required_cols - available_cols}")
            return DivergenceResult()

        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})

        # Take lookback window
        df = df.iloc[-lookback:].reset_index(drop=True)

        # Calculate RSI
        rsi = self._calculate_rsi(df["close"], rsi_len)

        # Find price swings
        price_swings = self._find_price_swings(df)

        if len(price_swings) < 2:
            logger.debug("Insufficient price swings for divergence")
            return DivergenceResult()

        # Find RSI swings at same indices
        rsi_swings = self._find_rsi_swings(rsi, price_swings)

        # Detect divergences
        divergences = []

        # Check for regular bullish divergence
        reg_bullish = self._detect_regular_bullish(price_swings, rsi_swings)
        if reg_bullish:
            divergences.append(reg_bullish)

        # Check for regular bearish divergence
        reg_bearish = self._detect_regular_bearish(price_swings, rsi_swings)
        if reg_bearish:
            divergences.append(reg_bearish)

        # Check for hidden bullish divergence
        hid_bullish = self._detect_hidden_bullish(price_swings, rsi_swings)
        if hid_bullish:
            divergences.append(hid_bullish)

        # Check for hidden bearish divergence
        hid_bearish = self._detect_hidden_bearish(price_swings, rsi_swings)
        if hid_bearish:
            divergences.append(hid_bearish)

        # Sort by timestamp (most recent first)
        divergences.sort(key=lambda x: x.timestamp or "", reverse=True)

        # Build result
        result = DivergenceResult(
            divergences=divergences,
            latest_type=divergences[0].divergence_type if divergences else None,
            latest_timestamp=divergences[0].timestamp if divergences else None,
            confidence=self._calculate_confidence(divergences),
        )

        if divergences:
            logger.info(
                f"Detected {len(divergences)} divergence(s), "
                f"latest: {result.latest_type.value if result.latest_type else 'None'}"
            )

        return result

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

    def _find_price_swings(
        self,
        df: pd.DataFrame,
        window: int = 5,
    ) -> List[SwingPoint]:
        """
        Find swing highs and lows in price data.

        Args:
            df: DataFrame with OHLCV data.
            window: Rolling window for swing detection.

        Returns:
            List of SwingPoint objects.
        """
        swings = []
        highs = df["high"].values
        lows = df["low"].values
        timestamps = df.index.tolist() if hasattr(df.index, "tolist") else list(range(len(df)))

        for i in range(window, len(df) - window):
            # Check for swing high
            left_highs = highs[i - window : i]
            right_highs = highs[i + 1 : i + window + 1]

            if len(left_highs) > 0 and len(right_highs) > 0:
                if highs[i] > left_highs.max() and highs[i] > right_highs.max():
                    # Calculate strength
                    left_diff = (highs[i] - left_highs.max()) / highs[i]
                    right_diff = (highs[i] - right_highs.max()) / highs[i]
                    strength = min(1.0, (left_diff + right_diff) * 10)

                    if strength >= 0.3:  # Minimum strength threshold
                        swings.append(SwingPoint(
                            price=float(highs[i]),
                            index=i,
                            timestamp=str(timestamps[i]),
                            swing_type="HIGH",
                            strength=float(strength),
                        ))

            # Check for swing low
            left_lows = lows[i - window : i]
            right_lows = lows[i + 1 : i + window + 1]

            if len(left_lows) > 0 and len(right_lows) > 0:
                if lows[i] < left_lows.min() and lows[i] < right_lows.min():
                    # Calculate strength
                    left_diff = (left_lows.min() - lows[i]) / lows[i]
                    right_diff = (right_lows.min() - lows[i]) / lows[i]
                    strength = min(1.0, (left_diff + right_diff) * 10)

                    if strength >= 0.3:
                        swings.append(SwingPoint(
                            price=float(lows[i]),
                            index=i,
                            timestamp=str(timestamps[i]),
                            swing_type="LOW",
                            strength=float(strength),
                        ))

        logger.debug(f"Found {len(swings)} price swings")
        return swings

    def _find_rsi_swings(
        self,
        rsi: pd.Series,
        price_swings: List[SwingPoint],
    ) -> List[DivergenceZone]:
        """
        Find RSI values at price swing points.

        Args:
            rsi: RSI series.
            price_swings: List of price swing points.

        Returns:
            List of DivergenceZone objects.
        """
        zones = []

        for swing in price_swings:
            if swing.index < len(rsi):
                rsi_value = rsi.iloc[swing.index]
                if not pd.isna(rsi_value):
                    zones.append(DivergenceZone(
                        price_swing=swing,
                        rsi_value=float(rsi_value),
                        timestamp=swing.timestamp,
                        index=swing.index,
                    ))

        return zones

    def _detect_regular_bullish(
        self,
        price_swings: List[SwingPoint],
        rsi_zones: List[DivergenceZone],
    ) -> Optional[DivergenceSignal]:
        """
        Detect regular bullish divergence.

        Pattern: Price makes lower low, RSI makes higher low.
        Signal: Potential bullish reversal.

        Args:
            price_swings: List of price swing points.
            rsi_zones: List of RSI zones at swing points.

        Returns:
            DivergenceSignal if detected, None otherwise.
        """
        # Get swing lows (sorted by index, oldest first)
        lows = [s for s in price_swings if s.swing_type == "LOW"]
        lows.sort(key=lambda x: x.index)

        if len(lows) < 2:
            return None

        # Get corresponding RSI zones
        rsi_lows = [z for z in rsi_zones if z.price_swing.swing_type == "LOW"]
        rsi_lows.sort(key=lambda x: x.index)

        if len(rsi_lows) < 2:
            return None

        # Check last 2 swing lows
        for i in range(len(lows) - 1, 0, -1):
            swing1 = lows[i - 1]  # Older low
            swing2 = lows[i]      # Newer low

            # Find corresponding RSI values
            rsi1 = None
            rsi2 = None
            for z in rsi_lows:
                if z.index == swing1.index:
                    rsi1 = z.rsi_value
                if z.index == swing2.index:
                    rsi2 = z.rsi_value

            if rsi1 is None or rsi2 is None:
                continue

            # Check for divergence: price lower low, RSI higher low
            price_lower_low = swing2.price < swing1.price * (1 - self.tolerance_pct)
            rsi_higher_low = rsi2 > rsi1 * (1 + self.tolerance_pct)

            if price_lower_low and rsi_higher_low:
                # Calculate confidence based on magnitude
                price_diff_pct = (swing1.price - swing2.price) / swing1.price
                rsi_diff_pct = (rsi2 - rsi1) / rsi1
                confidence = min(1.0, (price_diff_pct * 10 + rsi_diff_pct * 10) / 2)

                logger.debug(
                    f"Regular bullish divergence: price {swing1.price:.2f}→{swing2.price:.2f}, "
                    f"RSI {rsi1:.2f}→{rsi2:.2f}"
                )

                return DivergenceSignal(
                    divergence_type=DivergenceType.REGULAR_BULLISH,
                    price_swing_1=swing1,
                    price_swing_2=swing2,
                    rsi_swing_1=rsi1,
                    rsi_swing_2=rsi2,
                    confidence=confidence,
                    timestamp=swing2.timestamp,
                )

        return None

    def _detect_regular_bearish(
        self,
        price_swings: List[SwingPoint],
        rsi_zones: List[DivergenceZone],
    ) -> Optional[DivergenceSignal]:
        """
        Detect regular bearish divergence.

        Pattern: Price makes higher high, RSI makes lower high.
        Signal: Potential bearish reversal.

        Args:
            price_swings: List of price swing points.
            rsi_zones: List of RSI zones at swing points.

        Returns:
            DivergenceSignal if detected, None otherwise.
        """
        # Get swing highs
        highs = [s for s in price_swings if s.swing_type == "HIGH"]
        highs.sort(key=lambda x: x.index)

        if len(highs) < 2:
            return None

        # Get corresponding RSI zones
        rsi_highs = [z for z in rsi_zones if z.price_swing.swing_type == "HIGH"]
        rsi_highs.sort(key=lambda x: x.index)

        if len(rsi_highs) < 2:
            return None

        # Check last 2 swing highs
        for i in range(len(highs) - 1, 0, -1):
            swing1 = highs[i - 1]  # Older high
            swing2 = highs[i]      # Newer high

            # Find corresponding RSI values
            rsi1 = None
            rsi2 = None
            for z in rsi_highs:
                if z.index == swing1.index:
                    rsi1 = z.rsi_value
                if z.index == swing2.index:
                    rsi2 = z.rsi_value

            if rsi1 is None or rsi2 is None:
                continue

            # Check for divergence: price higher high, RSI lower high
            price_higher_high = swing2.price > swing1.price * (1 + self.tolerance_pct)
            rsi_lower_high = rsi2 < rsi1 * (1 - self.tolerance_pct)

            if price_higher_high and rsi_lower_high:
                # Calculate confidence
                price_diff_pct = (swing2.price - swing1.price) / swing1.price
                rsi_diff_pct = (rsi1 - rsi2) / rsi1
                confidence = min(1.0, (price_diff_pct * 10 + rsi_diff_pct * 10) / 2)

                logger.debug(
                    f"Regular bearish divergence: price {swing1.price:.2f}→{swing2.price:.2f}, "
                    f"RSI {rsi1:.2f}→{rsi2:.2f}"
                )

                return DivergenceSignal(
                    divergence_type=DivergenceType.REGULAR_BEARISH,
                    price_swing_1=swing1,
                    price_swing_2=swing2,
                    rsi_swing_1=rsi1,
                    rsi_swing_2=rsi2,
                    confidence=confidence,
                    timestamp=swing2.timestamp,
                )

        return None

    def _detect_hidden_bullish(
        self,
        price_swings: List[SwingPoint],
        rsi_zones: List[DivergenceZone],
    ) -> Optional[DivergenceSignal]:
        """
        Detect hidden bullish divergence.

        Pattern: Price makes higher low, RSI makes lower low.
        Signal: Bullish trend continuation.

        Args:
            price_swings: List of price swing points.
            rsi_zones: List of RSI zones at swing points.

        Returns:
            DivergenceSignal if detected, None otherwise.
        """
        lows = [s for s in price_swings if s.swing_type == "LOW"]
        lows.sort(key=lambda x: x.index)

        if len(lows) < 2:
            return None

        rsi_lows = [z for z in rsi_zones if z.price_swing.swing_type == "LOW"]
        rsi_lows.sort(key=lambda x: x.index)

        if len(rsi_lows) < 2:
            return None

        for i in range(len(lows) - 1, 0, -1):
            swing1 = lows[i - 1]
            swing2 = lows[i]

            rsi1 = None
            rsi2 = None
            for z in rsi_lows:
                if z.index == swing1.index:
                    rsi1 = z.rsi_value
                if z.index == swing2.index:
                    rsi2 = z.rsi_value

            if rsi1 is None or rsi2 is None:
                continue

            # Hidden bullish: price higher low, RSI lower low
            price_higher_low = swing2.price > swing1.price * (1 + self.tolerance_pct)
            rsi_lower_low = rsi2 < rsi1 * (1 - self.tolerance_pct)

            if price_higher_low and rsi_lower_low:
                price_diff_pct = (swing2.price - swing1.price) / swing1.price
                rsi_diff_pct = (rsi1 - rsi2) / rsi1
                confidence = min(1.0, (price_diff_pct * 10 + rsi_diff_pct * 10) / 2) * 0.8

                logger.debug(
                    f"Hidden bullish divergence: price {swing1.price:.2f}→{swing2.price:.2f}, "
                    f"RSI {rsi1:.2f}→{rsi2:.2f}"
                )

                return DivergenceSignal(
                    divergence_type=DivergenceType.HIDDEN_BULLISH,
                    price_swing_1=swing1,
                    price_swing_2=swing2,
                    rsi_swing_1=rsi1,
                    rsi_swing_2=rsi2,
                    confidence=confidence,
                    timestamp=swing2.timestamp,
                )

        return None

    def _detect_hidden_bearish(
        self,
        price_swings: List[SwingPoint],
        rsi_zones: List[DivergenceZone],
    ) -> Optional[DivergenceSignal]:
        """
        Detect hidden bearish divergence.

        Pattern: Price makes lower high, RSI makes higher high.
        Signal: Bearish trend continuation.

        Args:
            price_swings: List of price swing points.
            rsi_zones: List of RSI zones at swing points.

        Returns:
            DivergenceSignal if detected, None otherwise.
        """
        highs = [s for s in price_swings if s.swing_type == "HIGH"]
        highs.sort(key=lambda x: x.index)

        if len(highs) < 2:
            return None

        rsi_highs = [z for z in rsi_zones if z.price_swing.swing_type == "HIGH"]
        rsi_highs.sort(key=lambda x: x.index)

        if len(rsi_highs) < 2:
            return None

        for i in range(len(highs) - 1, 0, -1):
            swing1 = highs[i - 1]
            swing2 = highs[i]

            rsi1 = None
            rsi2 = None
            for z in rsi_highs:
                if z.index == swing1.index:
                    rsi1 = z.rsi_value
                if z.index == swing2.index:
                    rsi2 = z.rsi_value

            if rsi1 is None or rsi2 is None:
                continue

            # Hidden bearish: price lower high, RSI higher high
            price_lower_high = swing2.price < swing1.price * (1 - self.tolerance_pct)
            rsi_higher_high = rsi2 > rsi1 * (1 + self.tolerance_pct)

            if price_lower_high and rsi_higher_high:
                price_diff_pct = (swing1.price - swing2.price) / swing1.price
                rsi_diff_pct = (rsi2 - rsi1) / rsi1
                confidence = min(1.0, (price_diff_pct * 10 + rsi_diff_pct * 10) / 2) * 0.8

                logger.debug(
                    f"Hidden bearish divergence: price {swing1.price:.2f}→{swing2.price:.2f}, "
                    f"RSI {rsi1:.2f}→{rsi2:.2f}"
                )

                return DivergenceSignal(
                    divergence_type=DivergenceType.HIDDEN_BEARISH,
                    price_swing_1=swing1,
                    price_swing_2=swing2,
                    rsi_swing_1=rsi1,
                    rsi_swing_2=rsi2,
                    confidence=confidence,
                    timestamp=swing2.timestamp,
                )

        return None

    def _calculate_confidence(self, divergences: List[DivergenceSignal]) -> float:
        """
        Calculate overall confidence score.

        Args:
            divergences: List of detected divergence signals.

        Returns:
            Confidence score 0.0-1.0.
        """
        if not divergences:
            return 0.0

        # Average confidence of all divergences
        avg_confidence = sum(d.confidence for d in divergences) / len(divergences)

        # Bonus for multiple divergences
        if len(divergences) >= 2:
            avg_confidence = min(1.0, avg_confidence + 0.1)
        if len(divergences) >= 3:
            avg_confidence = min(1.0, avg_confidence + 0.1)

        return avg_confidence


def detect_divergence(
    df: pd.DataFrame,
    rsi_length: int = 14,
    lookback_bars: int = 50,
) -> DivergenceResult:
    """
    Convenience function to detect RSI divergence.

    Args:
        df: DataFrame with OHLCV data.
        rsi_length: RSI period.
        lookback_bars: Lookback period.

    Returns:
        DivergenceResult object.

    Example:
        >>> from src.data_fetcher import fetch_ohlcv
        >>> df = fetch_ohlcv('BTC/USDT', '4h')
        >>> result = detect_divergence(df)
        >>> if result.latest_type:
        ...     print(f"Divergence: {result.latest_type.value}")
    """
    detector = DivergenceDetector(
        rsi_length=rsi_length,
        lookback_bars=lookback_bars,
    )
    return detector.detect_divergence(df)
