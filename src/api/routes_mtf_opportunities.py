"""
MTF Opportunities API Routes.

Endpoints for managing MTF trading opportunities identified by the hourly
automated scanning system.

Endpoints:
  GET    /api/v1/mtf-opportunities          - List all opportunities
  GET    /api/v1/mtf-opportunities/active   - List active only
  GET    /api/v1/mtf-opportunities/stats    - Statistics
  GET    /api/v1/mtf-opportunities/{id}     - Get single opportunity
  POST   /api/v1/mtf-opportunities/{id}/close - Close opportunity
  DELETE /api/v1/mtf-opportunities/{id}     - Delete opportunity

Usage:
    # List active opportunities with minimum weighted score
    curl "http://localhost:8000/api/v1/mtf-opportunities?status=ACTIVE&min_weighted_score=0.60"

    # Get statistics
    curl "http://localhost:8000/api/v1/mtf-opportunities/stats"

    # Close opportunity
    curl -X POST "http://localhost:8000/api/v1/mtf-opportunities/123/close"
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.auth import verify_api_key
from src.database import get_db_session
from src.models.mtf_opportunity_model import MTFOpportunity
from src.services.mtf_opportunity_service import MTFOpportunityService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mtf-opportunities",
    tags=["mtf-opportunities"],
    dependencies=[Depends(verify_api_key)],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _get_service(db: Session) -> MTFOpportunityService:
    """Get opportunity service instance."""
    return MTFOpportunityService(db)


def _format_opportunity_list(opportunities: List[MTFOpportunity]) -> List[Dict[str, Any]]:
    """Format opportunities for list response (summary view)."""
    return [opp.to_summary_dict() for opp in opportunities]


def _format_opportunity_detail(opportunity: MTFOpportunity) -> Dict[str, Any]:
    """Format opportunity for detail response (full view)."""
    return opportunity.to_dict()


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List MTF opportunities",
)
def list_opportunities(
    pair: Optional[str] = Query(default=None, description="Filter by trading pair"),
    trading_style: Optional[str] = Query(default=None, description="Filter by trading style"),
    mtf_context: Optional[str] = Query(default=None, description="Filter by MTF context"),
    htf_bias: Optional[str] = Query(default=None, description="Filter by HTF bias"),
    min_weighted_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum weighted score filter",
    ),
    min_rr_ratio: Optional[float] = Query(
        default=None,
        gt=0,
        description="Minimum R:R ratio filter",
    ),
    status: Optional[str] = Query(
        default="ACTIVE",
        description="Filter by status (ACTIVE/CLOSED/EXPIRED/ALL)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    List MTF opportunities with optional filters.

    **Filters:**
    - `pair`: Trading pair (e.g., BTC/USDT)
    - `trading_style`: POSITION/SWING/INTRADAY/DAY/SCALPING
    - `mtf_context`: TRENDING_PULLBACK/TRENDING_EXTENSION/BREAKING_OUT/etc.
    - `htf_bias`: BULLISH/BEARISH/NEUTRAL
    - `min_weighted_score`: Minimum 0.0-1.0 (recommended: 0.60)
    - `min_rr_ratio`: Minimum R:R ratio (recommended: 2.0)
    - `status`: ACTIVE/CLOSED/EXPIRED/ALL (default: ACTIVE)

    **Pagination:**
    - `limit`: 1-200 (default: 50)
    - `offset`: For pagination (default: 0)

    **Example:**
        GET /api/v1/mtf-opportunities?status=ACTIVE&min_weighted_score=0.60&limit=20
    """
    service = _get_service(db)

    # Handle "ALL" status
    status_filter = None if status == "ALL" else status

    opportunities = service.get_active_opportunities(
        pair=pair,
        trading_style=trading_style,
        mtf_context=mtf_context,
        htf_bias=htf_bias,
        min_weighted_score=min_weighted_score,
        min_rr_ratio=min_rr_ratio,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    # Get total count (for pagination)
    total_query = db.query(MTFOpportunity)
    if pair:
        total_query = total_query.filter(MTFOpportunity.pair == pair)
    if status_filter:
        total_query = total_query.filter(MTFOpportunity.status == status_filter)
    total = total_query.count()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "opportunities": _format_opportunity_list(opportunities),
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(opportunities) < total,
        },
        "filters": {
            "pair": pair,
            "trading_style": trading_style,
            "mtf_context": mtf_context,
            "htf_bias": htf_bias,
            "min_weighted_score": min_weighted_score,
            "min_rr_ratio": min_rr_ratio,
            "status": status,
        },
    }


@router.get(
    "/active",
    response_model=Dict[str, Any],
    summary="List active MTF opportunities",
)
def list_active_opportunities(
    min_weighted_score: float = Query(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Minimum weighted score (default: 0.60)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    List only active MTF opportunities.

    Shortcut for `/mtf-opportunities?status=ACTIVE&min_weighted_score=0.60`.

    **Example:**
        GET /api/v1/mtf-opportunities/active?min_weighted_score=0.75
    """
    service = _get_service(db)

    opportunities = service.get_active_opportunities(
        status="ACTIVE",
        min_weighted_score=min_weighted_score,
        limit=limit,
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "opportunities": _format_opportunity_list(opportunities),
        "count": len(opportunities),
        "filters": {
            "status": "ACTIVE",
            "min_weighted_score": min_weighted_score,
        },
    }


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get MTF opportunities statistics",
)
def get_statistics(
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get MTF opportunities statistics.

    Returns:
    - Total opportunities by status
    - Distribution by HTF bias
    - Distribution by recommendation
    - Weighted score metrics
    - High conviction count
    - Today's opportunities

    **Example:**
        GET /api/v1/mtf-opportunities/stats
    """
    service = _get_service(db)
    stats = service.get_statistics()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": stats,
    }


@router.get(
    "/{opportunity_id}",
    response_model=Dict[str, Any],
    summary="Get MTF opportunity by ID",
)
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get single opportunity by ID.

    Returns full opportunity details including:
    - All 4-layer framework fields
    - Pullback quality scores
    - Patterns and divergence
    - Trade parameters

    **Example:**
        GET /api/v1/mtf-opportunities/123
    """
    service = _get_service(db)
    opportunity = service.get_opportunity_by_id(opportunity_id)

    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "opportunity": _format_opportunity_detail(opportunity),
    }


@router.post(
    "/{opportunity_id}/close",
    response_model=Dict[str, Any],
    summary="Close MTF opportunity",
)
def close_opportunity(
    opportunity_id: int,
    reason: str = Query(
        default="MANUAL",
        description="Reason for closing (MANUAL/TARGET_HIT/STOP_HIT/INVALID)",
    ),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Close an opportunity manually.

    **Reasons:**
    - `MANUAL`: User manually closed
    - `TARGET_HIT`: Target price reached
    - `STOP_HIT`: Stop loss hit
    - `INVALID`: Opportunity was invalid

    **Example:**
        POST /api/v1/mtf-opportunities/123/close?reason=TARGET_HIT
    """
    service = _get_service(db)

    # Check if exists
    opportunity = service.get_opportunity_by_id(opportunity_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )

    # Check if already closed
    if opportunity.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Opportunity {opportunity_id} is already {opportunity.status}",
        )

    # Close
    success = service.close_opportunity(opportunity_id, reason=reason)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close opportunity",
        )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "message": f"Opportunity {opportunity_id} closed",
        "opportunity": {
            "id": opportunity_id,
            "pair": opportunity.pair,
            "status": "CLOSED",
            "reason": reason,
        },
    }


@router.delete(
    "/{opportunity_id}",
    response_model=Dict[str, Any],
    summary="Delete MTF opportunity",
)
def delete_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Delete an opportunity permanently.

    WARNING: This action cannot be undone.

    **Example:**
        DELETE /api/v1/mtf-opportunities/123
    """
    service = _get_service(db)

    # Check if exists
    opportunity = service.get_opportunity_by_id(opportunity_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )

    # Delete
    try:
        db.delete(opportunity)
        db.commit()

        logger.info(f"Deleted opportunity {opportunity_id} ({opportunity.pair})")

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Opportunity {opportunity_id} deleted",
            "opportunity": {
                "id": opportunity_id,
                "pair": opportunity.pair,
            },
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete opportunity {opportunity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete opportunity: {e}",
        )


@router.get(
    "/pairs/list",
    response_model=Dict[str, Any],
    summary="List pairs with opportunities",
)
def list_pairs_with_opportunities(
    status: str = Query(default="ACTIVE", description="Filter by status"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get list of unique pairs with opportunities.

    Useful for building filter dropdowns in the UI.

    **Example:**
        GET /api/v1/mtf-opportunities/pairs/list?status=ACTIVE
    """
    service = _get_service(db)
    pairs = service.get_pairs_with_opportunities(status=status)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "pairs": sorted(pairs),
        "count": len(pairs),
        "status": status,
    }
