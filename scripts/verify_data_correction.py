#!/usr/bin/env python3
"""
Verify Historical Data Correction was Successful.

This script verifies that the data correction process completed successfully by:
1. Checking h1 data has all 24 hours represented
2. Checking h4 data is available with correct timestamps
3. Checking data freshness (last 24-48 hours)
4. Generating a verification report

Usage:
    python scripts/verify_data_correction.py
    
    # With custom parameters
    python scripts/verify_data_correction.py --days 7 --symbols XAU/USD XAG/USD
"""

import argparse
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


def print_section(text: str):
    """Print section header."""
    print(f"\n{text}")
    print("-" * 80)


def verify_h1_data(db, days: int = 7, symbols: list = None):
    """
    Verify h1 data has all 24 hours represented.
    
    Returns (passed, details_dict).
    """
    if symbols is None:
        symbols = ['XAU/USD', 'XAG/USD']
    
    print_section(f"[1] h1 Data Verification (Last {days} Days)")
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    all_passed = True
    details = {}
    
    for symbol in symbols:
        h1_candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == 'h1',
            OHLCVUniversal.timestamp >= cutoff
        ).all()
        
        if not h1_candles:
            print(f"\n  ❌ {symbol}: No h1 candles found in last {days} days")
            all_passed = False
            details[symbol] = {
                'passed': False,
                'reason': 'No candles found',
                'count': 0,
                'hours': []
            }
            continue
        
        # Analyze hour distribution
        hours = sorted(set(c.timestamp.hour for c in h1_candles))
        hour_count = len(hours)
        
        # Count candles per hour
        candles_per_hour = defaultdict(int)
        for c in h1_candles:
            candles_per_hour[c.timestamp.hour] += 1
        
        # Expected: 24 hours, roughly equal distribution
        expected_hours = list(range(24))
        missing_hours = set(expected_hours) - set(hours)
        
        print(f"\n  {symbol}:")
        print(f"    Total candles: {len(h1_candles):,}")
        print(f"    Unique hours: {hour_count}/24")
        
        if hour_count == 24:
            print(f"    ✅ All 24 hours present")
        else:
            print(f"    ❌ Missing hours: {sorted(missing_hours)}")
            all_passed = False
        
        # Check distribution (should be roughly equal)
        if candles_per_hour:
            avg_per_hour = len(h1_candles) / 24
            min_per_hour = min(candles_per_hour.values())
            max_per_hour = max(candles_per_hour.values())
            print(f"    Candles per hour: {min_per_hour}-{max_per_hour} (avg: {avg_per_hour:.1f})")
        
        details[symbol] = {
            'passed': hour_count == 24,
            'count': len(h1_candles),
            'hours': hours,
            'missing_hours': list(missing_hours),
            'candles_per_hour': dict(candles_per_hour)
        }
    
    return all_passed, details


def verify_h4_data(db, symbols: list = None):
    """
    Verify h4 data is available with correct timestamps.
    
    Returns (passed, details_dict).
    """
    if symbols is None:
        symbols = ['XAU/USD', 'XAG/USD']
    
    print_section(f"[2] h4 Data Verification")
    
    all_passed = True
    details = {}
    
    # Expected h4 timestamps: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    expected_hours = {0, 4, 8, 12, 16, 20}
    
    for symbol in symbols:
        h4_candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == 'h4'
        ).all()
        
        if not h4_candles:
            print(f"\n  ❌ {symbol}: No h4 candles found")
            all_passed = False
            details[symbol] = {
                'passed': False,
                'reason': 'No candles found',
                'count': 0,
                'hours': []
            }
            continue
        
        # Analyze hour distribution
        hours = sorted(set(c.timestamp.hour for c in h4_candles))
        hour_set = set(hours)
        
        # Get date range
        dates = [c.timestamp for c in h4_candles]
        first_date = min(dates).date()
        last_date = max(dates).date()
        
        print(f"\n  {symbol}:")
        print(f"    Total candles: {len(h4_candles):,}")
        print(f"    Date range: {first_date} to {last_date}")
        print(f"    Hours present: {hours}")
        
        # Check if we have enough candles
        days_range = (max(dates) - min(dates)).days + 1
        expected_candles = days_range * 6  # 6 candles per day (24h / 4h)
        coverage = len(h4_candles) / expected_candles * 100 if expected_candles > 0 else 0
        
        print(f"    Expected candles: ~{expected_candles} ({days_range} days × 6)")
        print(f"    Coverage: {coverage:.1f}%")
        
        if len(h4_candles) >= 100:
            print(f"    ✅ Sufficient data (≥100 candles)")
        else:
            print(f"    ⚠️  Insufficient data (<100 candles)")
        
        # Check hour distribution
        if hour_set == expected_hours:
            print(f"    ✅ Correct h4 boundaries (0, 4, 8, 12, 16, 20)")
        else:
            missing = expected_hours - hour_set
            extra = hour_set - expected_hours
            if missing:
                print(f"    ❌ Missing hours: {sorted(missing)}")
                all_passed = False
            if extra:
                print(f"    ⚠️  Unexpected hours: {sorted(extra)}")
        
        details[symbol] = {
            'passed': len(h4_candles) >= 100 and hour_set == expected_hours,
            'count': len(h4_candles),
            'hours': hours,
            'expected_hours': list(expected_hours),
            'coverage': coverage,
            'date_range': (first_date, last_date)
        }
    
    return all_passed, details


def verify_data_freshness(db, hours: int = 24, symbols: list = None):
    """
    Verify data freshness (last N hours).
    
    Returns (passed, details_dict).
    """
    if symbols is None:
        symbols = ['XAU/USD', 'XAG/USD', 'BTC/USDT', 'ETH/USDT']
    
    print_section(f"[3] Data Freshness (Last {hours} Hours)")
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    all_passed = True
    details = {}
    
    print(f"\n  {'Symbol':<15} {'TF':<6} {'Candles':<10} {'Last Candle':<20} {'Age (h)':<10} {'Status':<10}")
    print(f"  {'-'*15} {'-'*6} {'-'*10} {'-'*20} {'-'*10} {'-'*10}")
    
    for symbol in symbols:
        for timeframe in ['h1', 'h4', 'd1']:
            candles = db.query(OHLCVUniversal).filter(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe,
                OHLCVUniversal.timestamp >= cutoff
            ).all()
            
            if not candles:
                continue
            
            last_candle = max(c.timestamp for c in candles)
            age_hours = (datetime.utcnow() - last_candle).total_seconds() / 3600
            
            # Determine status
            if timeframe == 'h1':
                max_age = 2  # 2 hours for h1
            elif timeframe == 'h4':
                max_age = 6  # 6 hours for h4
            else:
                max_age = 48  # 48 hours for d1
            
            if age_hours < max_age:
                status = "✅ Fresh"
            elif age_hours < max_age * 2:
                status = "⚠️  Aging"
            else:
                status = "❌ Stale"
                all_passed = False
            
            print(f"  {symbol:<15} {timeframe:<6} {len(candles):<10} {last_candle.strftime('%Y-%m-%d %H:%M'):<20} {age_hours:<10.1f} {status:<10}")
        
        print()  # Blank line between symbols
    
    return all_passed, {'freshness_check': 'passed' if all_passed else 'failed'}


def verify_no_midnight_only_days(db, symbols: list = None):
    """
    Verify there are no days with only midnight candles (BUG-032 pattern).
    
    Returns (passed, details_dict).
    """
    if symbols is None:
        symbols = ['XAU/USD', 'XAG/USD']
    
    print_section("[4] BUG-032 Pattern Check (No Midnight-Only Days)")
    
    all_passed = True
    details = {}
    
    for symbol in symbols:
        h1_candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == symbol,
            OHLCVUniversal.timeframe == 'h1'
        ).all()
        
        if not h1_candles:
            continue
        
        # Group by date
        by_date = defaultdict(list)
        for c in h1_candles:
            by_date[c.timestamp.date()].append(c)
        
        # Check for midnight-only days
        midnight_only_days = []
        for date, candles in by_date.items():
            hours = set(c.timestamp.hour for c in candles)
            if hours == {0}:
                midnight_only_days.append(date)
        
        print(f"\n  {symbol}:")
        print(f"    Total days with data: {len(by_date)}")
        print(f"    Midnight-only days: {len(midnight_only_days)}")
        
        if len(midnight_only_days) == 0:
            print(f"    ✅ No midnight-only days (BUG-032 fixed)")
        else:
            print(f"    ❌ Found {len(midnight_only_days)} midnight-only days:")
            for date in midnight_only_days[:5]:  # Show first 5
                print(f"       - {date}")
            if len(midnight_only_days) > 5:
                print(f"       ... and {len(midnight_only_days) - 5} more")
            all_passed = False
        
        details[symbol] = {
            'passed': len(midnight_only_days) == 0,
            'total_days': len(by_date),
            'midnight_only_days': midnight_only_days
        }
    
    return all_passed, details


def generate_report(h1_result, h4_result, freshness_result, bug032_result):
    """Generate verification report."""
    print_header("VERIFICATION REPORT")
    
    all_passed = all([h1_result[0], h4_result[0], freshness_result[0], bug032_result[0]])
    
    print(f"  Overall Status: {'✅ PASSED' if all_passed else '❌ FAILED'}\n")
    
    print(f"  {'Check':<40} {'Status':<10}")
    print(f"  {'-'*40} {'-'*10}")
    print(f"  {'h1 Data (24 hours)':<40} {'✅ PASS' if h1_result[0] else '❌ FAIL':<10}")
    print(f"  {'h4 Data (100+ candles)':<40} {'✅ PASS' if h4_result[0] else '❌ FAIL':<10}")
    print(f"  {'Data Freshness':<40} {'✅ PASS' if freshness_result[0] else '❌ FAIL':<10}")
    print(f"  {'BUG-032 Pattern Check':<40} {'✅ PASS' if bug032_result[0] else '❌ FAIL':<10}")
    
    if all_passed:
        print("\n  ✅ All verification checks passed!")
        print("  Data correction was successful.")
    else:
        print("\n  ❌ Some verification checks failed.")
        print("  Review the details above and consider re-running correction.")
    
    return all_passed


def main():
    """Main verification function."""
    parser = argparse.ArgumentParser(description='Verify historical data correction')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to check for h1 data (default: 7)')
    parser.add_argument('--freshness-hours', type=int, default=24,
                       help='Hours to check for data freshness (default: 24)')
    parser.add_argument('--symbols', nargs='+', default=['XAU/USD', 'XAG/USD', 'BTC/USDT', 'ETH/USDT'],
                       help='Symbols to verify (default: XAU/USD, XAG/USD, BTC/USDT, ETH/USDT)')
    
    args = parser.parse_args()
    
    print_header("DATA CORRECTION VERIFICATION")
    print(f"  Timestamp: {datetime.utcnow().isoformat()} UTC")
    print(f"  h1 check period: Last {args.days} days")
    print(f"  Freshness check: Last {args.freshness_hours} hours")
    print(f"  Symbols: {', '.join(args.symbols)}")
    
    try:
        with get_db_context() as db:
            # Run verifications
            h1_result = verify_h1_data(db, args.days, args.symbols)
            h4_result = verify_h4_data(db, args.symbols)
            freshness_result = verify_data_freshness(db, args.freshness_hours, args.symbols)
            bug032_result = verify_no_midnight_only_days(db, args.symbols)
            
            # Generate report
            all_passed = generate_report(h1_result, h4_result, freshness_result, bug032_result)
            
            # Save report to file
            report_file = project_root / "data" / f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            try:
                with open(report_file, 'w') as f:
                    f.write(f"Verification Report - {datetime.utcnow().isoformat()} UTC\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(f"Overall Status: {'PASSED' if all_passed else 'FAILED'}\n\n")
                    f.write(f"Symbols checked: {', '.join(args.symbols)}\n")
                    f.write(f"h1 check period: Last {args.days} days\n")
                    f.write(f"Freshness check: Last {args.freshness_hours} hours\n")
                
                print(f"\n  Report saved to: {report_file}")
            except Exception as e:
                print(f"\n  ⚠️  Could not save report: {e}")
            
            # Exit with appropriate code
            sys.exit(0 if all_passed else 1)
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
