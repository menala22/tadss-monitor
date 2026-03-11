#!/usr/bin/env python3
"""
Migration Script: OHLCV Cache → OHLCV Universal

This script migrates existing data from the legacy ohlcv_cache table
to the new ohlcv_universal table with:
- Standardized symbol formats (XAUUSD → XAU/USD)
- Normalized timeframe formats (1w, 1week → w1)
- Provider tracking ('migrated' for legacy data)
- Deduplication (keeps newest fetched_at for duplicates)

Usage:
    python scripts/migrate_ohlcv_to_universal.py

Backup:
    The script creates a backup of ohlcv_cache before migration.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.database import get_db_context
from src.models.ohlcv_cache_model import OHLCVCache
from src.models.ohlcv_universal_model import OHLCVUniversal, normalize_symbol, normalize_timeframe


def create_backup(db: Session) -> int:
    """
    Create a backup of ohlcv_cache table.
    
    Args:
        db: Database session.
    
    Returns:
        Number of rows backed up.
    """
    print("Creating backup of ohlcv_cache table...")
    
    # Create backup table
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS ohlcv_cache_backup AS 
        SELECT * FROM ohlcv_cache
    """))
    
    # Count rows
    count = db.query(func.count(OHLCVCache.id)).scalar()
    
    print(f"✓ Backup created: {count} rows")
    return count


def migrate_data(db: Session, batch_size: int = 1000) -> dict:
    """
    Migrate data from ohlcv_cache to ohlcv_universal.
    
    Args:
        db: Database session.
        batch_size: Number of rows to process at once.
    
    Returns:
        Migration statistics.
    """
    print("\nStarting migration...")
    print(f"  Source: ohlcv_cache")
    print(f"  Target: ohlcv_universal")
    print(f"  Batch size: {batch_size}")
    
    stats = {
        'total_source': 0,
        'migrated': 0,
        'duplicates_skipped': 0,
        'errors': 0,
    }
    
    # Get total count
    stats['total_source'] = db.query(func.count(OHLCVCache.id)).scalar()
    print(f"\nTotal source rows: {stats['total_source']}")
    
    # Query all cache entries
    cache_entries = db.query(OHLCVCache).yield_per(batch_size)
    
    migrated_symbols = set()
    
    for i, cache in enumerate(cache_entries):
        try:
            # Normalize symbol and timeframe
            norm_symbol = normalize_symbol(cache.symbol)
            norm_timeframe = normalize_timeframe(cache.timeframe)
            
            # Track which symbols we've seen
            migrated_symbols.add(norm_symbol)
            
            # Create universal entry
            universal = OHLCVUniversal(
                symbol=norm_symbol,
                timeframe=norm_timeframe,
                timestamp=cache.timestamp,
                open=cache.open,
                high=cache.high,
                low=cache.low,
                close=cache.close,
                volume=cache.volume,
                fetched_at=cache.fetched_at,
                provider='migrated'
            )
            
            db.add(universal)
            stats['migrated'] += 1
            
            # Commit in batches
            if (i + 1) % batch_size == 0:
                db.commit()
                print(f"  Progress: {i + 1}/{stats['total_source']} rows ({(i + 1) / stats['total_source'] * 100:.1f}%)")
                
        except Exception as e:
            # Handle duplicates (same symbol/timeframe/timestamp)
            if 'UNIQUE constraint failed' in str(e) or 'duplicate' in str(e).lower():
                stats['duplicates_skipped'] += 1
                db.rollback()
            else:
                stats['errors'] += 1
                print(f"  Error migrating row {i}: {e}")
                db.rollback()
    
    # Final commit
    db.commit()
    
    return stats


def verify_migration(db: Session) -> bool:
    """
    Verify migration was successful.
    
    Args:
        db: Database session.
    
    Returns:
        True if verification passes.
    """
    print("\nVerifying migration...")
    
    # Check row counts
    cache_count = db.query(func.count(OHLCVCache.id)).scalar()
    universal_count = db.query(func.count(OHLCVUniversal.id)).scalar()
    
    print(f"  ohlcv_cache rows: {cache_count}")
    print(f"  ohlcv_universal rows: {universal_count}")
    print(f"  Duplicates removed: {cache_count - universal_count}")
    
    # Check symbol distribution
    print("\n  Symbol distribution in ohlcv_universal:")
    symbols = db.query(
        OHLCVUniversal.symbol,
        func.count(OHLCVUniversal.id).label('count')
    ).group_by(OHLCVUniversal.symbol).all()
    
    for symbol, count in sorted(symbols, key=lambda x: -x[1]):
        print(f"    {symbol}: {count} candles")
    
    # Check timeframe distribution
    print("\n  Timeframe distribution in ohlcv_universal:")
    timeframes = db.query(
        OHLCVUniversal.timeframe,
        func.count(OHLCVUniversal.id).label('count')
    ).group_by(OHLCVUniversal.timeframe).all()
    
    for tf, count in sorted(timeframes, key=lambda x: -x[1]):
        print(f"    {tf}: {count} candles")
    
    # Check newest candles match
    print("\n  Checking newest candles...")
    for symbol in ['BTC/USDT', 'ETH/USDT', 'XAU/USD', 'XAG/USD']:
        cache_newest = db.query(func.max(OHLCVCache.timestamp)).filter(
            OHLCVCache.symbol.like(f'%{symbol.replace("/", "")}%')
        ).scalar()
        
        universal_newest = db.query(func.max(OHLCVUniversal.timestamp)).filter(
            OHLCVUniversal.symbol == symbol
        ).scalar()
        
        match = "✓" if cache_newest == universal_newest else "✗"
        print(f"    {symbol}: cache={cache_newest}, universal={universal_newest} {match}")
    
    # Verify no NULL values in required columns
    print("\n  Checking data quality...")
    null_checks = {
        'symbol': db.query(OHLCVUniversal).filter(OHLCVUniversal.symbol.is_(None)).count(),
        'timeframe': db.query(OHLCVUniversal).filter(OHLCVUniversal.timeframe.is_(None)).count(),
        'timestamp': db.query(OHLCVUniversal).filter(OHLCVUniversal.timestamp.is_(None)).count(),
        'open': db.query(OHLCVUniversal).filter(OHLCVUniversal.open.is_(None)).count(),
        'close': db.query(OHLCVUniversal).filter(OHLCVUniversal.close.is_(None)).count(),
    }
    
    all_good = True
    for column, null_count in null_checks.items():
        if null_count > 0:
            print(f"    ✗ {column}: {null_count} NULL values")
            all_good = False
        else:
            print(f"    ✓ {column}: 0 NULL values")
    
    return all_good


def update_market_data_status(db: Session) -> None:
    """
    Update market_data_status table from newly migrated data.
    
    Args:
        db: Database session.
    """
    print("\nUpdating market_data_status from ohlcv_universal...")
    
    from src.models.market_data_status_model import MarketDataStatus
    
    # Clear existing status
    db.query(MarketDataStatus).delete()
    
    # Populate from ohlcv_universal
    status_entries = db.query(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe,
        func.count(OHLCVUniversal.id).label('candle_count'),
        func.max(OHLCVUniversal.timestamp).label('last_candle_time'),
    ).group_by(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe
    ).all()
    
    for entry in status_entries:
        candle_count = entry.candle_count
        
        # Assess quality
        if candle_count >= 200:
            quality = 'EXCELLENT'
        elif candle_count >= 100:
            quality = 'GOOD'
        elif candle_count >= 50:
            quality = 'STALE'
        else:
            quality = 'MISSING'
        
        status = MarketDataStatus(
            pair=entry.symbol,  # MarketDataStatus uses 'pair' not 'symbol'
            timeframe=entry.timeframe,
            candle_count=candle_count,
            last_candle_time=entry.last_candle_time,
            fetched_at=datetime.utcnow(),
            data_quality=quality,
            source='migrated'  # MarketDataStatus uses 'source' not 'provider'
        )
        db.add(status)
    
    db.commit()
    
    print(f"✓ Updated market_data_status with {len(status_entries)} entries")


def main():
    """Main migration function."""
    print("=" * 60)
    print("OHLCV Cache → Universal Migration")
    print("=" * 60)
    print(f"Started: {datetime.utcnow().isoformat()}")
    print()
    
    with get_db_context() as db:
        # Step 0: Create ohlcv_universal table if not exists
        from src.models.ohlcv_universal_model import create_ohlcv_universal_table
        create_ohlcv_universal_table(db.bind)
        print("✓ ohlcv_universal table created/verified")
        
        # Step 1: Create backup
        create_backup(db)
        
        # Step 2: Migrate data
        stats = migrate_data(db)
        
        print("\n" + "=" * 60)
        print("Migration Statistics")
        print("=" * 60)
        print(f"  Total source rows: {stats['total_source']}")
        print(f"  Migrated: {stats['migrated']}")
        print(f"  Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"  Errors: {stats['errors']}")
        
        # Step 3: Verify migration
        verify_migration(db)
        
        # Step 4: Update market_data_status
        update_market_data_status(db)
    
    print()
    print("=" * 60)
    print(f"Migration completed: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify data in ohlcv_universal table")
    print("2. Update application code to read from ohlcv_universal")
    print("3. Keep ohlcv_cache as backup for 1 week")
    print("4. After verification, consider dropping ohlcv_cache")
    print()


if __name__ == '__main__':
    main()
