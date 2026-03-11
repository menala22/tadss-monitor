#!/usr/bin/env python3
"""
Assess Historical Data Quality in ohlcv_universal Table.

This script quantifies the scope of data corruption from:
- BUG-032 (hourly candles showing only midnight timestamps)
- Missing h4 data for Twelve Data pairs
- Dual-cache inconsistencies

Usage:
    python scripts/assess_data_quality.py

Output:
    - Corruption scope by symbol and timeframe
    - Hour distribution analysis
    - Recommendations for correction
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal


def print_header(text: str, char: str = "="):
    """Print formatted header."""
    print(f"\n{char * 80}")
    print(f"  {text}")
    print(f"{char * 80}\n")


def assess_bug032_corruption(db):
    """
    Assess BUG-032 corruption (midnight-only hourly candles).
    
    Returns dict with corruption statistics by symbol.
    """
    print("[1] Checking for BUG-032 corruption (midnight-only hourly candles)...")
    
    # Get all h1 candles from Twelve Data providers
    h1_candles = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.timeframe == 'h1',
        OHLCVUniversal.provider.in_(['twelvedata', 'gateio'])
    ).all()
    
    if not h1_candles:
        print("  ⚠ No h1 candles found for Twelve Data/Gate.io providers")
        return {}
    
    # Group by symbol and date
    midnight_candles = defaultdict(list)
    all_candles = defaultdict(list)
    
    for candle in h1_candles:
        key = (candle.symbol, candle.timestamp.date())
        all_candles[candle.symbol].append(candle.timestamp)
        
        if candle.timestamp.hour == 0:
            midnight_candles[key].append(candle)
    
    # Find days with only midnight candles (corrupted)
    corrupted_days = {}
    for (symbol, date), candles in midnight_candles.items():
        # Check if this day has ONLY midnight candles
        day_candles = [c for c in h1_candles 
                      if c.symbol == symbol and c.timestamp.date() == date]
        non_midnight = [c for c in day_candles if c.timestamp.hour != 0]
        
        if len(non_midnight) == 0 and len(candles) == 1:
            corrupted_days[(symbol, date)] = len(candles)
    
    # Group by symbol
    by_symbol = defaultdict(int)
    for (symbol, date), count in corrupted_days.items():
        by_symbol[symbol] += 1
    
    # Print results
    print(f"  Total h1 candles analyzed: {len(h1_candles):,}")
    print(f"  Corrupted days (midnight only): {len(corrupted_days)}")
    
    if by_symbol:
        print("\n  Corrupted days by symbol:")
        for symbol, days in sorted(by_symbol.items()):
            # Find date range
            dates = [date for (sym, date) in corrupted_days.keys() if sym == symbol]
            if dates:
                date_range = f"{min(dates)} to {max(dates)}"
                print(f"    {symbol}: {days} days ({date_range})")
    
    # Check hour distribution for last 7 days
    print("\n  Hour distribution (last 7 days):")
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    for symbol in sorted(set(c.symbol for c in h1_candles)):
        recent_candles = [c for c in h1_candles 
                         if c.symbol == symbol and c.timestamp >= seven_days_ago]
        
        if not recent_candles:
            continue
        
        hours = set(c.timestamp.hour for c in recent_candles)
        hour_count = len(hours)
        
        status = "✅" if hour_count == 24 else "⚠️ "
        print(f"    {status} {symbol}: {hour_count}/24 hours present {sorted(hours) if hour_count < 10 else ''}")
    
    return {
        'total_h1_candles': len(h1_candles),
        'corrupted_days': len(corrupted_days),
        'by_symbol': dict(by_symbol),
    }


def assess_h4_data(db):
    """
    Assess h4 data availability.
    
    Returns dict with h4 statistics by symbol.
    """
    print_header("h4 Data Availability")
    
    # Get all h4 candles
    h4_candles = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.timeframe == 'h4'
    ).all()
    
    if not h4_candles:
        print("  ⚠️  No h4 candles found in ohlcv_universal")
        return {'total': 0, 'by_symbol': {}}
    
    # Group by symbol
    by_symbol = defaultdict(list)
    for candle in h4_candles:
        by_symbol[candle.symbol].append(candle)
    
    # Check hour distribution (should be 0, 4, 8, 12, 16, 20)
    expected_hours = {0, 4, 8, 12, 16, 20}
    
    print(f"  Total h4 candles: {len(h4_candles):,}")
    print("\n  h4 candles by symbol:")
    
    for symbol, candles in sorted(by_symbol.items()):
        hours = set(c.timestamp.hour for c in candles)
        count = len(candles)
        
        # Check if hours are correct
        hour_status = "✅" if hours == expected_hours else "⚠️ "
        
        # Get date range
        dates = [c.timestamp for c in candles]
        date_range = f"{min(dates).date()} to {max(dates).date()}"
        
        print(f"    {hour_status} {symbol}: {count:,} candles ({date_range})")
        if hours != expected_hours:
            print(f"        Hours present: {sorted(hours)}")
            print(f"        Expected: {sorted(expected_hours)}")
    
    return {
        'total': len(h4_candles),
        'by_symbol': {k: len(v) for k, v in by_symbol.items()},
    }


def assess_dual_cache(db):
    """
    Assess dual-cache inconsistencies.
    
    Returns dict with comparison statistics.
    """
    print_header("Dual-Cache Comparison")
    
    from sqlalchemy import func
    
    try:
        # Query ohlcv_cache
        from src.models.ohlcv_cache_model import OHLCVCache
        
        cache_count = db.query(OHLCVCache).count()
        universal_count = db.query(OHLCVUniversal).count()
        
        print(f"  ohlcv_cache rows: {cache_count:,}")
        print(f"  ohlcv_universal rows: {universal_count:,}")
        
        # Check timeframe formats
        print("\n  Timeframe formats in ohlcv_cache:")
        cache_timeframes = db.query(
            OHLCVCache.timeframe, 
            func.count(OHLCVCache.id)
        ).group_by(OHLCVCache.timeframe).all()
        
        for tf, count in sorted(cache_timeframes):
            print(f"    {tf}: {count:,} rows")
        
        print("\n  Timeframe formats in ohlcv_universal:")
        universal_timeframes = db.query(
            OHLCVUniversal.timeframe,
            db.func.count(OHLCVUniversal.id)
        ).group_by(OHLCVUniversal.timeframe).all()
        
        for tf, count in sorted(universal_timeframes):
            print(f"    {tf}: {count:,} rows")
        
        # Check for format mismatches
        cache_tfs = set(tf for tf, _ in cache_timeframes)
        universal_tfs = set(tf for tf, _ in universal_timeframes)
        
        if cache_tfs != universal_tfs:
            print(f"\n  ⚠️  Format mismatch detected:")
            print(f"    Only in cache: {cache_tfs - universal_tfs}")
            print(f"    Only in universal: {universal_tfs - cache_tfs}")
        else:
            print(f"\n  ✅ Timeframe formats match")
        
        return {
            'cache_count': cache_count,
            'universal_count': universal_count,
            'cache_timeframes': dict(cache_timeframes),
            'universal_timeframes': dict(universal_timeframes),
        }
        
    except Exception as e:
        print(f"  ⚠️  Could not query ohlcv_cache: {e}")
        return {'error': str(e)}


def assess_data_freshness(db, hours: int = 24):
    """
    Assess data freshness for all symbols/timeframes.
    """
    print_header("Data Freshness (Last 24 Hours)")
    
    from sqlalchemy import func
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get all unique symbol/timeframe combinations
    combinations = db.query(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe,
        func.count(OHLCVUniversal.id).label('count'),
        func.max(OHLCVUniversal.timestamp).label('last_candle'),
        func.min(OHLCVUniversal.timestamp).label('first_candle')
    ).filter(
        OHLCVUniversal.timestamp >= cutoff
    ).group_by(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe
    ).order_by(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe
    ).all()
    
    if not combinations:
        print("  ⚠️  No data in last 24 hours!")
        return
    
    print(f"  {'Symbol':<15} {'TF':<6} {'Candles':<10} {'Last Candle':<20} {'Status':<10}")
    print(f"  {'-'*15} {'-'*6} {'-'*10} {'-'*20} {'-'*10}")
    
    for row in combinations:
        age_hours = (datetime.utcnow() - row.last_candle).total_seconds() / 3600
        
        # Determine status
        if age_hours < 2:
            status = "✅ Fresh"
        elif age_hours < 6:
            status = "⚠️  Aging"
        else:
            status = "❌ Stale"
        
        print(f"  {row.symbol:<15} {row.timeframe:<6} {row.count:<10} {row.last_candle.strftime('%Y-%m-%d %H:%M'):<20} {status:<10}")


def generate_recommendations(bug032_stats, h4_stats, dual_cache_stats):
    """
    Generate correction recommendations based on assessment.
    """
    print_header("Recommendations")
    
    recommendations = []
    
    # BUG-032 recommendations
    if bug032_stats.get('corrupted_days', 0) > 0:
        recommendations.append(
            f"🔴 BUG-032 Correction Required: {bug032_stats['corrupted_days']} corrupted days found\n"
            f"   Action: Delete midnight-only h1 candles and backfill\n"
            f"   Command: python scripts/correct_historical_data.py --correct"
        )
    
    # h4 data recommendations
    if h4_stats.get('total', 0) == 0:
        recommendations.append(
            f"🔴 h4 Data Missing: No h4 candles found\n"
            f"   Action: Trigger backfill with 4h aggregation\n"
            f"   Note: 4h aggregation now implemented for Twelve Data pairs"
        )
    elif h4_stats.get('total', 0) < 100:
        recommendations.append(
            f"⚠️  Insufficient h4 Data: Only {h4_stats['total']} candles\n"
            f"   Action: Backfill recommended (target: 200+ candles per symbol)"
        )
    
    # Dual-cache recommendations
    if dual_cache_stats.get('cache_count', 0) > 0:
        recommendations.append(
            f"⚠️  Dual-Cache Present: {dual_cache_stats['cache_count']:,} rows in ohlcv_cache\n"
            f"   Action: Monitor for 48h, then drop ohlcv_cache table\n"
            f"   Command: python scripts/phase5_cleanup_cache.py"
        )
    
    if not recommendations:
        print("  ✅ No critical issues found. Data quality is good.")
        return
    
    print("  Based on the assessment, the following actions are recommended:\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}\n")


def main():
    """Main assessment function."""
    print_header("DATA QUALITY ASSESSMENT")
    print(f"  Timestamp: {datetime.utcnow().isoformat()} UTC")
    print(f"  Database: positions.db (ohlcv_universal table)")
    
    try:
        with get_db_context() as db:
            # Run assessments
            bug032_stats = assess_bug032_corruption(db)
            h4_stats = assess_h4_data(db)
            dual_cache_stats = assess_dual_cache(db)
            assess_data_freshness(db, hours=24)
            
            # Generate recommendations
            generate_recommendations(bug032_stats, h4_stats, dual_cache_stats)
            
            print_header("ASSESSMENT COMPLETE")
            
            # Save results to file for reference
            results_file = project_root / "data" / f"assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            try:
                with open(results_file, 'w') as f:
                    f.write(f"Assessment Results - {datetime.utcnow().isoformat()} UTC\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"BUG-032 Corrupted Days: {bug032_stats.get('corrupted_days', 0)}\n")
                    f.write(f"Total h1 Candles: {bug032_stats.get('total_h1_candles', 0):,}\n")
                    f.write(f"Total h4 Candles: {h4_stats.get('total', 0):,}\n")
                    f.write(f"ohlcv_cache Rows: {dual_cache_stats.get('cache_count', 0):,}\n")
                    f.write(f"ohlcv_universal Rows: {dual_cache_stats.get('universal_count', 0):,}\n")
                
                print(f"  Results saved to: {results_file}")
            except Exception as e:
                print(f"  ⚠️  Could not save results: {e}")
            
    except Exception as e:
        print(f"\n❌ Assessment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
