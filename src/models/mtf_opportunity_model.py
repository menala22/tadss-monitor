"""
MTF Opportunity Model for TA-DSS.

This module provides the database model for storing MTF trading opportunities
identified by the hourly automated scanning system.

The model stores all opportunities from the upgraded 4-layer MTF framework:
- Layer 1: MTF Context Classification (ADX, ATR, EMA distance)
- Layer 2: Context-Gated Setup Detection
- Layer 3: Pullback Quality Scoring (5 factors)
- Layer 4: Weighted Alignment + Position Sizing

Usage:
    from src.models.mtf_opportunity_model import MTFOpportunity

    # Create opportunity
    opp = MTFOpportunity(
        pair='BTC/USDT',
        htf_bias='BULLISH',
        mtf_context='TRENDING_PULLBACK',
        weighted_score=0.78,
        ...
    )
    db.add(opp)
    db.commit()
"""

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, Float, Integer, String, Text,
    Index, text
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MTFOpportunity(Base):
    """
    MTF Trading Opportunity - stores opportunities from hourly scans.

    This table stores all trading opportunities identified by the automated
    MTF scanning system running every hour at :30.

    Architecture:
    - HTF Bias determines trend direction (BULLISH/BEARISH/NEUTRAL)
    - MTF Context refines entry timing within that trend
    - Layer 1-4 fields store upgraded framework metrics
    - Legacy fields (alignment_score, quality) kept for compatibility

    Table Structure:
    - id: Primary key
    - pair: Trading pair (e.g., 'BTC/USDT', 'XAU/USD')
    - timestamp: When opportunity was identified
    - trading_style: POSITION/SWING/INTRADAY/DAY/SCALPING
    - htf_bias: HTF direction (determines trend)
    - mtf_context: Context classification (Layer 1)
    - context_adx, context_distance_atr: Context metrics (Layer 1)
    - pullback_quality_*: Quality scores (Layer 3)
    - weighted_score, position_size_pct: Alignment metrics (Layer 4)
    - quality, alignment_score: Legacy fields (compatibility)
    - recommendation, mtf_setup, ltf_entry: Trade signals
    - entry_price, stop_loss, target_price, rr_ratio: Trade parameters
    - patterns: JSON array of detected patterns
    - divergence: Divergence type if detected
    - status: ACTIVE/CLOSED/EXPIRED
    - closed_at: When opportunity was closed
    - notes: Additional analysis notes

    Indexes:
    - idx_opp_pair: For pair filtering
    - idx_opp_status: For status filtering
    - idx_opp_timestamp: For time-range queries
    - idx_opp_weighted_score: For quality filtering
    - idx_opp_context: For context filtering
    - idx_opp_htf_bias: For trend direction filtering

    Example:
        # Create opportunity
        opp = MTFOpportunity(
            pair='BTC/USDT',
            timestamp=datetime.utcnow(),
            trading_style='SWING',
            htf_bias='BULLISH',
            mtf_context='TRENDING_PULLBACK',
            context_adx=28.5,
            context_distance_atr=0.8,
            weighted_score=0.78,
            position_size_pct=100.0,
            pullback_quality_score=0.82,
            pullback_distance_score=1.0,
            pullback_rsi_score=0.8,
            pullback_volume_score=1.0,
            pullback_confluence_score=0.5,
            pullback_structure_score=0.8,
            quality='HIGHEST',
            alignment_score=3,
            recommendation='BUY',
            mtf_setup='PULLBACK',
            ltf_entry='ENGULFING',
            entry_price=67500.0,
            stop_loss=65800.0,
            target_price=72900.0,
            rr_ratio=3.2,
            status='ACTIVE'
        )
        db.add(opp)
        db.commit()

        # Query active opportunities
        opps = db.query(MTFOpportunity).filter(
            MTFOpportunity.status == 'ACTIVE',
            MTFOpportunity.weighted_score >= 0.60
        ).order_by(
            MTFOpportunity.weighted_score.desc()
        ).all()
    """

    __tablename__ = 'mtf_opportunities'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic identification
    pair = Column(String(20), nullable=False, index=True)  # e.g., 'BTC/USDT'
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    trading_style = Column(String(20), nullable=False)  # POSITION/SWING/INTRADAY/DAY/SCALPING

    # HTF Bias - determines trend direction
    htf_bias = Column(String(20), nullable=False, index=True)  # BULLISH/BEARISH/NEUTRAL

    # Layer 1: Context Classification
    mtf_context = Column(String(30), nullable=False, index=True)  # TRENDING_PULLBACK, etc.
    context_adx = Column(Float, nullable=False)  # ADX value
    context_distance_atr = Column(Float, nullable=False)  # Distance from EMA in ATR units

    # Layer 3: Pullback Quality Scoring (5 factors)
    pullback_quality_score = Column(Float, nullable=True)  # Total score 0.0-1.0
    pullback_distance_score = Column(Float, nullable=True)  # 25% weight
    pullback_rsi_score = Column(Float, nullable=True)  # 20% weight
    pullback_volume_score = Column(Float, nullable=True)  # 25% weight
    pullback_confluence_score = Column(Float, nullable=True)  # 20% weight
    pullback_structure_score = Column(Float, nullable=True)  # 10% weight

    # Layer 4: Weighted Alignment
    weighted_score = Column(Float, nullable=False, index=True)  # 0.0-1.0
    position_size_pct = Column(Float, nullable=True)  # % of base risk

    # Legacy fields (kept for backward compatibility)
    quality = Column(String(20), nullable=False)  # HIGHEST/GOOD/POOR/AVOID
    alignment_score = Column(Integer, nullable=False)  # 0-3 binary score

    # Trade signals
    recommendation = Column(String(10), nullable=False)  # BUY/SELL/WAIT/AVOID
    mtf_setup = Column(String(20), nullable=False)  # PULLBACK/BREAKOUT/etc.
    ltf_entry = Column(String(20), nullable=False)  # ENGULFING/HAMMER/etc.

    # Trade parameters
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    target_method = Column(String(20), nullable=True)  # S/R, MEASURED_MOVE, FIBONACCI, ATR, PRIOR_SWING
    rr_ratio = Column(Float, nullable=False, default=0.0)
    
    # LTF Entry timestamp (timestamp of confirmation candle)
    entry_timestamp = Column(DateTime, nullable=True)

    # Alternative targets (JSON)
    alternative_targets = Column(Text, nullable=True)  # JSON with all target methods

    # Additional data
    patterns = Column(Text, nullable=True)  # JSON array of detected patterns
    divergence = Column(String(50), nullable=True)  # Divergence type if detected

    # Lifecycle management
    status = Column(String(20), nullable=False, default='ACTIVE', index=True)  # ACTIVE/CLOSED/EXPIRED
    closed_at = Column(DateTime, nullable=True)  # When closed
    notes = Column(Text, nullable=True)  # Additional notes

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_opp_pair', 'pair'),
        Index('idx_opp_status', 'status'),
        Index('idx_opp_timestamp', 'timestamp'),
        Index('idx_opp_weighted_score', 'weighted_score'),
        Index('idx_opp_context', 'mtf_context'),
        Index('idx_opp_htf_bias', 'htf_bias'),
        Index('idx_opp_trading_style', 'trading_style'),
        Index('idx_opp_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MTFOpportunity(id={self.id}, pair='{self.pair}', "
            f"htf_bias='{self.htf_bias}', context='{self.mtf_context}', "
            f"weighted_score={self.weighted_score:.2f}, status='{self.status}')>"
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API response.

        Returns:
            Dictionary with all opportunity fields.
        """
        import json

        return {
            'id': self.id,
            'pair': self.pair,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'trading_style': self.trading_style,
            'htf_bias': self.htf_bias,
            'mtf_context': self.mtf_context,
            'context_adx': round(self.context_adx, 2) if self.context_adx else None,
            'context_distance_atr': round(self.context_distance_atr, 2) if self.context_distance_atr else None,
            'pullback_quality': {
                'total_score': round(self.pullback_quality_score, 2) if self.pullback_quality_score else None,
                'distance_score': round(self.pullback_distance_score, 2) if self.pullback_distance_score else None,
                'rsi_score': round(self.pullback_rsi_score, 2) if self.pullback_rsi_score else None,
                'volume_score': round(self.pullback_volume_score, 2) if self.pullback_volume_score else None,
                'confluence_score': round(self.pullback_confluence_score, 2) if self.pullback_confluence_score else None,
                'structure_score': round(self.pullback_structure_score, 2) if self.pullback_structure_score else None,
            },
            'weighted_score': round(self.weighted_score, 2) if self.weighted_score else None,
            'position_size_pct': round(self.position_size_pct, 2) if self.position_size_pct else None,
            'legacy_fields': {
                'quality': self.quality,
                'alignment_score': self.alignment_score,
            },
            'recommendation': self.recommendation,
            'mtf_setup': self.mtf_setup,
            'ltf_entry': self.ltf_entry,
            'entry_price': round(self.entry_price, 5) if self.entry_price else None,
            'stop_loss': round(self.stop_loss, 5) if self.stop_loss else None,
            'entry_timestamp': self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            'target_price': round(self.target_price, 5) if self.target_price else None,
            'target_method': self.target_method,
            'alternative_targets': json.loads(self.alternative_targets) if self.alternative_targets else {},
            'rr_ratio': round(self.rr_ratio, 2) if self.rr_ratio else None,
            'patterns': json.loads(self.patterns) if self.patterns else [],
            'divergence': self.divergence,
            'status': self.status,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_summary_dict(self) -> dict:
        """
        Convert to summary dictionary for list views.

        Returns:
            Dictionary with key fields including pullback quality and target info.
        """
        import json
        
        return {
            'id': self.id,
            'pair': self.pair,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'trading_style': self.trading_style,
            'htf_bias': self.htf_bias,
            'mtf_context': self.mtf_context,
            'weighted_score': round(self.weighted_score, 2) if self.weighted_score else None,
            'position_size_pct': round(self.position_size_pct, 2) if self.position_size_pct else None,
            'quality': self.quality,
            'alignment_score': self.alignment_score,
            'recommendation': self.recommendation,
            'mtf_setup': self.mtf_setup,
            'ltf_entry': self.ltf_entry,
            # Pullback quality scores
            'pullback_quality_score': round(self.pullback_quality_score, 2) if self.pullback_quality_score else None,
            'pullback_distance_score': round(self.pullback_distance_score, 2) if self.pullback_distance_score else None,
            'pullback_rsi_score': round(self.pullback_rsi_score, 2) if self.pullback_rsi_score else None,
            'pullback_volume_score': round(self.pullback_volume_score, 2) if self.pullback_volume_score else None,
            'pullback_confluence_score': round(self.pullback_confluence_score, 2) if self.pullback_confluence_score else None,
            'pullback_structure_score': round(self.pullback_structure_score, 2) if self.pullback_structure_score else None,
            # Target info
            'entry_price': round(self.entry_price, 5) if self.entry_price else None,
            'stop_loss': round(self.stop_loss, 5) if self.stop_loss else None,
            'entry_timestamp': self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            'target_price': round(self.target_price, 5) if self.target_price else None,
            'target_method': self.target_method,
            'rr_ratio': round(self.rr_ratio, 2) if self.rr_ratio else None,
            # Alternative targets (JSON)
            'alternative_targets': json.loads(self.alternative_targets) if self.alternative_targets else {},
            # Divergence and patterns
            'divergence': self.divergence,
            'patterns': json.loads(self.patterns) if self.patterns else [],
            'status': self.status,
        }


def create_mtf_opportunities_table(engine) -> None:
    """
    Create the MTF opportunities table if it doesn't exist.

    Args:
        engine: SQLAlchemy engine instance.

    Example:
        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///./data/positions.db')
        create_mtf_opportunities_table(engine)
    """
    MTFOpportunity.metadata.create_all(bind=engine, checkfirst=True)


def migrate_add_mtf_opportunities_table(db_session) -> None:
    """
    Migration function to add MTF opportunities table to existing database.

    Args:
        db_session: SQLAlchemy session or engine.
    """
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    if 'mtf_opportunities' in inspector.get_table_names():
        return  # Table already exists

    MTFOpportunity.metadata.create_all(bind=db_session.bind)
