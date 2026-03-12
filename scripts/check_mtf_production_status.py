#!/usr/bin/env python3
"""Check MTF production status - opportunities and data availability."""

from src.database import get_db_context
from src.models.mtf_opportunity_model import MTFOpportunity
from src.models.ohlcv_universal_model import OHLCVUniversal
from sqlalchemy import func

def main():
    with get_db_context() as db:
        # Check opportunities
        opps = db.query(MTFOpportunity).filter(MTFOpportunity.status == 'ACTIVE').count()
        print(f"Active opportunities: {opps}")
        
        total_opps = db.query(MTFOpportunity).count()
        print(f"Total opportunities (all statuses): {total_opps}")
        
        # Check candle data
        pairs = ['BTC/USDT', 'ETH/USDT', 'XAG/USD', 'EUR/USD']
        for pair in pairs:
            candles = db.query(func.count(OHLCVUniversal.id)).filter(
                OHLCVUniversal.symbol == pair
            ).scalar()
            print(f"{pair} candles in ohlcv_universal: {candles}")
            
            # Check latest timestamp
            latest = db.query(OHLCVUniversal.timestamp).filter(
                OHLCVUniversal.symbol == pair
            ).order_by(OHLCVUniversal.timestamp.desc()).first()
            if latest:
                print(f"  Latest: {latest[0]}")
            else:
                print(f"  No data!")

if __name__ == '__main__':
    main()
