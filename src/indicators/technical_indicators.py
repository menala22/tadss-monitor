"""
Technical Indicators for MTF Analysis.

This module provides core indicator calculations:
- ADX: Average Directional Index (trend strength)
- ATR: Average True Range (volatility)
- EMA: Exponential Moving Average
- RSI: Relative Strength Index

These indicators are used for context classification and setup detection.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate ATR (Average True Range).
    
    ATR measures volatility by calculating the moving average of true range.
    True Range is the maximum of:
    - Current high - current low
    - |Current high - previous close|
    - |Current low - previous close|
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        period: ATR calculation period (default 14).
    
    Returns:
        ATR series.
    
    Example:
        >>> atr = compute_atr(ohlcv_df, period=14)
        >>> current_atr = atr.iloc[-1]
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # Calculate true range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR as EMA of true range
    atr = true_range.ewm(span=period, adjust=False).mean()
    
    return atr


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate ADX (Average Directional Index).
    
    ADX measures trend strength regardless of direction:
    - ADX > 25: Trending market
    - ADX < 20: Ranging market
    - ADX 20-25: Transition zone
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        period: ADX calculation period (default 14).
    
    Returns:
        ADX series.
    
    Example:
        >>> adx = compute_adx(ohlcv_df, period=14)
        >>> if adx.iloc[-1] > 25:
        ...     print("Trending market")
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    # Set to 0 if no directional movement
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # Calculate True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smooth +DM, -DM, and TR using Wilder's smoothing (EMA with alpha=1/period)
    atr = true_range.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    # Calculate DX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    
    # ADX is smoothed DX
    adx = dx.ewm(span=period, adjust=False).mean()
    
    return adx


def compute_ema(
    df: pd.DataFrame,
    column: str = "close",
    span: int = 21,
) -> pd.Series:
    """
    Calculate EMA (Exponential Moving Average).
    
    EMA gives more weight to recent prices, making it more responsive
    than simple moving average.
    
    Args:
        df: DataFrame with OHLCV data.
        column: Column to calculate EMA on (default 'close').
        span: EMA period (default 21).
    
    Returns:
        EMA series.
    
    Example:
        >>> ema21 = compute_ema(ohlcv_df, span=21)
        >>> ema50 = compute_ema(ohlcv_df, span=50)
    """
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame")
        return pd.Series(dtype=float)
    
    return df[column].ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index).
    
    RSI measures momentum on a scale of 0-100:
    - RSI > 70: Overbought
    - RSI < 30: Oversold
    - RSI 40-50: Bullish pullback zone
    - RSI 50-60: Bearish pullback zone
    
    Args:
        series: Price series (typically close prices).
        period: RSI calculation period (default 14).
    
    Returns:
        RSI series.
    
    Example:
        >>> rsi = compute_rsi(df['close'], period=14)
        >>> if rsi.iloc[-1] < 30:
        ...     print("Oversold")
    """
    delta = series.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    # Calculate average gain and loss using EMA
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    
    # Fill NaN (all gains = RSI 100, all losses = RSI 0)
    rsi = rsi.fillna(100).where(avg_loss != 0, 100)
    
    return rsi


def normalize_by_atr(
    price: float,
    reference: float,
    atr: float,
) -> float:
    """
    Normalize price distance by ATR.
    
    Converts absolute price distance to ATR units for consistent
    comparison across different assets and timeframes.
    
    Args:
        price: Current price.
        reference: Reference price (e.g., EMA, support level).
        atr: Current ATR value.
    
    Returns:
        Distance in ATR units (can be negative).
    
    Example:
        >>> dist_atr = normalize_by_atr(price, ema21, atr)
        >>> if dist_atr < 1.5:
        ...     print("Price near EMA")
    """
    if atr == 0 or pd.isna(atr):
        return 0.0
    
    return (price - reference) / atr


def get_prior_impulse_volume(
    df: pd.DataFrame,
    lookback: int = 10,
    impulse_threshold: float = 1.5,
) -> float:
    """
    Calculate prior impulse volume from recent directional move.
    
    Impulse volume is the average volume during strong directional candles
    (candles with close-open move > threshold).
    
    This is used to compare against pullback volume for quality scoring.
    
    Args:
        df: DataFrame with OHLCV data.
        lookback: Number of candles to look back for impulse detection.
        impulse_threshold: Minimum candle range / recent avg range ratio to qualify as impulse.
    
    Returns:
        Average volume during impulse candles, or recent average volume if no impulse found.
    
    Example:
        >>> impulse_vol = get_prior_impulse_volume(df, lookback=10)
        >>> pullback_vol = df['volume'].iloc[-5:].mean()
        >>> if pullback_vol < impulse_vol * 0.6:
        ...     print("Healthy pullback - volume declining")
    """
    if len(df) < lookback:
        return df["volume"].iloc[-5:].mean() if len(df) >= 5 else df["volume"].mean()
    
    recent = df.iloc[-lookback:]
    
    # Calculate candle ranges
    ranges = (recent["high"] - recent["low"]).abs()
    avg_range = ranges.rolling(5).mean().iloc[-1]
    
    # Identify impulse candles (large range in direction of move)
    body = (recent["close"] - recent["open"]).abs()
    is_impulse = body > (avg_range * impulse_threshold)
    
    # Get volume during impulse candles
    impulse_volumes = recent["volume"][is_impulse]
    
    if len(impulse_volumes) > 0:
        return impulse_volumes.mean()
    
    # Fallback: use average volume if no clear impulse
    return recent["volume"].mean()


def is_atr_extended(
    price: float,
    reference: float,
    atr: float,
    threshold_atr: float = 3.0,
) -> bool:
    """
    Check if price is extended from reference by threshold ATR.
    
    Used to identify overextended trends (TRENDING_EXTENSION context).
    
    Args:
        price: Current price.
        reference: Reference price (e.g., EMA21).
        atr: Current ATR value.
        threshold_atr: ATR threshold for extension (default 3.0).
    
    Returns:
        True if price is extended beyond threshold.
    
    Example:
        >>> if is_atr_extended(price, ema21, atr, threshold_atr=3.0):
        ...     context = MTFContext.TRENDING_EXTENSION
    """
    distance_atr = abs(normalize_by_atr(price, reference, atr))
    return distance_atr > threshold_atr


def compute_adx_atr(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate both ADX and ATR in a single call for efficiency.
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns.
        period: Calculation period for both indicators.
    
    Returns:
        Tuple of (ADX series, ATR series).
    
    Example:
        >>> adx, atr = compute_adx_atr(ohlcv_df, period=14)
    """
    atr = compute_atr(df, period)
    adx = compute_adx(df, period)
    return adx, atr
