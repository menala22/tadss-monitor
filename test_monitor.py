#!/usr/bin/env python3
"""
Test script for the Position Monitor.

This script runs check_all_positions() once manually (without waiting 4 hours)
so you can verify the full flow:
    DB → Fetch → Analyze → Telegram → DB Update

Usage:
    python test_monitor.py

Requirements:
    - Database must be initialized with positions table
    - .env file must have TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
    - At least one OPEN position in the database for testing
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.monitor import PositionMonitor, run_monitoring_check
from src.models.position_model import migrate_add_signal_columns
from src.database import initialize_database


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70 + "\n")


def print_section(text: str):
    """Print formatted section."""
    print(f"\n--- {text} ---\n")


def main():
    """Run the monitoring test."""
    print_header("TA-DSS Position Monitor Test")

    # Step 1: Initialize database
    print_section("Step 1: Initialize Database")
    print("Initializing database...")
    initialize_database(verbose=False)

    # Step 2: Run migration for signal columns
    print_section("Step 2: Database Migration")
    print("Adding signal tracking columns...")
    migrate_success = migrate_add_signal_columns()
    if migrate_success:
        print("✓ Migration completed")
    else:
        print("✗ Migration failed (columns may already exist)")

    # Step 3: Create monitor
    print_section("Step 3: Initialize Position Monitor")
    monitor = PositionMonitor(telegram_enabled=True)
    print(f"✓ Monitor initialized")
    print(f"  Telegram enabled: {monitor.telegram_enabled}")
    print(f"  Warning threshold: {monitor.pnl_warning_threshold}%")
    print(f"  Take profit threshold: {monitor.pnl_take_profit_threshold}%")

    # Step 4: Run monitoring check
    print_section("Step 4: Run Monitoring Check")
    print("Checking all open positions...")
    print("(This may take a few seconds to fetch data)\n")

    results = run_monitoring_check()

    # Step 5: Display results
    print_section("Step 5: Results")

    print(f"Total positions checked: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Alerts sent: {results['alerts_sent']}")
    print(f"Errors: {results['errors']}")

    if results.get('error'):
        print(f"\n⚠️  Global error: {results['error']}")

    # Display individual results
    if results['results']:
        print_section("Individual Position Results")

        for result in results['results']:
            pos_id = result['position_id']
            pair = result['pair']
            success = result['success']
            alert_sent = result.get('alert_sent', False)
            error = result.get('error')

            status_icon = "✅" if success else "❌"
            alert_icon = "🔔" if alert_sent else ""

            print(f"{status_icon} Position {pos_id} ({pair}) {alert_icon}")

            if success:
                current_status = result.get('current_status', 'N/A')
                pnl_pct = result.get('pnl_pct', 0)
                current_price = result.get('current_price', 0)

                print(f"    Status: {current_status}")
                print(f"    Price: ${current_price:,.2f}")
                print(f"    PnL: {pnl_pct:+.2f}%")

            if error:
                print(f"    Error: {error}")

            print()

    # Step 6: Summary
    print_section("Test Summary")

    if results['total'] == 0:
        print("⚠️  No open positions found in database.")
        print("\nTo test with a real position:")
        print("1. Start the API: uvicorn src.main:app --reload")
        print("2. Create a position:")
        print("   curl -X POST http://localhost:8000/api/v1/positions/open \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"pair\": \"BTCUSD\", \"entry_price\": 50000, \"position_type\": \"LONG\", \"timeframe\": \"h4\"}'")
        print("3. Run this test again: python test_monitor.py")
    elif results['successful'] > 0:
        print("✅ Test completed successfully!")
        print(f"\nChecked {results['successful']} positions")
        if results['alerts_sent'] > 0:
            print(f"Sent {results['alerts_sent']} Telegram alerts")
        print("\nCheck logs/monitor.log for detailed logs")
        print("Check your Telegram for alerts")
    else:
        print("❌ Test completed with errors")
        print("Check logs/monitor.log for details")

    print()
    print_header("Test Finished")

    return results


if __name__ == "__main__":
    try:
        results = main()

        # Exit with error code if there were errors
        if results['errors'] > 0 or results.get('error'):
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
