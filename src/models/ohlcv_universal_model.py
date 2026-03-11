"""
OHLCV Universal Model for TA-DSS.

This module provides the database model for the unified OHLCV data store.
Unlike the legacy ohlcv_cache table, this table:
- Uses standardized symbol formats (XAU/USD, not XAUUSD)
- Uses normalized timeframe formats (w1, d1, h4, not 1w, 1week, 4h)
- Tracks data provider (ccxt, twelvedata, gateio)
- Is the single source of truth for all market data
- Is read-only for consumers (written only by MarketDataOrchestrator)

Usage:
    from src.models.ohlcv_universal_model import OHLCVUniversal
    
    # Query data
    df = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.symbol == 'BTC/USDT',
        OHLCVUniversal.timeframe == 'd1'
    ).order_by(OHLCVUniversal.timestamp.desc()).limit(100).all()
"""

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, Float, Integer, String,
    Index, UniqueConstraint, text
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OHLCVUniversal(Base):
    """
    Universal OHLCV data store - single source of truth for all market data.
    
    This table replaces the legacy ohlcv_cache table with:
    - Standardized symbol formats (XAU/USD, BTC/USDT, etc.)
    - Normalized timeframe formats (w1, d1, h4, h1)
    - Provider tracking (ccxt, twelvedata, gateio)
    - Proper unique constraints and indexes
    
    Table Structure:
    - id: Primary key
    - symbol: Trading pair symbol (e.g., 'BTC/USDT', 'XAU/USD')
    - timeframe: Normalized timeframe (e.g., 'w1', 'd1', 'h4', 'h1')
    - timestamp: Candle open time (UTC)
    - open/high/low/close: Price data
    - volume: Trading volume (may be NULL for forex)
    - fetched_at: When this candle was fetched from API
    - provider: Data source ('ccxt', 'twelvedata', 'gateio', 'migrated')
    
    Indexes:
    - idx_universal_symbol_tf: For symbol+timeframe queries
    - idx_universal_timestamp: For time-range queries
    - idx_universal_symbol_tf_ts: For ordered symbol+timeframe queries (optimal)
    
    Unique Constraint:
    - (symbol, timeframe, timestamp): Prevent duplicate candles
    
    Example:
        # Create OHLCV entry
        candle = OHLCVUniversal(
            symbol='BTC/USDT',
            timeframe='d1',
            timestamp=datetime(2026, 3, 8, 0, 0),
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
            fetched_at=datetime.utcnow(),
            provider='ccxt'
        )
        db.add(candle)
        db.commit()
        
        # Query latest 100 daily candles
        candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == 'BTC/USDT',
            OHLCVUniversal.timeframe == 'd1'
        ).order_by(OHLCVUniversal.timestamp.desc()).limit(100).all()
    """
    
    __tablename__ = 'ohlcv_universal'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Data identification
    symbol = Column(String(20), nullable=False, index=True)  # e.g., 'BTC/USDT', 'XAU/USD'
    timeframe = Column(String(10), nullable=False, index=True)  # e.g., 'w1', 'd1', 'h4', 'h1'
    timestamp = Column(DateTime, nullable=False, index=True)  # Candle open time (UTC)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    
    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider = Column(String(20), nullable=False)  # 'ccxt', 'twelvedata', 'gateio', 'migrated'
    
    # Unique constraint to prevent duplicate candles
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_symbol_tf_ts'),
        Index('idx_universal_symbol_tf', 'symbol', 'timeframe'),
        Index('idx_universal_timestamp', 'timestamp'),
        Index('idx_universal_symbol_tf_ts', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_universal_provider', 'provider'),
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<OHLCVUniversal(symbol='{self.symbol}', timeframe='{self.timeframe}', "
            f"timestamp={self.timestamp}, close={self.close}, provider={self.provider})>"
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
            'provider': self.provider,
        }


def create_ohlcv_universal_table(engine) -> None:
    """
    Create the OHLCV universal table if it doesn't exist.
    
    Args:
        engine: SQLAlchemy engine instance.
    
    Example:
        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///./data/positions.db')
        create_ohlcv_universal_table(engine)
    """
    OHLCVUniversal.metadata.create_all(bind=engine, checkfirst=True)


def migrate_add_ohlcv_universal_table(db_session) -> None:
    """
    Migration function to add OHLCV universal table to existing database.
    
    Args:
        db_session: SQLAlchemy session or engine.
    """
    from sqlalchemy import inspect
    
    inspector = inspect(db_session.bind)
    if 'ohlcv_universal' in inspector.get_table_names():
        return  # Table already exists
    
    OHLCVUniversal.metadata.create_all(bind=db_session.bind)


def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol to standard format.
    
    Converts various formats to standard slash-separated format:
    - XAUUSD, XAU/USD → XAU/USD
    - XAGUSD, XAG/USD → XAG/USD
    - ETHUSDT, ETH/USDT → ETH/USDT
    - BTCUSDT, BTC/USDT → BTC/USDT
    
    Args:
        symbol: Raw symbol string.
    
    Returns:
        Normalized symbol in standard format.
    """
    symbol = symbol.upper().replace('-', '').replace('_', '')
    
    # Metals
    if symbol.startswith('XAU'):
        return 'XAU/USD'
    if symbol.startswith('XAG'):
        return 'XAG/USD'
    if symbol.startswith('XPT'):
        return 'XPT/USD'
    if symbol.startswith('XPD'):
        return 'XPD/USD'
    
    # Crypto
    if symbol.startswith('BTC'):
        return 'BTC/USDT'
    if symbol.startswith('ETH'):
        return 'ETH/USDT'
    if symbol.startswith('SOL'):
        return 'SOL/USDT'
    
    # Forex (6 characters ending in USD)
    if len(symbol) == 6 and symbol.endswith('USD'):
        return f"{symbol[:3]}/{symbol[3:]}"
    
    # Stocks (return as-is)
    return symbol


def normalize_timeframe(timeframe: str) -> str:
    """
    Normalize timeframe to standard internal format.
    
    Converts various API formats to standard format:
    - 1w, 1week, 1wk → w1
    - 1d, 1day → d1
    - 4h → h4
    - 1h → h1
    
    Args:
        timeframe: Raw timeframe string.
    
    Returns:
        Normalized timeframe in standard format.
    """
    timeframe = timeframe.lower().strip()
    
    mapping = {
        # Weekly
        '1w': 'w1', '1week': 'w1', '1wk': 'w1', 'week': 'w1',
        # Daily
        '1d': 'd1', '1day': 'd1', 'day': 'd1',
        # Hours
        '1h': 'h1', '1hour': 'h1', 'hour': 'h1',
        '2h': 'h2',
        '4h': 'h4',
        '6h': 'h6',
        '8h': 'h8',
        '12h': 'h12',
        # Minutes
        '1m': 'm1', '1min': 'm1',
        '5m': 'm5', '5min': 'm5',
        '15m': 'm15', '15min': 'm15',
        '30m': 'm30', '30min': 'm30',
        # Monthly
        '1M': 'M1', '1month': 'M1', 'month': 'M1',
    }
    
    return mapping.get(timeframe, timeframe)
