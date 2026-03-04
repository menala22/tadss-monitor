"""
Migration script to create signal_changes table.

This script adds the signal_changes table to track all MA10 and OTT
status changes for detailed signal analysis and backtesting.

Usage:
    python -m src.migrations.migrate_signal_changes
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import inspect

from src.database import db_manager
from src.models.signal_change_model import SignalChange, SignalType, SignalStatus


def migrate_add_signal_changes_table(database_url: str = None, verbose: bool = True) -> bool:
    """
    Create signal_changes table if it doesn't exist.

    This migration is safe to run multiple times - it will skip creation
    if the table already exists.

    Args:
        database_url: Database connection URL. Defaults to settings.
        verbose: If True, print status messages.

    Returns:
        True if migration was successful, False otherwise.
    """
    from src.config import settings
    
    db_url = database_url or settings.database_url

    try:
        engine = db_manager.engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "signal_changes" in tables:
            if verbose:
                print("✓ signal_changes table already exists")
            return True

        if verbose:
            print(f"Creating signal_changes table in: {db_url}")

        # Create the table
        SignalChange.metadata.create_all(bind=engine)

        if verbose:
            print("✓ signal_changes table created successfully")
            
            # Verify creation
            tables = inspect(engine).get_table_names()
            if "signal_changes" in tables:
                print("✓ Table verified in database")
                
                # Print column info
                columns = inspect(engine).get_columns("signal_changes")
                print(f"✓ Columns: {', '.join([c['name'] for c in columns])}")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def run_all_signal_migrations(database_url: str = None, verbose: bool = True) -> bool:
    """
    Run all signal-related migrations.

    Args:
        database_url: Database connection URL. Defaults to settings.
        verbose: If True, print status messages.

    Returns:
        True if all migrations succeeded, False otherwise.
    """
    if verbose:
        print("=" * 60)
        print("Running Signal Changes Migration")
        print("=" * 60)

    success = True

    if verbose:
        print("\n[1/1] Signal Changes Table Migration")
        print("-" * 40)
    
    if not migrate_add_signal_changes_table(database_url, verbose):
        success = False

    if verbose:
        print("\n" + "=" * 60)
        if success:
            print("✓ Migration completed successfully")
        else:
            print("✗ Migration failed")
        print("=" * 60)

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run signal changes migration")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="Database URL (defaults to settings.database_url)"
    )
    args = parser.parse_args()

    success = run_all_signal_migrations(
        database_url=args.database_url,
        verbose=not args.quiet
    )

    sys.exit(0 if success else 1)
