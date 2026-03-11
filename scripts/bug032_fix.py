#!/usr/bin/env python3
"""
BUG-032 Fix Script: Clear Corrupted Hourly Data and Repopulate.

This script:
1. Clears corrupted hourly cache data (daily candles only)
2. Fetches fresh hourly data from API
3. Verifies the fix worked

Usage:
    python scripts/bug032_fix.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.services.ohlcv_cache_manager import OHLCVCacheManager
from src.models.ohlcv_cache_model import OHLCVCache
from src.data_fetcher import DataFetcher


def clear_and_repopulate():
    """Clear corrupted hourly data and repopulate."""
    
    print("=" * 80)
    print("BUG-032 Fix: Clear Corrupted Hourly Data & Repopulate")
    print("=" * 80)
    
    # Pairs and timeframes to fix
    pairs_to_fix = [
        ('XAU/USD', 'h1'),
        ('XAU/USD', 'h4'),
        ('XAG/USD', 'h1'),
        ('XAG/USD', 'h4'),
    ]
    
    fetcher = DataFetcher(source='twelvedata')
    
    for symbol, timeframe in pairs_to_fix:
        print(f"\n{'─' * 80}")
        print(f"Processing: {symbol} {timeframe}")
        print(f"{'─' * 80}")
        
        # Map to Twelve Data format
        tf_mapping = {'h1': '1h', 'h4': '4h'}
        td_timeframe = tf_mapping.get(timeframe, timeframe)
        
        with get_db_context() as db:
            # Check current state
            candles = (
                db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == td_timeframe,
                )
                .all()
            )
            
            if candles:
                hours = set(c.timestamp.hour for c in candles)
                print(f"  Current cache: {len(candles)} candles, hours: {sorted(hours)}")
                
                if hours == {0}:
                    print(f"  ⚠️  CORRUPTED: Only midnight candles detected")
                else:
                    print(f"  ✓ Has diverse hours, may not need clearing")
            
            # Clear corrupted data
            print(f"  Clearing cache for {symbol} {td_timeframe}...")
            count = (
                db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == td_timeframe,
                )
                .delete()
            )
            db.commit()
            print(f"  Deleted {count} candles")
        
        # Fetch fresh data
        print(f"  Fetching fresh data from Twelve Data...")
        limit = 200 if timeframe == 'h1' else 100
        
        try:
            df = fetcher.get_ohlcv(symbol, td_timeframe, limit=limit, skip_cache_check=True)
            
            print(f"  ✓ Fetched {len(df)} candles from API")
            
            # Verify hourly distribution
            hours = set(ts.hour for ts in df.index)
            print(f"  Hours in fetched data: {sorted(hours)}")
            
            if len(hours) > 1:
                print(f"  ✓ SUCCESS: Has diverse hourly candles")
            else:
                print(f"  ⚠️  WARNING: Still only has hour {hours}")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("Fix Complete!")
    print("=" * 80)
    
    # Final verification
    print("\nFinal Verification:")
    print("-" * 80)
    
    with get_db_context() as db:
        for symbol, timeframe in pairs_to_fix:
            td_timeframe = tf_mapping.get(timeframe, timeframe)
            
            candles = (
                db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == td_timeframe,
                )
                .order_by(OHLCVCache.timestamp.desc())
                .limit(10)
                .all()
            )
            
            if candles:
                hours = set(c.timestamp.hour for c in candles)
                last_ts = candles[0].timestamp
                print(f"  {symbol} {td_timeframe}: {len(candles)} candles, last: {last_ts}, hours: {sorted(hours)}")
            else:
                print(f"  {symbol} {td_timeframe}: NO DATA")


if __name__ == '__main__':
    clear_and_repopulate()
