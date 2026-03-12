"""
Migration: Add entry_timestamp column to mtf_opportunities table.

This adds tracking for the LTF confirmation candle timestamp.

Usage:
    python -m src.migrations.migrate_ltf_entry_timestamp run
    python -m src.migrations.migrate_ltf_entry_timestamp rollback
    python -m src.migrations.migrate_ltf_entry_timestamp stats
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database import get_db_context


def run_migration():
    """Add entry_timestamp column to mtf_opportunities table."""
    with get_db_context() as db:
        # Check if column already exists
        result = db.execute(text("""
            SELECT name FROM pragma_table_info('mtf_opportunities') 
            WHERE name='entry_timestamp'
        """))
        if result.fetchone():
            print("✓ Column 'entry_timestamp' already exists, skipping migration")
            return
        
        # Add column
        db.execute(text("""
            ALTER TABLE mtf_opportunities 
            ADD COLUMN entry_timestamp DATETIME
        """))
        db.commit()
        print("✓ Added 'entry_timestamp' column to mtf_opportunities table")


def rollback_migration():
    """Rollback: Remove entry_timestamp column (SQLite doesn't support DROP COLUMN directly)."""
    print("⚠ SQLite does not support DROP COLUMN. Column will remain but unused.")
    print("  To fully remove, recreate the table without the column.")


def show_stats():
    """Show statistics about entry_timestamp column."""
    with get_db_context() as db:
        # Count total opportunities
        result = db.execute(text("""
            SELECT COUNT(*) FROM mtf_opportunities
        """))
        total = result.fetchone()[0]
        
        # Count opportunities with entry_timestamp
        result = db.execute(text("""
            SELECT COUNT(*) FROM mtf_opportunities
            WHERE entry_timestamp IS NOT NULL
        """))
        with_timestamp = result.fetchone()[0]
        
        # Show sample data
        result = db.execute(text("""
            SELECT pair, ltf_entry, entry_price, entry_timestamp 
            FROM mtf_opportunities 
            WHERE entry_timestamp IS NOT NULL 
            ORDER BY entry_timestamp DESC
            LIMIT 5
        """))
        samples = result.fetchall()
        
        print(f"\n📊 Entry Timestamp Statistics:")
        print(f"  Total opportunities: {total}")
        print(f"  With entry_timestamp: {with_timestamp} ({with_timestamp/total*100:.1f}% if total > 0 else 0)")
        
        if samples:
            print(f"\n📋 Recent entries with timestamps:")
            for row in samples:
                print(f"  {row[0]}: {row[1]} @ {row[2]} ({row[3]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_ltf_entry_timestamp.py [run|rollback|stats]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "run":
        run_migration()
    elif command == "rollback":
        rollback_migration()
    elif command == "stats":
        show_stats()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python migrate_ltf_entry_timestamp.py [run|rollback|stats]")
        sys.exit(1)
