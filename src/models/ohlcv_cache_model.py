"""
OHLCV Cache Model for TA-DSS.

This module provides database models for caching OHLCV (candlestick) data.
Caching reduces API calls by storing historical data locally and only
fetching new candles when needed.

Usage:
    from src.models.ohlcv_cache_model import OHLCVCache
    
    # Query cached data
    cache = db.query(OHLCVCache).filter(
        OHLCVCache.symbol == 'XAUUSD',
        OHLCVCache.timeframe == 'd1'
    ).all()
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OHLCVCache(Base):
    """
    Database model for caching OHLCV candlestick data.
    
    This table stores historical price data to reduce API calls.
    The data fetcher checks this table first before making API requests,
    and only fetches missing candles from the API.
    
    Table Structure:
    - id: Primary key
    - symbol: Trading pair symbol (e.g., 'XAUUSD', 'ETHUSD')
    - timeframe: Timeframe (e.g., 'd1', 'h4', 'h1')
    - timestamp: Candle timestamp (UTC)
    - open/high/low/close: Price data
    - volume: Trading volume
    - fetched_at: When this candle was first fetched from API
    
    Indexes:
    - idx_symbol_timeframe: For fast symbol+timeframe queries
    - idx_timestamp: For time-range queries
    
    Unique Constraint:
    - (symbol, timeframe, timestamp): Prevent duplicate candles
    
    Example:
        # Create cache entry
        cache = OHLCVCache(
            symbol='XAUUSD',
            timeframe='d1',
            timestamp=datetime(2026, 3, 6, 0, 0),
            open=5000.0,
            high=5100.0,
            low=4950.0,
            close=5050.0,
            volume=1000.0
        )
        db.add(cache)
        db.commit()
        
        # Query cached data
        candles = db.query(OHLCVCache).filter(
            OHLCVCache.symbol == 'XAUUSD',
            OHLCVCache.timeframe == 'd1'
        ).order_by(OHLCVCache.timestamp).all()
    """
    
    __tablename__ = 'ohlcv_cache'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Candle identification
    symbol = Column(String(20), nullable=False)  # e.g., 'XAUUSD', 'ETHUSD'
    timeframe = Column(String(10), nullable=False)  # e.g., 'd1', 'h4', 'h1'
    timestamp = Column(DateTime, nullable=False)  # Candle open time (UTC)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    
    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Unique constraint to prevent duplicate candles
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_symbol_timeframe_timestamp'),
        Index('idx_symbol_timeframe', 'symbol', 'timeframe'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<OHLCVCache(symbol='{self.symbol}', timeframe='{self.timeframe}', "
            f"timestamp={self.timestamp}, close={self.close})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'fetched_at': self.fetched_at,
        }


def create_ohlcv_cache_table(engine) -> None:
    """
    Create the OHLCV cache table if it doesn't exist.
    
    This function uses SQLAlchemy's metadata creation to add the table
    to an existing database without affecting other tables.
    
    Args:
        engine: SQLAlchemy engine instance.
    
    Example:
        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///./data/positions.db')
        create_ohlcv_cache_table(engine)
    """
    # Create only this table (not all tables)
    OHLCVCache.metadata.create_all(bind=engine, checkfirst=True)


def migrate_add_ohlcv_cache_table(db_session) -> None:
    """
    Migration function to add OHLCV cache table to existing database.
    
    This can be called during application startup to ensure the table
    exists, even for databases created before this feature was added.
    
    Args:
        db_session: SQLAlchemy session or engine.
    
    Example:
        with get_db_context() as db:
            migrate_add_ohlcv_cache_table(db)
    """
    from sqlalchemy import inspect
    
    # Check if table already exists
    inspector = inspect(db_session.bind)
    if 'ohlcv_cache' in inspector.get_table_names():
        return  # Table already exists
    
    # Create the table
    OHLCVCache.metadata.create_all(bind=db_session.bind)
