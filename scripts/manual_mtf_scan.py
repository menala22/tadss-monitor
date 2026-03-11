#!/usr/bin/env python3
"""
Manual MTF Opportunity Scan Script.

This script triggers an immediate MTF opportunity scan outside of the
scheduled hourly run. Useful for testing and on-demand analysis.

Usage:
    python scripts/manual_mtf_scan.py

    # With custom parameters
    python scripts/manual_mtf_scan.py --trading-style SWING --min-weighted 0.60
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from src.database import get_db_context
from src.models.mtf_models import TradingStyle
from src.models.mtf_watchlist_model import get_watchlist
from src.models.ohlcv_universal_model import OHLCVUniversal
from src.services.mtf_opportunity_scanner import MTFOpportunityScanner
from src.services.mtf_opportunity_service import MTFOpportunityService
from src.services.mtf_notifier import send_new_opportunity_alert

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_pair_data(db: Session, pair: str, config) -> dict:
    """Load HTF/MTF/LTF DataFrames for a pair from ohlcv_universal table."""
    roles = [
        ("htf", config.htf_timeframe),
        ("mtf", config.mtf_timeframe),
        ("ltf", config.ltf_timeframe),
    ]
    result = {}

    for role, internal_tf in roles:
        limit = 250 if role == "htf" else (150 if role == "mtf" else 100)

        # Query from ohlcv_universal
        candles = db.query(OHLCVUniversal).filter(
            OHLCVUniversal.symbol == pair,
            OHLCVUniversal.timeframe == internal_tf,
        ).order_by(
            OHLCVUniversal.timestamp.desc()
        ).limit(limit).all()

        if not candles or len(candles) < 10:
            logger.info(f"No data in ohlcv_universal for {pair} {internal_tf}")
            return None

        # Convert to DataFrame
        data = [c.to_dict() for c in candles]
        df = pd.DataFrame(data)

        # Sort by timestamp ascending
        df = df.sort_values('timestamp').reset_index(drop=True)
        df.set_index('timestamp', inplace=True)

        # Select OHLCV columns and rename to lowercase
        columns = ['open', 'high', 'low', 'close', 'volume']
        df = df[columns]

        result[role] = df

    return result


def run_manual_scan(
    trading_styles: list = None,
    min_weighted_score: float = 0.50,
    alert_threshold: float = 0.60,
    verbose: bool = True,
) -> dict:
    """
    Run manual MTF opportunity scan.

    Args:
        trading_styles: List of trading styles to scan (default: ["SWING"]).
        min_weighted_score: Minimum weighted score to save opportunity.
        alert_threshold: Minimum weighted score to send Telegram alert.
        verbose: Print detailed output.

    Returns:
        Dictionary with scan results.
    """
    if trading_styles is None:
        trading_styles = ["SWING"]
    
    start_time = datetime.utcnow()

    if verbose:
        print("=" * 60)
        print("🔍 MTF Manual Opportunity Scan")
        print("=" * 60)
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Trading Styles: {', '.join(trading_styles)}")
        print(f"Min Weighted Score: {min_weighted_score}")
        print(f"Alert Threshold: {alert_threshold}")
        print("-" * 60)

    try:
        with get_db_context() as db:
            # Get watchlist pairs
            watchlist = get_watchlist(db)
            if not watchlist:
                logger.error("No pairs in watchlist")
                return {"error": "No pairs in watchlist"}

            if verbose:
                print(f"Watchlist: {', '.join(watchlist)}")
                print(f"Trading Styles: {', '.join(trading_styles)}")
                print("-" * 60)

            # Track results
            opportunities_saved = []
            alerts_sent = []
            errors = []
            total_scanned = 0

            # Scan each pair with each trading style
            for pair in watchlist:
                for trading_style_str in trading_styles:
                    try:
                        trading_style = TradingStyle[trading_style_str.upper()]
                    except KeyError:
                        logger.error(f"Invalid trading style: {trading_style_str}")
                        errors.append(f"Invalid style: {trading_style_str}")
                        continue

                    total_scanned += 1

                    if verbose:
                        print(f"\n📊 Scanning {pair} ({trading_style.value})...")

                    try:
                        # Initialize scanner for this trading style
                        scanner = MTFOpportunityScanner(
                            min_alignment=2,
                            min_rr_ratio=2.0,
                            trading_style=trading_style,
                        )

                        # Load data from ohlcv_universal table
                        data = load_pair_data(db, pair, scanner.config)

                        if data is None:
                            if verbose:
                                print(f"  ⚠️  No data available, skipping")
                            continue

                        # Initialize service
                        opportunity_service = MTFOpportunityService(db)

                        # Run MTF analysis
                        alignment = scanner.analyzer.analyze_pair(
                            pair=pair,
                            htf_data=data["htf"],
                            mtf_data=data["mtf"],
                            ltf_data=data["ltf"],
                        )

                        if verbose:
                            print(f"  HTF Bias: {alignment.htf_bias.direction.value}")
                            print(f"  MTF Context: {alignment.mtf_setup.mtf_context}")
                            print(f"  Weighted Score: {alignment.weighted_score:.2f}")

                        # Check if should save
                        if opportunity_service.should_save_opportunity(alignment):
                            # Detect patterns
                            patterns = scanner._detect_patterns(
                                htf_bias=alignment.htf_bias,
                                mtf_setup=alignment.mtf_setup,
                                ltf_entry=alignment.ltf_entry,
                            )

                            # Detect divergence
                            divergence_result = scanner.divergence_detector.detect_divergence(data["mtf"])
                            divergence = divergence_result.latest_type.value if divergence_result.divergences else None

                            # Save opportunity with HTF/MTF data for target calculation
                            opp = opportunity_service.save_opportunity(
                                pair=pair,
                                alignment=alignment,
                                trading_style=trading_style,
                                patterns=patterns,
                                divergence=divergence,
                                htf_data=data["htf"],
                                mtf_data=data["mtf"],
                            )

                            opportunities_saved.append(opp)

                            if verbose:
                                if opp.id in [o.id for o in opportunities_saved[:-1]]:
                                    print(f"  ℹ️  Updated: {opp.pair} ({trading_style.value}) - Weighted: {opp.weighted_score:.2f}")
                                else:
                                    print(f"  ✅ Saved: {opp.pair} ({trading_style.value}) - Weighted: {opp.weighted_score:.2f}")
                                print(f"     Context: {opp.mtf_context}, Rec: {opp.recommendation}")

                            # Send alert if meets threshold
                            if opp.weighted_score >= alert_threshold:
                                try:
                                    sent = send_new_opportunity_alert(opp)
                                    if sent:
                                        alerts_sent.append(opp)
                                        if verbose:
                                            print(f"  🔔 Alert sent!")
                                except Exception as alert_err:
                                    logger.error(f"Failed to send alert for {pair}: {alert_err}")
                                    errors.append(f"Alert failed for {pair}: {alert_err}")
                        else:
                            if verbose:
                                print(f"  ❌ Does not meet criteria")
                                print(f"     Reason: HTF={alignment.htf_bias.direction.value}, "
                                      f"Context={alignment.mtf_setup.mtf_context}, "
                                      f"Weighted={alignment.weighted_score:.2f}")

                    except Exception as e:
                        logger.error(f"Error scanning {pair} ({trading_style.value}): {e}", exc_info=True)
                        errors.append(f"{pair} ({trading_style.value}): {e}")
                        if verbose:
                            print(f"  ❌ Error: {e}")

            # Summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            if verbose:
                print("\n" + "=" * 60)
                print("📊 Scan Summary")
                print("=" * 60)
                print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"Duration: {duration:.2f} seconds")
                print(f"Pair/Style Combinations: {total_scanned}")
                print(f"Opportunities Saved: {len(opportunities_saved)}")
                print(f"Alerts Sent: {len(alerts_sent)}")
                print(f"Errors: {len(errors)}")

                if opportunities_saved:
                    print("\n📋 Opportunities:")
                    for opp in opportunities_saved:
                        quality_badge = "🟢" if opp.weighted_score >= 0.75 else (
                            "🟡" if opp.weighted_score >= 0.60 else "🟠"
                        )
                        print(f"  {quality_badge} {opp.pair} ({opp.trading_style}) - "
                              f"{opp.htf_bias} - {opp.mtf_context} - {opp.weighted_score:.2f} - "
                              f"{opp.recommendation}")

                if alerts_sent:
                    print("\n🔔 Alerts Sent:")
                    for opp in alerts_sent:
                        print(f"  {opp.pair} ({opp.recommendation}) - {opp.weighted_score:.2f}")

            return {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "pairs_scanned": len(watchlist),
                "opportunities_saved": len(opportunities_saved),
                "alerts_sent": len(alerts_sent),
                "errors": len(errors),
                "opportunities": [opp.to_summary_dict() for opp in opportunities_saved],
            }

    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manual MTF Opportunity Scan")
    parser.add_argument(
        "--trading-styles",
        type=str,
        default="SWING",
        help="Comma-separated trading styles (default: SWING). Example: SWING,INTRADAY,DAY"
    )
    parser.add_argument(
        "--min-weighted",
        type=float,
        default=0.50,
        help="Minimum weighted score to save (default: 0.50)"
    )
    parser.add_argument(
        "--alert-threshold",
        type=float,
        default=0.60,
        help="Minimum weighted score to send alert (default: 0.60)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    # Parse trading styles
    trading_styles = [s.strip().upper() for s in args.trading_styles.split(",")]

    result = run_manual_scan(
        trading_styles=trading_styles,
        min_weighted_score=args.min_weighted,
        alert_threshold=args.alert_threshold,
        verbose=not args.quiet,
    )

    if "error" in result:
        print(f"\n❌ Scan failed: {result['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ Scan completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
