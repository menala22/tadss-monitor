#!/usr/bin/env python3
"""
MTF Scan Status Checker

This script verifies if the MTF hourly scan is running at :30 as designed.

Usage:
    python check_mtf_scan.py
"""

from datetime import datetime, timedelta
from src.database import get_db_context
from src.models.mtf_opportunity_model import MTFOpportunity
from src.models.mtf_watchlist_model import MTFWatchlistItem


def check_mtf_scan_status():
    """Check MTF scan status and recent opportunities."""
    
    print("=" * 70)
    print("MTF SCAN STATUS CHECK")
    print("=" * 70)
    print(f"Current UTC time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Schedule: Every hour at :30 minutes")
    print("=" * 70)
    
    with get_db_context() as db:
        # Check watchlist
        watchlist = db.query(MTFWatchlistItem).all()
        print(f"\n📋 MTF Watchlist: {len(watchlist)} pairs")
        for item in watchlist:
            styles = item.get_trading_styles()
            print(f"  - {item.pair}: {styles}")
        
        # Check recent opportunities
        print("\n📊 Recent MTF Opportunities (last 20):")
        print("-" * 70)
        
        opps = db.query(MTFOpportunity).order_by(
            MTFOpportunity.created_at.desc()
        ).limit(20).all()
        
        if not opps:
            print("  ⚠️  No opportunities found!")
        else:
            now = datetime.utcnow()
            for opp in opps:
                age = now - opp.created_at
                age_str = str(age).split('.')[0]
                trading_style = opp.trading_style if isinstance(opp.trading_style, str) else opp.trading_style.value
                print(f"  {opp.pair:12} | {trading_style:8} | "
                      f"weighted={opp.weighted_score:.2f} | "
                      f"age={age_str:>12} | "
                      f"created={opp.created_at.strftime('%H:%M:%S')}")
        
        # Check for opportunities created in the last 2 hours
        print("\n" + "=" * 70)
        print("RECENT ACTIVITY (Last 2 Hours):")
        print("=" * 70)
        
        two_hours_ago = now - timedelta(hours=2)
        recent_opps = db.query(MTFOpportunity).filter(
            MTFOpportunity.created_at >= two_hours_ago
        ).all()
        
        if recent_opps:
            print(f"  ✅ {len(recent_opps)} opportunities created in last 2 hours")
            
            # Group by hour
            hour_counts = {}
            for opp in recent_opps:
                hour = opp.created_at.strftime('%Y-%m-%d %H:00')
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            print("\n  Opportunities by hour:")
            for hour, count in sorted(hour_counts.items()):
                print(f"    {hour} - {count} opportunities")
        else:
            print("  ⚠️  No opportunities created in last 2 hours")
            print("  MTF scan may not be running!")
        
        # Check for scan times
        print("\n" + "=" * 70)
        print("EXPECTED vs ACTUAL SCAN TIMES:")
        print("=" * 70)
        
        # Get unique scan times from opportunities
        scan_times = set()
        for opp in opps[:50]:  # Check last 50 opportunities
            scan_time = opp.created_at.strftime('%Y-%m-%d %H:%M')
            scan_times.add(scan_time)
        
        print("\n  Last 10 unique scan times:")
        for scan_time in sorted(scan_times, reverse=True)[:10]:
            # Check if it's at :30
            minute = scan_time.split(':')[1]
            marker = "✅" if minute == '30' else "⚠️ "
            print(f"    {marker} {scan_time}")
        
        # Summary
        print("\n" + "=" * 70)
        print("VERDICT:")
        print("=" * 70)
        
        # Check if last scan was at :30
        if opps:
            last_scan = opps[0].created_at
            last_minute = last_scan.strftime('%M')
            
            if last_minute == '30':
                print(f"  ✅ MTF scan is running at :30 as designed")
                print(f"     Last scan: {last_scan.strftime('%Y-%m-%d %H:%M UTC')}")
            else:
                print(f"  ⚠️  Last scan was at :{last_minute}, not :30")
                print(f"     Last scan: {last_scan.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            print("  ⚠️  No recent scan data available")
            print("     Wait until next :30 and check again")
        
        print("=" * 70)


if __name__ == "__main__":
    check_mtf_scan_status()
