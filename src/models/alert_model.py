"""
SQLAlchemy model for alert history tracking.

This module defines the database schema for storing alert history,
providing an audit trail for all Telegram notifications sent by the system.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AlertType(str, PyEnum):
    """Enumeration for alert types."""

    POSITION_HEALTH = "POSITION_HEALTH"
    PRICE_MOVEMENT = "PRICE_MOVEMENT"
    SIGNAL_CHANGE = "SIGNAL_CHANGE"
    DAILY_SUMMARY = "DAILY_SUMMARY"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CUSTOM = "CUSTOM"


class AlertStatus(str, PyEnum):
    """Enumeration for alert delivery status."""

    SENT = "SENT"
    FAILED = "FAILED"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"  # Anti-spam logic prevented sending


class AlertHistory(Base):
    """
    Represents a sent alert in the monitoring system.

    This table provides an audit trail for all notifications,
    allowing tracking of alert frequency, delivery success,
    and historical analysis of system behavior.

    Attributes:
        id: Primary key identifier.
        timestamp: When the alert was generated.
        pair: Trading pair symbol (e.g., 'BTC/USDT'). Nullable for system alerts.
        alert_type: Type of alert (POSITION_HEALTH, PRICE_MOVEMENT, etc.).
        status: Delivery status (SENT, FAILED, PENDING, SKIPPED).
        previous_status: Previous position health status (nullable).
        current_status: Current position health status.
        reason: Reason for triggering this alert.
        message: Full alert message text sent to Telegram.
        price_movement_pct: Price movement percentage that triggered alert (nullable).
        error_message: Error details if delivery failed (nullable).
        retry_count: Number of retry attempts made (default 0).
        created_at: Record creation timestamp.
    """

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    pair = Column(String(20), nullable=True, index=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.PENDING)
    previous_status = Column(String(20), nullable=True)
    current_status = Column(String(20), nullable=False)
    reason = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    price_movement_pct = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Index for efficient querying by status and timestamp
    __table_args__ = (
        Index("ix_alert_history_status_timestamp", "status", "timestamp"),
        Index("ix_alert_history_type_timestamp", "alert_type", "timestamp"),
    )

    @classmethod
    def create_alert(
        cls,
        alert_type: AlertType,
        current_status: str,
        reason: str,
        message: str,
        pair: Optional[str] = None,
        previous_status: Optional[str] = None,
        price_movement_pct: Optional[float] = None,
    ) -> "AlertHistory":
        """
        Factory method to create a new alert record.

        Args:
            alert_type: Type of alert being created.
            current_status: Current position health status.
            reason: Reason for triggering this alert.
            message: Full alert message text.
            pair: Trading pair symbol (optional).
            previous_status: Previous status before change (optional).
            price_movement_pct: Price movement percentage (optional).

        Returns:
            New AlertHistory instance with status set to PENDING.

        Example:
            alert = AlertHistory.create_alert(
                alert_type=AlertType.POSITION_HEALTH,
                current_status="WARNING",
                reason="Status changed from HEALTHY to WARNING",
                message="Position Health Alert for BTC/USDT...",
                pair="BTC/USDT",
                previous_status="HEALTHY"
            )
        """
        return cls(
            alert_type=alert_type,
            current_status=current_status,
            reason=reason,
            message=message,
            pair=pair,
            previous_status=previous_status,
            price_movement_pct=price_movement_pct,
            status=AlertStatus.PENDING,
        )

    def mark_sent(self) -> None:
        """Mark this alert as successfully sent."""
        self.status = AlertStatus.SENT

    def mark_failed(self, error: str) -> None:
        """
        Mark this alert as failed with error message.

        Args:
            error: Error message describing the failure.
        """
        self.status = AlertStatus.FAILED
        self.error_message = error
        self.retry_count += 1

    def mark_skipped(self) -> None:
        """Mark this alert as skipped (anti-spam logic)."""
        self.status = AlertStatus.SKIPPED

    def __repr__(self) -> str:
        """Return a string representation of the alert."""
        return (
            f"<AlertHistory(id={self.id}, pair='{self.pair}', "
            f"type={self.alert_type.value}, status={self.status.value})>"
        )
