"""
Migration: Add trading_styles column to mtf_watchlist table.

This migration adds support for multiple trading styles per pair.

Usage:
    python -m src.migrations.migrate_watchlist_trading_styles
"""

import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def run_migration(db_session, verbose: bool = True) -> bool:
    """
    Add trading_styles column to mtf_watchlist table.
    
    Args:
        db_session: SQLAlchemy session.
        verbose: If True, print status messages.
    
    Returns:
        True if migration was successful.
    """
    try:
        inspector = inspect(db_session.bind)
        
        # Check if column already exists
        if 'mtf_watchlist' not in inspector.get_table_names():
            if verbose:
                logger.warning("mtf_watchlist table does not exist, creating it first")
            from src.models.mtf_watchlist_model import create_mtf_watchlist_table
            create_mtf_watchlist_table(db_session.bind)
        
        # Check if column exists
        columns = [col['name'] for col in inspector.get_columns('mtf_watchlist')]
        
        if 'trading_styles' in columns:
            if verbose:
                logger.info("Migration skipped: trading_styles column already exists")
            return True
        
        if verbose:
            logger.info("Running migration: add trading_styles column to mtf_watchlist")
        
        # Add column (SQLite doesn't support ADD COLUMN with default, so we use ALTER TABLE)
        db_session.execute(
            text("ALTER TABLE mtf_watchlist ADD COLUMN trading_styles VARCHAR DEFAULT 'SWING'")
        )
        db_session.commit()
        
        if verbose:
            logger.info("✓ Migration completed: trading_styles column added")
            logger.info("✓ Default value: 'SWING' (backward compatible)")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    import sys
    from src.database import get_db_context
    
    print("MTF Watchlist Trading Styles Migration")
    print("=" * 40)
    
    with get_db_context() as db:
        success = run_migration(db, verbose=True)
        if success:
            print("\n✓ Migration completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Migration failed")
            sys.exit(1)
