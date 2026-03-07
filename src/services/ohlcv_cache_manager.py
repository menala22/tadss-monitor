"""
OHLCV Cache Manager for TA-DSS.

This module provides caching functionality for OHLCV data to reduce API calls.
It implements incremental fetch - only fetching new candles that aren't cached.

Usage:
    from src.services.ohlcv_cache_manager import OHLCVCacheManager
    
    cache_mgr = OHLCVCacheManager(db_session)
    
    # Get cached data (returns None if not enough data)
    df = cache_mgr.get_cached_ohlcv('XAUUSD', 'd1', limit=100)
    
    # Save new candles to cache
    cache_mgr.save_ohlcv('XAUUSD', 'd1', new_candles_df)
    
    # Get last cached candle timestamp
    last_ts = cache_mgr.get_last_cached_timestamp('XAUUSD', 'd1')
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

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
            timeframe: Timeframe.
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
        candle_intervals = {
            'm1': timedelta(minutes=1),
            'm5': timedelta(minutes=5),
            'm15': timedelta(minutes=15),
            'm30': timedelta(minutes=30),
            'h1': timedelta(hours=1),
            'h2': timedelta(hours=2),
            'h4': timedelta(hours=4),
            'h6': timedelta(hours=6),
            'h8': timedelta(hours=8),
            'h12': timedelta(hours=12),
            'd1': timedelta(days=1),
            'd3': timedelta(days=3),
            'd5': timedelta(days=5),
            'w1': timedelta(weeks=1),
            'M1': timedelta(days=30),
        }
        
        interval = candle_intervals.get(timeframe, timedelta(hours=1))
        
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
