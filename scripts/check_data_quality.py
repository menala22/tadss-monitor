#!/usr/bin/env python3
"""
Data Quality Check Script

Run comprehensive data quality checks on OHLCV data.

Usage:
    python scripts/check_data_quality.py [--symbol SYMBOL] [--report] [--alert]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.models.ohlcv_universal_model import OHLCVUniversal
from sqlalchemy import func, and_


class DataQualityChecker:
    """Run data quality checks"""
    
    def __init__(self, db):
        self.db = db
    
    def check_freshness(self, symbol: str, timeframe: str) -> dict:
        """Check if data is fresh"""
        last_candle = self.db.query(
            func.max(OHLCVUniversal.timestamp)
        ).filter(
            and_(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe
            )
        ).scalar()
        
        if not last_candle:
            return {'status': 'FAIL', 'reason': 'No data'}
        
        age = (datetime.utcnow() - last_candle).total_seconds() / 60
        
        # Max age by timeframe
        max_age_map = {
            'm1': 5, 'm5': 10, 'm15': 20, 'm30': 35,
            'h1': 65, 'h4': 250, 'd1': 1500, 'w1': 10080
        }
        max_age = max_age_map.get(timeframe, 60)
        
        if age > max_age * 2:
            status = 'FAIL'
        elif age > max_age:
            status = 'WARN'
        else:
            status = 'PASS'
        
        return {
            'status': status,
            'last_candle': last_candle.isoformat(),
            'age_minutes': round(age, 1),
            'max_age_minutes': max_age
        }
    
    def check_completeness(self, symbol: str, timeframe: str) -> dict:
        """Check if we have enough candles"""
        # Expected: 200 candles for HTF, 50 for MTF, 50 for LTF
        expected_map = {
            'm1': 100, 'm5': 100, 'm15': 100, 'm30': 100,
            'h1': 200, 'h4': 200, 'd1': 200, 'w1': 100
        }
        expected = expected_map.get(timeframe, 100)
        
        actual = self.db.query(
            func.count(OHLCVUniversal.id)
        ).filter(
            and_(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe
            )
        ).scalar()
        
        completeness = (actual / expected * 100) if expected > 0 else 0
        
        if completeness < 90:
            status = 'FAIL'
        elif completeness < 95:
            status = 'WARN'
        else:
            status = 'PASS'
        
        return {
            'status': status,
            'expected': expected,
            'actual': actual,
            'completeness_pct': round(completeness, 1)
        }
    
    def check_accuracy(self, symbol: str, timeframe: str) -> dict:
        """Check for OHLC accuracy issues"""
        candles = self.db.query(OHLCVUniversal).filter(
            and_(
                OHLCVUniversal.symbol == symbol,
                OHLCVUniversal.timeframe == timeframe
            )
        ).order_by(
            OHLCVUniversal.timestamp.desc()
        ).limit(100).all()
        
        issues = []
        for candle in candles:
            if candle.high < candle.low:
                issues.append(f"High < Low at {candle.timestamp}")
            if candle.open > candle.high:
                issues.append(f"Open > High at {candle.timestamp}")
            if candle.close > candle.high:
                issues.append(f"Close > High at {candle.timestamp}")
            if candle.close < candle.low:
                issues.append(f"Close < Low at {candle.timestamp}")
        
        if len(issues) > 5:
            status = 'FAIL'
        elif issues:
            status = 'WARN'
        else:
            status = 'PASS'
        
        return {
            'status': status,
            'issues': issues[:10],
            'issue_count': len(issues)
        }
    
    def run_all_checks(self, symbol: str, timeframe: str = 'all') -> dict:
        """Run all checks for a symbol"""
        result = {
            'symbol': symbol,
            'timestamp': datetime.utcnow().isoformat(),
            'timeframes': {}
        }
        
        timeframes = ['h1', 'h4', 'd1'] if timeframe == 'all' else [timeframe]
        
        for tf in timeframes:
            result['timeframes'][tf] = {
                'freshness': self.check_freshness(symbol, tf),
                'completeness': self.check_completeness(symbol, tf),
                'accuracy': self.check_accuracy(symbol, tf)
            }
        
        # Overall status
        statuses = []
        for tf_data in result['timeframes'].values():
            for check in tf_data.values():
                statuses.append(check['status'])
        
        if 'FAIL' in statuses:
            result['overall_status'] = 'FAIL'
        elif 'WARN' in statuses:
            result['overall_status'] = 'WARN'
        else:
            result['overall_status'] = 'PASS'
        
        return result


def main():
    parser = argparse.ArgumentParser(description='Check data quality')
    parser.add_argument('--symbol', type=str, help='Specific symbol to check')
    parser.add_argument('--timeframe', type=str, default='all', help='Timeframe to check')
    parser.add_argument('--report', action='store_true', help='Generate JSON report')
    parser.add_argument('--alert', action='store_true', help='Send alerts for failures')
    
    args = parser.parse_args()
    
    with get_db_context() as db:
        checker = DataQualityChecker(db)
        
        # Get symbols to check
        if args.symbol:
            symbols = [args.symbol]
        else:
            symbols = db.query(OHLCVUniversal.symbol).distinct().all()
            symbols = [s[0] for s in symbols]
        
        print("=" * 70)
        print("🔍 DATA QUALITY CHECK")
        print("=" * 70)
        print()
        
        results = []
        for symbol in symbols:
            result = checker.run_all_checks(symbol, args.timeframe)
            results.append(result)
            
            # Print summary
            status_emoji = {
                'PASS': '✅',
                'WARN': '⚠️ ',
                'FAIL': '❌'
            }
            emoji = status_emoji.get(result['overall_status'], '❓')
            
            print(f"{emoji} {symbol}")
            
            for tf, checks in result['timeframes'].items():
                print(f"  {tf}:")
                for check_name, check_data in checks.items():
                    status = check_data['status']
                    status_symbol = '✓' if status == 'PASS' else ('⚠' if status == 'WARN' else '✗')
                    print(f"    {status_symbol} {check_name}: {status}")
            
            print()
        
        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        total = len(results)
        passed = sum(1 for r in results if r['overall_status'] == 'PASS')
        warned = sum(1 for r in results if r['overall_status'] == 'WARN')
        failed = sum(1 for r in results if r['overall_status'] == 'FAIL')
        
        print(f"Total symbols: {total}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"❌ Failed: {failed}")
        print()
        
        # Generate report
        if args.report:
            report_file = f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.utcnow().isoformat(),
                    'results': results
                }, f, indent=2)
            print(f"📄 Report saved to: {report_file}")
        
        # Send alerts
        if args.alert and failed > 0:
            print()
            print("🚨 CRITICAL ISSUES FOUND")
            for result in results:
                if result['overall_status'] == 'FAIL':
                    print(f"  - {result['symbol']}: Multiple checks failed")
                    for tf, checks in result['timeframes'].items():
                        for check_name, check_data in checks.items():
                            if check_data['status'] == 'FAIL':
                                print(f"    - {tf}/{check_name}: {check_data.get('reason', 'Failed')}")
        
        # Exit with error if any failures
        sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
