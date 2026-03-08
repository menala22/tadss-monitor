"""
Tests for Market Data Status Model.

Tests cover:
1. Model creation and serialization
2. Data quality assessment logic
3. Timeframe hour calculations
4. Database operations
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.market_data_status_model import (
    MarketDataStatus,
    DataQuality,
    create_market_data_status_table,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    create_market_data_status_table(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestMarketDataStatusModel:
    """Tests for MarketDataStatus model basics."""

    def test_create_status(self, test_db):
        """Test creating a MarketDataStatus entry."""
        status = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=150,
            last_candle_time=datetime(2026, 3, 8, 0, 0),
            data_quality=DataQuality.GOOD.value,
            source='ccxt',
        )
        test_db.add(status)
        test_db.commit()
        test_db.refresh(status)

        assert status.id is not None
        assert status.pair == 'BTC/USDT'
        assert status.timeframe == 'd1'
        assert status.candle_count == 150
        assert status.data_quality == DataQuality.GOOD.value
        assert status.source == 'ccxt'

    def test_to_dict(self, test_db):
        """Test converting status to dictionary."""
        status = MarketDataStatus(
            pair='ETH/USDT',
            timeframe='h4',
            candle_count=100,
            last_candle_time=datetime(2026, 3, 8, 12, 0),
            data_quality=DataQuality.EXCELLENT.value,
            source='ccxt',
        )
        test_db.add(status)
        test_db.commit()

        result = status.to_dict()

        assert result['pair'] == 'ETH/USDT'
        assert result['timeframe'] == 'h4'
        assert result['candle_count'] == 100
        assert result['data_quality'] == 'EXCELLENT'
        assert result['source'] == 'ccxt'
        assert 'last_candle_time' in result
        assert 'fetched_at' in result

    def test_repr(self, test_db):
        """Test string representation."""
        status = MarketDataStatus(
            pair='XAU/USD',
            timeframe='d1',
            candle_count=80,
            data_quality=DataQuality.STALE.value,
        )
        test_db.add(status)
        test_db.commit()

        repr_str = repr(status)
        assert 'XAU/USD' in repr_str
        assert 'd1' in repr_str
        assert '80' in repr_str
        assert 'STALE' in repr_str

    def test_unique_constraint(self, test_db):
        """Test that pair+timeframe combination is unique."""
        status1 = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=100,
            data_quality=DataQuality.GOOD.value,
        )
        test_db.add(status1)
        test_db.commit()

        # Try to add duplicate
        status2 = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=150,
            data_quality=DataQuality.GOOD.value,
        )
        test_db.add(status2)

        with pytest.raises(Exception):
            test_db.commit()

    def test_query_by_pair(self, test_db):
        """Test querying all timeframes for a single pair."""
        # Add multiple timeframes for same pair
        for tf in ['w1', 'd1', 'h4']:
            status = MarketDataStatus(
                pair='BTC/USDT',
                timeframe=tf,
                candle_count=100,
                data_quality=DataQuality.GOOD.value,
            )
            test_db.add(status)
        test_db.commit()

        # Query all timeframes for BTC/USDT
        results = test_db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == 'BTC/USDT'
        ).all()

        assert len(results) == 3
        timeframes = [s.timeframe for s in results]
        assert set(timeframes) == {'w1', 'd1', 'h4'}


class TestDataQualityAssessment:
    """Tests for data quality assessment logic."""

    def test_assess_quality_excellent(self):
        """Test EXCELLENT quality criteria."""
        # 200+ candles, very fresh
        quality = MarketDataStatus.assess_quality(
            candle_count=250,
            age_hours=10,
            timeframe='d1',  # 24h interval, max_age = 48h
        )
        assert quality == DataQuality.EXCELLENT

    def test_assess_quality_good(self):
        """Test GOOD quality criteria."""
        # 100+ candles, reasonably fresh
        quality = MarketDataStatus.assess_quality(
            candle_count=150,
            age_hours=50,
            timeframe='d1',  # 24h interval, max_age_good = 96h
        )
        assert quality == DataQuality.GOOD

    def test_assess_quality_stale_low_count(self):
        """Test STALE quality due to low candle count."""
        quality = MarketDataStatus.assess_quality(
            candle_count=75,  # 50-99 range
            age_hours=5,
            timeframe='d1',
        )
        assert quality == DataQuality.STALE

    def test_assess_quality_stale_old(self):
        """Test STALE quality due to age."""
        quality = MarketDataStatus.assess_quality(
            candle_count=120,
            age_hours=20,  # Old but not critical
            timeframe='h4',  # 4h interval
        )
        assert quality == DataQuality.STALE

    def test_assess_quality_missing(self):
        """Test MISSING quality criteria."""
        # Very few candles
        quality = MarketDataStatus.assess_quality(
            candle_count=30,
            age_hours=5,
            timeframe='d1',
        )
        assert quality == DataQuality.MISSING

    def test_assess_quality_missing_old(self):
        """Test MISSING quality due to very old data."""
        quality = MarketDataStatus.assess_quality(
            candle_count=150,
            age_hours=30,  # > 24h
            timeframe='h1',  # Short timeframe
        )
        assert quality == DataQuality.MISSING

    def test_assess_quality_boundary_candle_count(self):
        """Test quality at candle count boundaries."""
        # Exactly 50 candles
        quality = MarketDataStatus.assess_quality(
            candle_count=50,
            age_hours=2,
            timeframe='h4',
        )
        assert quality == DataQuality.STALE

        # Exactly 100 candles
        quality = MarketDataStatus.assess_quality(
            candle_count=100,
            age_hours=10,
            timeframe='d1',
        )
        assert quality == DataQuality.GOOD

        # Exactly 200 candles
        quality = MarketDataStatus.assess_quality(
            candle_count=200,
            age_hours=20,
            timeframe='d1',
        )
        assert quality == DataQuality.EXCELLENT

    def test_assess_quality_boundary_age(self):
        """Test quality at age boundaries."""
        tf = 'd1'  # 24h interval

        # Just under excellent threshold (2x tf = 48h)
        quality = MarketDataStatus.assess_quality(
            candle_count=250,
            age_hours=47,
            timeframe=tf,
        )
        assert quality == DataQuality.EXCELLENT

        # Just over excellent threshold
        quality = MarketDataStatus.assess_quality(
            candle_count=250,
            age_hours=49,
            timeframe=tf,
        )
        # Falls to GOOD (100+ candles, < 4x tf)
        assert quality == DataQuality.GOOD


class TestTimeframeHours:
    """Tests for timeframe hour calculations."""

    @pytest.mark.parametrize("timeframe,expected_hours", [
        ("m1", 1.0 / 60),
        ("m5", 5.0 / 60),
        ("m15", 15.0 / 60),
        ("m30", 30.0 / 60),
        ("h1", 1.0),
        ("h2", 2.0),
        ("h4", 4.0),
        ("h6", 6.0),
        ("h12", 12.0),
        ("d1", 24.0),
        ("d3", 72.0),
        ("w1", 168.0),
        ("M1", 720.0),
    ])
    def test_get_timeframe_hours(self, timeframe, expected_hours):
        """Test timeframe to hours conversion."""
        hours = MarketDataStatus._get_timeframe_hours(timeframe)
        assert hours == expected_hours

    def test_get_timeframe_hours_invalid(self):
        """Test invalid timeframe handling."""
        hours = MarketDataStatus._get_timeframe_hours("invalid")
        assert hours == 1.0  # Default fallback

    def test_get_timeframe_hours_short_string(self):
        """Test short string handling."""
        hours = MarketDataStatus._get_timeframe_hours("h")
        assert hours == 1.0  # Default fallback


class TestDatabaseOperations:
    """Integration tests for database operations."""

    def test_create_table_idempotent(self, test_db):
        """Test that table creation is idempotent."""
        # Table already created by fixture
        # Try to create again (should not raise)
        create_market_data_status_table(test_db.bind)
        # If we get here, test passed

    def test_query_by_quality(self, test_db):
        """Test querying by data quality."""
        # Add entries with different qualities
        for quality, count in [
            (DataQuality.EXCELLENT.value, 2),
            (DataQuality.GOOD.value, 3),
            (DataQuality.STALE.value, 1),
            (DataQuality.MISSING.value, 2),
        ]:
            for i in range(count):
                status = MarketDataStatus(
                    pair=f'PAIR_{quality}_{i}',
                    timeframe='d1',
                    candle_count=100,
                    data_quality=quality,
                )
                test_db.add(status)
        test_db.commit()

        # Query all STALE entries
        stale = test_db.query(MarketDataStatus).filter(
            MarketDataStatus.data_quality == DataQuality.STALE.value
        ).all()
        assert len(stale) == 1

        # Query all GOOD entries
        good = test_db.query(MarketDataStatus).filter(
            MarketDataStatus.data_quality == DataQuality.GOOD.value
        ).all()
        assert len(good) == 3

    def test_update_status(self, test_db):
        """Test updating status entry."""
        status = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=50,
            data_quality=DataQuality.STALE.value,
        )
        test_db.add(status)
        test_db.commit()

        # Update the status
        status.candle_count = 200
        status.data_quality = DataQuality.EXCELLENT.value
        status.last_candle_time = datetime.utcnow()
        test_db.commit()

        # Verify update
        updated = test_db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == 'BTC/USDT',
            MarketDataStatus.timeframe == 'd1',
        ).first()

        assert updated.candle_count == 200
        assert updated.data_quality == DataQuality.EXCELLENT.value

    def test_delete_status(self, test_db):
        """Test deleting status entry."""
        status = MarketDataStatus(
            pair='BTC/USDT',
            timeframe='d1',
            candle_count=100,
            data_quality=DataQuality.GOOD.value,
        )
        test_db.add(status)
        test_db.commit()

        # Delete
        test_db.delete(status)
        test_db.commit()

        # Verify deletion
        result = test_db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == 'BTC/USDT',
            MarketDataStatus.timeframe == 'd1',
        ).first()
        assert result is None
