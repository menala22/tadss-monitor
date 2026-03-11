"""
Migration: Add target_method and alternative_targets columns to mtf_opportunities table.

Usage:
    python -m src.migrations.migrate_opportunity_target_columns
"""

import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def run_migration(db_session, verbose: bool = True) -> bool:
    """
    Add target_method and alternative_targets columns.
    
    Args:
        db_session: SQLAlchemy session.
        verbose: If True, print status messages.
    
    Returns:
        True if migration was successful.
    """
    try:
        inspector = inspect(db_session.bind)
        
        # Check if table exists
        if 'mtf_opportunities' not in inspector.get_table_names():
            if verbose:
                logger.warning("mtf_opportunities table does not exist")
            return False
        
        # Check which columns exist
        columns = [col['name'] for col in inspector.get_columns('mtf_opportunities')]
        
        columns_to_add = []
        if 'target_method' not in columns:
            columns_to_add.append('target_method VARCHAR(20)')
        if 'alternative_targets' not in columns:
            columns_to_add.append('alternative_targets TEXT')
        
        if not columns_to_add:
            if verbose:
                logger.info("Migration skipped: columns already exist")
            return True
        
        if verbose:
            logger.info(f"Running migration: add columns {columns_to_add}")
        
        # Add columns
        for col_def in columns_to_add:
            col_name = col_def.split()[0]
            db_session.execute(
                text(f"ALTER TABLE mtf_opportunities ADD COLUMN {col_def}")
            )
            if verbose:
                logger.info(f"  ✓ Added column: {col_name}")
        
        db_session.commit()
        
        if verbose:
            logger.info("✓ Migration completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    import sys
    from src.database import get_db_context
    
    print("MTF Opportunities Target Columns Migration")
    print("=" * 50)
    
    with get_db_context() as db:
        success = run_migration(db, verbose=True)
        if success:
            print("\n✓ Migration completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Migration failed")
            sys.exit(1)
