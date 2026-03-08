"""
Market Data Prefetch API Routes.

Endpoints:
  POST /api/v1/market-data/prefetch        — Trigger manual smart fetch
  GET  /api/v1/market-data/prefetch/status — Get last prefetch result

Usage:
    # Trigger manual prefetch
    curl -X POST "http://localhost:8000/api/v1/market-data/prefetch" \
      -H "X-API-Key: your_key"
    
    # Get prefetch status
    curl "http://localhost:8000/api/v1/market-data/prefetch/status" \
      -H "X-API-Key: your_key"
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import verify_api_key
from src.database import get_db_session
from src.services.market_data_orchestrator import MarketDataOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/market-data",
    tags=["market-data"],
    dependencies=[Depends(verify_api_key)],
)

# Global variable to store last prefetch result
_last_prefetch_result: Optional[Dict[str, Any]] = None
_last_prefetch_time: Optional[datetime] = None


@router.post(
    "/prefetch",
    response_model=Dict[str, Any],
    summary="Trigger manual market data prefetch",
)
def trigger_prefetch(
    symbols: Optional[str] = Query(
        default=None,
        description="Comma-separated symbols to fetch (defaults to watchlist)",
    ),
    timeframes: Optional[str] = Query(
        default=None,
        description="Comma-separated timeframes (defaults to w1,d1,h4,h1)",
    ),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Trigger a manual smart fetch for market data.
    
    This endpoint runs the MarketDataOrchestrator smart fetch logic:
    1. Checks what data is needed (watchlist × timeframes)
    2. Checks what's cached (query ohlcv_universal)
    3. Calculates what's missing/stale
    4. Routes to optimal free providers
    5. Fetches + validates + saves data
    
    **Note:** This runs synchronously and may take 30-60 seconds for full refresh.
    
    Args:
        symbols: Optional comma-separated list of symbols.
        timeframes: Optional comma-separated list of timeframes.
    
    Returns:
        Prefetch result with statistics.
    
    Example:
        POST /api/v1/market-data/prefetch?symbols=BTC/USDT,ETH/USDT&timeframes=d1,h4
    """
    global _last_prefetch_result, _last_prefetch_time
    
    logger.info("Manual prefetch triggered")
    
    try:
        # Parse symbol and timeframe lists
        symbol_list = [s.strip() for s in symbols.split(",")] if symbols else None
        timeframe_list = [tf.strip() for tf in timeframes.split(",")] if timeframes else None
        
        # Run orchestrator
        orchestrator = MarketDataOrchestrator(db)
        result = orchestrator.run_smart_fetch(
            symbols=symbol_list,
            timeframes=timeframe_list,
        )
        
        # Store result
        _last_prefetch_result = result.to_dict()
        _last_prefetch_result['timestamp'] = datetime.utcnow().isoformat()
        _last_prefetch_time = datetime.utcnow()
        
        logger.info(
            f"Manual prefetch complete: {result.total_fetched} fetched, "
            f"{result.total_skipped} skipped, {result.total_errors} errors"
        )
        
        return {
            "status": "success" if result.total_errors == 0 else "partial",
            **_last_prefetch_result,
        }
        
    except Exception as e:
        logger.error(f"Manual prefetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prefetch failed: {str(e)}",
        )


@router.get(
    "/prefetch/status",
    response_model=Dict[str, Any],
    summary="Get last prefetch result",
)
def get_prefetch_status() -> Dict[str, Any]:
    """
    Get the result of the last prefetch operation.
    
    Returns information about:
    - When the last prefetch ran
    - How many symbols/timeframes were processed
    - How many were fetched, skipped, or had errors
    - Detailed fetch results per symbol/timeframe
    
    Returns:
        Last prefetch result with statistics.
    
    Example:
        GET /api/v1/market-data/prefetch/status
    """
    if _last_prefetch_result is None:
        return {
            "status": "no_data",
            "message": "No prefetch has been run yet",
            "last_run": None,
        }
    
    return {
        "status": "success",
        "last_run": _last_prefetch_time.isoformat() if _last_prefetch_time else None,
        **_last_prefetch_result,
    }
