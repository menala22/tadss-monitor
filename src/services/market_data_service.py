"""
Market data service for fetching OHLCV data.

This module provides a unified interface for fetching market data from
different sources (yfinance for stocks, CCXT for crypto) with proper
timeframe validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

import ccxt
import pandas as pd
import yfinance as yf

from src.config import (
    VALID_TIMEFRAMES_CCXT,
    VALID_TIMEFRAMES_YFINANCE,
    normalize_timeframe_to_source,
    validate_timeframe,
)
from src.utils.helpers import normalize_ticker

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Service for fetching market data from multiple sources.

    Supports:
    - yfinance: Stocks, ETFs, indices
    - CCXT: Cryptocurrencies (100+ exchanges)
    """

    def __init__(self, source: Literal["yfinance", "ccxt"] = "ccxt"):
        """
        Initialize the market data service.

        Args:
            source: Default data source ('yfinance' or 'ccxt').
        """
        self.source = source
        self._exchange: Optional[ccxt.Exchange] = None

    @property
    def exchange(self) -> ccxt.Exchange:
        """Get or create the CCXT exchange instance."""
        if self._exchange is None:
            self._exchange = ccxt.binance()  # Default to Binance
            self._exchange.load_markets()
        return self._exchange

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        source: Optional[Literal["yfinance", "ccxt"]] = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV (candlestick) data for a symbol.

        This method automatically validates the timeframe for the selected
        data source before fetching data.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSD', 'AAPL').
            timeframe: Analysis timeframe (e.g., 'h4', 'd1', '1h').
            limit: Number of candles to fetch.
            source: Data source to use. Defaults to instance source.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.

        Raises:
            ValueError: If timeframe is not supported by the source.
            RuntimeError: If data fetching fails.
        """
        source = source or self.source

        # CRITICAL: Validate timeframe BEFORE fetching data
        validated_timeframe = validate_timeframe(
            timeframe=timeframe,
            source=source,
            auto_fallback=True,
        )
        logger.info(
            f"Fetching {limit} candles for {symbol} "
            f"using {source} (timeframe: {validated_timeframe})"
        )

        try:
            if source == "yfinance":
                return self._fetch_yfinance(symbol, validated_timeframe, limit)
            elif source == "ccxt":
                return self._fetch_ccxt(symbol, validated_timeframe, limit)
            else:
                raise ValueError(f"Unknown data source: {source}")
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise RuntimeError(f"Data fetch failed: {e}") from e

    def _fetch_yfinance(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch data from yfinance.

        Args:
            symbol: Stock/crypto symbol.
            timeframe: Validated yfinance timeframe.
            limit: Number of periods.

        Returns:
            OHLCV DataFrame.
        """
        # For yfinance, stocks use raw symbol (AAPL), crypto uses BTC-USD
        # Detect if it's likely a stock (short alpha-only symbol)
        symbol_clean = symbol.strip().upper()
        
        # Common stock patterns: 1-5 alpha chars without separators
        if symbol_clean.isalpha() and len(symbol_clean) <= 5:
            yf_symbol = symbol_clean  # Use as-is for stocks
        else:
            # Crypto/forex - use normalized format
            yf_symbol = normalize_ticker(symbol, source="yfinance")

        # Map timeframe to yfinance interval
        interval = self._map_timeframe_to_yfinance(timeframe)

        # Calculate period based on timeframe and limit
        period = self._calculate_yfinance_period(interval, limit)

        logger.debug(f"yfinance: {yf_symbol}, interval={interval}, period={period}")

        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            raise RuntimeError(f"No data returned for {yf_symbol}")

        # Reset index and format
        df = df.reset_index()
        df.columns = df.columns.str.lower()

        # Rename to standard columns
        df = df.rename(columns={
            "date": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        })

        # Keep only standard columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        return df

    def _fetch_ccxt(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> pd.DataFrame:
        """
        Fetch data from CCXT exchange.

        Args:
            symbol: Crypto pair symbol.
            timeframe: Validated CCXT timeframe.
            limit: Number of candles.

        Returns:
            OHLCV DataFrame.
        """
        # Normalize symbol for CCXT
        ccxt_symbol = normalize_ticker(symbol, source="ccxt")

        logger.debug(f"CCXT: {ccxt_symbol}, timeframe={timeframe}, limit={limit}")

        # Fetch OHLCV data
        ohlcv = self.exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)

        if not ohlcv:
            raise RuntimeError(f"No data returned for {ccxt_symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )

        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        return df

    def _map_timeframe_to_yfinance(self, timeframe: str) -> str:
        """
        Map internal timeframe to yfinance interval.

        Args:
            timeframe: Internal format (e.g., 'h1', 'd1').

        Returns:
            yfinance interval string.
        """
        # Normalize to source format first
        yf_tf = normalize_timeframe_to_source(timeframe, "yfinance")

        # Handle special cases
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
            # Default to 1h for unknown
            logger.warning(f"Unknown yfinance timeframe '{yf_tf}', defaulting to '1h'")
            return "1h"

    def _calculate_yfinance_period(
        self,
        interval: str,
        limit: int,
    ) -> str:
        """
        Calculate yfinance period string based on interval and limit.

        yfinance uses period strings like '1d', '5d', '1mo', '1y', 'max'.

        Args:
            interval: yfinance interval (e.g., '1h', '1d').
            limit: Number of candles needed.

        Returns:
            yfinance period string.
        """
        # Estimate based on interval
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
            years = min(limit // 252 + 1, 5)  # ~252 trading days/year
            return f"{years}y"
        elif interval in ["1wk", "1mo"]:
            # Weekly/monthly - use max
            return "max"
        else:
            return "1y"

    def get_current_price(
        self,
        symbol: str,
        source: Optional[Literal["yfinance", "ccxt"]] = None,
    ) -> float:
        """
        Get the current/latest price for a symbol.

        Args:
            symbol: Trading pair symbol.
            source: Data source. Defaults to instance source.

        Returns:
            Current price as float.

        Raises:
            RuntimeError: If price fetch fails.
        """
        source = source or self.source

        try:
            # Fetch recent data
            df = self.fetch_ohlcv(symbol, timeframe="d1", limit=1, source=source)
            return float(df["close"].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            raise RuntimeError(f"Price fetch failed: {e}") from e

    def get_available_timeframes(
        self,
        source: Optional[Literal["yfinance", "ccxt"]] = None,
    ) -> set[str]:
        """
        Get available timeframes for the data source.

        Args:
            source: Data source. Defaults to instance source.

        Returns:
            Set of valid timeframe strings.
        """
        source = source or self.source

        if source == "yfinance":
            return VALID_TIMEFRAMES_YFINANCE.copy()
        elif source == "ccxt":
            return VALID_TIMEFRAMES_CCXT.copy()
        else:
            return set()

    def close(self) -> None:
        """Close any open connections (CCXT exchange)."""
        if self._exchange:
            try:
                self._exchange.close()
            except Exception:
                pass
            self._exchange = None
