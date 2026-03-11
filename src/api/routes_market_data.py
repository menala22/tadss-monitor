"""
Market Data API Routes.

Endpoints for managing and monitoring market data cache status:
  GET  /api/v1/market-data/status          - Get all pairs status
  GET  /api/v1/market-data/status/{pair}   - Get single pair status
  GET  /api/v1/market-data/summary         - Get summary statistics
  POST /api/v1/market-data/refresh         - Refresh specific pair/timeframes
  POST /api/v1/market-data/refresh-all     - Refresh all stale pairs
  GET  /api/v1/market-data/watchlist       - Get MTF watchlist with status

Data flow:
  1. Read from market_data_status table (fast, cache-only)
  2. For refresh operations: fetch from API → update cache → update status
  3. Return structured JSON for dashboard display
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import verify_api_key
from src.database import get_db_session
from src.data_fetcher import DataFetcher, DataFetchError
from src.models.mtf_watchlist_model import get_watchlist
from src.services.market_data_service import MarketDataService, PairStatus
from src.services.ohlcv_cache_manager import OHLCVCacheManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/market-data",
    tags=["market-data"],
    dependencies=[Depends(verify_api_key)],
)

# MTF timeframes by trading style
MTF_TIMEFRAMES = {
    "SWING": ["w1", "d1", "h4"],
    "INTRADAY": ["d1", "h4", "h1"],
    "DAY": ["h4", "h1", "m15"],
    "POSITION": ["M1", "w1", "d1"],
    "SCALPING": ["h1", "m15", "m5"],
}

# Timeframe → DataFetcher API format
_TF_API_MAP: Dict[str, str] = {
    "m1": "1m", "m5": "5m", "m15": "15m", "m30": "30m",
    "h1": "1h", "h2": "2h", "h4": "4h", "h6": "6h", "h12": "12h",
    "d1": "1d",
    "w1": "1w",
    "M1": "1M",
}

# Candle limits per timeframe
_TF_LIMITS: Dict[str, int] = {
    "m1": 100, "m5": 100, "m15": 100, "m30": 100,
    "h1": 150, "h2": 150, "h4": 150, "h6": 150, "h12": 150,
    "d1": 250,
    "w1": 100,
    "M1": 50,
}


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _fetch_and_save_data(
    pair: str,
    timeframe: str,
    fetcher: DataFetcher,
    cache_mgr: OHLCVCacheManager,
) -> Dict[str, Any]:
    """
    Fetch data from API and save to cache.

    Args:
        pair: Trading pair symbol.
        timeframe: Internal timeframe (e.g., "d1", "h4").
        fetcher: DataFetcher instance.
        cache_mgr: OHLCVCacheManager instance.

    Returns:
        Dict with fetch result details.
    """
    api_tf = _TF_API_MAP.get(timeframe, timeframe)
    limit = _TF_LIMITS.get(timeframe, 100)

    try:
        df = fetcher.get_ohlcv(pair, api_tf, limit=limit)

        if df is None or df.empty:
            return {
                "success": False,
                "error": "Empty response from API",
                "candles_fetched": 0,
            }

        # Save to cache (DataFetcher already saves, but ensure internal format too)
        cache_mgr.save_ohlcv(pair, timeframe, df)

        return {
            "success": True,
            "candles_fetched": len(df),
            "last_candle_time": df.index.max().isoformat() if len(df) > 0 else None,
        }

    except DataFetchError as e:
        logger.error(f"DataFetchError for {pair} {timeframe}: {e}")
        return {
            "success": False,
            "error": f"Fetch failed: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Unexpected error for {pair} {timeframe}: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


def _format_pair_status(
    pair: str,
    status_obj: Optional[PairStatus],
) -> Dict[str, Any]:
    """
    Format PairStatus for API response.

    Args:
        pair: Trading pair symbol.
        status_obj: PairStatus object or None.

    Returns:
        Formatted dictionary for API response.
    """
    if status_obj is None:
        return {
            "pair": pair,
            "overall_quality": "MISSING",
            "timeframes": {},
            "mtf_ready": False,
            "recommendation": "No data available - refresh required",
        }

    return status_obj.to_dict()


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get all pairs market data status",
)
def get_all_status(
    filter_quality: Optional[str] = Query(
        default=None,
        description="Filter by quality: EXCELLENT, GOOD, STALE, MISSING",
    ),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get market data status for all pairs.

    Returns cached status information including:
    - Candle count per timeframe
    - Data quality assessment
    - Last update timestamp
    - MTF readiness status

    **Quality Levels:**
    - EXCELLENT: 200+ candles, very fresh
    - GOOD: 100+ candles, recent
    - STALE: 50-99 candles OR old data
    - MISSING: <50 candles

    **Example:**
        GET /api/v1/market-data/status?filter_quality=STALE
    """
    service = MarketDataService(db)

    try:
        all_statuses = service.get_all_statuses(filter_quality=filter_quality)
    except Exception as e:
        logger.error(f"Error getting all statuses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )

    # Format for response
    pairs_data = {
        pair: _format_pair_status(pair, status)
        for pair, status in all_statuses.items()
    }

    # Calculate summary
    summary = {
        "total_pairs": len(pairs_data),
        "by_quality": {
            "EXCELLENT": sum(1 for s in all_statuses.values() if s.overall_quality == "EXCELLENT"),
            "GOOD": sum(1 for s in all_statuses.values() if s.overall_quality == "GOOD"),
            "STALE": sum(1 for s in all_statuses.values() if s.overall_quality == "STALE"),
            "MISSING": sum(1 for s in all_statuses.values() if s.overall_quality == "MISSING"),
        },
        "mtf_ready": sum(1 for s in all_statuses.values() if s.mtf_ready),
    }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": summary,
        "pairs": pairs_data,
    }


@router.get(
    "/status/{pair}",
    response_model=Dict[str, Any],
    summary="Get single pair market data status",
)
def get_pair_status(
    pair: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get detailed market data status for a specific pair.

    Shows all timeframes with:
    - Candle count
    - Quality assessment
    - Last candle timestamp
    - Data source

    **Example:**
        GET /api/v1/market-data/status/BTC/USDT
    """
    service = MarketDataService(db)

    try:
        status_obj = service.get_pair_status(pair)
    except Exception as e:
        logger.error(f"Error getting status for {pair}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )

    if status_obj is None:
        return {
            "pair": pair,
            "fetched_at": datetime.utcnow().isoformat(),
            "overall_quality": "MISSING",
            "timeframes": {},
            "mtf_ready": False,
            "recommendation": "No data available - refresh to fetch from API",
        }

    return {
        "pair": pair,
        "fetched_at": datetime.utcnow().isoformat(),
        **status_obj.to_dict(),
    }


@router.get(
    "/summary",
    response_model=Dict[str, Any],
    summary="Get market data summary statistics",
)
def get_summary(
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get summary statistics for all market data.

    Returns:
    - Total pairs tracked
    - Pairs by quality level
    - MTF ready count
    - Pairs needing refresh

    **Example:**
        GET /api/v1/market-data/summary
    """
    service = MarketDataService(db)

    try:
        summary = service.get_summary()
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}",
        )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        **summary,
    }


@router.post(
    "/refresh",
    response_model=Dict[str, Any],
    summary="Refresh market data for specific pair",
)
def refresh_pair_data(
    request: Dict[str, Any],
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Refresh market data for a specific pair and timeframes.

    **Request Body:**
    ```json
    {
        "pair": "BTC/USDT",
        "timeframes": ["d1", "h4"],  // Optional, defaults to MTF timeframes
        "trading_style": "SWING"      // Used if timeframes not specified
    }
    ```

    **Process:**
    1. Fetch data from API for each timeframe
    2. Save to OHLCV cache
    3. Update market_data_status table
    4. Return results

    **Example:**
        POST /api/v1/market-data/refresh
        {"pair": "BTC/USDT", "timeframes": ["d1", "h4"]}
    """
    pair = request.get("pair", "").strip()
    if not pair:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'pair' field is required",
        )

    # Determine timeframes to refresh
    timeframes = request.get("timeframes")
    if not timeframes:
        trading_style = request.get("trading_style", "SWING").upper()
        timeframes = MTF_TIMEFRAMES.get(trading_style, ["w1", "d1", "h4"])

    service = MarketDataService(db)
    cache_mgr = OHLCVCacheManager(db)
    fetcher = DataFetcher()

    results = {
        "pair": pair,
        "refreshed": [],
        "skipped": [],
        "errors": [],
    }

    logger.info(f"Starting refresh for {pair}: {timeframes}")

    for timeframe in timeframes:
        try:
            # Fetch from API
            fetch_result = _fetch_and_save_data(
                pair=pair,
                timeframe=timeframe,
                fetcher=fetcher,
                cache_mgr=cache_mgr,
            )

            if fetch_result["success"]:
                # Update status
                status_entry = service.update_status(
                    pair=pair,
                    timeframe=timeframe,
                    candle_count=fetch_result["candles_fetched"],
                    last_candle_time=(
                        datetime.fromisoformat(fetch_result["last_candle_time"])
                        if fetch_result.get("last_candle_time")
                        else None
                    ),
                    source=None,  # Auto-detected by DataFetcher
                )

                results["refreshed"].append({
                    "timeframe": timeframe,
                    "candles_fetched": fetch_result["candles_fetched"],
                    "quality": status_entry.data_quality,
                })
            else:
                results["errors"].append({
                    "timeframe": timeframe,
                    "error": fetch_result.get("error", "Unknown error"),
                })

        except Exception as e:
            logger.error(f"Error refreshing {pair} {timeframe}: {e}")
            results["errors"].append({
                "timeframe": timeframe,
                "error": str(e),
            })

    # Update overall status
    updated_status = service.get_pair_status(pair)

    return {
        "status": "success" if not results["errors"] else "partial",
        "pair": pair,
        "refreshed": results["refreshed"],
        "skipped": results["skipped"],
        "errors": results["errors"],
        "overall_quality": updated_status.overall_quality if updated_status else "MISSING",
        "mtf_ready": updated_status.mtf_ready if updated_status else False,
    }


@router.post(
    "/refresh-all",
    response_model=Dict[str, Any],
    summary="Refresh all stale pairs",
)
def refresh_all_stale(
    request: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Refresh market data for all pairs with STALE or MISSING quality.

    This endpoint:
    1. Identifies all pairs with STALE or MISSING status
    2. Fetches fresh data for each pair's MTF timeframes
    3. Updates cache and status tables
    4. Returns summary of results

    **Request Body (Optional):**
    ```json
    {
        "trading_style": "SWING",  // Which timeframes to refresh
        "max_concurrent": 3        // Max pairs to refresh simultaneously
    }
    ```

    **Example:**
        POST /api/v1/market-data/refresh-all
    """
    request = request or {}
    trading_style = request.get("trading_style", "SWING").upper()
    timeframes = MTF_TIMEFRAMES.get(trading_style, ["w1", "d1", "h4"])

    service = MarketDataService(db)
    cache_mgr = OHLCVCacheManager(db)
    fetcher = DataFetcher()

    # Get stale pairs from watchlist
    watchlist = get_watchlist(db)
    stale_pairs = []

    for pair in watchlist:
        status = service.get_pair_status(pair)
        if status and status.overall_quality in ("STALE", "MISSING"):
            stale_pairs.append(pair)
        elif status is None:
            # No status exists - treat as MISSING
            stale_pairs.append(pair)

    if not stale_pairs:
        return {
            "status": "success",
            "message": "All pairs have fresh data - no refresh needed",
            "summary": {
                "total_pairs": len(watchlist),
                "refreshed": 0,
                "skipped": len(watchlist),
                "errors": 0,
            },
        }

    logger.info(f"Refreshing {len(stale_pairs)} stale pairs: {stale_pairs}")

    results = {
        "refreshed": [],
        "skipped": [],
        "errors": [],
    }

    for pair in stale_pairs:
        pair_result = {
            "pair": pair,
            "timeframes": [],
            "status": "success",
        }

        for timeframe in timeframes:
            try:
                fetch_result = _fetch_and_save_data(
                    pair=pair,
                    timeframe=timeframe,
                    fetcher=fetcher,
                    cache_mgr=cache_mgr,
                )

                if fetch_result["success"]:
                    service.update_status(
                        pair=pair,
                        timeframe=timeframe,
                        candle_count=fetch_result["candles_fetched"],
                        last_candle_time=(
                            datetime.fromisoformat(fetch_result["last_candle_time"])
                            if fetch_result.get("last_candle_time")
                            else None
                        ),
                    )
                    pair_result["timeframes"].append({
                        "timeframe": timeframe,
                        "candles_fetched": fetch_result["candles_fetched"],
                    })
                else:
                    pair_result["status"] = "partial"
                    pair_result["error"] = fetch_result.get("error", "Unknown error")

            except Exception as e:
                logger.error(f"Error refreshing {pair} {timeframe}: {e}")
                pair_result["status"] = "error"
                pair_result["error"] = str(e)

        if pair_result["status"] == "success":
            results["refreshed"].append(pair_result)
        elif pair_result["status"] == "partial":
            results["refreshed"].append(pair_result)  # Partial success
        else:
            results["errors"].append(pair_result)

    return {
        "status": "success" if not results["errors"] else "partial",
        "summary": {
            "total_pairs": len(watchlist),
            "stale_pairs": len(stale_pairs),
            "refreshed": len(results["refreshed"]),
            "errors": len(results["errors"]),
        },
        "details": results["refreshed"] + results["errors"],
        "trading_style": trading_style,
        "timeframes": timeframes,
    }


@router.get(
    "/watchlist",
    response_model=Dict[str, Any],
    summary="Get MTF watchlist with data status",
)
def get_watchlist_with_status(
    trading_style: str = Query(
        default="SWING",
        description="Trading style for MTF timeframes",
    ),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get MTF watchlist pairs with their data status.

    Combines watchlist with market data status to show:
    - Which pairs are in the watchlist
    - Their current data quality
    - Whether they're ready for MTF scanning

    **Example:**
        GET /api/v1/market-data/watchlist?trading_style=SWING
    """
    try:
        style = trading_style.upper()
        timeframes = MTF_TIMEFRAMES.get(style, ["w1", "d1", "h4"])
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trading_style: {trading_style}",
        )

    watchlist = get_watchlist(db)
    service = MarketDataService(db)

    pairs_data = []

    for pair in watchlist:
        status = service.get_pair_status(pair)

        # Check if pair has all required timeframes
        has_all_tf = False
        missing_tf = []

        if status:
            for tf in timeframes:
                if tf not in status.timeframes:
                    missing_tf.append(tf)
                else:
                    tf_quality = status.timeframes[tf]["quality"]
                    if tf_quality in ("STALE", "MISSING"):
                        missing_tf.append(tf)
            has_all_tf = len(missing_tf) == 0

        pairs_data.append({
            "pair": pair,
            "overall_quality": status.overall_quality if status else "MISSING",
            "mtf_ready": status.mtf_ready if status else False,
            "has_all_timeframes": has_all_tf,
            "missing_timeframes": missing_tf,
            "timeframes": status.timeframes if status else {},
        })

    # Sort by quality (EXCELLENT first, MISSING last)
    quality_order = {"EXCELLENT": 4, "GOOD": 3, "STALE": 2, "MISSING": 1}
    pairs_data.sort(
        key=lambda x: quality_order.get(x["overall_quality"], 0),
        reverse=True,
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "trading_style": style,
        "timeframes": timeframes,
        "watchlist": pairs_data,
        "count": len(pairs_data),
        "mtf_ready_count": sum(1 for p in pairs_data if p["mtf_ready"]),
    }


@router.delete(
    "/status/{pair}",
    response_model=Dict[str, Any],
    summary="Delete market data status for a pair",
)
def delete_pair_status(
    pair: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Delete all market data status entries for a pair.

    **Note:** This does NOT delete the OHLCV cache data.
    Use this to reset status tracking while keeping cached data.

    **Example:**
        DELETE /api/v1/market-data/status/BTC/USDT
    """
    service = MarketDataService(db)

    try:
        count = service.delete_pair_status(pair)
    except Exception as e:
        logger.error(f"Error deleting status for {pair}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete status: {str(e)}",
        )

    return {
        "deleted": pair,
        "entries_removed": count,
    }


@router.get(
    "/rate-limit/twelve-data",
    response_model=Dict[str, Any],
    summary="Get Twelve Data rate limit status",
    tags=["market-data", "rate-limit"],
)
def get_twelve_data_rate_limit_status() -> Dict[str, Any]:
    """
    Get current Twelve Data API rate limit status.
    
    Returns information about the rate limiting applied to Twelve Data API calls
    to stay within the free tier limits (8 calls/minute, 800 credits/day).
    
    **Response Fields:**
    - `last_call`: ISO timestamp of the last API call
    - `seconds_since_last_call`: Seconds elapsed since last call
    - `ready_to_call`: Whether enough time has passed for the next call
    - `limit`: Minimum interval between calls (seconds)
    
    **Example:**
        GET /api/v1/market-data/rate-limit/twelve-data
        
        Response:
        {
            "last_call": "2026-03-10T03:20:15.430000",
            "seconds_since_last_call": 12.5,
            "ready_to_call": true,
            "limit": 8.0
        }
    """
    from src.data_fetcher import _get_twelve_data_rate_limit_status
    
    status_data = _get_twelve_data_rate_limit_status()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "twelvedata",
        "free_tier_limits": {
            "calls_per_minute": 8,
            "credits_per_day": 800,
        },
        "rate_limit": status_data,
    }
