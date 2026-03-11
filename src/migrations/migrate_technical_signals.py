"""
Migration: Add Technical Signals Table (Option 2 Implementation)

This migration creates the technical_signals table for pre-calculated signals
and the ohlcv_with_signals VIEW for easy querying.

Usage:
    python -m src.migrations.migrate_technical_signals

Or programmatically:
    from src.migrations.migrate_technical_signals import run_migration
    from src.database import get_db_context
    
    with get_db_context() as db:
        run_migration(db)
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from src.database import get_db_context
from src.models.technical_signal_model import TechnicalSignal, create_technical_signals_table, create_ohlcv_with_signals_view

logger = logging.getLogger(__name__)

# Migration version
VERSION = '1.0'


def run_migration(db: Session) -> bool:
    """
    Run the technical signals table migration.

    Args:
        db: Database session.

    Returns:
        True if migration succeeded, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("Migration: Add Technical Signals Table")
    logger.info("=" * 60)

    try:
        # Check if table already exists
        inspector = inspect(db.bind)
        if 'technical_signals' in inspector.get_table_names():
            logger.info("✓ Table 'technical_signals' already exists")
            
            # Check if VIEW exists
            view_exists = db.execute(text(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='ohlcv_with_signals'"
            )).fetchone()
            
            if not view_exists:
                logger.info("Creating VIEW 'ohlcv_with_signals'...")
                create_ohlcv_with_signals_view(db.bind)
                logger.info("✓ VIEW created successfully")
            else:
                logger.info("✓ VIEW 'ohlcv_with_signals' already exists")
            
            return True

        # Create table
        logger.info("Creating table 'technical_signals'...")
        create_technical_signals_table(db.bind)
        logger.info("✓ Table created successfully")

        # Create VIEW
        logger.info("Creating VIEW 'ohlcv_with_signals'...")
        create_ohlcv_with_signals_view(db.bind)
        logger.info("✓ VIEW created successfully")

        # Optional: Backfill signals for existing OHLCV data
        logger.info("Checking if backfill is needed...")
        backfill_count = backfill_signals(db)
        
        if backfill_count > 0:
            logger.info(f"✓ Backfilled {backfill_count} signals")
        else:
            logger.info("✓ No backfill needed (no OHLCV data yet)")

        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        return False


def backfill_signals(db: Session, limit_per_pair: int = 100) -> int:
    """
    Backfill signals for existing OHLCV data.

    This calculates signals for all existing OHLCV candles that don't
    have signals yet.

    Args:
        db: Database session.
        limit_per_pair: Number of candles to calculate per symbol/timeframe.

    Returns:
        Number of signals backfilled.
    """
    from src.models.ohlcv_universal_model import OHLCVUniversal
    from src.services.technical_signal_calculator import TechnicalSignalCalculator

    try:
        # Get distinct symbol/timeframe pairs
        pairs = db.query(
            OHLCVUniversal.symbol,
            OHLCVUniversal.timeframe,
        ).distinct().all()

        if not pairs:
            logger.info("No OHLCV data found - skipping backfill")
            return 0

        logger.info(f"Found {len(pairs)} symbol/timeframe pairs to backfill")

        calculator = TechnicalSignalCalculator(db, version=VERSION)
        total_backfilled = 0

        for symbol, timeframe in pairs:
            # Check if signals already exist
            existing_count = db.query(TechnicalSignal).filter(
                TechnicalSignal.symbol == symbol,
                TechnicalSignal.timeframe == timeframe,
            ).count()

            if existing_count > 0:
                logger.debug(f"Skipping {symbol} {timeframe} - {existing_count} signals already exist")
                continue

            # Calculate and save signals
            logger.info(f"Backfilling {symbol} {timeframe}...")
            count = calculator.calculate_and_save_for_pair(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit_per_pair,
            )

            if count > 0:
                total_backfilled += count
                logger.info(f"  ✓ Backfilled {count} signals for {symbol} {timeframe}")

        return total_backfilled

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        return 0


def rollback_migration(db: Session) -> bool:
    """
    Rollback the migration (drop table and VIEW).

    WARNING: This will delete all signal data!

    Args:
        db: Database session.

    Returns:
        True if rollback succeeded, False otherwise.
    """
    logger.warning("Rolling back technical signals migration...")
    logger.warning("WARNING: This will delete all signal data!")

    try:
        # Drop VIEW
        db.execute(text("DROP VIEW IF EXISTS ohlcv_with_signals"))
        logger.info("✓ VIEW dropped")

        # Drop table
        db.execute(text("DROP TABLE IF EXISTS technical_signals"))
        logger.info("✓ Table dropped")

        db.commit()
        logger.info("Rollback completed successfully")

        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        db.rollback()
        return False


def verify_migration(db: Session) -> dict:
    """
    Verify the migration was successful.

    Args:
        db: Database session.

    Returns:
        Dictionary with verification results.
    """
    from src.models.ohlcv_universal_model import OHLCVUniversal

    results = {
        'table_exists': False,
        'view_exists': False,
        'signal_count': 0,
        'ohlcv_count': 0,
        'coverage_pct': 0.0,
    }

    try:
        # Check table exists
        inspector = inspect(db.bind)
        results['table_exists'] = 'technical_signals' in inspector.get_table_names()

        # Check VIEW exists
        view_exists = db.execute(text(
            "SELECT name FROM sqlite_master WHERE type='view' AND name='ohlcv_with_signals'"
        )).fetchone()
        results['view_exists'] = view_exists is not None

        # Count signals
        results['signal_count'] = db.query(TechnicalSignal).count()

        # Count OHLCV candles
        results['ohlcv_count'] = db.query(OHLCVUniversal).count()

        # Calculate coverage
        if results['ohlcv_count'] > 0:
            results['coverage_pct'] = (results['signal_count'] / results['ohlcv_count']) * 100

        return results

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return results


if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )

    with get_db_context() as db:
        success = run_migration(db)

        if success:
            print("\n✓ Migration completed successfully!")
            
            # Verify
            results = verify_migration(db)
            print(f"\nVerification:")
            print(f"  Table exists: {results['table_exists']}")
            print(f"  VIEW exists: {results['view_exists']}")
            print(f"  Signals: {results['signal_count']}")
            print(f"  OHLCV candles: {results['ohlcv_count']}")
            print(f"  Coverage: {results['coverage_pct']:.1f}%")
        else:
            print("\n✗ Migration failed!")
            sys.exit(1)
