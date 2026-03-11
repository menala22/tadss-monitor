#!/usr/bin/env python3
"""
Correct Historical Data Quality Issues in ohlcv_universal Table.

This script corrects data corruption from:
- BUG-032 (hourly candles showing only midnight timestamps)
- Missing h4 data for Twelve Data pairs

The correction process:
1. Creates a backup of ohlcv_universal
2. Deletes corrupted candles (midnight-only h1/h4)
3. Triggers backfill using MarketDataOrchestrator
4. Verifies the correction

Usage:
    python scripts/correct_historical_data.py --assess     # Assess first
    python scripts/correct_historical_data.py --correct    # Run correction
    python scripts/correct_historical_data.py --verify     # Verify after

WARNING: This script deletes data. Always run --assess first and ensure
you have a backup before running --correct.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.services.market_data_orchestrator import MarketDataOrchestrator


def print_header(text: str, char: str = "="):
    """Print formatted header."""
    print(f"\n{char * 80}")
    print(f"  {text}")
    print(f"{char * 80}\n")


def print_warning(text: str):
    """Print warning message."""
    print(f"\n⚠️  WARNING: {text}\n")


def print_success(text: str):
    """Print success message."""
    print(f"\n✅ SUCCESS: {text}\n")


def print_error(text: str):
    """Print error message."""
    print(f"\n❌ ERROR: {text}\n")


def create_backup(db, backup_name: str = None):
    """
    Create backup of ohlcv_universal table.
    
    Returns backup table name.
    """
    if backup_name is None:
        backup_name = f"ohlcv_universal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"[1] Creating backup: {backup_name}")
    
    try:
        from sqlalchemy import text
        
        # Create backup table
        db.execute(text(f"CREATE TABLE {backup_name} AS SELECT * FROM ohlcv_universal"))
        db.commit()
        
        # Verify backup
        result = db.execute(text(f"SELECT COUNT(*) FROM {backup_name}")).fetchone()
        backup_count = result[0] if result else 0
        
        # Get original count
        original_count = db.query(OHLCVUniversal).count()
        
        if backup_count == original_count:
            print_success(f"Backup created: {backup_name} ({backup_count:,} rows)")
            return backup_name
        else:
            print_warning(f"Backup row count mismatch: {backup_count:,} vs {original_count:,}")
            return backup_name
            
    except Exception as e:
        print_error(f"Backup failed: {e}")
        raise


def delete_corrupted_data(db, cutoff: datetime = None):
    """
    Delete corrupted candles (midnight-only h1/h4).
    
    Returns number of rows deleted.
    """
    if cutoff is None:
        # Default: when fix was deployed (2026-03-10 15:00 UTC)
        cutoff = datetime(2026, 3, 10, 15, 0, 0)
    
    print(f"[2] Deleting corrupted data (cutoff: {cutoff.isoformat()})")
    
    from sqlalchemy import text
    
    total_deleted = 0
    
    # Delete corrupted h1 candles
    print("  Deleting corrupted h1 candles...")
    
    # Count before deletion
    h1_before = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.timeframe == 'h1',
        OHLCVUniversal.provider.in_(['twelvedata', 'gateio']),
        OHLCVUniversal.timestamp < cutoff
    ).count()
    
    # Delete using raw SQL (need strftime for hour extraction)
    result = db.execute(text("""
        DELETE FROM ohlcv_universal 
        WHERE timeframe = 'h1' 
          AND provider IN ('twelvedata', 'gateio')
          AND timestamp < :cutoff
          AND strftime('%H', timestamp) = '00'
    """), {'cutoff': cutoff.isoformat()})
    
    h1_deleted = result.rowcount
    total_deleted += h1_deleted
    db.commit()
    
    print(f"    Deleted {h1_deleted:,} h1 candles")
    
    # Delete corrupted h4 candles (if any)
    print("  Deleting corrupted h4 candles...")
    
    result = db.execute(text("""
        DELETE FROM ohlcv_universal 
        WHERE timeframe = 'h4' 
          AND provider IN ('twelvedata', 'gateio')
          AND timestamp < :cutoff
          AND strftime('%H', timestamp) = '00'
    """), {'cutoff': cutoff.isoformat()})
    
    h4_deleted = result.rowcount
    total_deleted += h4_deleted
    db.commit()
    
    print(f"    Deleted {h4_deleted:,} h4 candles")
    
    # Verify deletion
    h1_after = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.timeframe == 'h1',
        OHLCVUniversal.provider.in_(['twelvedata', 'gateio']),
        OHLCVUniversal.timestamp < cutoff
    ).count()
    
    print(f"\n  h1 candles before: {h1_before:,}, after: {h1_after:,}")
    print(f"  Total deleted: {total_deleted:,}")
    
    return total_deleted


def trigger_backfill(db, symbols: list = None, timeframes: list = None):
    """
    Trigger backfill using MarketDataOrchestrator.
    
    Returns backfill results.
    """
    if symbols is None:
        symbols = ['XAU/USD', 'XAG/USD']
    
    if timeframes is None:
        timeframes = ['h1', 'h4']
    
    print(f"[3] Triggering backfill for {symbols} ({timeframes})")
    
    try:
        orchestrator = MarketDataOrchestrator(db)
        
        # Clear for backfill (uses full FETCH_LIMITS)
        print("  Clearing existing data for backfill...")
        deleted = orchestrator.clear_for_backfill(
            symbols=symbols,
            timeframes=timeframes
        )
        print(f"    Cleared {deleted:,} rows")
        
        # Run smart fetch
        print("  Running smart fetch...")
        result = orchestrator.run_smart_fetch(
            symbols=symbols,
            timeframes=timeframes
        )
        
        print(f"\n  Backfill results:")
        print(f"    Total needed: {result.total_needed}")
        print(f"    Total fetched: {result.total_fetched}")
        print(f"    Total skipped: {result.total_skipped}")
        print(f"    Total errors: {result.total_errors}")
        
        if result.total_errors > 0:
            print_warning(f"{result.total_errors} fetches failed")
            for fetch in result.fetches:
                if not fetch.success:
                    print(f"      {fetch.symbol} {fetch.timeframe}: {fetch.error}")
        else:
            print_success("Backfill complete!")
        
        return result
        
    except Exception as e:
        print_error(f"Backfill failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def verify_correction(db):
    """
    Verify correction was successful.
    
    Returns True if verification passes.
    """
    print(f"[4] Verifying correction...")
    
    all_passed = True
    
    # Check h1 data (last 7 days)
    print("\n  Checking h1 data (last 7 days)...")
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    for symbol in ['XAU/USD', 'XAG/USD']:
        h1_candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == 'h1',
            OHLCVUniversal.timestamp >= seven_days_ago
        ).all()
        
        if not h1_candles:
            print(f"    ❌ {symbol}: No h1 candles found")
            all_passed = False
            continue
        
        hours = set(c.timestamp.hour for c in h1_candles)
        hour_count = len(hours)
        
        if hour_count == 24:
            print(f"    ✅ {symbol}: All 24 hours present")
        else:
            print(f"    ❌ {symbol}: Only {hour_count}/24 hours present")
            all_passed = False
    
    # Check h4 data
    print("\n  Checking h4 data availability...")
    
    for symbol in ['XAU/USD', 'XAG/USD']:
        h4_candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == 'h4'
        ).all()
        
        if not h4_candles:
            print(f"    ❌ {symbol}: No h4 candles found")
            all_passed = False
            continue
        
        count = len(h4_candles)
        if count >= 100:
            print(f"    ✅ {symbol}: {count:,} candles (sufficient)")
        else:
            print(f"    ⚠️  {symbol}: {count:,} candles (<100, insufficient)")
    
    return all_passed


def run_assessment():
    """Run data quality assessment."""
    print_header("DATA QUALITY ASSESSMENT")
    
    # Import and run assessment script
    from scripts.assess_data_quality import main as assess_main
    assess_main()


def run_correction(backup_name: str = None, skip_backup: bool = False):
    """Run full correction process."""
    print_header("DATA CORRECTION")
    
    # Confirmation
    print_warning("This will DELETE corrupted data and trigger backfill.")
    response = input("Type 'yes' to confirm: ").strip().lower()
    if response != 'yes':
        print("Correction cancelled.")
        sys.exit(0)
    
    cutoff = datetime(2026, 3, 10, 15, 0, 0)
    print(f"\nCorrection cutoff: {cutoff.isoformat()}")
    print("All corrupted data before this timestamp will be deleted.\n")
    
    try:
        with get_db_context() as db:
            # Step 1: Create backup
            if not skip_backup:
                backup_name = create_backup(db, backup_name)
            else:
                print_warning("Skipping backup (user requested)")
            
            # Step 2: Delete corrupted data
            deleted = delete_corrupted_data(db, cutoff)
            
            if deleted == 0:
                print_warning("No corrupted data found to delete")
            
            # Step 3: Trigger backfill
            result = trigger_backfill(db)
            
            # Step 4: Verify
            passed = verify_correction(db)
            
            if passed:
                print_header("CORRECTION COMPLETE")
                print_success("All verification checks passed!")
            else:
                print_header("CORRECTION PARTIALLY COMPLETE")
                print_warning("Some verification checks failed. Review output above.")
            
            print(f"\nBackup location: {backup_name}")
            print("To rollback: DROP TABLE ohlcv_universal; CREATE TABLE ohlcv_universal AS SELECT * FROM {backup_name};")
            
    except Exception as e:
        print_error(f"Correction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_verify():
    """Verify correction was successful."""
    print_header("CORRECTION VERIFICATION")
    
    try:
        with get_db_context() as db:
            passed = verify_correction(db)
            
            if passed:
                print_header("VERIFICATION PASSED")
                print_success("All checks passed! Data correction successful.")
            else:
                print_header("VERIFICATION FAILED")
                print_warning("Some checks failed. Review output above.")
                sys.exit(1)
                
    except Exception as e:
        print_error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Correct historical data quality issues in ohlcv_universal table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run assessment (read-only, no risk)
  python scripts/correct_historical_data.py --assess
  
  # Run correction (deletes data, creates backup first)
  python scripts/correct_historical_data.py --correct
  
  # Run correction without backup (NOT RECOMMENDED)
  python scripts/correct_historical_data.py --correct --skip-backup
  
  # Verify correction after completion
  python scripts/correct_historical_data.py --verify

WARNING: --correct will DELETE data. Always run --assess first.
        """
    )
    
    parser.add_argument('--assess', action='store_true',
                       help='Run data quality assessment (read-only)')
    parser.add_argument('--correct', action='store_true',
                       help='Run correction (deletes data, creates backup)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify correction was successful')
    parser.add_argument('--skip-backup', action='store_true',
                       help='Skip backup creation (NOT RECOMMENDED)')
    parser.add_argument('--backup-name', type=str, default=None,
                       help='Custom backup table name')
    
    args = parser.parse_args()
    
    if args.assess:
        run_assessment()
    elif args.correct:
        run_correction(args.backup_name, args.skip_backup)
    elif args.verify:
        run_verify()
    else:
        parser.print_help()
        print("\nError: Must specify --assess, --correct, or --verify")
        sys.exit(1)


if __name__ == '__main__':
    main()
