#!/usr/bin/env python3
"""
Test script for MarketDataOrchestrator.

Usage:
    python scripts/test_orchestrator.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.services.market_data_orchestrator import MarketDataOrchestrator


def main():
    """Test the orchestrator."""
    print("=" * 60)
    print("MarketDataOrchestrator Test")
    print("=" * 60)
    
    with get_db_context() as db:
        orchestrator = MarketDataOrchestrator(db)
        
        # Test 1: Run smart fetch for all watchlist symbols
        print("\nTest 1: Smart fetch for all watchlist symbols")
        result = orchestrator.run_smart_fetch()
        
        print(f"\nResults:")
        print(f"  Total needed: {result.total_needed}")
        print(f"  Total fetched: {result.total_fetched}")
        print(f"  Total skipped: {result.total_skipped}")
        print(f"  Total errors: {result.total_errors}")
        
        if result.fetches:
            print(f"\nFetch details:")
            for fetch in result.fetches[:5]:  # Show first 5
                status = "✓" if fetch.success else "✗"
                print(f"  {status} {fetch.symbol} {fetch.timeframe}: {fetch.candles_fetched} candles ({fetch.provider})")
        
        # Test 2: Check data status
        print("\n\nTest 2: Data status after fetch")
        from src.models.market_data_status_model import MarketDataStatus
        
        statuses = db.query(MarketDataStatus).all()
        print(f"  Status entries: {len(statuses)}")
        
        for status in statuses[:10]:
            print(f"  {status.pair} {status.timeframe}: {status.data_quality} ({status.candle_count} candles)")
        
        print("\n" + "=" * 60)
        print("Test complete!")
        print("=" * 60)


if __name__ == '__main__':
    main()
