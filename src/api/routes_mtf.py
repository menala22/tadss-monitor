"""
MTF (Multi-Timeframe) Analysis API Routes.

Endpoints:
  GET  /api/v1/mtf/opportunities          — scan watchlist for opportunities
  GET  /api/v1/mtf/opportunities/{pair}   — detailed analysis for one pair
  GET  /api/v1/mtf/configs                — timeframe configurations
  POST /api/v1/mtf/scan                   — on-demand scan with custom pairs
  GET  /api/v1/mtf/watchlist              — current watchlist

Data flow (Cache-First with Smart Fallback):
  1. Check market_data_status table for data quality.
  2. If GOOD/EXCELLENT: Load OHLCV from cache → scan immediately.
  3. If STALE/MISSING: Return actionable error with refresh suggestion.
  4. Zero live API calls during scan — refresh is explicit user action.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import verify_api_key
from src.database import get_db_session
from src.models.mtf_models import MTFTimeframeConfig, TradingStyle
from src.models.mtf_watchlist_model import MTFWatchlistItem, get_watchlist
from src.services.market_data_service import MarketDataService
from src.services.mtf_notifier import send_mtf_opportunity_alert
from src.services.mtf_opportunity_scanner import MTFOpportunityScanner
from src.services.ohlcv_cache_manager import OHLCVCacheManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mtf",
    tags=["mtf-analysis"],
    dependencies=[Depends(verify_api_key)],
)

DEFAULT_MTF_WATCHLIST = [
    "BTC/USDT",
    "ETH/USDT",
    "XAU/USD",
    "XAG/USD",
]

# Internal timeframe name → DataFetcher API format
_TF_API_MAP: Dict[str, str] = {
    "m1": "1m",  "m5": "5m",  "m15": "15m", "m30": "30m",
    "h1": "1h",  "h2": "2h",  "h4": "4h",   "h6": "6h",
    "h12": "12h",
    "d1": "1d",
    "w1": "1w",
    "M1": "1M",
}

# Candle limits per role. HTF needs more for SMA-200.
_ROLE_LIMITS: Dict[str, int] = {"htf": 250, "mtf": 150, "ltf": 100}


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _check_data_status(
    pair: str,
    config: MTFTimeframeConfig,
    service: MarketDataService,
) -> tuple[bool, Optional[str], List[str]]:
    """
    Check if pair has sufficient data quality for MTF scanning.

    Args:
        pair: Trading pair symbol.
        config: MTF timeframe configuration.
        service: MarketDataService instance.

    Returns:
        (is_ready, overall_quality, missing_timeframes)
        - is_ready: True if all timeframes have GOOD+ quality
        - overall_quality: Worst quality across timeframes
        - missing_timeframes: List of timeframes needing refresh
    """
    status = service.get_pair_status(pair)
    
    if status is None:
        return False, "MISSING", ["htf", "mtf", "ltf"]
    
    required_timeframes = [
        config.htf_timeframe,
        config.mtf_timeframe,
        config.ltf_timeframe,
    ]
    
    missing = []
    overall_quality = "EXCELLENT"
    
    quality_order = {"EXCELLENT": 4, "GOOD": 3, "STALE": 2, "MISSING": 1}
    
    for tf in required_timeframes:
        if tf not in status.timeframes:
            missing.append(tf)
            overall_quality = "MISSING"
        else:
            tf_quality = status.timeframes[tf]["quality"]
            if quality_order.get(tf_quality, 0) < quality_order.get(overall_quality, 0):
                overall_quality = tf_quality
            if tf_quality in ("STALE", "MISSING"):
                missing.append(tf)
    
    is_ready = len(missing) == 0 and overall_quality in ("EXCELLENT", "GOOD")
    
    return is_ready, overall_quality, missing


def _load_pair_data_from_universal(
    pair: str,
    config: MTFTimeframeConfig,
    db: Session,
) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load HTF/MTF/LTF DataFrames for a pair from ohlcv_universal table (read-only).
    
    This is the NEW method that reads from the internal market database.
    It never makes live API calls - all data comes from ohlcv_universal.
    
    Strategy:
      1. Query ohlcv_universal table for each timeframe.
      2. If any timeframe has no data or <10 candles, return None.
      3. Convert to DataFrame and return.
    
    Args:
        pair: Trading pair symbol.
        config: MTF timeframe configuration.
        db: SQLAlchemy database session.
    
    Returns:
        {"htf": df, "mtf": df, "ltf": df} or None if any timeframe is missing.
    """
    from src.models.ohlcv_universal_model import OHLCVUniversal
    
    roles = [
        ("htf", config.htf_timeframe),
        ("mtf", config.mtf_timeframe),
        ("ltf", config.ltf_timeframe),
    ]
    result: Dict[str, pd.DataFrame] = {}
    
    for role, internal_tf in roles:
        limit = _ROLE_LIMITS[role]
        
        # Query from ohlcv_universal
        candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == pair,
            OHLCVUniversal.timeframe == internal_tf,
        ).order_by(
            OHLCVUniversal.timestamp.desc()
        ).limit(limit).all()
        
        if not candles or len(candles) < 10:
            logger.info(
                f"No data in ohlcv_universal for {pair} {internal_tf} — "
                "waiting for prefetch job"
            )
            return None
        
        # Convert to DataFrame
        data = [c.to_dict() for c in candles]
        df = pd.DataFrame(data)
        
        # Sort by timestamp ascending
        df = df.sort_values('timestamp').reset_index(drop=True)
        df.set_index('timestamp', inplace=True)
        
        # Select OHLCV columns and rename to lowercase
        columns = ['open', 'high', 'low', 'close', 'volume']
        df = df[columns]
        
        result[role] = df
    
    return result


def _load_pair_data(
    pair: str,
    config: MTFTimeframeConfig,
    cache_mgr: OHLCVCacheManager,
) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load HTF/MTF/LTF DataFrames for a pair from the OHLCV cache (cache-only).
    
    DEPRECATED: Use _load_pair_data_from_universal() instead.
    This method is kept for backward compatibility during migration.
    
    Strategy:
      1. Read from SQLite OHLCV cache — fast, non-blocking.
      2. If any timeframe has no data or stale data, return None.
         The MTF prefetch scheduler job (every 2h at :20) will refresh the
         cache; the next user scan will succeed.
    
    Returns:
      {"htf": df, "mtf": df, "ltf": df} or None if any timeframe is missing/stale.
    """
    roles = [
        ("htf", config.htf_timeframe),
        ("mtf", config.mtf_timeframe),
        ("ltf", config.ltf_timeframe),
    ]
    result: Dict[str, pd.DataFrame] = {}

    for role, internal_tf in roles:
        limit = _ROLE_LIMITS[role]
        df = cache_mgr.get_cached_ohlcv(pair, internal_tf, limit=limit)

        if df is None or len(df) < 10:
            logger.info(
                f"No cached data for {pair} {internal_tf} — "
                "skipping (MTF prefetch job will populate cache)"
            )
            return None

        df = df.rename(columns=str.lower)
        result[role] = df

    return result


def _format_scan_result(pair: str, scan_result) -> Dict[str, Any]:
    """
    Flatten a ScanResult into a dashboard-compatible dict.

    The dashboard expects a flat structure with top-level keys like
    "htf_bias", "entry_price", "patterns" etc.
    """
    alignment = scan_result.alignment
    ltf = alignment.ltf_entry
    target = alignment.target

    return {
        "pair": pair,
        "quality": alignment.quality.value,
        "alignment_score": alignment.alignment_score,
        "recommendation": alignment.recommendation.value,
        "rr_ratio": round(alignment.rr_ratio, 2),
        "htf_bias": alignment.htf_bias.direction.value,
        "htf_confidence": round(alignment.htf_bias.confidence, 2),
        "mtf_setup": alignment.mtf_setup.setup_type.value,
        "mtf_confidence": round(alignment.mtf_setup.confidence, 2),
        "ltf_entry": ltf.signal_type.value if ltf else "NONE",
        "entry_price": round(ltf.entry_price, 4) if ltf and ltf.entry_price else None,
        "stop_loss": round(ltf.stop_loss, 4) if ltf and ltf.stop_loss else None,
        "target_price": round(target.target_price, 4) if target else None,
        "patterns": scan_result.patterns,
        "divergence": (
            scan_result.divergence.latest_type.value
            if scan_result.divergence and scan_result.divergence.latest_type
            else None
        ),
        "passes_filters": scan_result.passes_filters,
        "notes": alignment.notes,
    }


def _run_scan_from_universal(
    pair_list: List[str],
    config: MTFTimeframeConfig,
    db: Session,
    scanner: MTFOpportunityScanner,
) -> List[Dict[str, Any]]:
    """
    Scan a list of pairs using ohlcv_universal table (read-only).
    
    This is the NEW method that reads from the internal market database.
    It never makes live API calls - all data comes from ohlcv_universal.
    
    Args:
        pair_list: List of pair symbols to scan.
        config: MTF timeframe configuration.
        db: SQLAlchemy database session.
        scanner: MTFOpportunityScanner instance.
    
    Returns:
        List of formatted scan results.
    """
    results = []
    for pair in pair_list:
        data = _load_pair_data_from_universal(pair, config, db)
        if data is None:
            logger.warning(f"Skipping {pair} — no data in ohlcv_universal")
            continue
        try:
            scan_result = scanner.scan_pair_detailed(
                pair=pair,
                htf_data=data["htf"],
                mtf_data=data["mtf"],
                ltf_data=data["ltf"],
            )
            results.append(_format_scan_result(pair, scan_result))
        except Exception as exc:
            logger.error(f"Scan failed for {pair}: {exc}", exc_info=True)
    return results


def _run_scan(
    pair_list: List[str],
    config: MTFTimeframeConfig,
    cache_mgr: OHLCVCacheManager,
    scanner: MTFOpportunityScanner,
) -> List[Dict[str, Any]]:
    """
    Scan a list of pairs and return formatted results.
    
    DEPRECATED: Use _run_scan_from_universal() instead.
    This method is kept for backward compatibility during migration.
    
    Args:
        pair_list: List of pair symbols to scan.
        config: MTF timeframe configuration.
        cache_mgr: OHLCVCacheManager instance.
        scanner: MTFOpportunityScanner instance.
    
    Returns:
        List of formatted scan results.
    """
    results = []
    for pair in pair_list:
        data = _load_pair_data(pair, config, cache_mgr)
        if data is None:
            logger.warning(f"Skipping {pair} — no data available")
            continue
        try:
            scan_result = scanner.scan_pair_detailed(
                pair=pair,
                htf_data=data["htf"],
                mtf_data=data["mtf"],
                ltf_data=data["ltf"],
            )
            results.append(_format_scan_result(pair, scan_result))
        except Exception as exc:
            logger.error(f"Scan failed for {pair}: {exc}", exc_info=True)
    return results


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/opportunities",
    response_model=Dict[str, Any],
    summary="Scan for MTF opportunities",
)
def scan_opportunities(
    trading_style: str = Query(
        default="SWING",
        description="POSITION | SWING | INTRADAY | DAY | SCALPING",
    ),
    min_alignment: int = Query(default=2, ge=0, le=3),
    min_rr_ratio: float = Query(default=2.0, gt=0),
    pairs: Optional[str] = Query(
        default=None,
        description="Comma-separated pair list. Defaults to watchlist.",
    ),
    check_status: bool = Query(
        default=True,
        description="Check data status before scanning (returns actionable errors)",
    ),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Scan multiple pairs for MTF-aligned trading opportunities.

    **Internal Market Database Architecture:**
    1. All data reads from ohlcv_universal table (read-only, no live API calls).
    2. Checks market_data_status for data quality before scanning.
    3. If GOOD/EXCELLENT: Loads OHLCV from ohlcv_universal → scans immediately.
    4. If STALE/MISSING: Reports in `data_issues` with refresh suggestion.
    5. Prefetch job (every hour at :10) keeps ohlcv_universal fresh.

    **Response includes:**
    - `opportunities`: Pairs that pass filters (alignment + R:R).
    - `all_results`: All scanned pairs (including those that didn't pass).
    - `data_issues`: Pairs with stale/missing data (for UI to show refresh button).
    - `summary`: Scan statistics.

    **Example:**
        GET /api/v1/mtf/opportunities?trading_style=SWING&check_status=true
    """
    try:
        style = TradingStyle[trading_style.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trading_style '{trading_style}'. "
                   f"Valid: POSITION, SWING, INTRADAY, DAY, SCALPING",
        )

    config = MTFTimeframeConfig.get_config(style)
    pair_list = [p.strip() for p in pairs.split(",")] if pairs else get_watchlist(db)

    # Initialize services
    scanner = MTFOpportunityScanner(
        min_alignment=min_alignment,
        min_rr_ratio=min_rr_ratio,
        trading_style=style,
    )
    market_data_service = MarketDataService(db)
    
    # Check data status if requested
    data_issues = []
    ready_pairs = []
    
    if check_status:
        for pair in pair_list:
            is_ready, quality, missing = _check_data_status(pair, config, market_data_service)
            if is_ready:
                ready_pairs.append(pair)
            else:
                data_issues.append({
                    "pair": pair,
                    "overall_quality": quality,
                    "missing_timeframes": missing,
                    "recommendation": f"Refresh required - {len(missing)} timeframe(s) need update",
                })
                # Still try to scan if some data exists (may partially succeed)
                if quality != "MISSING":
                    ready_pairs.append(pair)  # Try anyway
    else:
        ready_pairs = pair_list
    
    # Run scan on ready pairs (using ohlcv_universal - read-only)
    all_results = _run_scan_from_universal(ready_pairs, config, db, scanner)
    opportunities = [r for r in all_results if r["passes_filters"]]
    high_conviction = sum(1 for r in opportunities if r["alignment_score"] == 3)

    for opp in opportunities:
        if opp["alignment_score"] == 3:
            send_mtf_opportunity_alert(
                pair=opp["pair"],
                quality=opp["quality"],
                alignment_score=opp["alignment_score"],
                recommendation=opp["recommendation"],
                entry_price=opp.get("entry_price"),
                stop_loss=opp.get("stop_loss"),
                target_price=opp.get("target_price"),
                rr_ratio=opp.get("rr_ratio", 0.0),
                patterns=opp.get("patterns"),
                divergence=opp.get("divergence"),
                trading_style=style.value,
            )

    logger.info(
        f"MTF scan complete: style={style.value}, "
        f"{len(opportunities)}/{len(all_results)} pairs qualify"
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "trading_style": style.value,
        "timeframes": {
            "htf": config.htf_timeframe,
            "mtf": config.mtf_timeframe,
            "ltf": config.ltf_timeframe,
        },
        "filters": {"min_alignment": min_alignment, "min_rr_ratio": min_rr_ratio},
        "opportunities": opportunities,
        "all_results": all_results,
        "data_issues": data_issues if check_status else [],
        "summary": {
            "total_requested": len(pair_list),
            "pairs_scanned": len(all_results),
            "pairs_no_data": len(pair_list) - len(all_results),
            "pairs_with_issues": len(data_issues),
            "opportunities_found": len(opportunities),
            "high_conviction": high_conviction,
        },
    }


@router.get(
    "/opportunities/{pair}",
    response_model=Dict[str, Any],
    summary="Detailed MTF analysis for one pair",
)
def get_pair_analysis(
    pair: str,
    trading_style: str = Query(default="SWING"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Full MTF analysis for a single pair: bias, setup, entry, patterns,
    divergence, key S/R levels.
    """
    try:
        style = TradingStyle[trading_style.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trading_style: {trading_style}",
        )

    config = MTFTimeframeConfig.get_config(style)
    cache_mgr = OHLCVCacheManager(db)
    data = _load_pair_data(pair, config, cache_mgr)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"No OHLCV data available for {pair}. "
                "The MTF prefetch job runs every 2 hours at :20 and will "
                "populate the cache — try again after the next prefetch run."
            ),
        )

    scanner = MTFOpportunityScanner(trading_style=style)
    try:
        scan_result = scanner.scan_pair_detailed(
            pair=pair,
            htf_data=data["htf"],
            mtf_data=data["mtf"],
            ltf_data=data["ltf"],
        )
    except Exception as exc:
        logger.error(f"Analysis failed for {pair}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        )

    return {
        "pair": pair,
        "timestamp": datetime.utcnow().isoformat(),
        "trading_style": style.value,
        "timeframes": {
            "htf": config.htf_timeframe,
            "mtf": config.mtf_timeframe,
            "ltf": config.ltf_timeframe,
        },
        "analysis": scan_result.alignment.to_dict(),
        "patterns": scan_result.patterns,
        "divergence": scan_result.divergence.to_dict() if scan_result.divergence else None,
        "key_levels": [
            {
                "price": lvl.price,
                "type": lvl.level_type.value,
                "strength": lvl.strength.value,
            }
            for lvl in scan_result.key_levels
        ],
        "passes_filters": scan_result.passes_filters,
    }


@router.get(
    "/configs",
    response_model=Dict[str, Any],
    summary="Available MTF timeframe configurations",
)
def get_timeframe_configs() -> Dict[str, Any]:
    """Return all trading-style → timeframe mappings."""
    return {
        "configs": MTFTimeframeConfig.get_all_configs(),
        "description": {
            "htf": "Higher Timeframe — directional bias (50/200 SMA, price structure)",
            "mtf": "Middle Timeframe — setup identification (pullback, divergence)",
            "ltf": "Lower Timeframe — entry timing (candlestick patterns, EMA reclaim)",
        },
    }


@router.post(
    "/scan",
    response_model=Dict[str, Any],
    summary="On-demand scan with custom pairs",
)
def trigger_mtf_scan(
    request: Dict[str, Any],
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Trigger an on-demand MTF scan with a custom pair list.

    Body: {"pairs": ["BTC/USDT"], "trading_style": "SWING",
           "min_alignment": 2, "min_rr_ratio": 2.0}
    """
    pair_list = request.get("pairs", DEFAULT_MTF_WATCHLIST)
    trading_style = request.get("trading_style", "SWING")
    min_alignment = request.get("min_alignment", 2)
    min_rr_ratio = request.get("min_rr_ratio", 2.0)

    try:
        style = TradingStyle[trading_style.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trading_style: {trading_style}",
        )

    config = MTFTimeframeConfig.get_config(style)
    cache_mgr = OHLCVCacheManager(db)
    scanner = MTFOpportunityScanner(
        min_alignment=min_alignment,
        min_rr_ratio=min_rr_ratio,
        trading_style=style,
    )

    all_results = _run_scan(pair_list, config, cache_mgr, scanner)
    opportunities = [r for r in all_results if r["passes_filters"]]

    for opp in opportunities:
        if opp["alignment_score"] == 3:
            send_mtf_opportunity_alert(
                pair=opp["pair"],
                quality=opp["quality"],
                alignment_score=opp["alignment_score"],
                recommendation=opp["recommendation"],
                entry_price=opp.get("entry_price"),
                stop_loss=opp.get("stop_loss"),
                target_price=opp.get("target_price"),
                rr_ratio=opp.get("rr_ratio", 0.0),
                patterns=opp.get("patterns"),
                divergence=opp.get("divergence"),
                trading_style=style.value,
            )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "trading_style": style.value,
        "opportunities": opportunities,
        "summary": {
            "total_scanned": len(all_results),
            "opportunities_found": len(opportunities),
        },
    }


@router.get(
    "/watchlist",
    response_model=Dict[str, Any],
    summary="List MTF watchlist pairs",
)
def list_watchlist(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """Return all pairs in the MTF scanner watchlist (seeds defaults if empty)."""
    items = db.query(MTFWatchlistItem).order_by(MTFWatchlistItem.added_at).all()
    if not items:
        pairs = get_watchlist(db)  # seeds and returns defaults
        items = db.query(MTFWatchlistItem).order_by(MTFWatchlistItem.added_at).all()
    return {
        "watchlist": [item.to_dict() for item in items],
        "count": len(items),
    }


@router.post(
    "/watchlist",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add a pair to the MTF watchlist",
)
def add_to_watchlist(
    request: Dict[str, Any],
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Add a trading pair to the MTF watchlist.

    Body: {"pair": "SOL/USDT", "notes": "optional"}
    """
    pair = request.get("pair", "").strip().upper()
    if not pair:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'pair' field is required",
        )

    existing = db.query(MTFWatchlistItem).filter(MTFWatchlistItem.pair == pair).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{pair} is already in the watchlist",
        )

    item = MTFWatchlistItem(
        pair=pair,
        notes=request.get("notes"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info(f"Watchlist: added {pair}")
    return {"added": item.to_dict()}


@router.delete(
    "/watchlist/{pair:path}",
    response_model=Dict[str, Any],
    summary="Remove a pair from the MTF watchlist",
)
def remove_from_watchlist(
    pair: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Remove a trading pair from the MTF watchlist."""
    pair = pair.strip().upper()
    item = db.query(MTFWatchlistItem).filter(MTFWatchlistItem.pair == pair).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{pair} not found in watchlist",
        )
    db.delete(item)
    db.commit()
    logger.info(f"Watchlist: removed {pair}")
    return {"removed": pair}
