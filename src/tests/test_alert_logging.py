"""
Test script to verify alert history logging works correctly.

This script creates test alert records and verifies they are stored
in the database properly.

Usage:
    python -m src.tests.test_alert_logging
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database import get_db_context
from src.models.alert_model import AlertHistory, AlertType, AlertStatus


def test_create_alert_record():
    """Test creating an alert record in the database."""
    print("\n" + "=" * 60)
    print("Testing Alert History Logging")
    print("=" * 60)
    
    with get_db_context() as db:
        # Create a test alert
        test_alert = AlertHistory(
            alert_type=AlertType.POSITION_HEALTH,
            pair="BTC/USDT",
            current_status="WARNING",
            reason="Test alert - status changed",
            message="Test message for alert logging verification",
            previous_status="HEALTHY",
            price_movement_pct=-2.5,
            status=AlertStatus.SENT,
        )
        
        db.add(test_alert)
        print(f"✓ Created test alert: {test_alert}")
        
        # Create another test alert (skipped)
        skipped_alert = AlertHistory(
            alert_type=AlertType.SIGNAL_CHANGE,
            pair="ETH/USDT",
            current_status="BEARISH",
            reason="No significant change",
            message="Alert skipped - no significant change",
            previous_status="BEARISH",
            price_movement_pct=0.5,
            status=AlertStatus.SKIPPED,
        )
        
        db.add(skipped_alert)
        print(f"✓ Created skipped alert: {skipped_alert}")
    
    print("\n" + "-" * 60)
    print("Querying alerts from database...")
    print("-" * 60)
    
    with get_db_context() as db:
        alerts = db.query(AlertHistory).all()
        
        print(f"\n✓ Found {len(alerts)} alert(s) in database:\n")
        
        for alert in alerts:
            print(f"  ID: {alert.id}")
            print(f"  Pair: {alert.pair}")
            print(f"  Type: {alert.alert_type.value}")
            print(f"  Status: {alert.status.value}")
            print(f"  Reason: {alert.reason}")
            print(f"  Timestamp: {alert.timestamp}")
            print(f"  Created: {alert.created_at}")
            print()
    
    print("=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)
    print("\nYou can now query alerts with:")
    print("  sqlite3 data/positions.db \"SELECT * FROM alert_history;\"")
    print()


def show_alert_history_schema():
    """Display the alert_history table schema."""
    print("\n" + "=" * 60)
    print("Alert History Table Schema")
    print("=" * 60)
    
    with get_db_context() as db:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        columns = inspector.get_columns("alert_history")
        
        print("\nColumns:")
        for col in columns:
            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
            print(f"  - {col['name']}: {col['type']} ({nullable})")
        
        indexes = inspector.get_indexes("alert_history")
        if indexes:
            print("\nIndexes:")
            for idx in indexes:
                print(f"  - {idx['name']}: {idx['column_names']}")
    
    print()


if __name__ == "__main__":
    show_alert_history_schema()
    test_create_alert_record()
