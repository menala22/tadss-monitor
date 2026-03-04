"""
SQLAlchemy models for the Post-Trade Position Monitoring System.

This module defines the database schema for tracking trading positions,
including their metadata, status, and lifecycle management.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class PositionType(str, PyEnum):
    """Enumeration for position direction (Long or Short)."""

    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, PyEnum):
    """Enumeration for position status (Open or Closed)."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Position(Base):
    """
    Represents a trading position in the monitoring system.

    Attributes:
        id: Primary key identifier.
        pair: Trading pair symbol (e.g., 'BTC/USDT', 'AAPL').
        entry_price: Price at which the position was opened.
        entry_time: Timestamp when the position was opened.
        position_type: Direction of the position (LONG or SHORT).
        timeframe: Analysis timeframe (e.g., 'h4', 'd1').
        status: Current status (OPEN or CLOSED).
        close_price: Price at which the position was closed (nullable).
        close_time: Timestamp when the position was closed (nullable).
        last_signal_status: Last recorded signal status for spam prevention (nullable).
        last_checked_at: Timestamp of last analysis check (nullable).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    position_type = Column(Enum(PositionType), nullable=False)
    timeframe = Column(String(10), nullable=False)
    status = Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    close_price = Column(Float, nullable=True)
    close_time = Column(DateTime, nullable=True)
    last_signal_status = Column(String(20), nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def close(self, close_price: float, close_time: Optional[datetime] = None) -> None:
        """
        Close the position with the given close price and timestamp.

        This method updates the position status to CLOSED and records the
        close price and time. It does not commit the transaction; the caller
        is responsible for committing the session.

        Args:
            close_price: The price at which the position was closed.
            close_time: The timestamp of closure. Defaults to current UTC time.

        Raises:
            ValueError: If the position is already closed.
        """
        if self.status == PositionStatus.CLOSED:
            raise ValueError(f"Position {self.id} is already closed.")

        self.status = PositionStatus.CLOSED
        self.close_price = close_price
        self.close_time = close_time or datetime.utcnow()

    def is_open(self) -> bool:
        """
        Check if the position is currently open.

        Returns:
            True if the position status is OPEN, False otherwise.
        """
        return self.status == PositionStatus.OPEN

    def update_signal_status(self, signal_status: str) -> None:
        """
        Update the last signal status and checked timestamp.

        Args:
            signal_status: The signal status to store (e.g., 'BULLISH', 'BEARISH').
        """
        self.last_signal_status = signal_status
        self.last_checked_at = datetime.utcnow()

    def calculate_pnl(self, current_price: float) -> float:
        """
        Calculate the unrealized or realized profit/loss.

        For open positions, uses the current price. For closed positions,
        uses the close price.

        Args:
            current_price: The current market price (or close price for closed positions).

        Returns:
            The profit/loss value (positive = profit, negative = loss).
        """
        if self.status == PositionStatus.CLOSED and self.close_price is not None:
            price = self.close_price
        else:
            price = current_price

        if self.position_type == PositionType.LONG:
            return price - self.entry_price
        else:  # SHORT
            return self.entry_price - price

    def __repr__(self) -> str:
        """Return a string representation of the position."""
        return (
            f"<Position(id={self.id}, pair='{self.pair}', "
            f"type={self.position_type.value}, status={self.status.value})>"
        )


def get_engine(database_url: str = "sqlite:///./positions.db") -> any:
    """
    Create and return a SQLAlchemy engine.

    Args:
        database_url: Database connection URL. Defaults to SQLite file.

    Returns:
        A SQLAlchemy engine instance.
    """
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args)


def get_session_factory(database_url: str = "sqlite:///./positions.db"):
    """
    Create and return a session factory for database operations.

    Args:
        database_url: Database connection URL. Defaults to SQLite file.

    Returns:
        A SQLAlchemy session factory.
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_add_signal_columns(database_url: str = "sqlite:///./positions.db") -> bool:
    """
    Add signal tracking columns to positions table if they don't exist.

    This migration adds:
    - last_signal_status: String column for storing last signal status
    - last_checked_at: DateTime column for tracking last check time

    Args:
        database_url: Database connection URL.

    Returns:
        True if migration was successful, False otherwise.
    """
    from sqlalchemy import inspect, text

    try:
        engine = get_engine(database_url)
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('positions')]

        with engine.connect() as conn:
            if 'last_signal_status' not in columns:
                conn.execute(text(
                    "ALTER TABLE positions ADD COLUMN last_signal_status VARCHAR(20)"
                ))
                print("✓ Added last_signal_status column")

            if 'last_checked_at' not in columns:
                conn.execute(text(
                    "ALTER TABLE positions ADD COLUMN last_checked_at DATETIME"
                ))
                print("✓ Added last_checked_at column")

            conn.commit()

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False
