"""
Migration: Add trading_styles column to mtf_watchlist table

This migration adds the trading_styles column to store multiple trading styles
per pair (e.g., "SWING,INTRADAY,DAY").

Run: python -m src.migrations.migrate_mtf_watchlist_trading_styles run
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_context
from sqlalchemy import text


def run_migration():
    """Add trading_styles column to mtf_watchlist table."""
    print("MTF Watchlist - trading_styles Column Migration")
    print("=" * 50)
    
    with get_db_context() as db:
        # Check if column already exists
        try:
            result = db.execute(text("SELECT trading_styles FROM mtf_watchlist LIMIT 1"))
            print("✓ Column 'trading_styles' already exists")
            return
        except Exception as e:
            if "no such column" in str(e) or "Unknown column" in str(e):
                print("Column 'trading_styles' does not exist - creating...")
            else:
                raise
        
        # Add column
        print("Adding 'trading_styles' column to mtf_watchlist table...")
        db.execute(text("""
            ALTER TABLE mtf_watchlist 
            ADD COLUMN trading_styles VARCHAR(50) DEFAULT 'SWING'
        """))
        db.commit()
        
        print("✓ Column added successfully")
        
        # Update existing rows to have 'SWING' as default
        db.execute(text("""
            UPDATE mtf_watchlist 
            SET trading_styles = 'SWING' 
            WHERE trading_styles IS NULL
        """))
        db.commit()
        
        print("✓ Existing rows updated with default value 'SWING'")
        
        # Show statistics
        result = db.execute(text("SELECT COUNT(*) FROM mtf_watchlist"))
        count = result.scalar()
        
        result = db.execute(text("""
            SELECT trading_styles, COUNT(*) as count 
            FROM mtf_watchlist 
            GROUP BY trading_styles
        """))
        style_counts = result.fetchall()
        
        print("\nTable Statistics:")
        print(f"  Total pairs: {count}")
        print("  By trading styles:")
        for styles, cnt in style_counts:
            print(f"    {styles or 'NULL'}: {cnt}")
        
        print("\n✓ Migration completed successfully")


def rollback():
    """Rollback: Remove trading_styles column."""
    print("Rolling back migration...")
    
    with get_db_context() as db:
        # Note: SQLite doesn't support DROP COLUMN in older versions
        # This rollback may not work on all SQLite versions
        try:
            db.execute(text("ALTER TABLE mtf_watchlist DROP COLUMN trading_styles"))
            db.commit()
            print("✓ Rollback completed")
        except Exception as e:
            print(f"⚠ Rollback failed: {e}")
            print("  SQLite may not support DROP COLUMN")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        run_migration()
