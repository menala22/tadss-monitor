"""
Migration: Add MTF Opportunities Table

This migration creates the mtf_opportunities table for storing
automated MTF scanning opportunities.

The table stores all opportunities from the upgraded 4-layer MTF framework:
- Layer 1: MTF Context Classification (ADX, ATR, EMA distance)
- Layer 2: Context-Gated Setup Detection
- Layer 3: Pullback Quality Scoring (5 factors)
- Layer 4: Weighted Alignment + Position Sizing

Usage:
    # Run migration
    python -m src.migrations.migrate_mtf_opportunities

    # Or import in code
    from src.migrations.migrate_mtf_opportunities import run_migration
    from src.database import get_db_context

    with get_db_context() as db:
        run_migration(db)
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import inspect

logger = logging.getLogger(__name__)


def check_migration_status(db_session) -> dict:
    """
    Check current migration status for MTF opportunities table.

    Args:
        db_session: SQLAlchemy session.

    Returns:
        Dictionary with migration status.
    """
    inspector = inspect(db_session.bind)
    table_exists = 'mtf_opportunities' in inspector.get_table_names()

    return {
        'table_exists': table_exists,
        'migration_name': 'migrate_mtf_opportunities',
        'status': 'completed' if table_exists else 'pending',
        'tables': inspector.get_table_names(),
    }


def run_migration(db_session, verbose: bool = True) -> bool:
    """
    Run migration to create MTF opportunities table.

    This function is idempotent - safe to run multiple times.

    Args:
        db_session: SQLAlchemy session.
        verbose: If True, print status messages.

    Returns:
        True if migration was successful (or already completed).
    """
    try:
        # Check if table already exists
        inspector = inspect(db_session.bind)
        if 'mtf_opportunities' in inspector.get_table_names():
            if verbose:
                logger.info("Migration skipped: mtf_opportunities table already exists")
            return True

        if verbose:
            logger.info("Running migration: create mtf_opportunities table")

        # Import model to ensure it's registered with Base metadata
        from src.models.mtf_opportunity_model import MTFOpportunity

        # Create table
        MTFOpportunity.metadata.create_all(bind=db_session.bind)

        if verbose:
            logger.info("✓ Migration completed: mtf_opportunities table created")

        # Verify creation
        inspector = inspect(db_session.bind)
        if 'mtf_opportunities' in inspector.get_table_names():
            if verbose:
                logger.info("✓ Table verified: mtf_opportunities exists")

                # Print table info
                columns = inspector.get_columns('mtf_opportunities')
                logger.info(f"✓ Columns: {len(columns)}")

                indexes = inspector.get_indexes('mtf_opportunities')
                logger.info(f"✓ Indexes: {len(indexes)}")

            return True
        else:
            logger.error("✗ Migration failed: table not found after creation")
            return False

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def rollback_migration(db_session, verbose: bool = True) -> bool:
    """
    Rollback migration by dropping MTF opportunities table.

    WARNING: This will delete all data in the table.

    Args:
        db_session: SQLAlchemy session.
        verbose: If True, print status messages.

    Returns:
        True if rollback was successful.
    """
    try:
        inspector = inspect(db_session.bind)
        if 'mtf_opportunities' not in inspector.get_table_names():
            if verbose:
                logger.info("Rollback skipped: mtf_opportunities table does not exist")
            return True

        if verbose:
            logger.warning("Rolling back migration: dropping mtf_opportunities table")
            logger.warning("WARNING: All data in mtf_opportunities will be deleted!")

        # Drop table
        from src.models.mtf_opportunity_model import MTFOpportunity
        MTFOpportunity.metadata.drop_all(bind=db_session.bind)

        if verbose:
            logger.info("✓ Rollback completed: mtf_opportunities table dropped")

        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return False


def verify_migration(db_session, verbose: bool = True) -> dict:
    """
    Verify migration was successful and table structure is correct.

    Args:
        db_session: SQLAlchemy session.
        verbose: If True, print status messages.

    Returns:
        Dictionary with verification results.
    """
    inspector = inspect(db_session.bind)

    results = {
        'table_exists': False,
        'columns_correct': False,
        'indexes_correct': False,
        'verified': False,
        'issues': [],
    }

    # Check table exists
    if 'mtf_opportunities' not in inspector.get_table_names():
        results['issues'].append("Table 'mtf_opportunities' does not exist")
        if verbose:
            logger.error("✗ Verification failed: table does not exist")
        return results

    results['table_exists'] = True

    # Check columns
    expected_columns = {
        'id', 'pair', 'timestamp', 'trading_style',
        'htf_bias',
        'mtf_context', 'context_adx', 'context_distance_atr',
        'pullback_quality_score', 'pullback_distance_score', 'pullback_rsi_score',
        'pullback_volume_score', 'pullback_confluence_score', 'pullback_structure_score',
        'weighted_score', 'position_size_pct',
        'quality', 'alignment_score',
        'recommendation', 'mtf_setup', 'ltf_entry',
        'entry_price', 'stop_loss', 'target_price', 'rr_ratio',
        'patterns', 'divergence',
        'status', 'closed_at', 'notes',
        'created_at', 'updated_at',
    }

    actual_columns = {col['name'] for col in inspector.get_columns('mtf_opportunities')}

    missing_columns = expected_columns - actual_columns
    extra_columns = actual_columns - expected_columns

    if missing_columns:
        results['issues'].append(f"Missing columns: {missing_columns}")
    if extra_columns:
        results['issues'].append(f"Extra columns: {extra_columns}")

    results['columns_correct'] = len(missing_columns) == 0

    # Check indexes
    indexes = inspector.get_indexes('mtf_opportunities')
    index_names = {idx['name'] for idx in indexes}

    expected_indexes = {
        'idx_opp_pair',
        'idx_opp_status',
        'idx_opp_timestamp',
        'idx_opp_weighted_score',
        'idx_opp_context',
        'idx_opp_htf_bias',
    }

    missing_indexes = expected_indexes - index_names
    if missing_indexes:
        results['issues'].append(f"Missing indexes: {missing_indexes}")

    results['indexes_correct'] = len(missing_indexes) == 0

    # Overall verification
    results['verified'] = (
        results['table_exists'] and
        results['columns_correct']
    )

    if verbose:
        if results['verified']:
            logger.info("✓ Verification passed: mtf_opportunities table is correct")
        else:
            logger.error(f"✗ Verification failed: {results['issues']}")

    return results


def get_table_stats(db_session) -> dict:
    """
    Get statistics about MTF opportunities table.

    Args:
        db_session: SQLAlchemy session.

    Returns:
        Dictionary with table statistics.
    """
    from src.models.mtf_opportunity_model import MTFOpportunity
    from sqlalchemy import func

    try:
        # Total opportunities
        total = db_session.query(func.count(MTFOpportunity.id)).scalar()

        # By status
        active = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'ACTIVE'
        ).scalar()

        closed = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'CLOSED'
        ).scalar()

        expired = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.status == 'EXPIRED'
        ).scalar()

        # By HTF bias
        bullish = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.htf_bias == 'BULLISH'
        ).scalar()

        bearish = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.htf_bias == 'BEARISH'
        ).scalar()

        # Average weighted score
        avg_weighted = db_session.query(func.avg(MTFOpportunity.weighted_score)).scalar()

        # High conviction (weighted >= 0.75)
        high_conviction = db_session.query(func.count(MTFOpportunity.id)).filter(
            MTFOpportunity.weighted_score >= 0.75
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
            'avg_weighted_score': round(avg_weighted, 2) if avg_weighted else None,
            'high_conviction': high_conviction,
        }

    except Exception as e:
        logger.error(f"Failed to get table stats: {e}")
        return {
            'total': 0,
            'error': str(e),
        }


# CLI entry point
if __name__ == '__main__':
    import sys
    from src.database import get_db_context

    print("MTF Opportunities Table Migration")
    print("=" * 40)

    command = sys.argv[1] if len(sys.argv) > 1 else 'run'

    with get_db_context() as db:
        if command == 'status':
            # Check migration status
            status = check_migration_status(db)
            print(f"\nMigration: {status['migration_name']}")
            print(f"Status: {status['status']}")
            print(f"Table exists: {status['table_exists']}")

        elif command == 'run':
            # Run migration
            success = run_migration(db, verbose=True)
            if success:
                print("\n✓ Migration completed successfully")
                sys.exit(0)
            else:
                print("\n✗ Migration failed")
                sys.exit(1)

        elif command == 'verify':
            # Verify migration
            results = verify_migration(db, verbose=True)
            if results['verified']:
                print("\n✓ Verification passed")

                # Show stats
                stats = get_table_stats(db)
                print(f"\nTable Statistics:")
                print(f"  Total opportunities: {stats['total']}")
                print(f"  Active: {stats['by_status']['active']}")
                print(f"  High conviction: {stats['high_conviction']}")
                if stats['avg_weighted_score']:
                    print(f"  Avg weighted score: {stats['avg_weighted_score']}")
                sys.exit(0)
            else:
                print(f"\n✗ Verification failed: {results['issues']}")
                sys.exit(1)

        elif command == 'rollback':
            # Rollback (with confirmation)
            confirm = input("\nWARNING: This will delete all data in mtf_opportunities table.\nAre you sure? [y/N]: ")
            if confirm.lower() == 'y':
                success = rollback_migration(db, verbose=True)
                if success:
                    print("\n✓ Rollback completed successfully")
                    sys.exit(0)
                else:
                    print("\n✗ Rollback failed")
                    sys.exit(1)
            else:
                print("\nRollback cancelled")
                sys.exit(0)

        elif command == 'stats':
            # Show statistics
            stats = get_table_stats(db)
            print(f"\nTable Statistics:")
            print(f"  Total opportunities: {stats['total']}")
            print(f"  By status:")
            print(f"    Active: {stats['by_status']['active']}")
            print(f"    Closed: {stats['by_status']['closed']}")
            print(f"    Expired: {stats['by_status']['expired']}")
            print(f"  By HTF bias:")
            print(f"    Bullish: {stats['by_bias']['bullish']}")
            print(f"    Bearish: {stats['by_bias']['bearish']}")
            print(f"    Neutral: {stats['by_bias']['neutral']}")
            if stats['avg_weighted_score']:
                print(f"  Average weighted score: {stats['avg_weighted_score']}")
            print(f"  High conviction (≥0.75): {stats['high_conviction']}")
            sys.exit(0)

        else:
            print(f"\nUnknown command: {command}")
            print("\nUsage: python -m src.migrations.migrate_mtf_opportunities [command]")
            print("\nCommands:")
            print("  run      - Run migration (create table)")
            print("  verify   - Verify migration")
            print("  status   - Check migration status")
            print("  stats    - Show table statistics")
            print("  rollback - Rollback migration (drop table)")
            sys.exit(1)
