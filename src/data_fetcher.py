"""
Data Fetcher for TA-DSS.

This module provides a unified interface for fetching OHLCV market data
from multiple sources (yfinance for stocks, ccxt for crypto) with robust
error handling, retry logic, and data validation.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import ccxt
import pandas as pd
import yfinance as yf

from src.config import validate_timeframe
from src.utils.helpers import normalize_ticker

# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================


class DataFetchError(Exception):
    """
    Custom exception raised when data fetching fails after all retries.

    Attributes:
        symbol: The symbol that failed to fetch.
        timeframe: The requested timeframe.
        attempts: Number of retry attempts made.
        last_error: The last error message received.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        attempts: int,
        last_error: Optional[str] = None,
    ):
        """
        Initialize DataFetchError.

        Args:
            symbol: The symbol that failed to fetch.
            timeframe: The requested timeframe.
            attempts: Number of retry attempts made.
            last_error: The last error message received.
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.attempts = attempts
        self.last_error = last_error

        message = (
            f"Failed to fetch data for {symbol} (timeframe: {timeframe}) "
            f"after {attempts} attempts"
        )
        if last_error:
            message += f": {last_error}"

        super().__init__(message)


# =============================================================================
# DATA FETCHER CLASS
# =============================================================================


class DataFetcher:
    """
    Unified data fetcher for stocks and crypto assets.

    This class provides a consistent interface for fetching OHLCV data
    from multiple sources with automatic retry logic, data validation,
    and comprehensive logging.

    Attributes:
        source: Data source ('yfinance' for stocks, 'ccxt' for crypto).
        retry_attempts: Number of retry attempts on failure.
        retry_delay: Base delay between retries in seconds.
        log_dir: Directory for log files.

    Example:
        >>> fetcher = DataFetcher(source='yfinance')
        >>> df = fetcher.get_ohlcv('AAPL', '1d', limit=100)
        >>> print(df.head())
    """

    def __init__(
        self,
        source: Literal["yfinance", "ccxt"] = "yfinance",
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        log_dir: str = "logs",
    ):
        """
        Initialize the DataFetcher.

        Args:
            source: Data source ('yfinance' for stocks, 'ccxt' for crypto).
                Defaults to 'yfinance'.
            retry_attempts: Number of retry attempts on API failure.
                Defaults to 3.
            retry_delay: Base delay between retries in seconds.
                Exponential backoff is applied (delay * 2^attempt).
                Defaults to 1.0.
            log_dir: Directory for log files. Defaults to 'logs'.

        Raises:
            ValueError: If source is not 'yfinance' or 'ccxt'.
        """
        if source not in ("yfinance", "ccxt"):
            raise ValueError(f"Invalid source: {source}. Use 'yfinance' or 'ccxt'.")

        self.source = source
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.log_dir = Path(log_dir)

        # Setup logging
        self._setup_logging()

        # Initialize CCXT exchange if needed
        self._exchange: Optional[ccxt.Exchange] = None
        if source == "ccxt":
            self._exchange = ccxt.binance()
            self._exchange.load_markets()

        self.logger.info(f"DataFetcher initialized (source={source})")

    def _setup_logging(self) -> None:
        """
        Setup logging configuration for data fetch operations.

        Creates the log directory if it doesn't exist and configures
        a file handler for data fetch logs.
        """
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("data_fetcher")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []

        # File handler
        log_file = self.log_dir / "data_fetch.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV (candlestick) data for a symbol.

        This method fetches historical market data with automatic retry logic,
        data validation, and error handling. The returned DataFrame is sorted
        chronologically with Datetime as the index.

        Args:
            symbol: Trading symbol (e.g., 'AAPL' for stocks, 'BTCUSD' for crypto).
            timeframe: Data timeframe. For yfinance: '1m', '5m', '1h', '1d', '1wk', '1mo'.
                For CCXT: '1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M'.
            limit: Number of candles to fetch. Defaults to 100.

        Returns:
            Pandas DataFrame with columns:
                - Datetime (index): Timestamp of each candle
                - Open: Opening price
                - High: Highest price
                - Low: Lowest price
                - Close: Closing price
                - Volume: Trading volume

        Raises:
            DataFetchError: If data cannot be retrieved after all retry attempts.
            ValueError: If timeframe is invalid for the selected source.

        Example:
            >>> fetcher = DataFetcher(source='yfinance')
            >>> df = fetcher.get_ohlcv('AAPL', '1d', limit=100)
            >>> print(df.columns)
            Index(['Open', 'High', 'Low', 'Close', 'Volume'], dtype='object')
        """
        # Validate timeframe for source
        try:
            validated_tf = validate_timeframe(timeframe, self.source, auto_fallback=True)
            self.logger.info(
                f"Fetching {limit} candles for {symbol} "
                f"(timeframe: {timeframe} -> {validated_tf})"
            )
        except ValueError as e:
            self.logger.warning(f"Timeframe validation warning: {e}")
            validated_tf = timeframe

        last_error: Optional[str] = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                self.logger.info(f"Fetch attempt {attempt}/{self.retry_attempts} for {symbol}")

                if self.source == "yfinance":
                    df = self._fetch_yfinance(symbol, validated_tf, limit)
                else:  # ccxt
                    df = self._fetch_ccxt(symbol, validated_tf, limit)

                # Validate and clean data
                df = self._validate_and_clean(df, symbol)

                self.logger.info(
                    f"Successfully fetched {len(df)} candles for {symbol}"
                )
                return df

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Attempt {attempt} failed: {last_error}")

                if attempt < self.retry_attempts:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)

        # All retries failed
        self.logger.error(
            f"All {self.retry_attempts} attempts failed for {symbol}"
        )
        raise DataFetchError(
            symbol=symbol,
            timeframe=timeframe,
            attempts=self.retry_attempts,
            last_error=last_error,
        )

    def _fetch_yfinance(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from yfinance.

        Args:
            symbol: Stock/crypto symbol.
            timeframe: yfinance-compatible timeframe.
            limit: Number of candles to fetch.

        Returns:
            Raw DataFrame from yfinance.

        Raises:
            RuntimeError: If yfinance returns no data.
        """
        # Normalize symbol for yfinance
        yf_symbol = self._normalize_yfinance_symbol(symbol)

        # Map timeframe to yfinance interval
        interval = self._map_timeframe_to_yfinance(timeframe)

        # Calculate period based on timeframe and limit
        period = self._calculate_yfinance_period(interval, limit)

        self.logger.debug(
            f"yfinance: symbol={yf_symbol}, interval={interval}, period={period}"
        )

        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            raise RuntimeError(f"yfinance returned no data for {yf_symbol}")

        return df

    def _fetch_ccxt(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from CCXT exchange.

        Args:
            symbol: Crypto pair symbol.
            timeframe: CCXT-compatible timeframe.
            limit: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV data.

        Raises:
            RuntimeError: If CCXT returns no data.
        """
        if self._exchange is None:
            raise RuntimeError("CCXT exchange not initialized")

        # Normalize symbol for CCXT
        ccxt_symbol = normalize_ticker(symbol, source="ccxt")

        self.logger.debug(
            f"CCXT: symbol={ccxt_symbol}, timeframe={timeframe}, limit={limit}"
        )

        # Fetch OHLCV data
        ohlcv = self._exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)

        if not ohlcv:
            raise RuntimeError(f"CCXT returned no data for {ccxt_symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "Open", "High", "Low", "Close", "Volume"],
        )

        # Convert timestamp to datetime
        df["Datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop(columns=["timestamp"])

        return df

    def _normalize_yfinance_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for yfinance.

        Args:
            symbol: Raw symbol string.

        Returns:
            Normalized symbol for yfinance.
        """
        symbol = symbol.strip().upper()

        # Stock symbols (1-5 alpha chars) - use as-is
        if symbol.isalpha() and len(symbol) <= 5:
            return symbol

        # Crypto/forex - use dash-separated format
        return normalize_ticker(symbol, source="yfinance")

    def _map_timeframe_to_yfinance(self, timeframe: str) -> str:
        """
        Map internal timeframe to yfinance interval.

        Args:
            timeframe: Internal format timeframe.

        Returns:
            yfinance interval string.
        """
        # Normalize to yfinance format
        yf_tf = validate_timeframe(timeframe, "yfinance", auto_fallback=True)

        # Handle common formats
        if yf_tf in ["60m", "1h"]:
            return "1h"
        elif yf_tf == "1d":
            return "1d"
        elif yf_tf == "1wk":
            return "1wk"
        elif yf_tf == "1mo":
            return "1mo"
        elif yf_tf.endswith("m"):
            return yf_tf
        else:
            self.logger.warning(f"Unknown yfinance timeframe '{yf_tf}', defaulting to '1d'")
            return "1d"

    def _calculate_yfinance_period(
        self,
        interval: str,
        limit: int,
    ) -> str:
        """
        Calculate yfinance period string based on interval and limit.

        Args:
            interval: yfinance interval (e.g., '1h', '1d').
            limit: Number of candles needed.

        Returns:
            yfinance period string (e.g., '1d', '5d', '1mo', '1y').
        """
        if interval in ["1m", "2m", "5m", "15m", "30m"]:
            # Intraday - max 7 days for 1m, 60 days for others
            days = min(limit * int(interval.replace("m", "")) // 60 // 24 + 1, 60)
            return f"{max(days, 1)}d"
        elif interval == "1h":
            # Hourly - max ~2 years
            days = min(limit // 24 + 1, 730)
            return f"{days}d"
        elif interval == "1d":
            # Daily - max ~5 years
            years = min(limit // 252 + 1, 5)
            return f"{years}y"
        elif interval in ["1wk", "1mo"]:
            return "max"
        else:
            return "1y"

    def _validate_and_clean(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        """
        Validate and clean the fetched DataFrame.

        This method:
        1. Checks if DataFrame is empty
        2. Ensures Datetime is the index
        3. Sorts chronologically
        4. Checks for null values in critical columns
        5. Drops rows with null values

        Args:
            df: Raw DataFrame from data source.
            symbol: Symbol being fetched (for logging).

        Returns:
            Cleaned DataFrame with Datetime index.

        Raises:
            DataFetchError: If DataFrame is empty or has no valid data.
        """
        # Check for empty DataFrame
        if df.empty:
            raise DataFetchError(
                symbol=symbol,
                timeframe="unknown",
                attempts=1,
                last_error="Returned DataFrame is empty",
            )

        # Ensure Datetime column exists and is the index
        if "Datetime" in df.columns:
            df = df.set_index("Datetime")
        elif not isinstance(df.index, pd.DatetimeIndex):
            # Try to convert index to datetime
            df.index = pd.to_datetime(df.index)

        # Sort chronologically
        df = df.sort_index()

        # Standardize column names (capitalize first letter)
        column_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "datetime": "Datetime",
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Check for critical columns
        critical_columns = ["Close", "High", "Low"]
        missing_cols = [col for col in critical_columns if col not in df.columns]
        if missing_cols:
            raise DataFetchError(
                symbol=symbol,
                timeframe="unknown",
                attempts=1,
                last_error=f"Missing critical columns: {missing_cols}",
            )

        # Check for null values in critical columns
        null_counts = df[critical_columns].isnull().sum()
        total_nulls = null_counts.sum()

        if total_nulls > 0:
            self.logger.warning(
                f"Found {total_nulls} null values in critical columns for {symbol}. "
                f"Dropping rows with nulls."
            )
            df = df.dropna(subset=critical_columns)

        # Check if we still have data after dropping nulls
        if df.empty:
            raise DataFetchError(
                symbol=symbol,
                timeframe="unknown",
                attempts=1,
                last_error="No valid data remaining after dropping null values",
            )

        self.logger.info(
            f"Validated {len(df)} rows for {symbol} "
            f"(dropped {total_nulls} rows with nulls)"
        )

        return df

    def get_current_price(self, symbol: str) -> float:
        """
        Get the current/latest price for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Current price as float.

        Raises:
            DataFetchError: If price cannot be retrieved.
        """
        try:
            # Fetch recent data
            df = self.get_ohlcv(symbol, timeframe="1d", limit=1)
            return float(df["Close"].iloc[-1])
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            raise DataFetchError(
                symbol=symbol,
                timeframe="1d",
                attempts=1,
                last_error=f"Price fetch failed: {e}",
            )

    def close(self) -> None:
        """
        Close any open connections (CCXT exchange).

        Should be called when the DataFetcher is no longer needed
        to properly release resources.
        """
        if hasattr(self, "_exchange") and self._exchange:
            try:
                self._exchange.close()
                self.logger.info("CCXT exchange connection closed")
            except Exception as e:
                if hasattr(self, "logger") and self.logger:
                    self.logger.error(f"Error closing exchange: {e}")
            self._exchange = None

    def __del__(self) -> None:
        """Destructor to ensure connections are closed."""
        self.close()
