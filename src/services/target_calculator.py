"""
Target Calculator for MTF Analysis.

This module calculates profit targets using 5 methods from the MTF framework:
1. Next HTF S/R level (primary)
2. Measured move / pattern target
3. Fibonacci extension (1.272, 1.618, 2.618)
4. ATR-based target (2x, 3x, 4-5x ATR)
5. Prior swing high/low (structural)

See multi_timeframe.md - Target Methods section.
"""

import logging
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.models.mtf_models import (
    HTFBias,
    LevelType,
    MTFDirection,
    MTFSetup,
    SetupType,
    SupportResistanceLevel,
    TargetMethod,
    TargetResult,
)

logger = logging.getLogger(__name__)


@dataclass
class FibLevels:
    """
    Fibonacci extension levels.

    Attributes:
        level_1272: 1.272 extension (conservative target).
        level_1618: 1.618 extension (standard target).
        level_2618: 2.618 extension (extended target).
    """

    level_1272: float
    level_1618: float
    level_2618: float


class TargetCalculator:
    """
    Calculate profit targets using 5 methods.

    The target calculator provides multiple methods for defining
    profit targets, allowing traders to choose based on market conditions.

    Attributes:
        atr_period: ATR calculation period (default 14).
        fib_anchor_bars: Number of bars to anchor Fibonacci (default 20).
    """

    def __init__(
        self,
        atr_period: int = 14,
        fib_anchor_bars: int = 20,
    ):
        """
        Initialize target calculator.

        Args:
            atr_period: ATR calculation period.
            fib_anchor_bars: Number of bars for Fibonacci anchoring.
        """
        self.atr_period = atr_period
        self.fib_anchor_bars = fib_anchor_bars

    def calculate_target(
        self,
        df_htf: pd.DataFrame,
        df_mtf: pd.DataFrame,
        entry_price: float,
        stop_loss: float,
        direction: Literal["LONG", "SHORT"],
        method: Optional[TargetMethod] = None,
        setup: Optional[MTFSetup] = None,
        htf_bias: Optional[HTFBias] = None,
    ) -> TargetResult:
        """
        Calculate target using specified or auto-selected method.

        Target Priority Guide:
        | Situation | Preferred Method |
        |-----------|------------------|
        | Clear HTF S/R ahead | HTF S/R Level |
        | Classical pattern present | Measured Move |
        | Strong new impulse starting | Fibonacci Extension |
        | No clear S/R; high volatility | ATR-Based |
        | Counter-trend or range trade | Prior Swing |

        Args:
            df_htf: HTF OHLCV data.
            df_mtf: MTF OHLCV data.
            entry_price: Entry price.
            stop_loss: Stop loss price.
            direction: LONG or SHORT.
            method: Target method (auto-selected if None).
            setup: MTF setup (for pattern targets).
            htf_bias: HTF bias (for S/R levels).

        Returns:
            TargetResult with target price and metadata.

        Example:
            >>> calc = TargetCalculator()
            >>> target = calc.calculate_target(
            ...     df_htf, df_mtf, entry=100, stop=95,
            ...     direction="LONG"
            ... )
            >>> print(f"Target: {target.target_price}, R:R: {target.rr_ratio}")
        """
        # Auto-select method if not specified
        if method is None:
            method = self._select_best_method(
                df_htf=df_htf,
                df_mtf=df_mtf,
                direction=direction,
                setup=setup,
                htf_bias=htf_bias,
                entry_price=entry_price,
                stop_loss=stop_loss,
            )

        # Calculate target based on method
        if method == TargetMethod.SR_LEVEL:
            target = self._calculate_sr_target(
                htf_bias=htf_bias,
                entry_price=entry_price,
                direction=direction,
            )
        elif method == TargetMethod.MEASURED_MOVE:
            target = self._calculate_measured_move(
                df=df_mtf,
                setup=setup,
                entry_price=entry_price,
                direction=direction,
            )
        elif method == TargetMethod.FIBONACCI:
            target = self._calculate_fib_target(
                df=df_mtf,
                entry_price=entry_price,
                direction=direction,
            )
        elif method == TargetMethod.ATR:
            target = self._calculate_atr_target(
                df=df_mtf,
                entry_price=entry_price,
                direction=direction,
            )
        elif method == TargetMethod.PRIOR_SWING:
            target = self._calculate_prior_swing_target(
                df=df_mtf,
                entry_price=entry_price,
                direction=direction,
            )
        else:
            # Default to ATR
            target = self._calculate_atr_target(
                df=df_mtf,
                entry_price=entry_price,
                direction=direction,
            )

        # Calculate R:R
        risk = abs(entry_price - stop_loss)
        if risk > 0:
            reward = abs(target.target_price - entry_price)
            target.rr_ratio = reward / risk

        logger.debug(
            f"Target calculated: {target.target_price:.4f} "
            f"({method.value}, R:R={target.rr_ratio:.2f})"
        )

        return target

    def _select_best_method(
        self,
        df_htf: pd.DataFrame,
        df_mtf: pd.DataFrame,
        direction: str,
        setup: Optional[MTFSetup],
        htf_bias: Optional[HTFBias],
        entry_price: float,
        stop_loss: float,
    ) -> TargetMethod:
        """
        Select best target method based on market conditions.

        Selection criteria:
        1. Calculate ALL methods
        2. Filter to methods with R:R >= 1.5:1 (to achieve final >= 2:1)
        3. Select method with highest R:R

        Args:
            df_htf: HTF OHLCV data.
            df_mtf: MTF OHLCV data.
            direction: LONG or SHORT.
            setup: MTF setup.
            htf_bias: HTF bias.
            entry_price: Entry price for R:R calculation.
            stop_loss: Stop loss for R:R calculation.

        Returns:
            TargetMethod enum value.
        """
        # Calculate all methods and their R:R
        method_results = []
        
        # Priority 1: Check for classical pattern (measured move)
        if setup and setup.setup_type in (
            SetupType.CONSOLIDATION,
            SetupType.BREAKOUT,
        ):
            if setup.consolidation_pattern in ("FLAG", "TRIANGLE", "RECTANGLE"):
                logger.debug("Auto-select: Measured Move (pattern detected)")
                return TargetMethod.MEASURED_MOVE
        
        # Try each method and calculate R:R
        for method in TargetMethod:
            try:
                target_result = self.calculate_target(
                    df_htf=df_htf,
                    df_mtf=df_mtf,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    direction=direction,
                    method=method,
                    setup=setup,
                    htf_bias=htf_bias,
                )
                
                # Only consider methods with acceptable R:R
                if target_result.rr_ratio >= 1.5:
                    method_results.append({
                        'method': method,
                        'rr_ratio': target_result.rr_ratio,
                        'confidence': target_result.confidence,
                    })
                    
            except Exception as e:
                logger.debug(f"Method {method.value} failed: {e}")
                continue
        
        # Select method with highest R:R
        if method_results:
            best = max(method_results, key=lambda x: (x['rr_ratio'], x['confidence']))
            logger.debug(f"Auto-select: {best['method'].value} (highest R:R: {best['rr_ratio']:.2f}:1)")
            return best['method']
        
        # Fallback: ATR (most reliable)
        logger.debug("Auto-select: ATR (fallback - no method met R:R threshold)")
        return TargetMethod.ATR

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate ATR for R:R estimation.
        
        Args:
            df: DataFrame with OHLCV data.
            period: ATR period (default 14).
            
        Returns:
            Current ATR value.
        """
        if len(df) < period + 1:
            return df["close"].std() if "close" in df.columns else 100.0
        
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(window=period).mean()
        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else float(atr.mean())

    def _calculate_sr_target(
        self,
        htf_bias: Optional[HTFBias],
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> TargetResult:
        """
        Calculate target using next HTF S/R level.

        Args:
            htf_bias: HTF bias with key levels.
            entry_price: Entry price.
            direction: LONG or SHORT.

        Returns:
            TargetResult object.
        """
        if not htf_bias or not htf_bias.key_levels:
            # Fallback to ATR
            return TargetResult(
                target_price=entry_price,
                method=TargetMethod.SR_LEVEL,
                confidence=0.0,
                description="No HTF S/R levels available — fallback method needed",
            )

        # Find next S/R level in trade direction
        target_price = None
        target_level_type = None

        for level in sorted(
            htf_bias.key_levels,
            key=lambda x: x.price,
            reverse=(direction == "SHORT"),
        ):
            if direction == "LONG":
                if level.level_type == LevelType.RESISTANCE and level.price > entry_price:
                    target_price = level.price
                    target_level_type = "resistance"
                    break
            else:  # SHORT
                if level.level_type == LevelType.SUPPORT and level.price < entry_price:
                    target_price = level.price
                    target_level_type = "support"
                    break

        if target_price is None:
            return TargetResult(
                target_price=entry_price,
                method=TargetMethod.SR_LEVEL,
                confidence=0.3,
                description=f"No {'resistance' if direction == 'LONG' else 'support'} level above entry — consider ATR method",
            )

        return TargetResult(
            target_price=target_price,
            method=TargetMethod.SR_LEVEL,
            confidence=0.8 if target_level_type else 0.6,
            description=f"Next HTF {'resistance' if direction == 'LONG' else 'support'} at ${target_price:,.2f} — high-probability target",
        )

    def _calculate_measured_move(
        self,
        df: pd.DataFrame,
        setup: Optional[MTFSetup],
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> TargetResult:
        """
        Calculate target using measured move / pattern target.

        Pattern Targets:
        - Bull flag: flagpole length projected from breakout
        - Inverse H&S: head-to-neckline distance projected above
        - Double bottom: trough-to-neckline distance projected above

        Args:
            df: MTF OHLCV data.
            setup: MTF setup with pattern info.
            entry_price: Entry price.
            direction: LONG or SHORT.

        Returns:
            TargetResult object.
        """
        if not setup or not setup.consolidation_pattern:
            # Estimate from recent price action
            lookback = min(20, len(df))
            recent_range = df["high"].iloc[-lookback:].max() - df["low"].iloc[-lookback:].min()
            if direction == "LONG":
                target_price = entry_price + recent_range
            else:
                target_price = entry_price - recent_range

            return TargetResult(
                target_price=target_price,
                method=TargetMethod.MEASURED_MOVE,
                confidence=0.5,
                description=f"Estimated measured move ({recent_range:.4f})",
            )

        # Calculate based on pattern type
        pattern = setup.consolidation_pattern
        lookback = min(50, len(df))

        if pattern == "FLAG":
            # Flagpole = recent impulse move
            if direction == "LONG":
                impulse_start = df["low"].iloc[-lookback:].min()
                breakout_level = df["high"].iloc[-20:].max()
                flagpole = breakout_level - impulse_start
                target_price = entry_price + flagpole
            else:
                impulse_start = df["high"].iloc[-lookback:].max()
                breakout_level = df["low"].iloc[-20:].min()
                flagpole = impulse_start - breakout_level
                target_price = entry_price - flagpole

            return TargetResult(
                target_price=target_price,
                method=TargetMethod.MEASURED_MOVE,
                confidence=0.6,
                description=f"Flag pattern target (flagpole={flagpole:.4f})",
            )

        elif pattern == "RECTANGLE":
            # Rectangle height
            high = df["high"].iloc[-lookback:].max()
            low = df["low"].iloc[-lookback:].min()
            height = high - low

            if direction == "LONG":
                target_price = high + height
            else:
                target_price = low - height

            return TargetResult(
                target_price=target_price,
                method=TargetMethod.MEASURED_MOVE,
                confidence=0.55,
                description=f"Rectangle pattern target (height={height:.4f})",
            )

        else:
            # Generic consolidation
            recent_range = df["high"].iloc[-lookback:].max() - df["low"].iloc[-lookback:].min()
            if direction == "LONG":
                target_price = entry_price + recent_range
            else:
                target_price = entry_price - recent_range

            return TargetResult(
                target_price=target_price,
                method=TargetMethod.MEASURED_MOVE,
                confidence=0.5,
                description=f"Consolidation target (range={recent_range:.4f})",
            )

    def _calculate_fib_target(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> TargetResult:
        """
        Calculate target using Fibonacci extension.

        Levels:
        - 1.272: Conservative (partial profit)
        - 1.618: Standard target
        - 2.618: Extended target (trail into)

        Args:
            df: MTF OHLCV data.
            entry_price: Entry price.
            direction: LONG or SHORT.

        Returns:
            TargetResult object.
        """
        lookback = min(self.fib_anchor_bars, len(df))

        if direction == "LONG":
            # Find impulse: swing low to swing high
            swing_low = df["low"].iloc[-lookback:].min()
            swing_high = df["high"].iloc[-lookback:].max()

            # Find retracement low
            retracement_idx = df["low"].iloc[-lookback:].idxmin()
            retracement_low = df["low"].iloc[-lookback:].min()

            # Calculate extensions
            impulse = swing_high - swing_low
            fib_1618 = retracement_low + impulse * 1.618
            target_price = fib_1618

        else:  # SHORT
            swing_high = df["high"].iloc[-lookback:].max()
            swing_low = df["low"].iloc[-lookback:].min()
            retracement_high = df["high"].iloc[-lookback:].max()

            impulse = swing_high - swing_low
            fib_1618 = retracement_high - impulse * 1.618
            target_price = fib_1618

        return TargetResult(
            target_price=target_price,
            method=TargetMethod.FIBONACCI,
            confidence=0.65,
            description=f"Fibonacci 1.618 extension ({target_price:.4f})",
        )

    def _calculate_atr_target(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
        multiplier: Optional[float] = None,
    ) -> TargetResult:
        """
        Calculate target using ATR (Average True Range).

        Multipliers:
        - 2x ATR: Minimum target
        - 3x ATR: Standard target
        - 4-5x ATR: Extended (strong trend only)

        Args:
            df: MTF OHLCV data.
            entry_price: Entry price.
            direction: LONG or SHORT.
            multiplier: ATR multiplier (auto-selected if None).

        Returns:
            TargetResult object.
        """
        atr = self._calculate_atr(df)

        if pd.isna(atr) or atr == 0:
            # Fallback
            return TargetResult(
                target_price=entry_price,
                method=TargetMethod.ATR,
                confidence=0.0,
                description="ATR not available",
            )

        # Auto-select multiplier based on trend strength
        if multiplier is None:
            if self._is_strong_trend(df, direction):
                multiplier = 4.0  # Strong trend
            else:
                multiplier = 3.0  # Standard

        target_distance = atr * multiplier

        if direction == "LONG":
            target_price = entry_price + target_distance
        else:
            target_price = entry_price - target_distance

        return TargetResult(
            target_price=target_price,
            method=TargetMethod.ATR,
            confidence=0.6,
            description=f"{multiplier}x ATR target ({atr:.4f} × {multiplier} = {target_distance:.4f})",
        )

    def _calculate_prior_swing_target(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> TargetResult:
        """
        Calculate target using prior swing high/low.

        Most conservative method, appropriate for:
        - Counter-trend trades
        - Range markets
        - Elevated volatility

        Args:
            df: MTF OHLCV data.
            entry_price: Entry price.
            direction: LONG or SHORT.

        Returns:
            TargetResult object.
        """
        lookback = min(50, len(df))

        if direction == "LONG":
            # Target: prior swing high
            prior_high = df["high"].iloc[-lookback:].max()

            # Make sure it's a prior high (not current)
            if df["high"].iloc[-1] >= prior_high * 0.999:
                # Current is at high, look further back
                prior_high = df["high"].iloc[-lookback:-5].max()

            target_price = prior_high

        else:  # SHORT
            # Target: prior swing low
            prior_low = df["low"].iloc[-lookback:].min()

            if df["low"].iloc[-1] <= prior_low * 1.001:
                prior_low = df["low"].iloc[-lookback:-5].min()

            target_price = prior_low

        return TargetResult(
            target_price=target_price,
            method=TargetMethod.PRIOR_SWING,
            confidence=0.55,
            description=f"Prior swing {'high' if direction == 'LONG' else 'low'} at {target_price:.4f}",
        )

    def _calculate_atr(
        self,
        df: pd.DataFrame,
        period: int,
    ) -> float:
        """
        Calculate Average True Range (ATR).

        Args:
            df: DataFrame with OHLCV data.
            period: ATR period.

        Returns:
            ATR value.
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = EMA of TR
        atr = tr.ewm(span=period, adjust=False).mean()

        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0

    def _is_strong_impulse(
        self,
        df: pd.DataFrame,
        direction: Literal["LONG", "SHORT"],
    ) -> bool:
        """
        Check if market is in strong impulse move.

        Args:
            df: MTF OHLCV data.
            direction: LONG or SHORT.

        Returns:
            True if strong impulse detected.
        """
        lookback = min(20, len(df))
        recent_closes = df["close"].iloc[-lookback:]

        if direction == "LONG":
            # Check for strong upward momentum
            gains = (recent_closes - recent_closes.shift(1)).dropna()
            strong_gains = (gains > 0).sum()
            return strong_gains >= lookback * 0.7  # 70% up days
        else:
            losses = (recent_closes.shift(1) - recent_closes).dropna()
            strong_losses = (losses > 0).sum()
            return strong_losses >= lookback * 0.7  # 70% down days

    def _is_strong_trend(
        self,
        df: pd.DataFrame,
        direction: Literal["LONG", "SHORT"],
    ) -> bool:
        """
        Check if market is in strong trend.

        Args:
            df: MTF OHLCV data.
            direction: LONG or SHORT.

        Returns:
            True if strong trend detected.
        """
        lookback = min(50, len(df))

        if direction == "LONG":
            # Check if price is making consistent higher highs
            highs = df["high"].iloc[-lookback:]
            lows = df["low"].iloc[-lookback:]

            # Uptrend: higher highs and higher lows
            hh = highs.iloc[-1] > highs.iloc[-lookback // 2].max()
            hl = lows.iloc[-1] > lows.iloc[-lookback // 2].min()

            return hh and hl
        else:
            highs = df["high"].iloc[-lookback:]
            lows = df["low"].iloc[-lookback:]

            lh = highs.iloc[-1] < highs.iloc[-lookback // 2].max()
            ll = lows.iloc[-1] < lows.iloc[-lookback // 2].min()

            return lh and ll


def calculate_target(
    df_htf: pd.DataFrame,
    df_mtf: pd.DataFrame,
    entry_price: float,
    stop_loss: float,
    direction: Literal["LONG", "SHORT"],
    method: Optional[TargetMethod] = None,
) -> TargetResult:
    """
    Convenience function to calculate profit target.

    Args:
        df_htf: HTF OHLCV data.
        df_mtf: MTF OHLCV data.
        entry_price: Entry price.
        stop_loss: Stop loss price.
        direction: LONG or SHORT.
        method: Target method (auto-selected if None).

    Returns:
        TargetResult object.
    """
    calc = TargetCalculator()
    return calc.calculate_target(
        df_htf=df_htf,
        df_mtf=df_mtf,
        entry_price=entry_price,
        stop_loss=stop_loss,
        direction=direction,
        method=method,
    )


def calculate_all_targets(
    df_htf: pd.DataFrame,
    df_mtf: pd.DataFrame,
    entry_price: float,
    stop_loss: float,
    direction: Literal["LONG", "SHORT"],
    htf_bias=None,
    setup=None,
) -> dict:
    """
    Calculate targets using ALL methods and return as dictionary.

    Args:
        df_htf: HTF OHLCV data.
        df_mtf: MTF OHLCV data.
        entry_price: Entry price.
        stop_loss: Stop loss price.
        direction: LONG or SHORT.
        htf_bias: HTF bias (for S/R method).
        setup: MTF setup (for measured move).

    Returns:
        Dictionary with all target methods and their values.
        Example: {
            "S/R": {"target": 5200, "rr": 2.1, "confidence": 0.7},
            "MEASURED_MOVE": {"target": 5300, "rr": 2.5, "confidence": 0.5},
            ...
        }
    """
    calc = TargetCalculator()
    results = {}
    
    for method in TargetMethod:
        try:
            target_result = calc.calculate_target(
                df_htf=df_htf,
                df_mtf=df_mtf,
                entry_price=entry_price,
                stop_loss=stop_loss,
                direction=direction,
                method=method,
                htf_bias=htf_bias,
                setup=setup,
            )
            
            results[method.value] = {
                "target_price": round(target_result.target_price, 5),
                "rr_ratio": round(target_result.rr_ratio, 2),
                "confidence": round(target_result.confidence, 2),
                "description": target_result.description,
            }
        except Exception as e:
            results[method.value] = {
                "error": str(e),
            }
    
    return results

