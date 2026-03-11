#!/usr/bin/env python3
"""
Check OHLCV Universal Table Status

This script checks if the ohlcv_universal table is up to date according to the scheduler.
The scheduler runs market data prefetch every hour at :20 minutes.

Usage:
    python check_ohlcv_status.py
"""

from datetime import datetime, timedelta
from sqlalchemy import func, distinct
from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.models.market_data_status_model import MarketDataStatus


def check_ohlcv_universal_status():
    """Check the status of the ohlcv_universal table."""
    
    print("=" * 70)
    print("OHLCV UNIVERSAL TABLE STATUS CHECK")
    print("=" * 70)
    print(f"Current UTC time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scheduler prefetch: Every hour at :20 minutes")
    print("=" * 70)
    
    with get_db_context() as db:
        # Get all unique symbol/timeframe combinations
        combinations = db.query(
            OHLCVUniversal.symbol,
            OHLCVUniversal.timeframe
        ).distinct().all()
        
        print(f"\n📊 Total symbol/timeframe combinations: {len(combinations)}")
        
        if not combinations:
            print("\n⚠️  WARNING: ohlcv_universal table is EMPTY!")
            return
        
        # Get statistics by provider
        provider_stats = db.query(
            OHLCVUniversal.provider,
            func.count(OHLCVUniversal.id).label('count')
        ).group_by(OHLCVUniversal.provider).all()
        
        print("\n📦 Data by Provider:")
        print("-" * 50)
        for stat in provider_stats:
            print(f"  {stat.provider:15} : {stat.count:,} candles")
        
        # Check freshness for each combination
        print("\n🕒 Data Freshness Check (Latest candle per symbol/timeframe):")
        print("-" * 70)
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        four_hours_ago = now - timedelta(hours=4)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        fresh_count = 0
        stale_1h_count = 0
        stale_4h_count = 0
        stale_24h_count = 0
        
        for symbol, timeframe in sorted(combinations):
            # Get latest candle timestamp
            latest = db.query(OHLCVUniversal).filter(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe
            ).order_by(OHLCVUniversal.timestamp.desc()).first()
            
            if latest:
                age = now - latest.timestamp
                
                # Determine status
                if latest.timestamp > one_hour_ago:
                    status = "✅ FRESH (<1h)"
                    fresh_count += 1
                elif latest.timestamp > four_hours_ago:
                    status = "⚠️  STALE (>1h)"
                    stale_1h_count += 1
                elif latest.timestamp > twenty_four_hours_ago:
                    status = "🟠 OLD (>4h)"
                    stale_4h_count += 1
                else:
                    status = "❌ VERY OLD (>24h)"
                    stale_24h_count += 1
                
                print(f"  {symbol:12} | {timeframe:4} | Age: {str(age):>12} | {status} | Close: {latest.close:,.2f}")
        
        # Summary
        print("\n" + "=" * 70)
        print("📋 FRESHNESS SUMMARY:")
        print("=" * 70)
        print(f"  ✅ Fresh (<1h)     : {fresh_count:4} combinations")
        print(f"  ⚠️  Stale (>1h)    : {stale_1h_count:4} combinations")
        print(f"  🟠 Old (>4h)       : {stale_4h_count:4} combinations")
        print(f"  ❌ Very Old (>24h) : {stale_24h_count:4} combinations")
        print(f"  {'':4}{'─' * 30}")
        print(f"  Total             : {len(combinations):4} combinations")
        
        # Check against scheduler schedule
        print("\n" + "=" * 70)
        print("🕐 SCHEDULER ALIGNMENT CHECK:")
        print("=" * 70)
        
        # Calculate when the last prefetch should have run
        current_minute = now.minute
        minutes_since_last_sched = current_minute - 20 if current_minute >= 20 else current_minute + 40
        last_sched_run = now - timedelta(minutes=minutes_since_last_sched)
        
        print(f"  Last scheduler prefetch: ~{int(minutes_since_last_sched)} minutes ago")
        print(f"  Expected fresh data: Candles with timestamp >= {last_sched_run.strftime('%H:%M UTC')}")
        
        # Check market_data_status table
        print("\n" + "=" * 70)
        print("📊 MARKET DATA STATUS TABLE:")
        print("=" * 70)
        
        status_records = db.query(MarketDataStatus).order_by(
            MarketDataStatus.fetched_at.desc()
        ).limit(10).all()
        
        if status_records:
            print("\n  Last 10 status records:")
            for status in status_records:
                fetch_age = now - status.fetched_at if status.fetched_at else timedelta.max
                print(f"    {status.pair:12} | {status.timeframe:4} | "
                      f"Last fetch: {status.fetched_at.strftime('%H:%M:%S') if status.fetched_at else 'N/A'} | "
                      f"Age: {str(fetch_age).split('.')[0]:>10} | "
                      f"Candles: {status.candle_count:4} | "
                      f"Quality: {status.data_quality:>8}")
        else:
            print("\n  ⚠️  No records in market_data_status table")
        
        # Final verdict
        print("\n" + "=" * 70)
        print("🎯 VERDICT:")
        print("=" * 70)
        
        if fresh_count == len(combinations):
            print("  ✅ All data is FRESH - ohlcv_universal table is UP TO DATE")
        elif fresh_count > len(combinations) * 0.8:
            print(f"  ⚠️  Most data is fresh ({fresh_count}/{len(combinations)}) - Minor staleness detected")
        elif fresh_count > len(combinations) * 0.5:
            print(f"  🟠 Significant staleness ({fresh_count}/{len(combinations)}) - Prefetch may be failing")
        else:
            print(f"  ❌ Critical staleness ({fresh_count}/{len(combinations)}) - Prefetch likely broken")
        
        print("=" * 70)


if __name__ == "__main__":
    check_ohlcv_universal_status()
