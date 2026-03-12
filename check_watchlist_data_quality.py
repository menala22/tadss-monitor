#!/usr/bin/env python3
"""
Check MTF Watchlist Data Quality.

This script checks all pairs in the MTF watchlist and verifies their
data quality in the ohlcv_universal and market_data_status tables.

Usage:
    python check_watchlist_data_quality.py
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, '.')

from src.models.mtf_watchlist_model import MTFWatchlistItem, get_watchlist
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.models.market_data_status_model import MarketDataStatus, DataQuality
from src.database import db_manager


def get_actual_candle_counts(db: Session) -> Dict[str, Dict[str, int]]:
    """
    Get actual candle counts from ohlcv_universal table.
    
    Returns:
        Dict of pair -> {timeframe -> candle_count}
    """
    result = {}
    
    # Query all pairs and timeframes with their counts
    query = db.query(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe,
        func.count(OHLCVUniversal.id).label('candle_count')
    ).group_by(
        OHLCVUniversal.symbol,
        OHLCVUniversal.timeframe
    ).all()
    
    for symbol, timeframe, count in query:
        if symbol not in result:
            result[symbol] = {}
        result[symbol][timeframe] = count
    
    return result


def check_pair_data_quality(
    db: Session,
    pair: str,
    actual_counts: Dict[str, Dict[str, int]]
) -> dict:
    """
    Check data quality for a single pair.
    
    Returns:
        Dict with quality assessment for each timeframe and overall.
    """
    # Get status entries
    status_entries = db.query(MarketDataStatus).filter(
        MarketDataStatus.pair == pair
    ).all()
    
    result = {
        'pair': pair,
        'timeframes': {},
        'overall_quality': 'MISSING',
        'mtf_ready': False,
        'issues': []
    }
    
    # Check if pair exists in ohlcv_universal
    if pair not in actual_counts:
        result['issues'].append('❌ No data in ohlcv_universal table')
        return result
    
    # Required timeframes for SWING trading
    required_timeframes = ['w1', 'd1', 'h4']
    
    # Check each timeframe
    quality_order = {
        'EXCELLENT': 4,
        'GOOD': 3,
        'STALE': 2,
        'MISSING': 1
    }
    
    min_quality = 4  # Start with EXCELLENT
    
    for tf in required_timeframes:
        tf_info = {
            'candle_count': 0,
            'quality': 'MISSING',
            'status': 'MISSING'
        }
        
        # Get actual count
        if tf in actual_counts.get(pair, {}):
            tf_info['candle_count'] = actual_counts[pair][tf]
        
        # Get status entry
        status_entry = next(
            (s for s in status_entries if s.timeframe == tf),
            None
        )
        
        if status_entry:
            tf_info['status'] = status_entry.data_quality
            tf_info['last_candle'] = status_entry.last_candle_time
            tf_info['source'] = status_entry.source
        else:
            tf_info['status'] = 'MISSING'
        
        # Calculate quality based on candle count
        count = tf_info['candle_count']
        if count >= 200:
            tf_info['quality'] = 'EXCELLENT'
        elif count >= 100:
            tf_info['quality'] = 'GOOD'
        elif count >= 50:
            tf_info['quality'] = 'STALE'
        else:
            tf_info['quality'] = 'MISSING'
            if count > 0:
                result['issues'].append(f'❌ {tf}: Only {count} candles (need 50+)')
            else:
                result['issues'].append(f'❌ {tf}: No data available')
        
        # Track minimum quality
        tf_quality_value = quality_order.get(tf_info['quality'], 1)
        if tf_quality_value < min_quality:
            min_quality = tf_quality_value
        
        result['timeframes'][tf] = tf_info
    
    # Determine overall quality
    quality_names = {4: 'EXCELLENT', 3: 'GOOD', 2: 'STALE', 1: 'MISSING'}
    result['overall_quality'] = quality_names[min_quality]
    
    # Check MTF readiness
    all_good = all(
        result['timeframes'].get(tf, {}).get('quality') in ['GOOD', 'EXCELLENT']
        for tf in required_timeframes
    )
    result['mtf_ready'] = all_good
    
    if all_good:
        result['issues'].append('✅ All timeframes have GOOD+ quality')
    
    return result


def print_report(pairs: List[str], results: List[dict]) -> None:
    """Print formatted report."""
    print("\n" + "=" * 80)
    print("MTF WATCHLIST DATA QUALITY REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.utcnow().isoformat()}")
    print(f"Pairs checked: {len(pairs)}")
    print("=" * 80 + "\n")
    
    mtf_ready_count = 0
    
    for result in results:
        pair = result['pair']
        overall = result['overall_quality']
        mtf_ready = result['mtf_ready']
        
        # Quality emoji
        quality_emoji = {
            'EXCELLENT': '🟢',
            'GOOD': '🟢',
            'STALE': '🟡',
            'MISSING': '🔴'
        }.get(overall, '⚪')
        
        print(f"{quality_emoji} {pair}")
        print(f"   Overall Quality: {overall}")
        print(f"   MTF Ready: {'✅ Yes' if mtf_ready else '❌ No'}")
        print()
        
        # Timeframe breakdown
        print("   Timeframe Breakdown:")
        for tf, info in result['timeframes'].items():
            tf_emoji = {
                'EXCELLENT': '🟢',
                'GOOD': '🟢',
                'STALE': '🟡',
                'MISSING': '🔴'
            }.get(info['quality'], '⚪')
            
            last_candle = info.get('last_candle')
            if last_candle:
                if isinstance(last_candle, datetime):
                    last_candle_str = last_candle.strftime('%Y-%m-%d %H:%M')
                else:
                    last_candle_str = str(last_candle)[:19]
            else:
                last_candle_str = 'N/A'
            
            source = info.get('source', 'N/A')
            
            print(f"   {tf_emoji} {tf:4s}: {info['candle_count']:4d} candles | "
                  f"Last: {last_candle_str} | Source: {source}")
        
        print()
        
        # Issues
        if result['issues']:
            print("   Issues:")
            for issue in result['issues']:
                print(f"   - {issue}")
            print()
        
        print("-" * 80 + "\n")
        
        if mtf_ready:
            mtf_ready_count += 1
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total pairs: {len(pairs)}")
    print(f"MTF Ready: {mtf_ready_count}/{len(pairs)}")
    print(f"Need attention: {len(pairs) - mtf_ready_count}")
    print()
    
    # Quality breakdown
    quality_counts = {'EXCELLENT': 0, 'GOOD': 0, 'STALE': 0, 'MISSING': 0}
    for result in results:
        quality_counts[result['overall_quality']] = quality_counts.get(result['overall_quality'], 0) + 1
    
    print("Quality Breakdown:")
    for quality, count in quality_counts.items():
        if count > 0:
            emoji = {'EXCELLENT': '🟢', 'GOOD': '🟢', 'STALE': '🟡', 'MISSING': '🔴'}.get(quality, '⚪')
            print(f"  {emoji} {quality}: {count}")
    
    print("=" * 80)
    
    # Recommendations
    needs_attention = [r for r in results if not r['mtf_ready']]
    if needs_attention:
        print("\nRECOMMENDATIONS:")
        for result in needs_attention:
            print(f"  • {result['pair']}: Run market data refresh")
        print("\n  To refresh all stale pairs:")
        print("  curl -X POST http://localhost:8000/api/v1/market-data/refresh-all")
    else:
        print("\n✅ All pairs have sufficient data quality for MTF scanning!")
    
    print()


def main():
    """Main function."""
    print("Checking MTF Watchlist data quality...\n")
    
    # Get database session
    db = db_manager.create_session()
    
    try:
        # Get watchlist
        watchlist = get_watchlist(db)
        print(f"Watchlist contains {len(watchlist)} pairs: {', '.join(watchlist)}\n")
        
        # Get actual candle counts from ohlcv_universal
        actual_counts = get_actual_candle_counts(db)
        
        # Check each pair
        results = []
        for pair in watchlist:
            result = check_pair_data_quality(db, pair, actual_counts)
            results.append(result)
        
        # Print report
        print_report(watchlist, results)
        
    finally:
        db.close()


if __name__ == '__main__':
    main()
