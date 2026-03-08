"""
Market Data Orchestrator for TA-DSS.

This service orchestrates all market data fetching for the system.
It implements a cache-first architecture where:
1. All reads come from ohlcv_universal table (never direct API calls)
2. Smart prefetch keeps cache fresh based on staleness thresholds
3. Provider routing optimizes for cost (free tiers first)

Usage:
    from src.services.market_data_orchestrator import MarketDataOrchestrator
    from src.database import get_db_context
    
    with get_db_context() as db:
        orchestrator = MarketDataOrchestrator(db)
        orchestrator.run_smart_fetch()
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.data_fetcher import DataFetcher, DataFetchError
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.models.market_data_status_model import MarketDataStatus, DataQuality
from src.models.mtf_watchlist_model import get_watchlist

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a single fetch operation."""
    symbol: str
    timeframe: str
    candles_fetched: int
    provider: str
    success: bool
    error: Optional[str] = None
    is_refresh: bool = False  # True if updating existing data


@dataclass
class SmartFetchResult:
    """Result of a smart fetch operation."""
    total_needed: int
    total_fetched: int
    total_skipped: int
    total_errors: int
    fetches: List[FetchResult] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'total_needed': self.total_needed,
            'total_fetched': self.total_fetched,
            'total_skipped': self.total_skipped,
            'total_errors': self.total_errors,
            'fetches': [
                {
                    'symbol': f.symbol,
                    'timeframe': f.timeframe,
                    'candles_fetched': f.candles_fetched,
                    'provider': f.provider,
                    'success': f.success,
                    'error': f.error,
                    'is_refresh': f.is_refresh,
                }
                for f in self.fetches
            ],
        }


class MarketDataOrchestrator:
    """
    Central orchestrator for all market data fetching.
    
    Responsibilities:
    1. Maintain watchlist of symbols to track
    2. Schedule smart fetches based on staleness
    3. Route to optimal free providers
    4. Validate and save data to ohlcv_universal
    5. Update market_data_status metadata
    
    Example:
        with get_db_context() as db:
            orchestrator = MarketDataOrchestrator(db)
            result = orchestrator.run_smart_fetch()
            print(f"Fetched {result.total_fetched} candles")
    """
    
    # Timeframes to fetch for MTF analysis
    MTF_TIMEFRAMES = ['w1', 'd1', 'h4', 'h1']
    
    # Staleness thresholds (hours)
    STALENESS_THRESHOLDS = {
        'm1': 1,      # 1 hour
        'm5': 2,      # 2 hours
        'm15': 4,     # 4 hours
        'm30': 6,     # 6 hours
        'h1': 4,      # 4 hours
        'h2': 8,      # 8 hours
        'h4': 12,     # 12 hours
        'h6': 24,     # 24 hours
        'h8': 24,     # 24 hours
        'h12': 24,    # 24 hours
        'd1': 48,     # 48 hours
        'd3': 96,     # 96 hours
        'w1': 240,    # 10 days
        'M1': 720,    # 30 days
    }
    
    # Fetch limits per timeframe
    FETCH_LIMITS = {
        'm1': 100, 'm5': 100, 'm15': 100, 'm30': 100,
        'h1': 150, 'h2': 150, 'h4': 150, 'h6': 150, 'h8': 150, 'h12': 150,
        'd1': 250, 'd3': 250,
        'w1': 100,
        'M1': 50,
    }
    
    def __init__(self, db: Session):
        """
        Initialize the orchestrator.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db
        # Initialize with ccxt as base source (auto-detect will override per symbol)
        # This ensures CCXT exchange is initialized for crypto pairs
        self.fetcher = DataFetcher(source="ccxt")
    
    def run_smart_fetch(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> SmartFetchResult:
        """
        Run smart fetch for all watchlist symbols.
        
        Args:
            symbols: Optional list of symbols to fetch (defaults to watchlist).
            timeframes: Optional list of timeframes to fetch (defaults to MTF_TIMEFRAMES).
        
        Returns:
            SmartFetchResult with statistics.
        """
        # Get symbols from watchlist if not specified
        if symbols is None:
            symbols = get_watchlist(self.db)
        
        # Get timeframes if not specified
        if timeframes is None:
            timeframes = self.MTF_TIMEFRAMES
        
        logger.info(f"Starting smart fetch: {len(symbols)} symbols × {len(timeframes)} timeframes")
        
        result = SmartFetchResult(
            total_needed=len(symbols) * len(timeframes),
            total_fetched=0,
            total_skipped=0,
            total_errors=0,
        )
        
        for symbol in symbols:
            for timeframe in timeframes:
                fetch_result = self.fetch_if_needed(symbol, timeframe)
                result.fetches.append(fetch_result)
                
                if fetch_result.success:
                    result.total_fetched += 1
                elif fetch_result.error and 'skip' in fetch_result.error.lower():
                    result.total_skipped += 1
                else:
                    result.total_errors += 1
        
        logger.info(
            f"Smart fetch complete: {result.total_fetched} fetched, "
            f"{result.total_skipped} skipped, {result.total_errors} errors"
        )
        
        return result
    
    def fetch_if_needed(self, symbol: str, timeframe: str) -> FetchResult:
        """
        Fetch data for symbol/timeframe if needed.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
        
        Returns:
            FetchResult with operation details.
        """
        # Check what we have
        last_candle = self.get_last_candle(symbol, timeframe)
        
        # Determine if we need to fetch
        if last_candle is None:
            # No data → fetch full history
            limit = self.FETCH_LIMITS.get(timeframe, 100)
            is_refresh = False
            logger.info(f"Initial fetch: {symbol} {timeframe} ({limit} candles)")
            
        elif self.is_stale(last_candle, timeframe):
            # Old data → fetch new candles only
            missing = self.calculate_missing(last_candle, timeframe)
            limit = min(missing, self.FETCH_LIMITS.get(timeframe, 100))
            is_refresh = True
            logger.info(f"Refresh fetch: {symbol} {timeframe} ({limit} candles, {missing} missing)")
            
        else:
            # Fresh → skip
            logger.debug(f"Skip {symbol} {timeframe}: fresh (last: {last_candle})")
            return FetchResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_fetched=0,
                provider='N/A',
                success=True,
                error='skip: data is fresh',
            )
        
        # Get optimal provider
        provider = self.get_optimal_provider(symbol)
        
        # Fetch from API
        try:
            df = self.fetch_from_api(symbol, timeframe, limit, provider)
            
            if df is None or df.empty:
                return FetchResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles_fetched=0,
                    provider=provider,
                    success=False,
                    error='Empty response from API',
                    is_refresh=is_refresh,
                )
            
            # Validate data
            if not self.validate_data(df):
                return FetchResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles_fetched=0,
                    provider=provider,
                    success=False,
                    error='Data validation failed',
                    is_refresh=is_refresh,
                )
            
            # Save to universal table
            self.save_to_universal(symbol, timeframe, df, provider)
            
            # Update status
            self.update_status(symbol, timeframe, df, provider)
            
            return FetchResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_fetched=len(df),
                provider=provider,
                success=True,
                is_refresh=is_refresh,
            )
            
        except DataFetchError as e:
            logger.error(f"Fetch failed for {symbol} {timeframe}: {e}")
            return FetchResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_fetched=0,
                provider=provider,
                success=False,
                error=str(e),
                is_refresh=is_refresh,
            )
    
    def get_last_candle(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """
        Get timestamp of last cached candle for symbol/timeframe.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
        
        Returns:
            Timestamp of last candle, or None if no data.
        """
        result = self.db.query(
            func.max(OHLCVUniversal.timestamp)
        ).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).scalar()
        
        return result
    
    def is_stale(self, last_candle: datetime, timeframe: str) -> bool:
        """
        Check if cached data is stale (timeframe-relative).
        
        Args:
            last_candle: Timestamp of last cached candle.
            timeframe: Timeframe.
        
        Returns:
            True if data is stale.
        """
        age_hours = (datetime.utcnow() - last_candle).total_seconds() / 3600
        threshold = self.STALENESS_THRESHOLDS.get(timeframe, 24)
        
        return age_hours > threshold
    
    def calculate_missing(self, last_candle: datetime, timeframe: str) -> int:
        """
        Calculate how many candles to fetch.
        
        Args:
            last_candle: Timestamp of last cached candle.
            timeframe: Timeframe.
        
        Returns:
            Number of candles to fetch.
        """
        age_hours = (datetime.utcnow() - last_candle).total_seconds() / 3600
        
        # Get candle interval in hours
        tf_hours = self.STALENESS_THRESHOLDS.get(timeframe, 1)
        
        # Calculate missing candles
        missing = int(age_hours / tf_hours) + 1  # +1 for current forming candle
        
        # Cap at reasonable limit
        return min(missing, 500)
    
    def get_optimal_provider(self, symbol: str) -> str:
        """
        Return best free provider for symbol.
        
        Args:
            symbol: Trading pair symbol.
        
        Returns:
            Provider name ('ccxt', 'twelvedata', 'gateio').
        """
        symbol_upper = symbol.upper().replace('-', '').replace('_', '')
        
        # Silver → Gate.io (free swap, Twelve Data requires paid)
        if symbol_upper.startswith('XAG'):
            return 'gateio'
        
        # Gold → Twelve Data (free tier works)
        if symbol_upper.startswith('XAU'):
            return 'twelvedata'
        
        # Crypto → CCXT/Kraken (free, unlimited)
        crypto_prefixes = {'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC'}
        for prefix in crypto_prefixes:
            if symbol_upper.startswith(prefix):
                return 'ccxt'
        
        # Forex/Stocks → Twelve Data (free tier)
        return 'twelvedata'
    
    def fetch_from_api(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        provider: str,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data from API provider.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of candles to fetch.
            provider: Provider name.
        
        Returns:
            DataFrame with OHLCV data, or None if failed.
        """
        # Map internal timeframe to API format
        api_timeframe = self._map_timeframe_to_api(timeframe, provider)
        
        # Fetch using DataFetcher
        df = self.fetcher.get_ohlcv(symbol, api_timeframe, limit=limit)
        
        return df
    
    def _map_timeframe_to_api(self, timeframe: str, provider: str) -> str:
        """
        Map internal timeframe to provider-specific format.
        
        Args:
            timeframe: Internal timeframe (e.g., 'w1', 'd1', 'h4').
            provider: Provider name.
        
        Returns:
            Provider-specific timeframe.
        """
        if provider == 'twelvedata':
            mapping = {
                'm1': '1min', 'm5': '5min', 'm15': '15min', 'm30': '30min',
                'h1': '1h', 'h2': '2h', 'h4': '4h', 'h6': '6h', 'h8': '8h', 'h12': '12h',
                'd1': '1day', 'd3': '3day',
                'w1': '1week',
                'M1': '1month',
            }
        elif provider == 'ccxt':
            mapping = {
                'm1': '1m', 'm5': '5m', 'm15': '15m', 'm30': '30m',
                'h1': '1h', 'h2': '2h', 'h4': '4h', 'h6': '6h', 'h8': '8h', 'h12': '12h',
                'd1': '1d', 'd3': '3d',
                'w1': '1w',
                'M1': '1M',
            }
        elif provider == 'gateio':
            mapping = {
                'm1': '1m', 'm5': '5m', 'm15': '15m', 'm30': '30m',
                'h1': '1h', 'h2': '2h', 'h4': '4h', 'h6': '6h', 'h8': '8h', 'h12': '12h',
                'd1': '1d', 'd3': '3d',
                'w1': '7d',
                'M1': '30d',
            }
        else:
            mapping = {}
        
        return mapping.get(timeframe, timeframe)
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data.
        
        Returns:
            True if data is valid.
        """
        if df.empty:
            return False
        
        # Check for required columns
        required_columns = ['Open', 'High', 'Low', 'Close']
        for col in required_columns:
            if col not in df.columns:
                return False
        
        # Check for NULL/zero values in required columns
        for col in required_columns:
            if df[col].isnull().all() or (df[col] == 0).all():
                return False
        
        # Check for reasonable prices (no negative values)
        for col in ['Open', 'High', 'Low', 'Close']:
            if (df[col] < 0).any():
                return False
        
        return True
    
    def save_to_universal(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        provider: str,
    ) -> int:
        """
        Save OHLCV data to ohlcv_universal table.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            df: DataFrame with OHLCV data.
            provider: Provider name.
        
        Returns:
            Number of candles saved.
        """
        saved_count = 0
        
        for timestamp, row in df.iterrows():
            # Check if candle already exists (upsert logic)
            existing = self.db.query(OHLCVUniversal).filter(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe,
                OHLCVUniversal.timestamp == timestamp,
            ).first()
            
            if existing:
                # Update existing
                existing.open = row.get('Open', row.get('open', 0))
                existing.high = row.get('High', row.get('high', 0))
                existing.low = row.get('Low', row.get('low', 0))
                existing.close = row.get('Close', row.get('close', 0))
                existing.volume = row.get('Volume', row.get('volume'))
                existing.fetched_at = datetime.utcnow()
                existing.provider = provider
            else:
                # Insert new
                candle = OHLCVUniversal(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=row.get('Open', row.get('open', 0)),
                    high=row.get('High', row.get('high', 0)),
                    low=row.get('Low', row.get('low', 0)),
                    close=row.get('Close', row.get('close', 0)),
                    volume=row.get('Volume', row.get('volume')),
                    fetched_at=datetime.utcnow(),
                    provider=provider,
                )
                self.db.add(candle)
            
            saved_count += 1
        
        self.db.commit()
        
        logger.debug(f"Saved {saved_count} candles for {symbol} {timeframe}")
        
        return saved_count
    
    def update_status(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        provider: str,
    ) -> None:
        """
        Update market_data_status for symbol/timeframe.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            df: DataFrame with OHLCV data.
            provider: Provider name.
        """
        candle_count = self.db.query(
            func.count(OHLCVUniversal.id)
        ).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).scalar()
        
        last_candle_time = self.db.query(
            func.max(OHLCVUniversal.timestamp)
        ).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).scalar()
        
        # Assess quality
        age_hours = 0
        if last_candle_time:
            age_hours = (datetime.utcnow() - last_candle_time).total_seconds() / 3600
        
        tf_hours = self.STALENESS_THRESHOLDS.get(timeframe, 24)
        
        if candle_count >= 200 and age_hours < tf_hours * 2:
            quality = DataQuality.EXCELLENT.value
        elif candle_count >= 100 and age_hours < tf_hours * 4:
            quality = DataQuality.GOOD.value
        elif candle_count >= 50:
            quality = DataQuality.STALE.value
        else:
            quality = DataQuality.MISSING.value
        
        # Upsert status
        status = self.db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == symbol,
            MarketDataStatus.timeframe == timeframe,
        ).first()
        
        if status:
            status.candle_count = candle_count
            status.last_candle_time = last_candle_time
            status.fetched_at = datetime.utcnow()
            status.data_quality = quality
            status.source = provider
        else:
            status = MarketDataStatus(
                pair=symbol,
                timeframe=timeframe,
                candle_count=candle_count,
                last_candle_time=last_candle_time,
                fetched_at=datetime.utcnow(),
                data_quality=quality,
                source=provider,
            )
            self.db.add(status)
        
        self.db.commit()
        
        logger.debug(f"Updated status for {symbol} {timeframe}: {quality}")
