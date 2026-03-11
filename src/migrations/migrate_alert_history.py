"""
Migration script to create alert_history table.

This script adds the alert_history table to the existing database
for tracking all Telegram alerts sent by the system.

Usage:
    python -m src.migrations.migrate_alert_history
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import inspect, text

from src.database import db_manager
from src.models.alert_model import AlertHistory, AlertType, AlertStatus


def migrate_add_alert_history_table(database_url: str = None, verbose: bool = True) -> bool:
    """
    Create alert_history table if it doesn't exist.

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

        if "alert_history" in tables:
            if verbose:
                print("✓ alert_history table already exists")
            return True

        if verbose:
            print(f"Creating alert_history table in: {db_url}")

        # Create the table
        AlertHistory.metadata.create_all(bind=engine)

        if verbose:
            print("✓ alert_history table created successfully")
            
            # Verify creation
            tables = inspect(engine).get_table_names()
            if "alert_history" in tables:
                print("✓ Table verified in database")
                
                # Print column info
                columns = inspect(engine).get_columns("alert_history")
                print(f"✓ Columns: {', '.join([c['name'] for c in columns])}")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def migrate_add_ma10_ott_columns(database_url: str = None, verbose: bool = True) -> bool:
    """
    Add MA10 and OTT tracking columns to positions table.

    This migration adds separate columns for tracking MA10 and OTT status
    independently, allowing for more granular alert triggering.

    Args:
        database_url: Database connection URL. Defaults to settings.
        verbose: If True, print status messages.

    Returns:
        True if migration was successful (or columns already exist), False otherwise.
    """
    from src.config import settings
    
    db_url = database_url or settings.database_url

    try:
        engine = db_manager.engine
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("positions")]

        with engine.connect() as conn:
            if "last_ma10_status" not in columns:
                conn.execute(text(
                    "ALTER TABLE positions ADD COLUMN last_ma10_status VARCHAR(20)"
                ))
                if verbose:
                    print("✓ Added last_ma10_status column")

            if "last_ott_status" not in columns:
                conn.execute(text(
                    "ALTER TABLE positions ADD COLUMN last_ott_status VARCHAR(20)"
                ))
                if verbose:
                    print("✓ Added last_ott_status column")

            conn.commit()

        if verbose and "last_ma10_status" not in columns or "last_ott_status" not in columns:
            print("✓ Position columns migration completed")
        elif verbose:
            print("✓ Position columns already up-to-date")

        return True

    except Exception as e:
        print(f"✗ Position columns migration failed: {e}")
        return False


def run_all_migrations(database_url: str = None, verbose: bool = True) -> bool:
    """
    Run all pending migrations.

    Args:
        database_url: Database connection URL. Defaults to settings.
        verbose: If True, print status messages.

    Returns:
        True if all migrations succeeded, False otherwise.
    """
    if verbose:
        print("=" * 60)
        print("Running Database Migrations")
        print("=" * 60)

    success = True

    # Migration 1: Alert history table
    if verbose:
        print("\n[1/2] Alert History Table Migration")
        print("-" * 40)
    if not migrate_add_alert_history_table(database_url, verbose):
        success = False

    # Migration 2: MA10/OTT columns
    if verbose:
        print("\n[2/2] Position Columns Migration")
        print("-" * 40)
    if not migrate_add_ma10_ott_columns(database_url, verbose):
        success = False

    if verbose:
        print("\n" + "=" * 60)
        if success:
            print("✓ All migrations completed successfully")
        else:
            print("✗ Some migrations failed")
        print("=" * 60)

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run database migrations")
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

    success = run_all_migrations(
        database_url=args.database_url,
        verbose=not args.quiet
    )

    sys.exit(0 if success else 1)
