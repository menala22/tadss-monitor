"""
Technical Signals Model for TA-DSS.

This module provides the database model for pre-calculated technical signals.
Unlike on-the-fly calculation, this table:
- Stores signals for ALL candles (not just latest)
- Enables historical signal analysis and backtesting
- Tracks calculation algorithm version
- Is the single source of truth for signal states

Usage:
    from src.models.technical_signal_model import TechnicalSignal

    # Query latest signals
    signals = db.query(TechnicalSignal).filter(
        TechnicalSignal.symbol == 'BTC/USDT',
        TechnicalSignal.timeframe == 'd1'
    ).order_by(TechnicalSignal.timestamp.desc()).limit(100).all()

    # Query historical signals for backtesting
    signals = db.query(TechnicalSignal).filter(
        TechnicalSignal.symbol == 'BTC/USDT',
        TechnicalSignal.timeframe == 'd1',
        TechnicalSignal.timestamp >= datetime(2026, 1, 1)
    ).all()
"""

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, Float, Integer, String,
    Index, UniqueConstraint, text
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TechnicalSignal(Base):
    """
    Pre-calculated technical signals for OHLCV candles.

    This table stores signal states and indicator values for all candles,
    enabling historical analysis, backtesting, and signal audit trails.

    Table Structure:
    - id: Primary key
    - symbol: Trading pair symbol (e.g., 'BTC/USDT', 'XAU/USD')
    - timeframe: Timeframe (e.g., 'w1', 'd1', 'h4', 'h1')
    - timestamp: Candle timestamp (UTC)
    - signal_*: Signal states (BULLISH/BEARISH/NEUTRAL/OVERBOUGHT/OVERSOLD)
    - value_*: Raw indicator values for debugging
    - calculated_at: When signals were calculated
    - calculation_version: Algorithm version for tracking changes

    Signal States:
    - BULLISH: Indicator suggests upward movement
    - BEARISH: Indicator suggests downward movement
    - NEUTRAL: No clear signal / insufficient data
    - OVERBOUGHT: RSI > 70 (extreme bullish, may reverse)
    - OVERSOLD: RSI < 30 (extreme bearish, may bounce)

    Unique Constraint:
    - (symbol, timeframe, timestamp): One signal set per candle

    Example:
        # Create signal entry
        signal = TechnicalSignal(
            symbol='BTC/USDT',
            timeframe='d1',
            timestamp=datetime(2026, 3, 8, 0, 0),
            signal_ma10='BULLISH',
            signal_ma20='BULLISH',
            signal_ma50='BEARISH',
            signal_macd='BULLISH',
            signal_rsi='BULLISH',
            signal_ott='BULLISH',
            signal_overall='BULLISH',
            value_ema10=66800.0,
            value_ema20=66300.0,
            value_ema50=67800.0,
            value_macd_hist=15.2,
            value_rsi=58.5,
            value_ott=66500.0,
            value_ott_trend=1,
            calculation_version='1.0'
        )
        db.add(signal)
        db.commit()

        # Query latest signals
        signals = db.query(TechnicalSignal).filter(
            TechnicalSignal.symbol == 'BTC/USDT',
            TechnicalSignal.timeframe == 'd1'
        ).order_by(TechnicalSignal.timestamp.desc()).limit(100).all()
    """

    __tablename__ = 'technical_signals'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Data identification (matches ohlcv_universal)
    symbol = Column(String(20), nullable=False, index=True)  # e.g., 'BTC/USDT', 'XAU/USD'
    timeframe = Column(String(10), nullable=False, index=True)  # e.g., 'w1', 'd1', 'h4', 'h1'
    timestamp = Column(DateTime, nullable=False, index=True)  # Candle timestamp (UTC)

    # Signal states (BULLISH/BEARISH/NEUTRAL/OVERBOUGHT/OVERSOLD)
    signal_ma10 = Column(String(20), nullable=True)  # EMA 10 signal
    signal_ma20 = Column(String(20), nullable=True)  # EMA 20 signal
    signal_ma50 = Column(String(20), nullable=True)  # EMA 50 signal
    signal_macd = Column(String(20), nullable=True)  # MACD signal
    signal_rsi = Column(String(20), nullable=True)   # RSI signal
    signal_ott = Column(String(20), nullable=True)   # OTT signal
    signal_overall = Column(String(20), nullable=True)  # Overall majority vote

    # Indicator values (for debugging and analysis)
    value_ema10 = Column(Float, nullable=True)   # EMA 10 value
    value_ema20 = Column(Float, nullable=True)   # EMA 20 value
    value_ema50 = Column(Float, nullable=True)   # EMA 50 value
    value_macd_hist = Column(Float, nullable=True)  # MACD histogram
    value_rsi = Column(Float, nullable=True)     # RSI value
    value_ott = Column(Float, nullable=True)     # OTT value
    value_ott_trend = Column(Integer, nullable=True)  # OTT trend (1, -1, 0)
    value_ott_mt = Column(Float, nullable=True)  # OTT MT (trailing stop)
    value_ott_mavg = Column(Float, nullable=True)  # OTT MAvg

    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    calculation_version = Column(String(10), default='1.0', nullable=False)  # Algorithm version

    # Unique constraint to prevent duplicate signals
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_signal_symbol_tf_ts'),
        Index('idx_signals_symbol_tf', 'symbol', 'timeframe'),
        Index('idx_signals_timestamp', 'timestamp'),
        Index('idx_signals_symbol_tf_ts', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_signals_calculated_at', 'calculated_at'),
        Index('idx_signals_version', 'calculation_version'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<TechnicalSignal(symbol='{self.symbol}', timeframe='{self.timeframe}', "
            f"timestamp={self.timestamp}, overall={self.signal_overall}, "
            f"version={self.calculation_version})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'signals': {
                'ma10': self.signal_ma10,
                'ma20': self.signal_ma20,
                'ma50': self.signal_ma50,
                'macd': self.signal_macd,
                'rsi': self.signal_rsi,
                'ott': self.signal_ott,
                'overall': self.signal_overall,
            },
            'indicator_values': {
                'ema10': self.value_ema10,
                'ema20': self.value_ema20,
                'ema50': self.value_ema50,
                'macd_hist': self.value_macd_hist,
                'rsi': self.value_rsi,
                'ott': self.value_ott,
                'ott_trend': self.value_ott_trend,
                'ott_mt': self.value_ott_mt,
                'ott_mavg': self.value_ott_mavg,
            },
            'calculated_at': self.calculated_at,
            'calculation_version': self.calculation_version,
        }

    def to_signal_states(self) -> dict:
        """
        Convert to signal_states format compatible with TechnicalAnalyzer.

        Returns:
            Dictionary matching TechnicalAnalyzer.generate_signal_states() output.

        Example:
            signal_states = db_signal.to_signal_states()
            overall = monitor._determine_overall_status(signal_states)
        """
        from src.services.technical_analyzer import SignalState

        return {
            'MA10': SignalState(self.signal_ma10) if self.signal_ma10 else None,
            'MA20': SignalState(self.signal_ma20) if self.signal_ma20 else None,
            'MA50': SignalState(self.signal_ma50) if self.signal_ma50 else None,
            'MACD': SignalState(self.signal_macd) if self.signal_macd else None,
            'RSI': SignalState(self.signal_rsi) if self.signal_rsi else None,
            'OTT': SignalState(self.signal_ott) if self.signal_ott else None,
            'values': {
                'EMA_10': self.value_ema10,
                'EMA_20': self.value_ema20,
                'EMA_50': self.value_ema50,
                'MACD_hist': self.value_macd_hist,
                'RSI': self.value_rsi,
                'OTT': self.value_ott,
                'OTT_Trend': self.value_ott_trend,
                'OTT_MT': self.value_ott_mt,
                'OTT_MAvg': self.value_ott_mavg,
            }
        }


def create_technical_signals_table(engine) -> None:
    """
    Create the technical signals table if it doesn't exist.

    Args:
        engine: SQLAlchemy engine instance.

    Example:
        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///./data/positions.db')
        create_technical_signals_table(engine)
    """
    TechnicalSignal.metadata.create_all(bind=engine, checkfirst=True)


def create_ohlcv_with_signals_view(engine) -> None:
    """
    Create the ohlcv_with_signals VIEW for easy querying.

    This VIEW joins ohlcv_universal with technical_signals,
    providing a single-table interface for OHLCV + signals data.

    Args:
        engine: SQLAlchemy engine instance.
    """
    from sqlalchemy import text

    view_sql = """
    CREATE VIEW IF NOT EXISTS ohlcv_with_signals AS
    SELECT 
        o.id,
        o.symbol,
        o.timeframe,
        o.timestamp,
        o.open,
        o.high,
        o.low,
        o.close,
        o.volume,
        o.fetched_at,
        o.provider,
        s.signal_ma10,
        s.signal_ma20,
        s.signal_ma50,
        s.signal_macd,
        s.signal_rsi,
        s.signal_ott,
        s.signal_overall,
        s.value_ema10,
        s.value_ema20,
        s.value_ema50,
        s.value_macd_hist,
        s.value_rsi,
        s.value_ott,
        s.value_ott_trend,
        s.value_ott_mt,
        s.value_ott_mavg,
        s.calculated_at,
        s.calculation_version
    FROM ohlcv_universal o
    LEFT JOIN technical_signals s 
        ON o.symbol = s.symbol 
        AND o.timeframe = s.timeframe 
        AND o.timestamp = s.timestamp;
    """

    with engine.connect() as conn:
        conn.execute(text(view_sql))
        conn.commit()


def migrate_add_technical_signals_table(db_session) -> None:
    """
    Migration function to add technical signals table to existing database.

    Args:
        db_session: SQLAlchemy session or engine.
    """
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    if 'technical_signals' in inspector.get_table_names():
        return  # Table already exists

    TechnicalSignal.metadata.create_all(bind=db_session.bind)

    # Create VIEW
    create_ohlcv_with_signals_view(db_session.bind)
