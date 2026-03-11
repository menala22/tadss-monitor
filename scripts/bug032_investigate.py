#!/usr/bin/env python3
"""
BUG-032 Investigation Script.

This script diagnoses the hourly candle corruption issue by:
1. Fetching data directly from Twelve Data API
2. Logging what the API returns (timestamps)
3. Logging what gets saved to cache
4. Comparing the two

Usage:
    python scripts/bug032_investigate.py
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.services.ohlcv_cache_manager import OHLCVCacheManager
from src.models.ohlcv_cache_model import OHLCVCache

# Setup logging to see detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bug032')


def investigate_hourly_corruption():
    """Investigate BUG-032: Hourly candles becoming daily."""
    
    print("=" * 80)
    print("BUG-032 Investigation: Hourly Candle Corruption")
    print("=" * 80)
    
    symbol = 'XAU/USD'
    timeframe = 'h1'
    limit = 24
    
    print(f"\nTest: Fetch {limit} candles for {symbol} {timeframe}")
    print("-" * 80)
    
    # Step 1: Check what's currently in cache
    print("\n[Step 1] Checking current cache contents...")
    with get_db_context() as db:
        cache_mgr = OHLCVCacheManager(db)
        
        # Query raw from DB
        candles = (
            db.query(OHLCVCache)
            .filter(
                OHLCVCache.symbol == symbol,
                OHLCVCache.timeframe == '1h',  # Twelve Data format
            )
            .order_by(OHLCVCache.timestamp.desc())
            .limit(30)
            .all()
        )
        
        print(f"\nCache has {len(candles)} candles for {symbol} 1h")
        if candles:
            print("\nLast 10 candles in cache:")
            for c in candles[:10]:
                print(f"  {c.timestamp} | Close: {c.close:.2f}")
            
            # Check unique hours
            hours = set(c.timestamp.hour for c in candles)
            print(f"\nUnique hours in cache: {sorted(hours)}")
            
            # Check if only midnight
            if hours == {0}:
                print("⚠️  CORRUPTION CONFIRMED: Only midnight candles (00:00:00)!")
            else:
                print("✓ Cache has diverse hourly timestamps")
    
    # Step 2: Fetch fresh from API (bypass cache)
    print("\n\n[Step 2] Fetching fresh data from Twelve Data API...")
    from src.data_fetcher import DataFetcher
    
    fetcher = DataFetcher(source='twelvedata')
    
    # Clear cache first to force fresh fetch
    print("Clearing cache for this test...")
    with get_db_context() as db:
        count = (
            db.query(OHLCVCache)
            .filter(
                OHLCVCache.symbol == symbol,
                OHLCVCache.timeframe == '1h',
            )
            .delete()
        )
        db.commit()
        print(f"Cleared {count} cached candles")
    
    # Fetch with skip_cache_check=True
    print(f"\nFetching {limit} candles from API...")
    df = fetcher.get_ohlcv(symbol, '1h', limit=limit, skip_cache_check=True)
    
    print(f"\nAPI returned {len(df)} candles")
    print("\nFirst 10 candles from API:")
    for i, (ts, row) in enumerate(df.head(10).iterrows()):
        print(f"  {ts} | Close: {row['Close']:.2f}")
    
    # Check unique hours in API response
    api_hours = set(ts.hour for ts in df.index)
    print(f"\nUnique hours in API response: {sorted(api_hours)}")
    
    if api_hours == {0}:
        print("⚠️  API RETURNING ONLY MIDNIGHT - Twelve Data issue!")
    else:
        print("✓ API returning correct hourly data")
    
    # Step 3: Check what was saved to cache
    print("\n\n[Step 3] Checking what was saved to cache...")
    with get_db_context() as db:
        candles = (
            db.query(OHLCVCache)
            .filter(
                OHLCVCache.symbol == symbol,
                OHLCVCache.timeframe == '1h',
            )
            .order_by(OHLCVCache.timestamp.desc())
            .limit(30)
            .all()
        )
        
        print(f"\nCache now has {len(candles)} candles")
        if candles:
            print("\nLast 10 candles saved:")
            for c in candles[:10]:
                print(f"  {c.timestamp} | Close: {c.close:.2f}")
            
            # Check unique hours
            saved_hours = set(c.timestamp.hour for c in candles)
            print(f"\nUnique hours in saved cache: {sorted(saved_hours)}")
    
    # Step 4: Compare API vs Saved
    print("\n\n[Step 4] Comparison:")
    print(f"  API hours:       {sorted(api_hours)}")
    print(f"  Saved hours:     {sorted(saved_hours)}")
    
    if api_hours != saved_hours:
        print("\n⚠️  CORRUPTION POINT IDENTIFIED: Data changes between API and DB!")
        print("   The issue is in the save path (save_ohlcv or OHLCVCache model)")
    else:
        print("\n✓ Hours match - corruption may have been from earlier fetch")
    
    # Step 5: Check timezone info
    print("\n\n[Step 5] Timezone Analysis:")
    if len(df) > 0:
        api_ts = df.index[0]
        print(f"  API timestamp type: {type(api_ts)}")
        print(f"  API timestamp: {api_ts}")
        print(f"  Has timezone: {api_ts.tzinfo is not None if hasattr(api_ts, 'tzinfo') else 'N/A'}")
    
    with get_db_context() as db:
        first_candle = db.query(OHLCVCache).filter(
            OHLCVCache.symbol == symbol,
            OHLCVCache.timeframe == '1h',
        ).first()
        
        if first_candle:
            print(f"  DB timestamp type: {type(first_candle.timestamp)}")
            print(f"  DB timestamp: {first_candle.timestamp}")
    
    print("\n" + "=" * 80)
    print("Investigation Complete")
    print("=" * 80)


if __name__ == '__main__':
    investigate_hourly_corruption()
