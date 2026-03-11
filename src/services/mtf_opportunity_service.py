"""
MTF Opportunity Service for TA-DSS.

This service handles all database operations for MTF trading opportunities,
including saving, querying, filtering, and lifecycle management.

The service uses the upgraded 4-layer MTF framework for filtering:
- Layer 1: MTF Context Classification
- Layer 2: Context-Gated Setup Detection
- Layer 3: Pullback Quality Scoring
- Layer 4: Weighted Alignment

Usage:
    from src.services.mtf_opportunity_service import MTFOpportunityService

    service = MTFOpportunityService(db)

    # Save opportunity
    opp = service.save_opportunity(
        pair='BTC/USDT',
        alignment=alignment,
        trading_style='SWING',
        patterns=['HTF Trend + MTF Pullback'],
    )

    # Get active opportunities
    opportunities = service.get_active_opportunities(
        min_weighted_score=0.60,
        limit=50
    )
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.mtf_opportunity_model import MTFOpportunity
from src.models.mtf_models import (
    MTFAlignment,
    MTFDirection,
    MTFContext,
    TradingStyle,
    Recommendation,
)

logger = logging.getLogger(__name__)


class MTFOpportunityService:
    """
    Service for managing MTF trading opportunities.

    Handles:
    - Saving opportunities from hourly scans
    - Querying with filters (pair, context, weighted score, etc.)
    - Lifecycle management (close, expire)
    - Statistics and reporting

    Attributes:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session):
        """
        Initialize opportunity service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def save_opportunity(
        self,
        pair: str,
        alignment: MTFAlignment,
        trading_style: TradingStyle,
        patterns: Optional[List[str]] = None,
        divergence: Optional[str] = None,
        notes: Optional[str] = None,
        htf_data=None,  # Optional: HTF DataFrame for target calculation
        mtf_data=None,  # Optional: MTF DataFrame for target calculation
    ) -> MTFOpportunity:
        """
        Save new opportunity to database with deduplication logic.

        Hybrid approach:
        1. Check for similar ACTIVE opportunity (same pair, style, recommendation)
        2. If found and meaningful change → Update existing
        3. If found and no meaningful change → Return existing (skip save)
        4. If not found → Check for opposite recommendation, close it, create new

        Maps upgraded 4-layer MTF framework fields to database model:
        - HTF bias (trend direction)
        - Layer 1: MTF context, ADX, ATR distance
        - Layer 3: Pullback quality scores (5 factors)
        - Layer 4: Weighted score, position size
        - Legacy fields: alignment_score, quality

        Args:
            pair: Trading pair (e.g., 'BTC/USDT').
            alignment: MTF alignment object from scanner.
            trading_style: Trading style used for scan.
            patterns: List of detected patterns.
            divergence: Divergence type if detected.
            notes: Additional analysis notes.
            htf_data: Optional HTF DataFrame for calculating alternative targets.
            mtf_data: Optional MTF DataFrame for calculating alternative targets.

        Returns:
            Saved or updated MTFOpportunity database object.

        Example:
            >>> alignment = mtf_scanner.analyze_pair(...)
            >>> opp = service.save_opportunity(
            ...     pair='BTC/USDT',
            ...     alignment=alignment,
            ...     trading_style=TradingStyle.SWING,
            ... )
            >>> print(f"Saved: {opp.pair} - weighted={opp.weighted_score:.2f}")
        """
        # Extract key fields for deduplication
        recommendation_str = alignment.recommendation.value
        trading_style_str = trading_style.value
        
        # Skip if recommendation is not actionable
        if recommendation_str not in ("BUY", "SELL"):
            logger.debug(f"Skipping non-actionable recommendation: {recommendation_str}")
            return None
        
        # Step 1: Check for similar ACTIVE opportunity
        existing = self._find_similar_opportunity(
            pair=pair,
            trading_style=trading_style_str,
            recommendation=recommendation_str,
            status='ACTIVE',
            max_age_hours=24,
        )
        
        if existing:
            # Step 2: Check if meaningful change
            if self._is_meaningful_change(existing, alignment):
                # Update existing opportunity
                self._update_opportunity(existing, alignment, patterns, divergence, notes, htf_data, mtf_data)
                logger.info(f"Updated opportunity {existing.id} for {pair} ({trading_style_str})")
                return existing
            else:
                # No meaningful change, skip save
                logger.debug(f"No meaningful change for {pair} ({trading_style_str}), skipping save")
                return existing
        
        # Step 3: No similar opportunity found
        # Check if opposite recommendation exists → close it
        opposite_rec = "SELL" if recommendation_str == "BUY" else "BUY"
        self._close_opportunities(
            pair=pair,
            trading_style=trading_style_str,
            recommendation=opposite_rec,
            reason="SIGNAL_REVERSED",
        )
        
        # Create new opportunity
        opp = self._create_opportunity(
            pair=pair,
            alignment=alignment,
            trading_style=trading_style,
            patterns=patterns,
            divergence=divergence,
            notes=notes,
        )
        
        self.db.add(opp)
        self.db.commit()
        
        # Calculate and save alternative targets if HTF/MTF data provided
        if htf_data is not None and mtf_data is not None and opp.entry_price and opp.stop_loss:
            try:
                from src.services.target_calculator import calculate_all_targets
                
                direction = "LONG" if opp.recommendation == "BUY" else "SHORT"
                
                alt_targets = calculate_all_targets(
                    df_htf=htf_data,
                    df_mtf=mtf_data,
                    entry_price=opp.entry_price,
                    stop_loss=opp.stop_loss,
                    direction=direction,
                )
                
                opp.alternative_targets = json.dumps(alt_targets)
                self.db.commit()
                
                logger.debug(f"Calculated {len(alt_targets)} alternative targets for {opp.pair}")
                
            except Exception as e:
                logger.warning(f"Failed to calculate alternative targets for {opp.pair}: {e}")
        
        self.db.refresh(opp)

        logger.info(
            f"Saved MTF opportunity: {opp.pair} {opp.htf_bias} "
            f"context={opp.mtf_context} weighted={opp.weighted_score:.2f}"
        )

        return opp

    def _find_similar_opportunity(
        self,
        pair: str,
        trading_style: str,
        recommendation: str,
        status: str = 'ACTIVE',
        max_age_hours: int = 24,
    ) -> Optional[MTFOpportunity]:
        """
        Find similar active opportunity for deduplication.

        Args:
            pair: Trading pair.
            trading_style: Trading style.
            recommendation: BUY or SELL.
            status: Opportunity status to match.
            max_age_hours: Maximum age in hours.

        Returns:
            Matching MTFOpportunity or None.
        """
        from sqlalchemy import and_

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        return self.db.query(MTFOpportunity).filter(
            and_(
                MTFOpportunity.pair == pair,
                MTFOpportunity.trading_style == trading_style,
                MTFOpportunity.recommendation == recommendation,
                MTFOpportunity.status == status,
                MTFOpportunity.timestamp >= cutoff,
            )
        ).order_by(
            MTFOpportunity.timestamp.desc()
        ).first()

    def _is_meaningful_change(
        self,
        existing: MTFOpportunity,
        alignment: MTFAlignment,
    ) -> bool:
        """
        Check if new alignment represents meaningful change from existing.

        Thresholds:
        - Weighted score changed by > 0.10
        - Context changed
        - R:R changed by > 0.5
        - Target price changed by > 2%

        Args:
            existing: Existing opportunity.
            alignment: New alignment.

        Returns:
            True if meaningful change.
        """
        # Check weighted score change
        if abs(existing.weighted_score - alignment.weighted_score) > 0.10:
            return True

        # Check context change
        if existing.mtf_context != alignment.mtf_setup.mtf_context.value:
            return True

        # Check R:R change
        if abs(existing.rr_ratio - alignment.rr_ratio) > 0.5:
            return True

        # Check target price change (if both have targets)
        if existing.target_price and alignment.target and alignment.target.target_price:
            target_change_pct = abs(existing.target_price - alignment.target.target_price) / existing.target_price
            if target_change_pct > 0.02:  # 2%
                return True

        return False  # No meaningful change

    def _update_opportunity(
        self,
        opp: MTFOpportunity,
        alignment: MTFAlignment,
        patterns: Optional[List[str]],
        divergence: Optional[str],
        notes: Optional[str],
        htf_data=None,
        mtf_data=None,
    ):
        """
        Update existing opportunity with new data.

        Args:
            opp: Opportunity to update.
            alignment: New alignment data.
            patterns: Detected patterns.
            divergence: Divergence type.
            notes: Additional notes.
            htf_data: Optional HTF DataFrame.
            mtf_data: Optional MTF DataFrame.
        """
        # Update fields
        opp.weighted_score = alignment.weighted_score
        opp.position_size_pct = alignment.position_size_pct
        opp.quality = alignment.quality.value
        opp.alignment_score = alignment.alignment_score
        opp.rr_ratio = alignment.rr_ratio

        if alignment.target:
            opp.target_price = alignment.target.target_price
            opp.target_method = alignment.target.method.value if alignment.target.method else None

        # Update context if changed
        if alignment.mtf_setup.mtf_context_result:
            opp.mtf_context = alignment.mtf_setup.mtf_context_result.context.value
            opp.context_adx = alignment.mtf_setup.mtf_context_result.adx
            opp.context_distance_atr = alignment.mtf_setup.mtf_context_result.distance_from_ema_atr

        # Update pullback quality
        if alignment.mtf_setup.pullback_quality_score:
            opp.pullback_quality_score = alignment.mtf_setup.pullback_quality_score.total_score
            opp.pullback_distance_score = alignment.mtf_setup.pullback_quality_score.distance_score
            opp.pullback_rsi_score = alignment.mtf_setup.pullback_quality_score.rsi_score
            opp.pullback_volume_score = alignment.mtf_setup.pullback_quality_score.volume_score
            opp.pullback_confluence_score = alignment.mtf_setup.pullback_quality_score.confluence_score
            opp.pullback_structure_score = alignment.mtf_setup.pullback_quality_score.structure_score

        # Update patterns and divergence
        if patterns:
            opp.patterns = json.dumps(patterns)
        if divergence:
            opp.divergence = divergence
        if notes:
            opp.notes = f"{opp.notes or ''} [Updated: {notes}]"

        opp.updated_at = datetime.utcnow()

        # Recalculate alternative targets if data provided
        if htf_data is not None and mtf_data is not None and opp.entry_price and opp.stop_loss:
            try:
                from src.services.target_calculator import calculate_all_targets

                direction = "LONG" if opp.recommendation == "BUY" else "SHORT"

                alt_targets = calculate_all_targets(
                    df_htf=htf_data,
                    df_mtf=mtf_data,
                    entry_price=opp.entry_price,
                    stop_loss=opp.stop_loss,
                    direction=direction,
                )

                opp.alternative_targets = json.dumps(alt_targets)

            except Exception as e:
                logger.warning(f"Failed to recalculate alternative targets: {e}")

    def _create_opportunity(
        self,
        pair: str,
        alignment: MTFAlignment,
        trading_style: TradingStyle,
        patterns: Optional[List[str]],
        divergence: Optional[str],
        notes: Optional[str],
    ) -> MTFOpportunity:
        """
        Create new opportunity object.

        Args:
            pair: Trading pair.
            alignment: MTF alignment.
            trading_style: Trading style.
            patterns: Detected patterns.
            divergence: Divergence type.
            notes: Additional notes.

        Returns:
            New MTFOpportunity object (not yet added to DB).
        """
        # Extract HTF bias direction
        htf_bias_str = alignment.htf_bias.direction.value

        # Extract MTF context
        mtf_context_result = alignment.mtf_setup.mtf_context_result
        if mtf_context_result:
            mtf_context_str = mtf_context_result.context.value
            context_adx = mtf_context_result.adx
            context_distance_atr = mtf_context_result.distance_from_ema_atr
        else:
            mtf_context_str = alignment.mtf_setup.mtf_context.value if alignment.mtf_setup.mtf_context else 'CONSOLIDATING'
            context_adx = 0.0
            context_distance_atr = 0.0

        # Extract pullback quality scores
        pullback_quality = alignment.mtf_setup.pullback_quality_score
        if pullback_quality:
            pullback_quality_score = pullback_quality.total_score
            pullback_distance_score = pullback_quality.distance_score
            pullback_rsi_score = pullback_quality.rsi_score
            pullback_volume_score = pullback_quality.volume_score
            pullback_confluence_score = pullback_quality.confluence_score
            pullback_structure_score = pullback_quality.structure_score
        else:
            pullback_quality_score = None
            pullback_distance_score = None
            pullback_rsi_score = None
            pullback_volume_score = None
            pullback_confluence_score = None
            pullback_structure_score = None

        return MTFOpportunity(
            pair=pair,
            timestamp=datetime.utcnow(),
            trading_style=trading_style.value,
            htf_bias=htf_bias_str,
            mtf_context=mtf_context_str,
            context_adx=context_adx,
            context_distance_atr=context_distance_atr,
            pullback_quality_score=pullback_quality_score,
            pullback_distance_score=pullback_distance_score,
            pullback_rsi_score=pullback_rsi_score,
            pullback_volume_score=pullback_volume_score,
            pullback_confluence_score=pullback_confluence_score,
            pullback_structure_score=pullback_structure_score,
            weighted_score=alignment.weighted_score,
            position_size_pct=alignment.position_size_pct,
            quality=alignment.quality.value,
            alignment_score=alignment.alignment_score,
            recommendation=alignment.recommendation.value,
            mtf_setup=alignment.mtf_setup.setup_type.value,
            ltf_entry=alignment.ltf_entry.signal_type.value,
            entry_price=alignment.ltf_entry.entry_price if alignment.ltf_entry.entry_price else None,
            stop_loss=alignment.ltf_entry.stop_loss if alignment.ltf_entry.stop_loss else None,
            target_price=alignment.target.target_price if alignment.target else None,
            target_method=alignment.target.method.value if alignment.target and alignment.target.method else None,
            rr_ratio=alignment.rr_ratio,
            patterns=json.dumps(patterns) if patterns else None,
            divergence=divergence,
            status='ACTIVE',
            notes=notes,
        )

    def _close_opportunities(
        self,
        pair: str,
        trading_style: str,
        recommendation: str,
        reason: str = "MANUAL",
    ) -> int:
        """
        Close opportunities matching criteria.

        Args:
            pair: Trading pair.
            trading_style: Trading style.
            recommendation: Recommendation to match (BUY or SELL).
            reason: Reason for closing.

        Returns:
            Number of opportunities closed.
        """
        from sqlalchemy import and_

        opportunities = self.db.query(MTFOpportunity).filter(
            and_(
                MTFOpportunity.pair == pair,
                MTFOpportunity.trading_style == trading_style,
                MTFOpportunity.recommendation == recommendation,
                MTFOpportunity.status == 'ACTIVE',
            )
        ).all()

        for opp in opportunities:
            opp.status = 'CLOSED'
            opp.closed_at = datetime.utcnow()
            if opp.notes:
                opp.notes = f"{opp.notes} [Closed: {reason}]"
            else:
                opp.notes = f"Closed: {reason}"

        self.db.commit()

        if opportunities:
            logger.info(f"Closed {len(opportunities)} opportunities for {pair} ({reason})")

        return len(opportunities)

    def should_save_opportunity(self, alignment: MTFAlignment) -> bool:
        """
        Check if opportunity meets minimum criteria for saving.

        Filtering logic using upgraded 4-layer framework:
        1. HTF bias must be directional (not NEUTRAL)
        2. MTF context != TRENDING_EXTENSION (hard gate)
        3. Weighted score >= 0.50
        4. R:R ratio >= 1.0 (lowered from 2.0 to capture more opportunities)
        5. Recommendation in (BUY, SELL)

        Args:
            alignment: MTF alignment to check.

        Returns:
            True if opportunity should be saved.

        Example:
            >>> if service.should_save_opportunity(alignment):
            ...     service.save_opportunity(pair, alignment, style)
        """
        # Hard gate 1: HTF bias must be directional
        if alignment.htf_bias.direction == MTFDirection.NEUTRAL:
            return False

        # Hard gate 2: Never save TRENDING_EXTENSION setups
        if alignment.mtf_setup.mtf_context:
            if alignment.mtf_setup.mtf_context == MTFContext.TRENDING_EXTENSION:
                return False

        # Hard gate 3: Minimum weighted score
        if alignment.weighted_score < 0.50:
            return False

        # Hard gate 4: Minimum R:R ratio (lowered to 1.0)
        if alignment.rr_ratio < 1.0:
            return False

        # Hard gate 5: Valid recommendation
        if alignment.recommendation not in (Recommendation.BUY, Recommendation.SELL):
            return False

        return True

    def get_active_opportunities(
        self,
        pair: Optional[str] = None,
        trading_style: Optional[str] = None,
        mtf_context: Optional[str] = None,
        htf_bias: Optional[str] = None,
        min_weighted_score: Optional[float] = None,
        min_rr_ratio: Optional[float] = None,
        status: str = 'ACTIVE',
        limit: int = 50,
        offset: int = 0,
    ) -> List[MTFOpportunity]:
        """
        List opportunities with optional filters.

        Args:
            pair: Filter by trading pair.
            trading_style: Filter by style (SWING, INTRADAY, etc.).
            mtf_context: Filter by context (TRENDING_PULLBACK, etc.).
            htf_bias: Filter by HTF bias (BULLISH, BEARISH).
            min_weighted_score: Minimum weighted score filter.
            min_rr_ratio: Minimum R:R ratio filter.
            status: Filter by status (default: ACTIVE).
            limit: Max results to return.
            offset: Pagination offset.

        Returns:
            List of MTFOpportunity objects matching filters.

        Example:
            >>> opps = service.get_active_opportunities(
            ...     min_weighted_score=0.60,
            ...     mtf_context='TRENDING_PULLBACK',
            ...     limit=20
            ... )
        """
        query = self.db.query(MTFOpportunity)

        # Apply filters
        if pair:
            query = query.filter(MTFOpportunity.pair == pair)

        if trading_style:
            query = query.filter(MTFOpportunity.trading_style == trading_style)

        if mtf_context:
            query = query.filter(MTFOpportunity.mtf_context == mtf_context)

        if htf_bias:
            query = query.filter(MTFOpportunity.htf_bias == htf_bias)

        if min_weighted_score is not None:
            query = query.filter(MTFOpportunity.weighted_score >= min_weighted_score)

        if min_rr_ratio is not None:
            query = query.filter(MTFOpportunity.rr_ratio >= min_rr_ratio)

        if status:
            query = query.filter(MTFOpportunity.status == status)

        # Order by weighted score (highest first), then timestamp
        query = query.order_by(
            MTFOpportunity.weighted_score.desc(),
            MTFOpportunity.timestamp.desc()
        )

        # Apply pagination
        opportunities = query.offset(offset).limit(limit).all()

        return opportunities

    def get_opportunity_by_id(
        self,
        opportunity_id: int,
    ) -> Optional[MTFOpportunity]:
        """
        Get single opportunity by ID.

        Args:
            opportunity_id: Opportunity ID.

        Returns:
            MTFOpportunity object or None if not found.

        Example:
            >>> opp = service.get_opportunity_by_id(123)
            >>> if opp:
            ...     print(f"{opp.pair} - {opp.recommendation}")
        """
        return self.db.query(MTFOpportunity).filter(
            MTFOpportunity.id == opportunity_id
        ).first()

    def get_recent_opportunities(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[MTFOpportunity]:
        """
        Get opportunities from the last N hours.

        Args:
            hours: Number of hours to look back.
            limit: Max results to return.

        Returns:
            List of recent opportunities.

        Example:
            >>> recent = service.get_recent_opportunities(hours=6)
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(MTFOpportunity).filter(
            MTFOpportunity.timestamp >= cutoff
        ).order_by(
            MTFOpportunity.weighted_score.desc()
        ).limit(limit).all()

    def close_opportunity(
        self,
        opportunity_id: int,
        reason: str = 'MANUAL',
    ) -> bool:
        """
        Mark opportunity as closed.

        Args:
            opportunity_id: Opportunity ID to close.
            reason: Reason for closing (MANUAL, TARGET_HIT, STOP_HIT, etc.).

        Returns:
            True if successfully closed, False if not found.

        Example:
            >>> success = service.close_opportunity(123, reason='TARGET_HIT')
        """
        opp = self.get_opportunity_by_id(opportunity_id)
        if not opp:
            logger.warning(f"Opportunity {opportunity_id} not found")
            return False

        opp.status = 'CLOSED'
        opp.closed_at = datetime.utcnow()
        if opp.notes:
            opp.notes = f"{opp.notes} [Closed: {reason}]"
        else:
            opp.notes = f"Closed: {reason}"

        self.db.commit()

        logger.info(f"Closed opportunity {opportunity_id} ({opp.pair}) - {reason}")
        return True

    def cleanup_expired_opportunities(
        self,
        expiry_hours: int = 24,
    ) -> int:
        """
        Auto-close opportunities older than expiry_hours.

        Args:
            expiry_hours: Hours after which opportunities expire.

        Returns:
            Number of opportunities expired.

        Example:
            >>> count = service.cleanup_expired_opportunities(expiry_hours=24)
            >>> print(f"Expired {count} opportunities")
        """
        cutoff = datetime.utcnow() - timedelta(hours=expiry_hours)

        # Find expired opportunities
        expired = self.db.query(MTFOpportunity).filter(
            MTFOpportunity.status == 'ACTIVE',
            MTFOpportunity.timestamp < cutoff,
        ).all()

        # Mark as expired
        for opp in expired:
            opp.status = 'EXPIRED'
            opp.closed_at = datetime.utcnow()
            if opp.notes:
                opp.notes = f"{opp.notes} [Expired: auto-closed after {expiry_hours}h]"
            else:
                opp.notes = f"Expired: auto-closed after {expiry_hours}h"

        self.db.commit()

        if expired:
            logger.info(f"Expired {len(expired)} opportunities (older than {expiry_hours}h)")

        return len(expired)

    def get_statistics(self) -> Dict:
        """
        Get opportunity statistics.

        Returns:
            Dictionary with statistics.

        Example:
            >>> stats = service.get_statistics()
            >>> print(f"Total: {stats['total']}, Active: {stats['active']}")
        """
        from sqlalchemy import func

        # Total by status
        total = self.db.query(func.count(MTFOpportunity.id)).scalar()
        active = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()
        closed = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'CLOSED'
        ).scalar()
        expired = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'EXPIRED'
        ).scalar()

        # By HTF bias
        bullish = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.htf_bias == 'BULLISH'
        ).scalar()
        bearish = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.htf_bias == 'BEARISH'
        ).scalar()

        # By recommendation
        buy_signals = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.recommendation == 'BUY',
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()
        sell_signals = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.recommendation == 'SELL',
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()

        # Weighted score metrics
        avg_weighted = self.db.query(func.avg(MTFOpportunity.weighted_score)).filter(
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()
        max_weighted = self.db.query(func.max(MTFOpportunity.weighted_score)).filter(
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()

        # High conviction (weighted >= 0.75)
        high_conviction = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.weighted_score >= 0.75,
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()

        # Today's opportunities
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.timestamp >= today_start
        ).scalar()

        return {
            'total': total,
            'by_status': {
                'active': active,
                'closed': closed,
                'expired': expired,
            },
            'by_bias': {
                'bullish': bullish,
                'bearish': bearish,
                'neutral': total - bullish - bearish,
            },
            'by_recommendation': {
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
            },
            'weighted_score': {
                'average': round(avg_weighted, 2) if avg_weighted else None,
                'maximum': round(max_weighted, 2) if max_weighted else None,
            },
            'high_conviction': high_conviction,
            'today_count': today_count,
        }

    def get_pairs_with_opportunities(
        self,
        status: str = 'ACTIVE',
    ) -> List[str]:
        """
        Get list of unique pairs with opportunities.

        Args:
            status: Filter by status.

        Returns:
            List of unique pair symbols.

        Example:
            >>> pairs = service.get_pairs_with_opportunities()
        """
        results = self.db.query(
            MTFOpportunity.pair
        ).filter(
            MTFOpportunity.status == status
        ).distinct().all()

        return [r[0] for r in results]


def get_opportunity_service(db: Session) -> MTFOpportunityService:
    """
    Get opportunity service instance.

    Convenience function for dependency injection.

    Args:
        db: SQLAlchemy database session.

    Returns:
        MTFOpportunityService instance.
    """
    return MTFOpportunityService(db)
