"""
Support/Resistance Level Detector for MTF Analysis.

This module identifies key support and resistance levels across timeframes,
following the MTF framework from multi_timeframe.md.

Methods:
- Swing-based S/R identification
- Volume-based S/R identification
- Round numbers (psychological levels)
- Converging levels (extremely significant)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    ConvergingLevel,
    LevelStrength,
    LevelType,
    SupportResistanceLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class VolumeNode:
    """
    Represents a high-volume price node.

    Attributes:
        price: Price level.
        volume: Total volume at this level.
        bar_count: Number of bars at this level.
    """

    price: float
    volume: float
    bar_count: int


class SupportResistanceDetector:
    """
    Identify key support and resistance levels.

    The detector uses multiple methods to find significant S/R levels:
    1. Swing highs/lows (price structure)
    2. Volume nodes (high-volume areas)
    3. Round numbers (psychological levels)

    Attributes:
        swing_window: Rolling window for swing detection (default 5).
        volume_bins: Number of price bins for volume analysis (default 50).
        round_number_base: Base for round numbers (default 10, 100, 1000).
    """

    def __init__(
        self,
        swing_window: int = 5,
        volume_bins: int = 50,
        round_number_base: float = 100,
    ):
        """
        Initialize S/R detector.

        Args:
            swing_window: Rolling window for swing detection.
            volume_bins: Number of price bins for volume analysis.
            round_number_base: Base for round number detection.
        """
        self.swing_window = swing_window
        self.volume_bins = volume_bins
        self.round_number_base = round_number_base

    def identify_levels(
        self,
        df: pd.DataFrame,
        timeframe: str = "unknown",
    ) -> List[SupportResistanceLevel]:
        """
        Identify significant S/R levels.

        Returns levels with:
        - Price
        - Strength (strong/medium/weak)
        - Type (support/resistance)
        - Touch count
        - Timeframe origin

        Args:
            df: DataFrame with OHLCV data (must have 'high', 'low', 'close').
            timeframe: Timeframe identifier for tracking origin.

        Returns:
            List of SupportResistanceLevel objects sorted by strength.

        Example:
            >>> detector = SupportResistanceDetector()
            >>> levels = detector.identify_levels(ohlcv_df, "d1")
            >>> for level in levels[:3]:
            ...     print(f"{level.level_type.value} at {level.price:.2f} ({level.strength.value})")
        """
        if df.empty or len(df) < self.swing_window * 2:
            logger.warning("Insufficient data for S/R detection")
            return []

        # Ensure required columns
        df = df.copy()
        required_cols = {"high", "low", "close"}
        available_cols = set(df.columns.str.lower())
        if not required_cols.issubset(available_cols):
            logger.warning(f"Missing columns for S/R: {required_cols - available_cols}")
            return []

        # Standardize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})

        levels = []

        # Method 1: Swing-based levels
        swing_levels = self._identify_swing_levels(df, timeframe)
        levels.extend(swing_levels)

        # Method 2: Volume-based levels (if volume available)
        if "volume" in df.columns:
            volume_levels = self._identify_volume_levels(df, timeframe)
            levels.extend(volume_levels)

        # Method 3: Round numbers near current price
        round_levels = self._identify_round_numbers(df, timeframe)
        levels.extend(round_levels)

        # Merge nearby levels and calculate strength
        merged_levels = self._merge_nearby_levels(levels)

        # Sort by strength
        merged_levels.sort(
            key=lambda x: (
                x.strength.value,
                x.touch_count,
            ),
            reverse=True,
        )

        logger.info(f"Identified {len(merged_levels)} S/R levels")
        return merged_levels

    def _identify_swing_levels(
        self,
        df: pd.DataFrame,
        timeframe: str,
    ) -> List[SupportResistanceLevel]:
        """
        Identify S/R levels from swing highs and lows.

        Args:
            df: DataFrame with OHLCV data.
            timeframe: Timeframe identifier.

        Returns:
            List of SupportResistanceLevel objects.
        """
        levels = []
        highs = df["high"].values
        lows = df["low"].values
        timestamps = df.index.tolist() if hasattr(df.index, "tolist") else list(range(len(df)))
        current_price = df["close"].iloc[-1]

        for i in range(self.swing_window, len(df) - self.swing_window):
            # Check for swing high
            left_highs = highs[i - self.swing_window : i]
            right_highs = highs[i + 1 : i + self.swing_window + 1]

            if len(left_highs) > 0 and len(right_highs) > 0:
                if highs[i] > left_highs.max() and highs[i] > right_highs.max():
                    # Calculate strength
                    left_diff = (highs[i] - left_highs.max()) / highs[i]
                    right_diff = (highs[i] - right_highs.max()) / highs[i]
                    strength_val = min(1.0, (left_diff + right_diff) * 10)

                    level_type = (
                        LevelType.RESISTANCE
                        if highs[i] > current_price
                        else LevelType.SUPPORT
                    )

                    levels.append(SupportResistanceLevel(
                        price=float(highs[i]),
                        level_type=level_type,
                        strength=self._strength_from_value(strength_val),
                        touch_count=1,
                        timeframe_origin=timeframe,
                        last_tested=str(timestamps[i]),
                    ))

            # Check for swing low
            left_lows = lows[i - self.swing_window : i]
            right_lows = lows[i + 1 : i + self.swing_window + 1]

            if len(left_lows) > 0 and len(right_lows) > 0:
                if lows[i] < left_lows.min() and lows[i] < right_lows.min():
                    left_diff = (left_lows.min() - lows[i]) / lows[i]
                    right_diff = (right_lows.min() - lows[i]) / lows[i]
                    strength_val = min(1.0, (left_diff + right_diff) * 10)

                    level_type = (
                        LevelType.SUPPORT
                        if lows[i] < current_price
                        else LevelType.RESISTANCE
                    )

                    levels.append(SupportResistanceLevel(
                        price=float(lows[i]),
                        level_type=level_type,
                        strength=self._strength_from_value(strength_val),
                        touch_count=1,
                        timeframe_origin=timeframe,
                        last_tested=str(timestamps[i]),
                    ))

        return levels

    def _identify_volume_levels(
        self,
        df: pd.DataFrame,
        timeframe: str,
    ) -> List[SupportResistanceLevel]:
        """
        Identify S/R levels from volume nodes (high-volume areas).

        Uses volume profile analysis to find price levels with significant
        trading activity.

        Args:
            df: DataFrame with OHLCV data.
            timeframe: Timeframe identifier.

        Returns:
            List of SupportResistanceLevel objects.
        """
        levels = []
        current_price = df["close"].iloc[-1]

        # Create price bins
        price_range = df["high"].max() - df["low"].min()
        if price_range == 0:
            return []

        bin_size = price_range / self.volume_bins
        volume_by_bin: Dict[int, float] = {}
        count_by_bin: Dict[int, int] = {}

        for _, row in df.iterrows():
            avg_price = (row["high"] + row["low"]) / 2
            bin_idx = int((avg_price - df["low"].min()) / bin_size)

            if bin_idx not in volume_by_bin:
                volume_by_bin[bin_idx] = 0
                count_by_bin[bin_idx] = 0

            volume_by_bin[bin_idx] += row["volume"]
            count_by_bin[bin_idx] += 1

        # Find high-volume bins
        if not volume_by_bin:
            return []

        avg_volume = sum(volume_by_bin.values()) / len(volume_by_bin)

        for bin_idx, volume in volume_by_bin.items():
            if volume > avg_volume * 1.5:  # 50% above average
                bin_price = df["low"].min() + bin_idx * bin_size + bin_size / 2

                level_type = (
                    LevelType.SUPPORT if bin_price < current_price else LevelType.RESISTANCE
                )

                # Strength based on volume relative to average
                strength_val = min(1.0, (volume / avg_volume - 1) / 2)

                levels.append(SupportResistanceLevel(
                    price=float(bin_price),
                    level_type=level_type,
                    strength=self._strength_from_value(strength_val),
                    touch_count=count_by_bin[bin_idx],
                    timeframe_origin=timeframe,
                ))

        return levels

    def _identify_round_numbers(
        self,
        df: pd.DataFrame,
        timeframe: str,
    ) -> List[SupportResistanceLevel]:
        """
        Identify psychological round number levels.

        Round numbers (e.g., 100, 1000, 50000) often act as S/R
        due to human psychology and option strikes.

        Args:
            df: DataFrame with OHLCV data.
            timeframe: Timeframe identifier.

        Returns:
            List of SupportResistanceLevel objects.
        """
        levels = []
        current_price = df["close"].iloc[-1]
        price_range = df["high"].max() - df["low"].min()

        # Generate round numbers near current price
        base = self.round_number_base
        current_round = round(current_price / base) * base

        # Check round numbers within 2x price range
        for offset in range(-3, 4):
            round_price = current_round + offset * base

            if abs(round_price - current_price) <= price_range * 2:
                level_type = (
                    LevelType.SUPPORT if round_price < current_price else LevelType.RESISTANCE
                )

                levels.append(SupportResistanceLevel(
                    price=float(round_price),
                    level_type=level_type,
                    strength=LevelStrength.MEDIUM,  # Round numbers are psychologically significant
                    touch_count=0,  # Not based on touches
                    timeframe_origin=timeframe,
                ))

        return levels

    def _merge_nearby_levels(
        self,
        levels: List[SupportResistanceLevel],
        tolerance_pct: float = 0.005,
    ) -> List[SupportResistanceLevel]:
        """
        Merge S/R levels that are close together.

        Multiple methods may identify levels at similar prices.
        This merges them and increases strength/touch count.

        Args:
            levels: List of S/R levels.
            tolerance_pct: Price tolerance for merging (default 0.5%).

        Returns:
            List of merged SupportResistanceLevel objects.
        """
        if not levels:
            return []

        # Sort by price
        levels.sort(key=lambda x: x.price)

        merged = []
        current_group = [levels[0]]

        for level in levels[1:]:
            # Check if level is close to current group
            avg_price = sum(l.price for l in current_group) / len(current_group)
            if avg_price == 0 or abs(level.price - avg_price) / avg_price <= tolerance_pct:
                # Merge into current group
                current_group.append(level)
            else:
                # Finalize current group and start new one
                merged.append(self._merge_level_group(current_group))
                current_group = [level]

        # Don't forget last group
        if current_group:
            merged.append(self._merge_level_group(current_group))

        return merged

    def _merge_level_group(
        self,
        group: List[SupportResistanceLevel],
    ) -> SupportResistanceLevel:
        """
        Merge a group of nearby levels into one.

        Args:
            group: List of S/R levels to merge.

        Returns:
            Merged SupportResistanceLevel object.
        """
        # Average price
        avg_price = sum(l.price for l in group) / len(group)

        # Sum touch counts
        total_touches = sum(l.touch_count for l in group)

        # Use most common level type
        support_count = sum(1 for l in group if l.level_type == LevelType.SUPPORT)
        resistance_count = sum(1 for l in group if l.level_type == LevelType.RESISTANCE)
        level_type = (
            LevelType.SUPPORT if support_count >= resistance_count else LevelType.RESISTANCE
        )

        # Calculate strength from group size and individual strengths
        strength_value = len(group) * 0.2  # Base from group size
        strength_value += sum(
            {"STRONG": 0.3, "MEDIUM": 0.2, "WEAK": 0.1}.get(l.strength.value, 0)
            for l in group
        )

        # Most recent timestamp
        timestamps = [l.last_tested for l in group if l.last_tested]
        last_tested = max(timestamps) if timestamps else None

        return SupportResistanceLevel(
            price=avg_price,
            level_type=level_type,
            strength=self._strength_from_value(min(1.0, strength_value)),
            touch_count=total_touches,
            timeframe_origin=group[0].timeframe_origin,
            last_tested=last_tested,
        )

    def _strength_from_value(self, value: float) -> LevelStrength:
        """
        Convert numeric strength value to LevelStrength enum.

        Args:
            value: Strength value 0.0-1.0.

        Returns:
            LevelStrength enum value.
        """
        if value >= 0.6:
            return LevelStrength.STRONG
        elif value >= 0.3:
            return LevelStrength.MEDIUM
        else:
            return LevelStrength.WEAK

    def find_converging_levels(
        self,
        levels_by_timeframe: Dict[str, List[SupportResistanceLevel]],
        tolerance_pct: float = 0.005,
    ) -> List[ConvergingLevel]:
        """
        Find S/R levels that converge across multiple timeframes.

        Converging levels (same price on multiple TFs) are extremely
        significant and often act as strong support/resistance.

        Args:
            levels_by_timeframe: Dict of timeframe → S/R levels.
            tolerance_pct: Price tolerance for convergence (default 0.5%).

        Returns:
            List of ConvergingLevel objects.

        Example:
            >>> detector = SupportResistanceDetector()
            >>> levels_htf = detector.identify_levels(htf_df, "d1")
            >>> levels_mtf = detector.identify_levels(mtf_df, "h4")
            >>> levels_ltf = detector.identify_levels(ltf_df, "h1")
            >>> converging = detector.find_converging_levels({
            ...     "d1": levels_htf, "h4": levels_mtf, "h1": levels_ltf
            ... })
            >>> if converging:
            ...     print(f"Converging level at {converging[0].avg_price}")
        """
        if not levels_by_timeframe:
            return []

        converging = []

        # Flatten all levels with their timeframe
        all_levels = []
        for tf, levels in levels_by_timeframe.items():
            for level in levels:
                all_levels.append((tf, level))

        if len(all_levels) < 2:
            return []

        # Group by price proximity
        all_levels.sort(key=lambda x: x[1].price)

        groups: List[List[Tuple[str, SupportResistanceLevel]]] = []
        current_group = [all_levels[0]]

        for tf, level in all_levels[1:]:
            avg_price = sum(l.price for _, l in current_group) / len(current_group)
            if abs(level.price - avg_price) / avg_price <= tolerance_pct:
                current_group.append((tf, level))
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [(tf, level)]

        if len(current_group) >= 2:
            groups.append(current_group)

        # Create ConvergingLevel objects
        for group in groups:
            timeframes = [tf for tf, _ in group]
            levels = [l for _, l in group]

            avg_price = sum(l.price for l in levels) / len(levels)

            # Strength increases with number of timeframes
            if len(timeframes) >= 3:
                strength = LevelStrength.STRONG
            elif len(timeframes) >= 2:
                strength = LevelStrength.MEDIUM
            else:
                strength = LevelStrength.WEAK

            # Determine type
            support_count = sum(1 for l in levels if l.level_type == LevelType.SUPPORT)
            resistance_count = sum(1 for l in levels if l.level_type == LevelType.RESISTANCE)
            level_type = (
                LevelType.SUPPORT if support_count >= resistance_count else LevelType.RESISTANCE
            )

            converging.append(ConvergingLevel(
                avg_price=avg_price,
                level_type=level_type,
                strength=strength,
                timeframes=timeframes,
                level_count=len(levels),
            ))

        # Sort by strength and timeframe count
        converging.sort(
            key=lambda x: (x.strength.value, x.level_count),
            reverse=True,
        )

        logger.info(f"Found {len(converging)} converging S/R levels")
        return converging


def identify_support_resistance(
    df: pd.DataFrame,
    timeframe: str = "unknown",
) -> List[SupportResistanceLevel]:
    """
    Convenience function to identify S/R levels.

    Args:
        df: DataFrame with OHLCV data.
        timeframe: Timeframe identifier.

    Returns:
        List of SupportResistanceLevel objects.
    """
    detector = SupportResistanceDetector()
    return detector.identify_levels(df, timeframe)
