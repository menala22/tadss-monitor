"""
Position service for CRUD operations.

This module handles all database operations related to trading positions,
providing a clean interface between the API layer and the database.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models.position_model import Position, PositionStatus, PositionType


class PositionService:
    """Service class for position CRUD operations."""

    def __init__(self, db: Session):
        """
        Initialize the position service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def create_position(
        self,
        pair: str,
        entry_price: float,
        position_type: PositionType,
        timeframe: str,
        entry_time: Optional[datetime] = None,
    ) -> Position:
        """
        Create a new trading position.

        Args:
            pair: Trading pair symbol (e.g., 'BTC-USD').
            entry_price: Price at which the position was opened.
            position_type: Direction of the position (LONG or SHORT).
            timeframe: Analysis timeframe (e.g., 'h4', 'd1').
            entry_time: Timestamp of entry. Defaults to current UTC time.

        Returns:
            The created Position object.
        """
        position = Position(
            pair=pair,
            entry_price=entry_price,
            position_type=position_type,
            timeframe=timeframe,
            entry_time=entry_time or datetime.utcnow(),
            status=PositionStatus.OPEN,
        )

        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        return position

    def get_position(self, position_id: int) -> Optional[Position]:
        """
        Retrieve a position by ID.

        Args:
            position_id: The position's primary key.

        Returns:
            The Position object if found, None otherwise.
        """
        return self.db.query(Position).filter(Position.id == position_id).first()

    def get_open_positions(self) -> list[Position]:
        """
        Retrieve all open positions.

        Returns:
            List of Position objects with status OPEN.
        """
        return (
            self.db.query(Position)
            .filter(Position.status == PositionStatus.OPEN)
            .order_by(Position.entry_time.desc())
            .all()
        )

    def get_all_positions(self, limit: int = 100) -> list[Position]:
        """
        Retrieve all positions (open and closed).

        Args:
            limit: Maximum number of positions to return.

        Returns:
            List of Position objects.
        """
        return (
            self.db.query(Position)
            .order_by(Position.entry_time.desc())
            .limit(limit)
            .all()
        )

    def close_position(
        self,
        position_id: int,
        close_price: float,
        close_time: Optional[datetime] = None,
    ) -> Optional[Position]:
        """
        Close an existing position.

        Args:
            position_id: The position's primary key.
            close_price: Price at which the position was closed.
            close_time: Timestamp of closure. Defaults to current UTC time.

        Returns:
            The updated Position object if found, None otherwise.

        Raises:
            ValueError: If the position is already closed.
        """
        position = self.get_position(position_id)

        if position is None:
            return None

        if position.status == PositionStatus.CLOSED:
            raise ValueError(f"Position {position_id} is already closed.")

        position.close(close_price=close_price, close_time=close_time)

        self.db.commit()
        self.db.refresh(position)

        return position

    def get_positions_by_pair(self, pair: str, status: Optional[PositionStatus] = None) -> list[Position]:
        """
        Retrieve positions filtered by trading pair.

        Args:
            pair: Trading pair symbol to filter by.
            status: Optional status filter (OPEN, CLOSED, or None for all).

        Returns:
            List of Position objects matching the criteria.
        """
        query = self.db.query(Position).filter(Position.pair == pair)

        if status:
            query = query.filter(Position.status == status)

        return query.order_by(Position.entry_time.desc()).all()

    def get_open_positions_count(self) -> int:
        """
        Count the number of open positions.

        Returns:
            The count of positions with status OPEN.
        """
        return (
            self.db.query(Position)
            .filter(Position.status == PositionStatus.OPEN)
            .count()
        )

    def update_position_status(
        self,
        position_id: int,
        status: PositionStatus,
    ) -> Optional[Position]:
        """
        Update the status of a position.

        Args:
            position_id: The position's primary key.
            status: New status to set.

        Returns:
            The updated Position object if found, None otherwise.
        """
        position = self.get_position(position_id)

        if position is None:
            return None

        position.status = status
        self.db.commit()
        self.db.refresh(position)

        return position
