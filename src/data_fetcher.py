"""
Data Fetcher for TA-DSS.

This module provides a unified interface for fetching OHLCV market data
from multiple sources with smart routing:
- Crypto (BTCUSD, ETHUSD, SOLUSD) → CCXT/Kraken (free, no API key)
- Metals (XAUUSD, XAGUSD) → Twelve Data (free tier: 800/day)
- Stocks (AAPL, TSLA) → Twelve Data or yfinance (fallback)

Multi-provider strategy for best coverage and cost ($0/month for current usage).
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import ccxt
import pandas as pd
import yfinance as yf

from src.config import validate_timeframe, settings
from src.utils.helpers import normalize_ticker
from src.database import get_db_context
from src.services.ohlcv_cache_manager import OHLCVCacheManager


def _detect_data_source(pair: str) -> Literal["yfinance", "ccxt", "twelvedata", "gateio"]:
    """
    Automatically detect the best data source for a given pair.

    Multi-provider routing strategy:
    - Crypto (BTC, ETH, SOL) → CCXT/Kraken (free, works on VM)
    - Metals (XAU) → Twelve Data (free tier, reliable)
    - Metals (XAG - Silver) → Gate.io (free, swap contract)
    - Stocks (AAPL, TSLA) → Twelve Data (free tier)
    - Forex → Twelve Data (free tier)

    Args:
        pair: Trading pair symbol (e.g., 'BTCUSD', 'XAUUSD', 'AAPL').

    Returns:
        Recommended data source ('yfinance', 'ccxt', 'twelvedata', or 'gateio').
    """
    pair_upper = pair.upper().replace("-", "").replace("_", "")

    # Silver (XAG) → Gate.io (free, Twelve Data requires paid plan)
    if pair_upper.startswith('XAG'):
        return "gateio"
    
    # Gold (XAU) → Twelve Data (free tier works)
    if pair_upper.startswith('XAU'):
        return "twelvedata"

    # Other metals (XPT, XPD) → Twelve Data (if you have paid plan)
    if pair_upper.startswith(('XPT', 'XPD')):
        return "twelvedata"

    # Common crypto symbols → CCXT/Kraken (free, no API key)
    crypto_prefixes = {
        'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC',
        'LTC', 'AVAX', 'LINK', 'UNI', 'ATOM', 'XLM', 'BCH', 'ALGO', 'VET',
        'XBT'  # Bitcoin alternative symbol
    }
    for prefix in crypto_prefixes:
        if pair_upper.startswith(prefix):
            return "ccxt"

    # Stocks (3-5 letters, no numbers) → Twelve Data (reliable)
    if len(pair_upper) <= 5 and pair_upper.isalpha():
        return "twelvedata"

    # Default → Twelve Data (covers forex pairs like EURUSD)
    return "twelvedata"

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
        source: Data source ('yfinance', 'ccxt', or 'twelvedata').
        retry_attempts: Number of retry attempts on failure.
        retry_delay: Base delay between retries in seconds.
        log_dir: Directory for log files.

    Example:
        >>> fetcher = DataFetcher(source='twelvedata')
        >>> df = fetcher.get_ohlcv('XAUUSD', '1d', limit=100)
        >>> print(df.head())
    """

    def __init__(
        self,
        source: Literal["yfinance", "ccxt", "twelvedata", "gateio"] = "twelvedata",
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        log_dir: str = "logs",
    ):
        """
        Initialize the DataFetcher.

        Args:
            source: Data source ('yfinance', 'ccxt', 'twelvedata', or 'gateio').
                Defaults to 'twelvedata' (multi-asset support).
            retry_attempts: Number of retry attempts on API failure.
                Defaults to 3.
            retry_delay: Base delay between retries in seconds.
                Exponential backoff is applied (delay * 2^attempt).
                Defaults to 1.0.
            log_dir: Directory for log files. Defaults to 'logs'.

        Raises:
            ValueError: If source is not valid.
        """
        if source not in ("yfinance", "ccxt", "twelvedata", "gateio"):
            raise ValueError(f"Invalid source: {source}. Use 'yfinance', 'ccxt', 'twelvedata', or 'gateio'.")

        self.source = source
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.log_dir = Path(log_dir)

        # Setup logging
        self._setup_logging()

        # Initialize CCXT exchange if needed
        self._exchange: Optional[ccxt.Exchange] = None
        if source == "ccxt":
            exchange_id = settings.ccxt_exchange.lower()
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self._exchange = exchange_class({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                self._exchange.load_markets()
                self.logger.info(f"CCXT exchange initialized: {exchange_id}")
            except AttributeError:
                self.logger.error(f"Unknown CCXT exchange: {exchange_id}, falling back to kraken")
                self._exchange = ccxt.kraken()
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
        auto_detect_source: bool = True,
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
            auto_detect_source: If True, automatically detect best data source for symbol.
                Overrides self.source for this call. Defaults to True.

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
        # Auto-detect source based on symbol (for smart routing)
        if auto_detect_source:
            detected_source = _detect_data_source(symbol)
            if detected_source != self.source:
                self.logger.info(
                    f"Smart routing: {symbol} using {detected_source} "
                    f"(configured source: {self.source})"
                )
        else:
            detected_source = self.source

        # Validate timeframe for source
        try:
            validated_tf = validate_timeframe(timeframe, detected_source, auto_fallback=True)
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

                if detected_source == "yfinance":
                    df = self._fetch_yfinance(symbol, validated_tf, limit)
                elif detected_source == "twelvedata":
                    df = self._fetch_twelvedata(symbol, validated_tf, limit)
                elif detected_source == "gateio":
                    df = self._fetch_gateio(symbol, validated_tf, limit)
                else:  # ccxt
                    df = self._fetch_ccxt(symbol, validated_tf, limit)

                # Validate and clean data
                df = self._validate_and_clean(df, symbol)

                # Save to cache for CCXT and Gate.io
                # (Twelve Data saves internally; yfinance not cached by design)
                if detected_source in ("ccxt", "gateio"):
                    try:
                        from src.services.ohlcv_cache_manager import OHLCVCacheManager
                        from src.database import get_db_context
                        with get_db_context() as db:
                            cache_mgr = OHLCVCacheManager(db)
                            cache_mgr.save_ohlcv(symbol, timeframe, df)
                    except Exception as cache_err:
                        self.logger.warning(
                            f"Cache save failed for {symbol} {timeframe}: {cache_err}"
                        )

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

    def _fetch_twelvedata(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Twelve Data API with caching.
        
        Uses incremental fetch:
        1. Check cache for existing data
        2. Calculate missing candles
        3. Fetch only missing candles from API
        4. Merge cached + new data
        5. Save new candles to cache

        Supports: stocks, forex, metals (XAU/XAG), and crypto.

        Args:
            symbol: Trading symbol (e.g., 'XAU/USD', 'AAPL', 'EUR/USD').
            timeframe: Twelve Data interval (e.g., '1h', '4h', '1day').
            limit: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV data.

        Raises:
            RuntimeError: If Twelve Data API is not configured or returns no data.
        """
        # Check if API key is configured
        api_key = settings.twelve_data_api_key
        if not api_key:
            raise RuntimeError(
                "Twelve Data API key not configured. "
                "Add TWELVE_DATA_API_KEY to your .env file or sign up at https://twelvedata.com/"
            )

        # Use database context for caching
        with get_db_context() as db:
            cache_mgr = OHLCVCacheManager(db)
            
            # Try to get cached data
            cached_df = cache_mgr.get_cached_ohlcv(symbol, timeframe, limit)
            
            if cached_df is not None and len(cached_df) >= limit:
                # Have enough cached data, return from cache
                self.logger.info(f"Cache hit: {len(cached_df)} candles for {symbol} {timeframe}")
                return cached_df
            
            # Need to fetch from API
            # Get last cached timestamp
            last_cached = cache_mgr.get_last_cached_timestamp(symbol, timeframe)
            
            # Calculate how many candles to fetch
            if last_cached:
                missing = cache_mgr.calculate_missing_candles(symbol, timeframe, last_cached)
                self.logger.info(
                    f"Fetching {missing} new candles for {symbol} {timeframe} "
                    f"(have {len(cached_df) if cached_df is not None else 0} cached)"
                )
            else:
                missing = limit
                self.logger.info(f"Fetching {missing} candles for {symbol} {timeframe} (no cache)")
            
            # Normalize symbol for Twelve Data
            td_symbol = self._normalize_twelvedata_symbol(symbol)

            # Map timeframe to Twelve Data interval
            interval = self._map_timeframe_to_twelvedata(timeframe)

            self.logger.debug(
                f"TwelveData: symbol={td_symbol}, interval={interval}, limit={missing}"
            )

            # Build API URL
            base_url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": td_symbol,
                "interval": interval,
                "outputsize": missing,
                "apikey": api_key,
                "format": "JSON"
            }

            # Make API request
            import requests
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "status" in data and data.get("status") == "error":
                raise RuntimeError(f"Twelve Data API error: {data.get('message', 'Unknown error')}")

            # Parse data into DataFrame
            if "values" not in data or not data["values"]:
                raise RuntimeError(f"Twelve Data returned no data for {td_symbol}")

            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            df.sort_index(inplace=True)

            # Rename columns to standard OHLCV format
            df.rename(columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
            }, inplace=True)

            # Handle Volume (may not be present for forex/metals)
            if "volume" in data["values"][0]:
                df.rename(columns={"volume": "Volume"}, inplace=True)
                df["Volume"] = pd.to_numeric(df["Volume"], errors='coerce')
            else:
                df["Volume"] = 0  # Set default volume for forex/metals

            # Convert to numeric types
            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Save new candles to cache
            saved = cache_mgr.save_ohlcv(symbol, timeframe, df)
            
            # Merge with cached data if we had some
            if cached_df is not None and len(cached_df) > 0:
                # Combine cached + new, remove duplicates, keep latest
                combined = pd.concat([cached_df, df])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
                df = combined.tail(limit)
            
            self.logger.info(
                f"Saved {saved} new candles to cache for {symbol} {timeframe}, "
                f"returning {len(df)} total candles"
            )
            
            return df

    def _normalize_twelvedata_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for Twelve Data API.

        Twelve Data format:
        - Metals: XAU/USD, XAG/USD
        - Forex: EUR/USD, GBP/USD
        - Stocks: AAPL, TSLA
        - Crypto: BTC/USD, ETH/USD

        Args:
            symbol: Input symbol (e.g., 'XAUUSD', 'EURUSD', 'AAPL').

        Returns:
            Normalized symbol for Twelve Data.
        """
        symbol = symbol.upper().replace("-", "").replace("_", "")

        # Metals
        if symbol.startswith('XAU'):
            return 'XAU/USD'
        if symbol.startswith('XAG'):
            return 'XAG/USD'
        if symbol.startswith('XPT'):
            return 'XPT/USD'
        if symbol.startswith('XPD'):
            return 'XPD/USD'

        # Forex (detect by length and structure)
        if len(symbol) == 6 and symbol.endswith('USD'):
            # EURUSD → EUR/USD
            return f"{symbol[:3]}/{symbol[3:]}"

        # Crypto (BTCUSD → BTC/USD)
        if symbol.endswith('USD') and len(symbol) > 4:
            base = symbol[:-3]
            return f"{base}/USD"

        # Stocks (AAPL, TSLA, etc.)
        return symbol

    def _map_timeframe_to_twelvedata(self, timeframe: str) -> str:
        """
        Map internal timeframe to Twelve Data interval.

        Twelve Data intervals:
        - Minutes: 1min, 5min, 15min, 30min
        - Hours: 1h, 2h, 4h, 6h, 8h, 12h
        - Days/Weeks: 1day, 1week, 1month

        Args:
            timeframe: Internal timeframe (e.g., 'm5', 'h1', 'd1').

        Returns:
            Twelve Data interval string.
        """
        mapping = {
            'm1': '1min',
            'm5': '5min',
            'm15': '15min',
            'm30': '30min',
            'h1': '1h',
            'h2': '2h',
            'h4': '4h',
            'h6': '6h',
            'h8': '8h',
            'h12': '12h',
            'd1': '1day',
            'd3': '3day',
            'w1': '1week',
            'm1': '1month',
            'M1': '1month'
        }
        return mapping.get(timeframe.lower(), '1day')

    def _fetch_gateio(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Gate.io (for silver XAG/USDT:USDT swap).

        Gate.io provides silver swap contracts which are suitable for price monitoring.

        Args:
            symbol: Trading symbol (e.g., 'XAGUSD').
            timeframe: Internal timeframe (e.g., 'd1', 'h4').
            limit: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV data.

        Raises:
            RuntimeError: If Gate.io returns no data.
        """
        import ccxt

        # Initialize Gate.io exchange
        gate = ccxt.gateio({
            'enableRateLimit': True,
            'timeout': 15000
        })
        gate.load_markets()

        # Gate.io silver symbol (swap contract)
        gate_symbol = 'XAG/USDT:USDT'

        # Map timeframe to Gate.io interval
        interval = self._map_timeframe_to_gateio(timeframe)

        self.logger.debug(
            f"Gate.io: symbol={gate_symbol}, interval={interval}, limit={limit}"
        )

        # Fetch OHLCV data
        ohlcv = gate.fetch_ohlcv(gate_symbol, interval, limit=limit)

        if not ohlcv:
            raise RuntimeError(f"Gate.io returned no data for {gate_symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        # Convert to numeric types
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        self.logger.info(f"Successfully fetched {len(df)} candles from Gate.io for {symbol}")
        return df

    def _map_timeframe_to_gateio(self, timeframe: str) -> str:
        """
        Map internal timeframe to Gate.io interval.

        Gate.io intervals:
        - Minutes: 1m, 5m, 15m, 30m
        - Hours: 1h, 4h, 8h, 12h
        - Days/Weeks: 1d, 7d, 30d

        Args:
            timeframe: Internal timeframe (e.g., 'm5', 'h1', 'd1').

        Returns:
            Gate.io interval string.
        """
        mapping = {
            'm1': '1m',
            'm5': '5m',
            'm15': '15m',
            'm30': '30m',
            'h1': '1h',
            'h2': '2h',
            'h4': '4h',
            'h6': '6h',
            'h8': '8h',
            'h12': '12h',
            'd1': '1d',
            'd3': '3d',
            'd5': '5d',
            'w1': '7d',
            'm1': '30d',
            'M1': '30d'
        }
        return mapping.get(timeframe.lower(), '1d')

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
