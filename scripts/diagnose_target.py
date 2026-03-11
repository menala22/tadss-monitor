#!/usr/bin/env python3
"""
Target Price Diagnostic Script.

This script shows how the target price was calculated for the latest opportunity.

Usage:
    python scripts/diagnose_target.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_context
from src.models.mtf_opportunity_model import MTFOpportunity
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.services.target_calculator import TargetCalculator, TargetMethod
import pandas as pd

def load_ohlcv(db, pair, timeframe, limit=200):
    """Load OHLCV data for a pair/timeframe."""
    candles = db.query(OHLCVUniversal).filter(
        OHLCVUniversal.symbol == pair,
        OHLCVUniversal.timeframe == timeframe,
    ).order_by(
        OHLCVUniversal.timestamp.desc()
    ).limit(limit).all()
    
    if not candles:
        return None
    
    data = [c.to_dict() for c in candles]
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp').reset_index(drop=True)
    df.set_index('timestamp', inplace=True)
    columns = ['open', 'high', 'low', 'close', 'volume']
    return df[columns]

def diagnose_latest_opportunity():
    """Diagnose target calculation for latest opportunity."""
    with get_db_context() as db:
        # Get latest opportunity
        opp = db.query(MTFOpportunity).order_by(MTFOpportunity.timestamp.desc()).first()
        
        if not opp:
            print("❌ No opportunities in database")
            return
        
        print("=" * 80)
        print("🎯 TARGET PRICE CALCULATION DIAGNOSTIC")
        print("=" * 80)
        print()
        print(f"Opportunity: {opp.pair} ({opp.trading_style})")
        print(f"Timestamp: {opp.timestamp}")
        print(f"Recommendation: {opp.recommendation}")
        print()
        
        # Current saved values
        print("💾 SAVED VALUES:")
        print(f"  Entry Price:  ${opp.entry_price:,.2f}" if opp.entry_price else "  Entry Price:  N/A")
        print(f"  Stop Loss:    ${opp.stop_loss:,.2f}" if opp.stop_loss else "  Stop Loss:    N/A")
        print(f"  Target Price: ${opp.target_price:,.2f}" if opp.target_price else "  Target Price: N/A")
        print(f"  R:R Ratio:    {opp.rr_ratio:.1f}:1")
        print()
        
        # Load HTF and MTF data
        htf_tf = "d1" if opp.trading_style == "SWING" else "h4"
        mtf_tf = "h4" if opp.trading_style == "SWING" else "h1"
        
        print(f"📊 Loading market data...")
        print(f"  HTF Timeframe: {htf_tf}")
        print(f"  MTF Timeframe: {mtf_tf}")
        
        htf_df = load_ohlcv(db, opp.pair, htf_tf)
        mtf_df = load_ohlcv(db, opp.pair, mtf_tf)
        
        if htf_df is None or mtf_df is None:
            print("❌ Could not load market data for target calculation")
            return
        
        print(f"  HTF candles: {len(htf_df)}")
        print(f"  MTF candles: {len(mtf_df)}")
        print()
        
        # Recalculate target using different methods
        if not opp.entry_price or not opp.stop_loss:
            print("❌ Missing entry or stop loss, cannot calculate target")
            return
        
        direction = "LONG" if opp.recommendation == "BUY" else "SHORT"
        calc = TargetCalculator()
        
        print("=" * 80)
        print("🎯 TARGET CALCULATION BY METHOD")
        print("=" * 80)
        print()
        
        methods = [
            TargetMethod.SR_LEVEL,
            TargetMethod.MEASURED_MOVE,
            TargetMethod.FIBONACCI,
            TargetMethod.ATR,
            TargetMethod.PRIOR_SWING,
        ]
        
        results = []
        for method in methods:
            try:
                target_result = calc.calculate_target(
                    df_htf=htf_df,
                    df_mtf=mtf_df,
                    entry_price=opp.entry_price,
                    stop_loss=opp.stop_loss,
                    direction=direction,
                    method=method,
                )
                
                risk = abs(opp.entry_price - opp.stop_loss)
                reward = abs(target_result.target_price - opp.entry_price)
                rr = reward / risk if risk > 0 else 0
                
                results.append({
                    'method': method.value,
                    'target': target_result.target_price,
                    'rr': rr,
                    'confidence': target_result.confidence,
                    'description': target_result.description,
                })
                
                print(f"{method.value:15} → Target: ${target_result.target_price:>10,.2f}  |  R:R: {rr:>5.2f}:1  |  Confidence: {target_result.confidence:.2f}")
                if target_result.description:
                    print(f"                  {target_result.description}")
                print()
                
            except Exception as e:
                print(f"{method.value:15} → ❌ Error: {e}")
                print()
        
        print("=" * 80)
        print("📊 COMPARISON")
        print("=" * 80)
        print()
        print(f"Saved Target:      ${opp.target_price:,.2f}  (R:R: {opp.rr_ratio:.1f}:1)")
        print()
        
        # Find closest match
        if results:
            closest = min(results, key=lambda x: abs(x['target'] - opp.target_price))
            print(f"Closest method:    ${closest['target']:,.2f}  ({closest['method']}, R:R: {closest['rr']:.2f}:1)")
            print()
            
            # Show best R:R method
            best_rr = max(results, key=lambda x: x['rr'])
            print(f"Best R:R method:   ${best_rr['target']:,.2f}  ({best_rr['method']}, R:R: {best_rr['rr']:.2f}:1)")
            print()
        
        print("=" * 80)
        print("💡 ANALYSIS")
        print("=" * 80)
        print()
        
        if opp.rr_ratio == 2.0:
            print("⚠️  R:R is exactly 2.0:1 - This is the MINIMUM filter threshold.")
            print()
            print("The target calculator likely calculated a target that achieves")
            print("exactly 2:1 R:R, which is the minimum acceptable for saving")
            print("the opportunity.")
            print()
            print("To get better targets, consider:")
            print("  1. Using HTF S/R levels (more realistic targets)")
            print("  2. Using measured move patterns (pattern-based)")
            print("  3. Using Fibonacci extensions (for trending markets)")
        elif opp.rr_ratio > 2.5:
            print("✅ Good R:R ratio (>2.5:1) - Target is based on actual market structure")
        else:
            print(f"ℹ️  R:R ratio is {opp.rr_ratio:.1f}:1 - Moderate risk:reward")
        
        print()

if __name__ == "__main__":
    diagnose_latest_opportunity()
