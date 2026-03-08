"""
Market Data Status Model for TA-DSS.

This module provides database models for tracking market data cache status.
It enables monitoring of cached OHLCV data quality, freshness, and coverage
across multiple pairs and timeframes.

Usage:
    from src.models.market_data_status_model import MarketDataStatus, DataQuality
    from src.services.market_data_service import MarketDataService

    # Get status for a pair
    status = service.get_pair_status("BTC/USDT")
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime, Integer, String, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DataQuality(str, Enum):
    """
    Data quality levels for market data cache.

    EXCELLENT: Fresh data, 200+ candles (full HTF analysis support)
    GOOD: Recent data, 100+ candles (standard analysis)
    STALE: Old data or insufficient candles (50-99 candles)
    MISSING: No data or critically low (<50 candles)
    """
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    STALE = "STALE"
    MISSING = "MISSING"


class MarketDataStatus(Base):
    """
    Database model for tracking market data cache status.

    This table provides metadata about cached OHLCV data:
    - How many candles are available per pair/timeframe
    - When data was last updated
    - Data quality assessment
    - Source provider information

    Table Structure:
    - id: Primary key
    - pair: Trading pair symbol (e.g., 'BTC/USDT', 'XAU/USD')
    - timeframe: Timeframe (e.g., 'h4', 'd1', 'w1')
    - candle_count: Number of cached candles
    - last_candle_time: Timestamp of most recent candle
    - fetched_at: When this status was last updated
    - data_quality: Quality assessment (EXCELLENT/GOOD/STALE/MISSING)
    - source: Data source used (ccxt, twelvedata, gateio)

    Indexes:
    - idx_pair_timeframe: For fast pair+timeframe queries
    - idx_pair: For single pair queries (all timeframes)

    Unique Constraint:
    - (pair, timeframe): One status entry per pair/timeframe combo

    Example:
        # Create status entry
        status = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=150,
            last_candle_time=datetime(2026, 3, 8, 0, 0),
            data_quality=DataQuality.GOOD,
            source='ccxt'
        )
        db.add(status)
        db.commit()

        # Query status
        statuses = db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == 'BTC/USDT'
        ).all()
    """

    __tablename__ = 'market_data_status'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Data identification
    pair = Column(String(20), nullable=False)  # e.g., 'BTC/USDT', 'XAU/USD'
    timeframe = Column(String(10), nullable=False)  # e.g., 'h4', 'd1', 'w1'

    # Data metrics
    candle_count = Column(Integer, default=0, nullable=False)
    last_candle_time = Column(DateTime, nullable=True)  # Most recent candle timestamp

    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_quality = Column(String(20), default=DataQuality.MISSING.value, nullable=False)
    source = Column(String(20), nullable=True)  # e.g., 'ccxt', 'twelvedata', 'gateio'

    # Unique constraint: one status per pair/timeframe
    __table_args__ = (
        UniqueConstraint('pair', 'timeframe', name='uq_pair_timeframe'),
        Index('idx_pair_timeframe', 'pair', 'timeframe'),
        Index('idx_pair', 'pair'),
        Index('idx_data_quality', 'data_quality'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MarketDataStatus(pair='{self.pair}', timeframe='{self.timeframe}', "
            f"candles={self.candle_count}, quality={self.data_quality})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'pair': self.pair,
            'timeframe': self.timeframe,
            'candle_count': self.candle_count,
            'last_candle_time': self.last_candle_time.isoformat() if self.last_candle_time else None,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None,
            'data_quality': self.data_quality,
            'source': self.source,
        }

    @classmethod
    def assess_quality(
        cls,
        candle_count: int,
        age_hours: float,
        timeframe: str,
    ) -> 'DataQuality':
        """
        Assess data quality based on candle count and age.

        Args:
            candle_count: Number of available candles.
            age_hours: Hours since last update.
            timeframe: Timeframe string (e.g., 'h4', 'd1').

        Returns:
            DataQuality enum value.

        Quality Criteria:
            EXCELLENT: 200+ candles, age < 2x timeframe interval
            GOOD: 100+ candles, age < 4x timeframe interval
            STALE: 50+ candles OR age < 24h
            MISSING: <50 candles OR age >= 24h
        """
        # Calculate timeframe interval in hours
        tf_hours = cls._get_timeframe_hours(timeframe)

        # Check candle count first
        if candle_count < 50:
            return DataQuality.MISSING

        if candle_count < 100:
            return DataQuality.STALE

        # Check freshness relative to timeframe
        max_age_excellent = tf_hours * 2
        max_age_good = tf_hours * 4
        max_age_stale = 24  # hours

        if candle_count >= 200 and age_hours < max_age_excellent:
            return DataQuality.EXCELLENT

        if candle_count >= 100 and age_hours < max_age_good:
            return DataQuality.GOOD

        if age_hours < max_age_stale:
            return DataQuality.STALE

        return DataQuality.MISSING

    @staticmethod
    def _get_timeframe_hours(timeframe: str) -> float:
        """
        Get timeframe interval in hours.

        Args:
            timeframe: Timeframe string (e.g., 'h4', 'd1', 'w1').

        Returns:
            Interval in hours.
        """
        if len(timeframe) < 2:
            return 1.0

        unit = timeframe[0].lower()
        
        # Handle uppercase M for month (M1, M3, etc.)
        if timeframe[0] == 'M':
            unit = 'M'
        
        try:
            value = int(timeframe[1:])
        except ValueError:
            return 1.0

        unit_hours = {
            'm': 1.0 / 60,  # minutes
            'h': 1.0,       # hours
            'd': 24.0,      # days
            'w': 168.0,     # weeks
            'M': 720.0,     # months (approximate)
        }

        return value * unit_hours.get(unit, 1.0)


def create_market_data_status_table(engine) -> None:
    """
    Create the market data status table if it doesn't exist.

    Args:
        engine: SQLAlchemy engine instance.

    Example:
        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///./data/positions.db')
        create_market_data_status_table(engine)
    """
    MarketDataStatus.metadata.create_all(bind=engine, checkfirst=True)


def migrate_add_market_data_status_table(db_session) -> None:
    """
    Migration function to add market data status table to existing database.

    Args:
        db_session: SQLAlchemy session or engine.
    """
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    if 'market_data_status' in inspector.get_table_names():
        return  # Table already exists

    MarketDataStatus.metadata.create_all(bind=db_session.bind)
