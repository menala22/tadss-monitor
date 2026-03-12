"""
Backfill script: Calculate entry_timestamp for existing opportunities.

This script finds the LTF confirmation candle timestamp for existing
opportunities by matching the stored entry_price to OHLCV data.

Usage:
    python -m src.migrations.backfill_entry_timestamp run
    python -m src.migrations.backfill_entry_timestamp dry-run
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.models.mtf_opportunity_model import MTFOpportunity


def get_ltf_timeframe(trading_style: str) -> str:
    """Get LTF timeframe for trading style."""
    mapping = {
        'POSITION': 'd1',
        'SWING': 'h4',
        'INTRADAY': 'h1',
        'DAY': 'm15',
        'SCALPING': 'm5',
    }
    return mapping.get(trading_style.upper(), 'h4')


def backfill_entry_timestamp(dry_run: bool = True):
    """
    Backfill entry_timestamp for existing opportunities.
    
    For each opportunity without entry_timestamp:
    1. Get LTF timeframe based on trading_style
    2. Find candle in ohlcv_universal matching entry_price
    3. Use candle timestamp as entry_timestamp
    """
    with get_db_context() as db:
        # Get opportunities without entry_timestamp
        opportunities = db.query(MTFOpportunity).filter(
            MTFOpportunity.entry_timestamp == None,
            MTFOpportunity.entry_price != None,
            MTFOpportunity.status == 'ACTIVE'
        ).limit(50).all()  # Process 50 at a time
        
        if not opportunities:
            print("✓ No opportunities need backfill")
            return
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Processing {len(opportunities)} opportunities...")
        
        updated = 0
        not_found = 0
        errors = 0
        
        for opp in opportunities:
            try:
                # Get LTF timeframe
                ltf_tf = get_ltf_timeframe(opp.trading_style)
                
                # Find matching candle in ohlcv_universal
                # Look for candles within 24 hours before opportunity was created
                cutoff_time = opp.timestamp - timedelta(hours=24)
                
                candles = db.query(OHLCVUniversal).filter(
                    OHLCVUniversal.symbol == opp.pair,
                    OHLCVUniversal.timeframe == ltf_tf,
                    OHLCVUniversal.timestamp >= cutoff_time,
                    OHLCVUniversal.timestamp <= opp.timestamp,
                ).order_by(OHLCVUniversal.timestamp.desc()).limit(100).all()
                
                if not candles:
                    print(f"  ✗ {opp.pair} ({opp.trading_style}): No LTF data found ({ltf_tf})")
                    not_found += 1
                    continue
                
                # Find candle with matching close price (within 0.1% tolerance)
                entry_price = opp.entry_price
                tolerance = entry_price * 0.001  # 0.1%
                
                matched_candle = None
                for candle in candles:
                    if abs(candle.close - entry_price) <= tolerance:
                        matched_candle = candle
                        break  # Use first match (most recent)
                
                if matched_candle:
                    if not dry_run:
                        opp.entry_timestamp = matched_candle.timestamp
                        updated += 1
                    print(f"  {'[SKIP] ' if dry_run else '✓ '} {opp.pair} ({opp.trading_style}): "
                          f"entry @{matched_candle.close} ({matched_candle.timestamp})")
                else:
                    print(f"  ✗ {opp.pair} ({opp.trading_style}): No matching candle for entry @{entry_price}")
                    not_found += 1
                    
            except Exception as e:
                print(f"  ✗ {opp.pair} ({opp.trading_style}): Error - {e}")
                errors += 1
        
        if not dry_run:
            db.commit()
            print(f"\n✓ Backfill complete: {updated} updated, {not_found} not found, {errors} errors")
        else:
            print(f"\n[DRY RUN] Would update {updated} opportunities")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backfill_entry_timestamp.py [run|dry-run]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "run":
        backfill_entry_timestamp(dry_run=False)
    elif command == "dry-run":
        backfill_entry_timestamp(dry_run=True)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python backfill_entry_timestamp.py [run|dry-run]")
        sys.exit(1)
