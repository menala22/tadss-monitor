#!/usr/bin/env python3
"""
Create test data for local development

Usage:
    python scripts/create-test-data.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_context
from src.models.position_model import Position, PositionType, PositionStatus
from datetime import datetime

def create_test_data():
    """Create test positions in local database"""
    with get_db_context() as db:
        # Create test positions
        test_positions = [
            Position(
                pair="BTCUSD",
                entry_price=50000,
                position_type=PositionType.LONG,
                timeframe="h4",
                status=PositionStatus.OPEN,
                last_signal_status="BULLISH",
                last_ma10_status="BULLISH",
                last_ott_status="BULLISH",
            ),
            Position(
                pair="ETHUSD",
                entry_price=3000,
                position_type=PositionType.SHORT,
                timeframe="h1",
                status=PositionStatus.OPEN,
                last_signal_status="BEARISH",
                last_ma10_status="BEARISH",
                last_ott_status="BEARISH",
            ),
            Position(
                pair="XAUUSD",
                entry_price=2000,
                position_type=LONG,
                timeframe="d1",
                status=PositionStatus.OPEN,
                last_signal_status="NEUTRAL",
                last_ma10_status="NEUTRAL",
                last_ott_status="NEUTRAL",
            ),
        ]
        
        db.add_all(test_positions)
        db.commit()
        print(f"✅ Created {len(test_positions)} test positions")
        print("   - BTCUSD LONG h4")
        print("   - ETHUSD SHORT h1")
        print("   - XAUUSD LONG d1")

if __name__ == "__main__":
    create_test_data()
