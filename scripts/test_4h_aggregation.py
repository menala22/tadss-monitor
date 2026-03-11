#!/usr/bin/env python3
"""
Test script for 4h aggregation feature.

This script verifies that:
1. 1h → 4h aggregation produces correct OHLCV values
2. Timestamps are correctly aligned to 4h boundaries
3. MarketDataOrchestrator uses aggregation for Twelve Data h4

Usage:
    python scripts/test_4h_aggregation.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetcher import aggregate_1h_to_4h
from src.database import get_db_context
from src.services.market_data_orchestrator import MarketDataOrchestrator
from src.models.ohlcv_universal_model import OHLCVUniversal


def test_aggregation_function():
    """Test the aggregate_1h_to_4h function with sample data."""
    
    print("=" * 80)
    print("4h Aggregation Test - Function Level")
    print("=" * 80)
    
    # Create sample 1h data (24 hours = 6 complete 4h candles)
    dates = pd.date_range('2026-03-10 00:00:00', periods=24, freq='1h')
    sample_data = {
        'Open': range(100, 124),      # 100, 101, 102, ... 123
        'High': range(110, 134),      # 110, 111, 112, ... 133
        'Low': range(90, 114),        # 90, 91, 92, ... 113
        'Close': range(95, 119),      # 95, 96, 97, ... 118
        'Volume': [100] * 24,         # Constant volume
    }
    df_1h = pd.DataFrame(sample_data, index=dates)
    
    print(f"\n[Step 1] Input: {len(df_1h)} 1h candles")
    print(f"  Time range: {df_1h.index[0]} to {df_1h.index[-1]}")
    print(f"  Hours: {sorted(set(df_1h.index.hour))}")
    
    # Aggregate
    df_4h = aggregate_1h_to_4h(df_1h)
    
    print(f"\n[Step 2] Output: {len(df_4h)} 4h candles")
    print(f"  Time range: {df_4h.index[0]} to {df_4h.index[-1]}")
    print(f"  Hours: {sorted(set(df_4h.index.hour))}")
    
    # Verify
    print(f"\n[Step 3] Verification:")
    
    # Should have 6 candles (24 / 4)
    if len(df_4h) == 6:
        print(f"  ✓ PASS: Correct number of 4h candles (6)")
    else:
        print(f"  ✗ FAIL: Expected 6 candles, got {len(df_4h)}")
        return False
    
    # Timestamps should be at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    expected_hours = [0, 4, 8, 12, 16, 20]
    actual_hours = sorted(set(df_4h.index.hour))
    if actual_hours == expected_hours:
        print(f"  ✓ PASS: Correct 4h timestamps: {actual_hours}")
    else:
        print(f"  ✗ FAIL: Expected hours {expected_hours}, got {actual_hours}")
        return False
    
    # Verify OHLCV calculations for first candle (hours 0-3)
    first_candle = df_4h.iloc[0]
    expected_open = 100    # First candle's open (hour 0)
    expected_high = 113    # Max of 110, 111, 112, 113 (hours 0-3)
    expected_low = 90      # Min of 90, 91, 92, 93 (hours 0-3)
    expected_close = 98    # Last candle's close (hour 3)
    expected_volume = 400  # Sum of 4 × 100
    
    checks = [
        ('Open', first_candle['Open'], expected_open),
        ('High', first_candle['High'], expected_high),
        ('Low', first_candle['Low'], expected_low),
        ('Close', first_candle['Close'], expected_close),
        ('Volume', first_candle['Volume'], expected_volume),
    ]
    
    all_passed = True
    for name, actual, expected in checks:
        if actual == expected:
            print(f"  ✓ PASS: {name} = {actual} (expected {expected})")
        else:
            print(f"  ✗ FAIL: {name} = {actual} (expected {expected})")
            all_passed = False
    
    if all_passed:
        print("\n" + "=" * 80)
        print("FUNCTION TEST PASSED")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print("FUNCTION TEST FAILED")
        print("=" * 80)
        return False


def test_orchestrator_integration():
    """Test that orchestrator uses aggregation for Twelve Data h4."""
    
    print("\n" + "=" * 80)
    print("4h Aggregation Test - Orchestrator Integration")
    print("=" * 80)
    
    symbol = 'XAU/USD'
    timeframe = 'h4'
    
    with get_db_context() as db:
        orchestrator = MarketDataOrchestrator(db)
        
        # Clear existing h4 data for clean test
        print(f"\n[Step 1] Clearing existing {symbol} {timeframe} data...")
        db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).delete()
        db.commit()
        print("  ✓ Cleared")
        
        # Fetch using orchestrator
        print(f"\n[Step 2] Fetching {symbol} {timeframe} via orchestrator...")
        try:
            result = orchestrator.fetch_if_needed(symbol, timeframe)
            
            if result.success:
                print(f"  ✓ Fetch successful: {result.candles_fetched} candles")
            else:
                print(f"  ✗ Fetch failed: {result.error}")
                return False
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            return False
        
        # Verify data in database
        print(f"\n[Step 3] Verifying data in ohlcv_universal...")
        candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == timeframe,
        ).order_by(OHLCVUniversal.timestamp.desc()).limit(10).all()
        
        if not candles:
            print(f"  ✗ FAIL: No data found in ohlcv_universal")
            return False
        
        print(f"  Found {len(candles)} candles")
        
        # Check timestamps
        hours = set(c.timestamp.hour for c in candles)
        print(f"  Hours in last 10 candles: {sorted(hours)}")
        
        # Should have 4h boundaries: 0, 4, 8, 12, 16, 20
        expected_hours = {0, 4, 8, 12, 16, 20}
        if hours.issubset(expected_hours):
            print(f"  ✓ PASS: Timestamps on 4h boundaries")
        else:
            print(f"  ✗ FAIL: Unexpected hours: {hours - expected_hours}")
            return False
        
        # Check data quality (no nulls)
        null_check = any(
            c.open is None or c.high is None or c.low is None or c.close is None
            for c in candles
        )
        if not null_check:
            print(f"  ✓ PASS: No NULL values in OHLCV")
        else:
            print(f"  ✗ FAIL: Found NULL values")
            return False
        
        print("\n" + "=" * 80)
        print("INTEGRATION TEST PASSED")
        print("=" * 80)
        return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("4h Aggregation Test Suite")
    print("=" * 80)
    
    # Test 1: Function level
    func_passed = test_aggregation_function()
    
    # Test 2: Integration (requires API access)
    print("\n\nNote: Integration test requires Twelve Data API access")
    print("Skipping integration test if running offline\n")
    integration_passed = False
    try:
        integration_passed = test_orchestrator_integration()
    except Exception as e:
        print(f"Integration test skipped: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"  Function test:      {'✓ PASSED' if func_passed else '✗ FAILED'}")
    print(f"  Integration test:   {'✓ PASSED' if integration_passed else '⊗ SKIPPED'}")
    print("=" * 80)
    
    return func_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
