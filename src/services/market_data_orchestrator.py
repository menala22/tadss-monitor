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

    # Staleness thresholds (hours) - REDUCED FREQUENCY to stay under Twelve Data limits
    # Free tier: 800 credits/day, 8 calls/minute
    # These thresholds reduce API calls by ~76% while maintaining data quality
    STALENESS_THRESHOLDS = {
        'm1': 1,      # 1 hour (unchanged - high frequency trading)
        'm5': 2,      # 2 hours (unchanged)
        'm15': 4,     # 4 hours (unchanged)
        'm30': 6,     # 6 hours (unchanged)
        'h1': 2,      # 2 hours (was 4h) - frequent enough for intraday
        'h2': 4,      # 4 hours (was 8h)
        'h4': 6,      # 6 hours (was 12h) - aligns with trading sessions
        'h6': 12,     # 12 hours (was 24h)
        'h8': 12,     # 12 hours (was 24h)
        'h12': 18,    # 18 hours (was 24h)
        'd1': 24,     # 24 hours (was 48h) - daily refresh sufficient
        'd3': 48,     # 48 hours (was 96h)
        'w1': 168,    # 7 days (was 10 days) - weekly is enough
        'M1': 720,    # 30 days (unchanged)
    }
    
    # Fetch limits per timeframe
    FETCH_LIMITS = {
        'm1': 100, 'm5': 200, 'm15': 300, 'm30': 300,
        'h1': 500, 'h2': 300, 'h4': 200, 'h6': 200, 'h8': 200, 'h12': 200,
        'd1': 500, 'd3': 200,
        'w1': 500,
        'M1': 50,
    }

    # Actual candle duration in hours — used for accurate missing-candle calculation
    CANDLE_DURATION_HOURS = {
        'm1': 1/60, 'm5': 5/60, 'm15': 15/60, 'm30': 30/60,
        'h1': 1, 'h2': 2, 'h4': 4, 'h6': 6, 'h8': 8, 'h12': 12,
        'd1': 24, 'd3': 72,
        'w1': 168,
        'M1': 720,
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
    
    def clear_for_backfill(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> int:
        """
        Delete existing rows from ohlcv_universal so the next smart fetch
        treats every symbol/timeframe as a fresh initial fetch (using full FETCH_LIMITS).

        Args:
            symbols: Symbols to clear (defaults to watchlist).
            timeframes: Timeframes to clear (defaults to MTF_TIMEFRAMES).

        Returns:
            Number of rows deleted.
        """
        if symbols is None:
            symbols = get_watchlist(self.db)
        if timeframes is None:
            timeframes = self.MTF_TIMEFRAMES

        deleted = 0
        for symbol in symbols:
            for timeframe in timeframes:
                count = self.db.query(OHLCVUniversal).filter(
                    OHLCVUniversal.symbol == symbol,
                    OHLCVUniversal.timeframe == timeframe,
                ).delete()
                deleted += count
                logger.info(f"Cleared {count} rows for {symbol} {timeframe}")

        self.db.commit()
        logger.info(f"Backfill clear complete: {deleted} rows deleted")
        return deleted

    def get_stale_items(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> List[tuple]:
        """
        Get list of (symbol, timeframe) pairs that need refresh.
        
        Used by scheduler to spread fetches across time and avoid rate limits.
        
        Args:
            symbols: Optional list of symbols (defaults to watchlist).
            timeframes: Optional list of timeframes (defaults to MTF_TIMEFRAMES).
            
        Returns:
            List of (symbol, timeframe) tuples that are stale.
        """
        if symbols is None:
            symbols = get_watchlist(self.db)
        if timeframes is None:
            timeframes = self.MTF_TIMEFRAMES
        
        stale_items = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                last_candle = self.get_last_candle(symbol, timeframe)
                
                if last_candle is None:
                    # No data → needs fetch
                    stale_items.append((symbol, timeframe))
                elif self.is_stale(last_candle, timeframe):
                    # Old data → needs refresh
                    stale_items.append((symbol, timeframe))
        
        # Sort: Twelve Data pairs first (they need more spacing)
        def _provider_priority(item):
            symbol, _ = item
            provider = self.get_optimal_provider(symbol)
            return 0 if provider == 'twelvedata' else 1
        
        stale_items.sort(key=_provider_priority)
        
        logger.debug(f"Stale items: {len(stale_items)} pairs need refresh")
        return stale_items

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

            # Calculate and save technical signals (NEW - Option 2 implementation)
            try:
                signal_count = self.calculate_and_save_signals(symbol, timeframe, limit=len(df))
                if signal_count > 0:
                    logger.debug(f"Calculated {signal_count} signals for {symbol} {timeframe}")
            except Exception as e:
                logger.error(f"Signal calculation failed for {symbol} {timeframe}: {e}")
                # Don't fail the entire fetch if signal calculation fails

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

        # Use actual candle duration, not the staleness threshold
        candle_hours = self.CANDLE_DURATION_HOURS.get(timeframe, 1)

        # Calculate missing candles
        missing = int(age_hours / candle_hours) + 1  # +1 for current forming candle
        
        # Cap at reasonable limit
        return min(missing, 500)
    
    def get_optimal_provider(self, symbol: str) -> str:
        """
        Return best free provider for symbol.

        Provider routing strategy:
        - Forex (USD/CAD, EUR/USD, etc.) → CCXT/Kraken (free, no API key needed)
        - Crypto (BTC, ETH, etc.) → CCXT/Kraken (free, unlimited)
        - Gold (XAU) → Twelve Data (free tier works)
        - Silver (XAG) → Gate.io (free swap contract)
        - Stocks → Twelve Data (free tier)

        Args:
            symbol: Trading pair symbol.

        Returns:
            Provider name ('ccxt', 'twelvedata', 'gateio').
        """
        # Normalize: remove all special characters
        symbol_upper = symbol.upper().replace('-', '').replace('_', '').replace('/', '')

        # Silver → Gate.io (free swap, Twelve Data requires paid)
        if symbol_upper.startswith('XAG'):
            return 'gateio'

        # Gold → Twelve Data (free tier works)
        if symbol_upper.startswith('XAU'):
            return 'twelvedata'

        # Forex pairs (6 chars, 3-letter currency codes) → CCXT/Kraken (free)
        # Examples: USDCAD, EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD
        if len(symbol_upper) == 6 and symbol_upper.isalpha():
            fiat_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD'}
            base = symbol_upper[:3]
            quote = symbol_upper[3:]
            if base in fiat_currencies or quote in fiat_currencies:
                return 'ccxt'

        # Crypto → CCXT/Kraken (free, unlimited)
        crypto_prefixes = {'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC'}
        for prefix in crypto_prefixes:
            if symbol_upper.startswith(prefix):
                return 'ccxt'

        # Stocks → Twelve Data (free tier)
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

        For Twelve Data h4 requests, fetches 1h data and aggregates to 4h
        (Twelve Data free tier doesn't support 4h interval).

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of candles to fetch.
            provider: Provider name.

        Returns:
            DataFrame with OHLCV data, or None if failed.
        """
        # Special handling for Twelve Data h4 (not available on free tier)
        if provider == 'twelvedata' and timeframe == 'h4':
            logger.info(f"Twelve Data h4: Fetching 1h data for aggregation (limit={limit * 4})")
            # Fetch 4× more 1h candles to get enough for 4h aggregation
            df_1h = self.fetcher.get_ohlcv(symbol, '1h', limit=limit * 4, skip_cache_check=True)
            
            if df_1h is None or df_1h.empty:
                logger.error(f"Failed to fetch 1h data for {symbol} h4 aggregation")
                return None
            
            # Aggregate 1h → 4h
            from src.data_fetcher import aggregate_1h_to_4h
            df_4h = aggregate_1h_to_4h(df_1h)
            
            if df_4h is None or df_4h.empty:
                logger.error(f"Failed to aggregate 1h→4h for {symbol}")
                return None
            
            logger.info(f"Successfully aggregated {len(df_1h)} 1h candles → {len(df_4h)} 4h candles")
            return df_4h
        
        # Normal fetch for all other cases
        # Map internal timeframe to API format
        api_timeframe = self._map_timeframe_to_api(timeframe, provider)

        # Fetch using DataFetcher
        # IMPORTANT: skip_cache_check=True because orchestrator already determined
        # this data is stale/missing. We don't want the cache to return old data.
        df = self.fetcher.get_ohlcv(symbol, api_timeframe, limit=limit, skip_cache_check=True)

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

    def calculate_and_save_signals(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> int:
        """
        Calculate and save technical signals for latest candles.

        This method:
        1. Fetches latest OHLCV data from ohlcv_universal
        2. Calculates technical indicators and signals
        3. Saves signals to technical_signals table

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of candles to calculate (default: 100).

        Returns:
            Number of signals saved.
        """
        from src.services.technical_signal_calculator import TechnicalSignalCalculator

        try:
            # Fetch latest OHLCV data
            candles = self.db.query(OHLCVUniversal).filter(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe,
            ).order_by(
                OHLCVUniversal.timestamp.desc()
            ).limit(limit).all()

            if not candles:
                logger.debug(f"No OHLCV data for {symbol} {timeframe}, skipping signal calculation")
                return 0

            # Convert to DataFrame
            data = [c.to_dict() for c in candles]
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()

            # Standardize column names
            df.columns = df.columns.str.lower()

            # Calculate and save signals
            calculator = TechnicalSignalCalculator(self.db)
            count = calculator.calculate_and_save(df, symbol, timeframe, limit=limit)

            return count

        except Exception as e:
            logger.error(f"Failed to calculate signals for {symbol} {timeframe}: {e}")
            return 0
        
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
