"""
OHLCV Cache Manager for TA-DSS.

This module provides caching functionality for OHLCV data to reduce API calls.
It implements incremental fetch - only fetching new candles that aren't cached.

Multi-Timeframe Support:
    - Cache multiple timeframes per symbol
    - Batch fetch for MTF analysis (3 TFs × N symbols)
    - Automatic cache invalidation

Usage:
    from src.services.ohlcv_cache_manager import OHLCVCacheManager

    cache_mgr = OHLCVCacheManager(db_session)

    # Get cached data (returns None if not enough data)
    df = cache_mgr.get_cached_ohlcv('XAUUSD', 'd1', limit=100)

    # Multi-timeframe fetch for MTF analysis
    data = cache_mgr.get_multi_timeframe_ohlcv(
        'BTC/USDT',
        timeframes=['w1', 'd1', 'h4']
    )

    # Save new candles to cache
    cache_mgr.save_ohlcv('XAUUSD', 'd1', new_candles_df)

    # Get last cached candle timestamp
    last_ts = cache_mgr.get_last_cached_timestamp('XAUUSD', 'd1')
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.models.ohlcv_cache_model import OHLCVCache

logger = logging.getLogger(__name__)


class OHLCVCacheManager:
    """
    Manages OHLCV data caching to reduce API calls.
    
    This class provides methods to:
    1. Query cached OHLCV data
    2. Save new candles to cache
    3. Get the last cached timestamp (for incremental fetch)
    4. Calculate missing candles
    
    The cache is stored in SQLite database for persistence across restarts.
    
    Example:
        cache_mgr = OHLCVCacheManager(db)
        
        # Check what's cached
        last_ts = cache_mgr.get_last_cached_timestamp('XAUUSD', 'd1')
        
        # If old data or no data, fetch from API
        if last_ts is None or (datetime.utcnow() - last_ts).total_seconds() > 3600:
            new_data = api.fetch_ohlcv('XAUUSD', 'd1')
            cache_mgr.save_ohlcv('XAUUSD', 'd1', new_data)
        
        # Get complete dataset
        df = cache_mgr.get_cached_ohlcv('XAUUSD', 'd1', limit=100)
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the cache manager.
        
        Args:
            db_session: SQLAlchemy database session.
        """
        self.db = db_session
    
    def get_cached_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Get cached OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'XAUUSD').
            timeframe: Timeframe (e.g., 'd1', 'h4'). Supports both internal ('d1') and API ('1d') formats.
            limit: Number of candles to return.
        
        Returns:
            DataFrame with OHLCV data, or None if not enough data cached.
        """
        try:
            # Normalize timeframe to match stored format
            timeframe_normalized = self._normalize_timeframe_for_cache(timeframe)
            
            # Query cached data
            candles = (
                self.db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == timeframe_normalized
                )
                .order_by(OHLCVCache.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            if not candles:
                return None
            
            # Convert to DataFrame
            data = [c.to_dict() for c in candles]
            df = pd.DataFrame(data)
            
            # Sort by timestamp ascending
            df = df.sort_values('timestamp').reset_index(drop=True)
            df.set_index('timestamp', inplace=True)
            
            # Select OHLCV columns
            columns = ['open', 'high', 'low', 'close', 'volume']
            df = df[columns]
            
            # Rename to standard format (capitalize first letter)
            df = df.rename(columns={c: c.capitalize() for c in columns})
            
            logger.debug(f"Cache hit: {len(df)} candles for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading cache for {symbol} {timeframe}: {e}")
            return None
    
    def _normalize_timeframe_for_cache(self, timeframe: str) -> str:
        """
        Normalize timeframe to match stored format.
        
        Twelve Data uses: 1d, 1h, 4h, etc.
        Internal format: d1, h1, h4, etc.
        
        Args:
            timeframe: Internal timeframe (e.g., 'd1', 'h4').
        
        Returns:
            Normalized timeframe for cache storage (e.g., '1d', '4h').
        """
        # Convert internal format to Twelve Data format
        conversion = {
            'm1': '1min', 'm5': '5min', 'm15': '15min', 'm30': '30min',
            'h1': '1h', 'h2': '2h', 'h4': '4h', 'h6': '6h', 'h8': '8h', 'h12': '12h',
            'd1': '1d', 'd3': '3d', 'd5': '5d',
            'w1': '1week',
            'M1': '1month',
        }
        return conversion.get(timeframe.lower(), timeframe)
    
    def get_last_cached_timestamp(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[datetime]:
        """
        Get the timestamp of the most recently cached candle.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.
        
        Returns:
            Timestamp of last cached candle, or None if no cache.
        """
        try:
            last_candle = (
                self.db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == timeframe
                )
                .order_by(OHLCVCache.timestamp.desc())
                .first()
            )
            
            if last_candle:
                logger.debug(
                    f"Last cached candle for {symbol} {timeframe}: {last_candle.timestamp}"
                )
                return last_candle.timestamp
            else:
                logger.debug(f"No cached data for {symbol} {timeframe}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting last cached timestamp: {e}")
            return None
    
    def calculate_missing_candles(
        self,
        symbol: str,
        timeframe: str,
        last_cached_timestamp: Optional[datetime]
    ) -> int:
        """
        Calculate how many candles are missing from cache.

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe (supports both internal 'h4' and API '4h' formats).
            last_cached_timestamp: Timestamp of last cached candle.

        Returns:
            Number of candles to fetch from API.
        """
        if last_cached_timestamp is None:
            # No cache, fetch full limit
            return 100

        # Calculate time since last candle
        time_since_last = datetime.utcnow() - last_cached_timestamp

        # Estimate candle interval based on timeframe
        # Supports both internal format (h4) and API format (4h)
        candle_intervals = {
            # Internal format
            'm1': timedelta(minutes=1), 'm5': timedelta(minutes=5),
            'm15': timedelta(minutes=15), 'm30': timedelta(minutes=30),
            'h1': timedelta(hours=1), 'h2': timedelta(hours=2),
            'h4': timedelta(hours=4), 'h6': timedelta(hours=6),
            'h8': timedelta(hours=8), 'h12': timedelta(hours=12),
            'd1': timedelta(days=1), 'd3': timedelta(days=3), 'd5': timedelta(days=5),
            'w1': timedelta(weeks=1),
            'M1': timedelta(days=30),
            # API format (Twelve Data, Gate.io)
            '1min': timedelta(minutes=1), '5min': timedelta(minutes=5),
            '15min': timedelta(minutes=15), '30min': timedelta(minutes=30),
            '1h': timedelta(hours=1), '2h': timedelta(hours=2),
            '4h': timedelta(hours=4), '6h': timedelta(hours=6),
            '8h': timedelta(hours=8), '12h': timedelta(hours=12),
            '1day': timedelta(days=1), '3day': timedelta(days=3),
            '1week': timedelta(weeks=1),
            '1month': timedelta(days=30)
        }

        interval = candle_intervals.get(timeframe.lower(), timedelta(hours=1))

        # Calculate missing candles (add 1 for current forming candle)
        missing = int(time_since_last.total_seconds() / interval.total_seconds()) + 1

        # Cap at reasonable limit
        missing = min(missing, 100)

        logger.debug(
            f"Missing candles for {symbol} {timeframe}: {missing} "
            f"(last: {last_cached_timestamp})"
        )

        return missing
    
    def save_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame
    ) -> int:
        """
        Save OHLCV candles to cache.
        
        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe (will be normalized for storage).
            df: DataFrame with OHLCV data (index=timestamp, columns=Open/High/Low/Close/Volume).
        
        Returns:
            Number of candles saved.
        """
        try:
            saved_count = 0
            
            # Normalize timeframe for storage
            timeframe_normalized = self._normalize_timeframe_for_cache(timeframe)
            
            for timestamp, row in df.iterrows():
                # Skip if already cached (upsert logic)
                existing = (
                    self.db.query(OHLCVCache)
                    .filter(
                        OHLCVCache.symbol == symbol,
                        OHLCVCache.timeframe == timeframe_normalized,
                        OHLCVCache.timestamp == timestamp
                    )
                    .first()
                )
                
                if existing:
                    continue  # Already cached
                
                # Create new cache entry
                cache_entry = OHLCVCache(
                    symbol=symbol,
                    timeframe=timeframe_normalized,
                    timestamp=timestamp,
                    open=row.get('Open', row.get('open', 0)),
                    high=row.get('High', row.get('high', 0)),
                    low=row.get('Low', row.get('low', 0)),
                    close=row.get('Close', row.get('close', 0)),
                    volume=row.get('Volume', row.get('volume', 0)),
                    fetched_at=datetime.utcnow()
                )
                
                self.db.add(cache_entry)
                saved_count += 1
            
            # Commit all at once
            self.db.commit()
            
            if saved_count > 0:
                logger.info(f"Saved {saved_count} candles to cache for {symbol} {timeframe}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error saving cache for {symbol} {timeframe}: {e}")
            self.db.rollback()
            return 0
    
    def clear_cache(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> int:
        """
        Clear cached data.
        
        Args:
            symbol: Optional symbol to clear (clears all if None).
            timeframe: Optional timeframe to clear (with symbol).
        
        Returns:
            Number of entries deleted.
        """
        try:
            query = self.db.query(OHLCVCache)
            
            if symbol:
                query = query.filter(OHLCVCache.symbol == symbol)
                if timeframe:
                    query = query.filter(OHLCVCache.timeframe == timeframe)
            
            count = query.delete()
            self.db.commit()

            logger.info(f"Cleared {count} cache entries")
            return count

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            self.db.rollback()
            return 0

    # ========================================================================
    # MULTI-TIMEFRAME SUPPORT (for MTF Analysis)
    # ========================================================================

    def get_multi_timeframe_ohlcv(
        self,
        symbol: str,
        timeframes: list[str],
        limit: int = 100,
    ) -> dict[str, Optional[pd.DataFrame]]:
        """
        Get cached OHLCV data for multiple timeframes.

        Used by MTF analysis to fetch data for 3 timeframes simultaneously.

        Args:
            symbol: Trading pair symbol.
            timeframes: List of timeframes (e.g., ['w1', 'd1', 'h4']).
            limit: Number of candles per timeframe.

        Returns:
            Dictionary of timeframe → DataFrame.

        Example:
            >>> data = cache_mgr.get_multi_timeframe_ohlcv(
            ...     'BTC/USDT', ['w1', 'd1', 'h4']
            ... )
            >>> htf_df = data['w1']  # Weekly
            >>> mtf_df = data['d1']  # Daily
            >>> ltf_df = data['h4']  # 4H
        """
        result = {}

        for tf in timeframes:
            df = self.get_cached_ohlcv(symbol, tf, limit=limit)
            result[tf] = df

        return result

    def get_cache_status(
        self,
        symbol: str,
        timeframes: list[str],
    ) -> dict[str, Any]:
        """
        Get cache status for multiple timeframes.

        Returns information about what's cached and what needs to be fetched.

        Args:
            symbol: Trading pair symbol.
            timeframes: List of timeframes.

        Returns:
            Dictionary with cache status for each timeframe.
        """
        status = {}

        for tf in timeframes:
            last_ts = self.get_last_cached_timestamp(symbol, tf)
            candle_count = self._get_cached_candle_count(symbol, tf)

            status[tf] = {
                "last_update": last_ts.isoformat() if last_ts else None,
                "candle_count": candle_count,
                "is_fresh": self._is_cache_fresh(last_ts, tf),
            }

        return status

    def _get_cached_candle_count(
        self,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        Get number of cached candles for a symbol/timeframe.

        Args:
            symbol: Trading pair symbol.
            timeframe: Timeframe.

        Returns:
            Number of cached candles.
        """
        try:
            timeframe_normalized = self._normalize_timeframe_for_cache(timeframe)

            count = (
                self.db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == timeframe_normalized,
                )
                .count()
            )

            return count

        except Exception as e:
            logger.error(f"Error getting candle count: {e}")
            return 0

    def _is_cache_fresh(
        self,
        last_update: Optional[datetime],
        timeframe: str,
    ) -> bool:
        """
        Check if cache is fresh enough for the timeframe.

        Args:
            last_update: Last update timestamp.
            timeframe: Timeframe.

        Returns:
            True if cache is fresh.
        """
        if last_update is None:
            return False

        # Define max age per timeframe
        max_age_hours = {
            "m1": 0.5,    # 30 minutes
            "m5": 1,      # 1 hour
            "m15": 2,     # 2 hours
            "m30": 4,     # 4 hours
            "h1": 4,      # 4 hours
            "h4": 12,     # 12 hours
            "d1": 48,     # 2 days
            "w1": 168,    # 1 week
            "M1": 720,    # 1 month
        }

        max_age = max_age_hours.get(timeframe, 24)
        age_hours = (datetime.utcnow() - last_update).total_seconds() / 3600

        return age_hours < max_age

    def batch_save_ohlcv(
        self,
        data: dict[str, dict[str, pd.DataFrame]],
    ) -> dict[str, int]:
        """
        Batch save OHLCV data for multiple symbols and timeframes.

        Optimized for MTF scanner that fetches 3 TFs × N symbols.

        Args:
            data: Nested dict {symbol: {timeframe: DataFrame}}.

        Returns:
            Dictionary of saved candle counts.

        Example:
            >>> data = {
            ...     "BTC/USDT": {
            ...         "w1": weekly_df,
            ...         "d1": daily_df,
            ...         "h4": hourly_df,
            ...     }
            ... }
            >>> result = cache_mgr.batch_save_ohlcv(data)
        """
        result = {}

        for symbol, timeframes in data.items():
            result[symbol] = {}
            for timeframe, df in timeframes.items():
                count = self.save_ohlcv(symbol, timeframe, df)
                result[symbol][timeframe] = count

        return result
