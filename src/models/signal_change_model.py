"""
SQLAlchemy model for MA10 and OTT signal change tracking.

This module defines the database schema for storing detailed signal changes,
providing granular tracking of when MA10 and OTT indicators change status.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Float, Index, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SignalType(str, PyEnum):
    """Enumeration for signal types."""

    MA10 = "MA10"
    MA20 = "MA20"
    MA50 = "MA50"
    OTT = "OTT"
    MACD = "MACD"
    RSI = "RSI"
    OVERALL = "OVERALL"


class SignalStatus(str, PyEnum):
    """Enumeration for signal status values."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    OVERBOUGHT = "OVERBOUGHT"
    OVERSOLD = "OVERSOLD"


class SignalChange(Base):
    """
    Represents a signal status change event in the monitoring system.

    This table provides detailed tracking of when individual indicators
    (MA10, OTT, etc.) change status, allowing for:
    - Historical analysis of signal patterns
    - Backtesting of signal-based strategies
    - Audit trail of all indicator changes
    - Correlation analysis between signals and price movements

    Attributes:
        id: Primary key identifier.
        timestamp: When the signal change occurred.
        pair: Trading pair symbol (e.g., 'BTC/USDT').
        timeframe: Analysis timeframe (e.g., 'h1', 'h4', 'd1').
        signal_type: Type of signal that changed (MA10, OTT, etc.).
        previous_status: Status before the change.
        current_status: Status after the change.
        price_at_change: Price when the signal changed.
        price_movement_pct: Price movement percentage at time of change.
        position_type: Position direction if applicable (LONG/SHORT).
        triggered_alert: Whether this change triggered an alert.
        extra_data: Additional JSON data about the change.
        created_at: Record creation timestamp.

    Example:
        change = SignalChange(
            pair='BTC/USDT',
            timeframe='h4',
            signal_type=SignalType.MA10,
            previous_status='BULLISH',
            current_status='BEARISH',
            price_at_change=50000.0,
            triggered_alert=True
        )
    """

    __tablename__ = "signal_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    pair = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False, index=True)
    previous_status = Column(String(20), nullable=False)
    current_status = Column(String(20), nullable=False)
    price_at_change = Column(Float, nullable=True)
    price_movement_pct = Column(Float, nullable=True)
    position_type = Column(String(5), nullable=True)  # LONG, SHORT, or NULL
    triggered_alert = Column(Integer, nullable=False, default=0)  # 0=False, 1=True
    extra_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Composite index for efficient querying by pair and signal type
    __table_args__ = (
        Index("ix_signal_changes_pair_signal", "pair", "signal_type"),
        Index("ix_signal_changes_pair_timeframe", "pair", "timeframe"),
        Index("ix_signal_changes_timestamp_pair", "timestamp", "pair"),
    )

    @classmethod
    def create_change(
        cls,
        pair: str,
        timeframe: str,
        signal_type: SignalType,
        previous_status: str,
        current_status: str,
        price_at_change: Optional[float] = None,
        price_movement_pct: Optional[float] = None,
        position_type: Optional[str] = None,
        triggered_alert: bool = False,
        extra_data: Optional[dict] = None,
    ) -> "SignalChange":
        """
        Factory method to create a new signal change record.

        Args:
            pair: Trading pair symbol.
            timeframe: Analysis timeframe.
            signal_type: Type of signal that changed.
            previous_status: Status before the change.
            current_status: Status after the change.
            price_at_change: Price when signal changed (optional).
            price_movement_pct: Price movement percentage (optional).
            position_type: Position direction (optional).
            triggered_alert: Whether this triggered an alert.
            extra_data: Additional metadata dict (will be JSON encoded).

        Returns:
            New SignalChange instance.

        Example:
            change = SignalChange.create_change(
                pair='BTC/USDT',
                timeframe='h4',
                signal_type=SignalType.MA10,
                previous_status='BULLISH',
                current_status='BEARISH',
                price_at_change=50000.0,
                triggered_alert=True
            )
        """
        import json

        extra_data_json = None
        if extra_data:
            extra_data_json = json.dumps(extra_data)

        return cls(
            pair=pair,
            timeframe=timeframe,
            signal_type=signal_type,
            previous_status=previous_status,
            current_status=current_status,
            price_at_change=price_at_change,
            price_movement_pct=price_movement_pct,
            position_type=position_type,
            triggered_alert=1 if triggered_alert else 0,
            extra_data=extra_data_json,
        )

    def get_extra_data(self) -> Optional[dict]:
        """
        Parse and return the extra_data JSON.

        Returns:
            Parsed extra_data dict or None if not set.
        """
        import json

        if self.extra_data:
            return json.loads(self.extra_data)
        return None

    def set_extra_data(self, data: dict) -> None:
        """
        Set extra_data from a dictionary.

        Args:
            data: Dictionary to store as JSON.
        """
        import json
        
        self.metadata = json.dumps(data)

    def __repr__(self) -> str:
        """Return a string representation of the signal change."""
        return (
            f"<SignalChange(id={self.id}, pair='{self.pair}', "
            f"signal={self.signal_type.value}, "
            f"{self.previous_status}→{self.current_status})>"
        )
