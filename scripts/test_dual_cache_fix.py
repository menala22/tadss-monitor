#!/usr/bin/env python3
"""
Test script to verify dual-cache write removal.

This script verifies that:
1. DataFetcher no longer writes to ohlcv_cache
2. MarketDataOrchestrator writes only to ohlcv_universal
3. No duplicate writes occur

Usage:
    python scripts/test_dual_cache_fix.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.services.market_data_orchestrator import MarketDataOrchestrator
from src.models.ohlcv_cache_model import OHLCVCache
from src.models.ohlcv_universal_model import OHLCVUniversal


def test_dual_cache_removal():
    """Test that dual-cache writes are removed."""
    
    print("=" * 80)
    print("Dual-Cache Removal Verification Test")
    print("=" * 80)
    
    symbol = 'XAU/USD'
    timeframe = 'h1'
    
    with get_db_context() as db:
        # Clear existing data for clean test
        print("\n[Step 1] Clearing existing test data...")
        db.query(OHLCVCache).filter(
            OHLCVCache.symbol == symbol,
            OHLCVCache.timeframe == '1h',
        ).delete()
        db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).delete()
        db.commit()
        print("  ✓ Cleared both cache tables")
        
        # Count before fetch
        cache_count_before = db.query(OHLCVCache).filter(
            OHLCVCache.symbol == symbol,
        ).count()
        universal_count_before = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).count()
        
        print(f"\n[Step 2] Counts before fetch:")
        print(f"  ohlcv_cache: {cache_count_before} rows")
        print(f"  ohlcv_universal: {universal_count_before} rows")
        
        # Run orchestrator fetch
        print(f"\n[Step 3] Running MarketDataOrchestrator fetch...")
        orchestrator = MarketDataOrchestrator(db)
        
        try:
            result = orchestrator.fetch_if_needed(symbol, timeframe)
            print(f"  Fetch result: {result.candles_fetched} candles, success={result.success}")
            if result.error:
                print(f"  Error: {result.error}")
        except Exception as e:
            print(f"  ✗ Fetch failed: {e}")
            return False
        
        # Count after fetch
        cache_count_after = db.query(OHLCVCache).filter(
            OHLCVCache.symbol == symbol,
        ).count()
        universal_count_after = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).count()
        
        print(f"\n[Step 4] Counts after fetch:")
        print(f"  ohlcv_cache: {cache_count_after} rows (Δ: {cache_count_after - cache_count_before})")
        print(f"  ohlcv_universal: {universal_count_after} rows (Δ: {universal_count_after - universal_count_before})")
        
        # Verify
        print(f"\n[Step 5] Verification:")
        
        cache_changed = (cache_count_after - cache_count_before) != 0
        universal_changed = (universal_count_after - universal_count_before) != 0
        
        if cache_changed:
            print(f"  ✗ FAIL: ohlcv_cache was modified (should be read-only)")
            print(f"     This means DataFetcher is still writing to cache!")
            return False
        else:
            print(f"  ✓ PASS: ohlcv_cache unchanged (read-only as expected)")
        
        if universal_changed and universal_count_after > 0:
            print(f"  ✓ PASS: ohlcv_universal has data (orchestrator writing correctly)")
        else:
            print(f"  ✗ FAIL: ohlcv_universal is empty (orchestrator not writing)")
            return False
        
        # Verify data quality
        print(f"\n[Step 6] Data quality check:")
        candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).order_by(OHLCVUniversal.timestamp.desc()).limit(10).all()
        
        if candles:
            hours = set(c.timestamp.hour for c in candles)
            print(f"  Last 10 candles hours: {sorted(hours)}")
            if len(hours) > 1:
                print(f"  ✓ PASS: Has diverse hourly data (not just midnight)")
            else:
                print(f"  ⚠ WARNING: Only has hour {hours} (may be API limitation)")
        else:
            print(f"  ✗ FAIL: No data in ohlcv_universal")
            return False
        
        print("\n" + "=" * 80)
        print("TEST PASSED: Dual-cache removal working correctly")
        print("=" * 80)
        return True


if __name__ == '__main__':
    success = test_dual_cache_removal()
    sys.exit(0 if success else 1)
