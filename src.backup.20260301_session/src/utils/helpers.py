"""
Utility functions for the TA-DSS project.

This module provides helper functions for common operations such as
ticker normalization, string formatting, and data validation.
"""

import re
from typing import Literal


def normalize_ticker(
    symbol: str,
    source: Literal["yfinance", "ccxt"] = "yfinance"
) -> str:
    """
    Normalize a trading pair symbol to the format required by the data source.

    Handles common variations in ticker formatting across different platforms
    and converts them to the standardized format expected by yfinance or CCXT.

    Args:
        symbol: The trading pair symbol (e.g., 'BTCUSD', 'ETHUSDT', 'BTC-USD').
        source: The target data source format ('yfinance' or 'ccxt').

    Returns:
        Normalized symbol in the format required by the source:
        - yfinance: 'BTC-USD', 'ETH-USD', etc.
        - ccxt: 'BTC/USDT', 'ETH/USDT', etc.

    Raises:
        ValueError: If the symbol cannot be parsed into base/quote components.

    Examples:
        >>> normalize_ticker('BTCUSD', 'yfinance')
        'BTC-USD'
        >>> normalize_ticker('BTCUSD', 'ccxt')
        'BTC/USDT'
        >>> normalize_ticker('ETH-USD', 'yfinance')
        'ETH-USD'
        >>> normalize_ticker('ETH/USDT', 'ccxt')
        'ETH/USDT'
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")

    # Clean and uppercase the symbol
    symbol = symbol.strip().upper()

    # Extract base and quote currency using regex
    base, quote = _parse_symbol(symbol)

    if source == "yfinance":
        return f"{base}-{quote}"
    elif source == "ccxt":
        # CCXT uses USDT as default stablecoin for crypto pairs
        quote_normalized = _normalize_quote_currency(quote)
        return f"{base}/{quote_normalized}"
    else:
        raise ValueError(f"Unknown source: {source}. Use 'yfinance' or 'ccxt'.")


def _parse_symbol(symbol: str) -> tuple[str, str]:
    """
    Parse a symbol string into base and quote currency components.

    Handles various formats:
    - Concatenated: 'BTCUSD', 'ETHUSDT'
    - Dash-separated: 'BTC-USD', 'ETH-USD'
    - Slash-separated: 'BTC/USD', 'ETH/USDT'
    - Underscore-separated: 'BTC_USD'

    Args:
        symbol: The raw symbol string.

    Returns:
        A tuple of (base_currency, quote_currency).

    Raises:
        ValueError: If the symbol cannot be parsed.
    """
    # Remove any whitespace
    symbol = symbol.strip()

    # Try slash separator first (CCXT format)
    if "/" in symbol:
        parts = symbol.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    # Try dash separator (yfinance format)
    if "-" in symbol:
        parts = symbol.split("-")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    # Try underscore separator
    if "_" in symbol:
        parts = symbol.split("_")
        if len(parts) == 2 and parts[0] and parts[1]:
            return parts[0], parts[1]

    # Try to split concatenated format (e.g., BTCUSD, ETHUSDT)
    # Look for common quote currencies
    quote_currencies = [
        "USDT", "USDC", "BUSD",  # Stablecoins
        "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF",  # Fiat
        "BTC", "ETH", "BNB",  # Crypto bases as quotes
    ]

    for quote in quote_currencies:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            if base:  # Ensure base is not empty
                return base, quote

    # Try to detect quote currency by common patterns (3-4 chars at end)
    # This handles cases like 'DOGEUSD' where USD is 3 chars
    if len(symbol) >= 6:
        # Assume last 3-4 characters are the quote
        for quote_len in [4, 3]:
            if len(symbol) > quote_len:
                base = symbol[:-quote_len]
                quote = symbol[-quote_len:]
                # Validate that base looks like a valid currency code
                if base.isalpha() and quote.isalpha():
                    return base, quote

    # Handle stock symbols without explicit quote (e.g., 'AAPL', 'TSLA')
    # Default to USD for yfinance compatibility
    if symbol.isalpha() and len(symbol) <= 5:
        return symbol, "USD"

    raise ValueError(
        f"Cannot parse symbol '{symbol}'. Expected format like 'BTCUSD', "
        "'BTC-USD', 'BTC/USDT', or 'ETHUSDT'."
    )


def _normalize_quote_currency(quote: str) -> str:
    """
    Normalize quote currency for CCXT format.

    CCXT typically uses USDT for stablecoin pairs. This function maps
    various USD-pegged stablecoins to their CCXT equivalents.

    Args:
        quote: The quote currency string.

    Returns:
        Normalized quote currency for CCXT.
    """
    # Map common variations to CCXT standard
    quote_mapping = {
        "USD": "USDT",  # Default to USDT for crypto
        "USDT": "USDT",
        "USDC": "USDC",
        "BUSD": "BUSD",
        "EUR": "EUR",
        "GBP": "GBP",
        "JPY": "JPY",
        "AUD": "AUD",
        "CAD": "CAD",
        "CHF": "CHF",
        "BTC": "BTC",
        "ETH": "ETH",
    }

    return quote_mapping.get(quote, quote)


def denormalize_ticker(symbol: str, source: Literal["yfinance", "ccxt"]) -> str:
    """
    Convert a normalized ticker back to a human-readable concatenated format.

    This is the inverse operation of normalize_ticker().

    Args:
        symbol: The normalized symbol (e.g., 'BTC-USD' or 'BTC/USDT').
        source: The source format type ('yfinance' or 'ccxt').

    Returns:
        Concatenated format (e.g., 'BTCUSD').

    Examples:
        >>> denormalize_ticker('BTC-USD', 'yfinance')
        'BTCUSD'
        >>> denormalize_ticker('BTC/USDT', 'ccxt')
        'BTCUSDT'
    """
    base, quote = _parse_symbol(symbol)

    # For CCXT, convert USDT back to USD for display if needed
    if source == "ccxt":
        quote = quote.replace("USDT", "USD")

    return f"{base}{quote}"


def format_currency(value: float, decimals: int = 2) -> str:
    """
    Format a numeric value as currency with specified decimal places.

    Args:
        value: The numeric value to format.
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string with thousands separators.

    Examples:
        >>> format_currency(1234567.89)
        '1,234,567.89'
        >>> format_currency(0.00123, decimals=5)
        '0.00123'
    """
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def format_pnl(pnl: float, entry_price: float) -> str:
    """
    Format profit/loss with percentage change.

    Args:
        pnl: The profit/loss value.
        entry_price: The original entry price for percentage calculation.

    Returns:
        Formatted string showing PnL and percentage (e.g., '+$123.45 (+2.5%)').
    """
    if entry_price == 0:
        pct_change = 0.0
    else:
        pct_change = (pnl / entry_price) * 100

    sign = "+" if pnl >= 0 else ""
    return f"{sign}${format_currency(pnl)} ({sign}{pct_change:.2f}%)"


def is_valid_timeframe(timeframe: str) -> bool:
    """
    Validate if a timeframe string is supported.

    Args:
        timeframe: The timeframe string to validate.

    Returns:
        True if valid, False otherwise.

    Examples:
        >>> is_valid_timeframe('h4')
        True
        >>> is_valid_timeframe('d1')
        True
        >>> is_valid_timeframe('1m')
        False
    """
    valid_timeframes = {"m5", "m15", "m30", "h1", "h2", "h4", "h6", "h12", "d1", "w1", "M1"}
    return timeframe.lower() in valid_timeframes


def timeframe_to_minutes(timeframe: str) -> int:
    """
    Convert a timeframe string to total minutes.

    Args:
        timeframe: The timeframe string (e.g., 'h4', 'd1', 'w1').

    Returns:
        Total minutes represented by the timeframe.

    Raises:
        ValueError: If the timeframe format is invalid.

    Examples:
        >>> timeframe_to_minutes('h4')
        240
        >>> timeframe_to_minutes('d1')
        1440
    """
    timeframe = timeframe.lower()

    if not timeframe or len(timeframe) < 2:
        raise ValueError(f"Invalid timeframe format: {timeframe}")

    unit = timeframe[-1]
    try:
        value = int(timeframe[:-1])
    except ValueError:
        raise ValueError(f"Invalid timeframe format: {timeframe}")

    multipliers = {
        "m": 1,       # minutes
        "h": 60,      # hours
        "d": 1440,    # days
        "w": 10080,   # weeks
        "M": 43200,   # months (approximate)
    }

    if unit not in multipliers:
        raise ValueError(f"Unknown timeframe unit: {unit}")

    return value * multipliers[unit]
