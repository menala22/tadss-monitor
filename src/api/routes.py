"""
API routes for position management.

This module defines the FastAPI router with endpoints for managing
trading positions (create, list, close) and monitoring scheduler status.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.api.schemas import (
    MessageResponse,
    PositionClose,
    PositionCreate,
    PositionResponse,
    PositionWithPnL,
    PositionsListResponse,
)
from src.database import get_db_session
from src.scheduler import get_scheduler_status
from src.services.position_service import PositionService

router = APIRouter(prefix="/positions", tags=["positions"])


# Note: get_db_session is imported from src.database and used directly as dependency
# No need for a local wrapper function


@router.post(
    "/open",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a new position",
    description="Create a new trading position after manually executing a trade externally.",
)
def open_position(
    position_data: PositionCreate,
    db: Session = Depends(get_db_session),
) -> PositionResponse:
    """
    Open a new trading position.

    This endpoint is called after a user manually executes a trade on an
    external exchange. The position is stored for monitoring.

    Args:
        position_data: Position creation details (pair, entry_price, type, timeframe).
        db: Database session (injected).

    Returns:
        The created position with all details.

    Raises:
        HTTPException: If position creation fails.
    """
    service = PositionService(db)

    try:
        position = service.create_position(
            pair=position_data.pair,
            entry_price=position_data.entry_price,
            position_type=position_data.position_type,
            timeframe=position_data.timeframe.value,
            entry_time=position_data.entry_time,
        )
        
        # Calculate and store initial signals immediately
        # This enables alerts on the first monitoring check
        try:
            from src.monitor import PositionMonitor
            monitor = PositionMonitor()
            initial_signals = monitor.calculate_initial_signals(position)
            
            if initial_signals:
                position.last_ma10_status = initial_signals['ma10']
                position.last_ott_status = initial_signals['ott']
                position.last_signal_status = initial_signals['overall']
                db.commit()
                logger.info(
                    f"Initial signals calculated for {position.pair}: "
                    f"MA10={initial_signals['ma10']}, OTT={initial_signals['ott']}, "
                    f"Overall={initial_signals['overall']}"
                )
            else:
                logger.warning(
                    f"Could not calculate initial signals for {position.pair}, "
                    f"will be calculated on first monitoring check"
                )
        except Exception as e:
            # Position created successfully, but signals calculation failed
            # This is OK - signals will be calculated on first monitoring check
            logger.warning(
                f"Initial signals calculation failed for {position.pair}: {e}. "
                f"Will be calculated on first monitoring check."
            )
        
        return PositionResponse.model_validate(position)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create position: {str(e)}",
        )


@router.get(
    "/open",
    response_model=List[PositionWithPnL],
    summary="List all open positions",
    description="Retrieve all currently open positions with their details, current price, and PnL.",
)
def list_open_positions(
    db: Session = Depends(get_db_session),
) -> List[PositionWithPnL]:
    """
    List all open positions with current price and PnL from cache.
    
    If cache is missing or stale (>5 min old), fetches fresh data from API.

    This endpoint reads OHLCV data from the cache database instead of
    fetching from external APIs, ensuring fast response times and
    zero API calls on dashboard refresh.

    Args:
        db: Database session (injected).

    Returns:
        List of open positions with full details including current_price and PnL.
    """
    from src.services.ohlcv_cache_manager import OHLCVCacheManager
    from datetime import timedelta
    
    service = PositionService(db)
    positions = service.get_open_positions()
    cache_mgr = OHLCVCacheManager(db)
    
    logger.info(f"Fetching {len(positions)} open positions from cache")
    
    result = []
    for p in positions:
        # Get cached OHLCV data (no API call!)
        cached_df = cache_mgr.get_cached_ohlcv(p.pair, p.timeframe, limit=1)
        
        # Check if cache is stale (older than 5 minutes)
        cache_fresh = False
        if cached_df is not None and not cached_df.empty:
            last_candle_time = cached_df.index[-1]
            time_diff = datetime.utcnow() - last_candle_time
            cache_fresh = time_diff < timedelta(minutes=5)
        
        logger.debug(f"Position {p.pair} {p.timeframe}: cache={'HIT' if cached_df is not None and not cached_df.empty else 'MISS'}, fresh={cache_fresh}")
        
        position_dict = PositionWithPnL.model_validate(p)
        
        if cached_df is not None and not cached_df.empty:
            # Use cached data (fresh or stale) - scheduler keeps cache updated hourly
            position_dict.current_price = float(cached_df['Close'].iloc[-1])

            # Calculate PnL
            if p.position_type.value == "LONG":
                pnl_pct = ((position_dict.current_price - p.entry_price) / p.entry_price) * 100
            else:
                pnl_pct = ((p.entry_price - position_dict.current_price) / p.entry_price) * 100

            position_dict.unrealized_pnl_pct = round(pnl_pct, 2)
            position_dict.unrealized_pnl = position_dict.current_price - p.entry_price
            freshness = "FRESH" if cache_fresh else "STALE"
            logger.debug(f"  -> Using {freshness} cache: current_price={position_dict.current_price}, pnl={pnl_pct:.2f}%")
        else:
            # No cache at all - fall back to entry price until scheduler runs
            logger.info(f"  -> No cache for {p.pair} {p.timeframe}, using entry price (scheduler will populate cache)")
            position_dict.current_price = p.entry_price
            position_dict.unrealized_pnl = 0.0
            position_dict.unrealized_pnl_pct = 0.0
        
        result.append(position_dict)
    
    logger.info(f"Returning {len(result)} positions")
    return result


@router.get(
    "",
    response_model=PositionsListResponse,
    summary="List all positions",
    description="Retrieve all positions (open and closed) with pagination.",
)
def list_all_positions(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum positions to return"),
    status_filter: str = Query(default="all", description="Filter by status: all, open, closed"),
    db: Session = Depends(get_db_session),
) -> PositionsListResponse:
    """
    List all positions with optional filtering.

    Args:
        limit: Maximum number of positions to return (1-1000).
        status_filter: Filter by status ('all', 'open', 'closed').
        db: Database session (injected).

    Returns:
        Paginated list of positions with counts.
    """
    service = PositionService(db)

    if status_filter == "open":
        positions = service.get_open_positions()
    elif status_filter == "closed":
        from src.models.position_model import PositionStatus

        positions = [
            p for p in service.get_all_positions(limit=limit) if p.status == PositionStatus.CLOSED
        ]
    else:
        positions = service.get_all_positions(limit=limit)

    open_count = sum(1 for p in positions if p.status.value == "OPEN")
    closed_count = sum(1 for p in positions if p.status.value == "CLOSED")

    return PositionsListResponse(
        positions=[PositionResponse.model_validate(p) for p in positions],
        total=len(positions),
        open_count=open_count,
        closed_count=closed_count,
    )


@router.post(
    "/{position_id}/close",
    response_model=PositionResponse,
    summary="Close a position",
    description="Mark an open position as closed with the given close price.",
)
def close_position(
    position_id: int,
    close_data: PositionClose,
    db: Session = Depends(get_db_session),
) -> PositionResponse:
    """
    Close an existing position.

    Marks the position as closed and records the close price and time.

    Args:
        position_id: The position's unique identifier.
        close_data: Close details (close_price, optional close_time).
        db: Database session (injected).

    Returns:
        The updated position with close details.

    Raises:
        HTTPException: If position not found or already closed.
    """
    service = PositionService(db)

    try:
        position = service.close_position(
            position_id=position_id,
            close_price=close_data.close_price,
            close_time=close_data.close_time,
        )

        if position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position {position_id} not found.",
            )

        return PositionResponse.model_validate(position)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close position: {str(e)}",
        )


@router.get(
    "/{position_id}",
    response_model=PositionResponse,
    summary="Get position by ID",
    description="Retrieve details of a specific position.",
)
def get_position(
    position_id: int,
    db: Session = Depends(get_db_session),
) -> PositionResponse:
    """
    Get a specific position by ID.

    Args:
        position_id: The position's unique identifier.
        db: Database session (injected).

    Returns:
        The position details.

    Raises:
        HTTPException: If position not found.
    """
    service = PositionService(db)
    position = service.get_position(position_id)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found.",
        )

    return PositionResponse.model_validate(position)


@router.delete(
    "/{position_id}",
    response_model=MessageResponse,
    summary="Delete a position",
    description="Permanently delete a position from the database.",
)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a position permanently.

    Args:
        position_id: The position's unique identifier.
        db: Database session (injected).

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If position not found.
    """
    service = PositionService(db)
    position = service.get_position(position_id)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position {position_id} not found.",
        )

    db.delete(position)
    db.commit()

    return MessageResponse(
        message="Position deleted successfully",
        detail=f"Position {position_id} ({position.pair}) has been permanently removed.",
    )


# =============================================================================
# SCHEDULER STATUS ENDPOINTS
# =============================================================================


@router.get(
    "/scheduler/status",
    response_model=Dict[str, Any],
    summary="Get scheduler status",
    description="Get the current status of the background position monitoring scheduler.",
    tags=["scheduler"],
)
def scheduler_status_endpoint() -> Dict[str, Any]:
    """
    Get the current status of the background scheduler.

    Returns information about:
    - Whether the scheduler is running
    - Next scheduled run time
    - Number of jobs

    Returns:
        Dictionary with scheduler status information.
    """
    status = get_scheduler_status()

    # Convert datetime to ISO format for JSON serialization
    if status.get("next_run_time"):
        status["next_run_time"] = status["next_run_time"].isoformat()

    return status


@router.post(
    "/scheduler/test-alert",
    response_model=MessageResponse,
    summary="Send test Telegram alert",
    description="Send a test alert to verify Telegram configuration.",
    tags=["scheduler"],
)
def test_telegram_alert() -> MessageResponse:
    """
    Send a test Telegram alert.

    This endpoint sends a test message to verify that Telegram
    notifications are configured correctly.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If Telegram is not configured or message fails.
    """
    from src.services.notification_service import test_telegram_config

    success = test_telegram_config()

    if success:
        return MessageResponse(
            message="Test alert sent successfully",
            detail="Check your Telegram for the test message",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test alert. Check Telegram configuration.",
        )


@router.post(
    "/scheduler/run-now",
    response_model=Dict[str, Any],
    summary="Run monitoring check immediately",
    description="Trigger an immediate position monitoring check without waiting for the scheduled time.",
    tags=["scheduler"],
)
def run_monitoring_now() -> Dict[str, Any]:
    """
    Run position monitoring check immediately.

    This endpoint triggers an immediate check of all open positions,
    calculating signals and sending Telegram alerts if needed.

    Returns:
        Dictionary with check results:
        - total: Total positions checked
        - successful: Number of successful checks
        - alerts_sent: Number of alerts sent
        - errors: Number of errors

    Example:
        curl -X POST http://localhost:8000/api/v1/positions/scheduler/run-now
    """
    from src.monitor import run_monitoring_check

    try:
        results = run_monitoring_check()

        return {
            "success": True,
            "message": f"Monitoring check completed",
            "total": results.get("total", 0),
            "successful": results.get("successful", 0),
            "alerts_sent": results.get("alerts_sent", 0),
            "errors": results.get("errors", 0),
        }

    except Exception as e:
        logger.error(f"Monitoring check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monitoring check failed: {str(e)}",
        )
