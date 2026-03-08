#!/usr/bin/env python3
"""
Phase 5: Cleanup Old ohlcv_cache Table

This script safely removes the legacy ohlcv_cache table after verifying:
1. ohlcv_universal is populated and has more/better data
2. MTF scanner is working with ohlcv_universal
3. Backup of ohlcv_cache exists

WARNING: This is irreversible. Make sure you have a backup!

Usage:
    python scripts/phase5_cleanup_cache.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from src.database import get_db_context
from src.models.ohlcv_cache_model import OHLCVCache
from src.models.ohlcv_universal_model import OHLCVUniversal


def check_prerequisites():
    """Check if it's safe to cleanup ohlcv_cache."""
    print("Checking prerequisites...")
    
    with get_db_context() as db:
        # Check ohlcv_universal has data
        universal_count = db.query(func.count(OHLCVUniversal.id)).scalar()
        cache_count = db.query(func.count(OHLCVCache.id)).scalar()
        
        print(f"  ohlcv_universal rows: {universal_count:,}")
        print(f"  ohlcv_cache rows: {cache_count:,}")
        
        if universal_count == 0:
            print("  ✗ FAIL: ohlcv_universal is empty!")
            print("     Run: python scripts/migrate_ohlcv_to_universal.py")
            return False
        
        if cache_count == 0:
            print("  ✓ ohlcv_cache is already empty - nothing to cleanup")
            return True
        
        # Check backup table exists
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'ohlcv_cache_backup' in tables:
            print("  ✓ ohlcv_cache_backup exists")
        else:
            print("  ⚠️  WARNING: No backup table found!")
            response = input("     Continue without backup? (y/N): ")
            if response.lower() != 'y':
                print("     Aborted")
                return False
        
        return True


def create_backup():
    """Create backup of ohlcv_cache if not exists."""
    print("\nCreating backup...")
    
    with get_db_context() as db:
        # Check if backup already exists
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'ohlcv_cache_backup' in tables:
            print("  ✓ Backup already exists")
            return True
        
        # Create backup
        try:
            db.execute(text("""
                CREATE TABLE ohlcv_cache_backup AS 
                SELECT * FROM ohlcv_cache
            """))
            db.commit()
            
            count = db.query(func.count(OHLCVCache.id)).scalar()
            print(f"  ✓ Backup created: {count:,} rows")
            return True
            
        except Exception as e:
            print(f"  ✗ FAIL: Backup failed: {e}")
            db.rollback()
            return False


def drop_ohlcv_cache():
    """Drop the ohlcv_cache table."""
    print("\nDropping ohlcv_cache table...")
    
    with get_db_context() as db:
        try:
            # Drop table
            db.execute(text("DROP TABLE IF EXISTS ohlcv_cache"))
            db.commit()
            
            print("  ✓ ohlcv_cache dropped successfully")
            return True
            
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            db.rollback()
            return False


def verify_cleanup():
    """Verify cleanup was successful."""
    print("\nVerifying cleanup...")
    
    with get_db_context() as db:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'ohlcv_cache' in tables:
            print("  ✗ FAIL: ohlcv_cache still exists")
            return False
        
        print("  ✓ ohlcv_cache removed")
        
        # Verify ohlcv_universal still works
        universal_count = db.query(func.count(OHLCVUniversal.id)).scalar()
        print(f"  ✓ ohlcv_universal rows: {universal_count:,}")
        
        # Verify backup still exists
        if 'ohlcv_cache_backup' in tables:
            backup_count = db.query(func.count(OHLCVCache.id)).filter(
                # Query backup table using raw SQL
                text("SELECT COUNT(*) FROM ohlcv_cache_backup")
            ).scalar()
            print(f"  ✓ ohlcv_cache_backup rows: {backup_count:,}")
        
        return True


def main():
    """Main cleanup function."""
    print("=" * 70)
    print("  Phase 5: Cleanup Old ohlcv_cache Table")
    print("=" * 70)
    print(f"Started: {datetime.utcnow().isoformat()}")
    print()
    
    # Import func here to avoid circular imports
    global func
    from sqlalchemy import func
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites not met - aborting")
        return
    
    # Create backup if needed
    if not create_backup():
        print("\n✗ Backup failed - aborting")
        return
    
    # Confirm
    print("\n" + "=" * 70)
    print("  WARNING: This will permanently delete ohlcv_cache table")
    print("=" * 70)
    response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
    
    if response.lower() != 'yes':
        print("\nAborted by user")
        return
    
    # Drop table
    if not drop_ohlcv_cache():
        print("\n✗ Cleanup failed")
        return
    
    # Verify
    if not verify_cleanup():
        print("\n✗ Verification failed")
        return
    
    # Success
    print("\n" + "=" * 70)
    print("  ✓ Cleanup Complete!")
    print("=" * 70)
    print(f"Completed: {datetime.utcnow().isoformat()}")
    print()
    print("Next steps:")
    print("1. Test MTF scanner: curl http://localhost:8000/api/v1/mtf/opportunities")
    print("2. Monitor prefetch job logs for errors")
    print("3. Keep backup for 30 days, then drop: DROP TABLE ohlcv_cache_backup")
    print("=" * 70)


if __name__ == '__main__':
    main()
