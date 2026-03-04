"""
Pydantic schemas for request/response validation.

This module defines the data models used for API request bodies and responses,
ensuring type safety and automatic validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.config import validate_timeframe


class PositionType(str, Enum):
    """Position direction enumeration."""

    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    """Position status enumeration."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Timeframe(str, Enum):
    """Supported analysis timeframes."""

    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    H1 = "h1"
    H2 = "h2"
    H4 = "h4"
    H6 = "h6"
    H12 = "h12"
    D1 = "d1"
    W1 = "w1"
    M1 = "M1"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class PositionCreate(BaseModel):
    """Schema for creating a new position."""

    pair: str = Field(..., min_length=3, max_length=20, description="Trading pair symbol")
    entry_price: float = Field(..., gt=0, description="Entry price must be positive")
    position_type: PositionType = Field(..., description="Position direction (LONG/SHORT)")
    timeframe: Timeframe = Field(..., description="Analysis timeframe")
    entry_time: Optional[datetime] = Field(default=None, description="Entry timestamp (defaults to now)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pair": "BTCUSD",
                "entry_price": 45000.00,
                "position_type": "LONG",
                "timeframe": "h4",
            }
        }
    )

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        """Validate and normalize the trading pair format."""
        v = v.strip().upper()
        if not v.replace("-", "").replace("/", "").replace("_", "").isalpha():
            raise ValueError("Pair must contain only letters and optional separators (-, /, _)")
        return v

    @model_validator(mode="after")
    def validate_timeframe_for_source(self) -> "PositionCreate":
        """
        Validate timeframe is supported by the data source.

        For yfinance, warns if 'h4' is used (not available) and falls back to '1h'.
        For CCXT, all standard timeframes including '4h' are supported.

        Note: This validation assumes CCXT as the default source since it provides
        better timeframe coverage for crypto trading.
        """
        from src.config import validate_timeframe

        # Default to CCXT for crypto (better timeframe support)
        # Can be made configurable via settings
        source = "ccxt"

        try:
            # Validate and normalize the timeframe
            validated_tf = validate_timeframe(
                self.timeframe.value,
                source=source,
                auto_fallback=True,
            )
            # Update timeframe if it was auto-corrected
            # Convert back to internal format for storage
            from src.config import normalize_timeframe_to_internal
            self.timeframe = Timeframe(normalize_timeframe_to_internal(validated_tf))
        except ValueError as e:
            raise ValueError(f"Invalid timeframe '{self.timeframe.value}': {e}")

        return self


class PositionClose(BaseModel):
    """Schema for closing a position."""

    close_price: float = Field(..., gt=0, description="Close price must be positive")
    close_time: Optional[datetime] = Field(default=None, description="Close timestamp (defaults to now)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "close_price": 46500.00,
            }
        }
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class PositionResponse(BaseModel):
    """Schema for position data in responses."""

    id: int
    pair: str
    entry_price: float
    entry_time: datetime
    position_type: PositionType
    timeframe: Timeframe
    status: PositionStatus
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PositionWithPnL(PositionResponse):
    """Extended position schema with PnL calculation."""

    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Position created successfully",
                "detail": None,
            }
        }
    )


class PositionsListResponse(BaseModel):
    """Schema for listing multiple positions."""

    positions: list[PositionResponse]
    total: int
    open_count: int
    closed_count: int


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    timestamp: datetime
    version: str = "1.0.0"
