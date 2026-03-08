"""
Tests for Market Data Service.

Tests cover:
1. Status queries (all, single pair, by quality)
2. Status updates and sync operations
3. MTF readiness checks
4. Summary statistics
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
from src.models.ohlcv_cache_model import OHLCVCache, create_ohlcv_cache_table
from src.services.market_data_service import MarketDataService, PairStatus


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    create_market_data_status_table(engine)
    create_ohlcv_cache_table(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def service(test_db):
    """Create MarketDataService instance."""
    return MarketDataService(test_db)


def create_test_status(
    test_db,
    pair: str,
    timeframe: str,
    candle_count: int = 100,
    quality: str = DataQuality.GOOD.value,
    hours_ago: float = 2,
):
    """Helper to create test status entries."""
    last_candle = datetime.utcnow() - timedelta(hours=hours_ago)
    status = MarketDataStatus(
        pair=pair,
        timeframe=timeframe,
        candle_count=candle_count,
        last_candle_time=last_candle,
        data_quality=quality,
        source="ccxt",
    )
    test_db.add(status)
    test_db.commit()
    return status


class TestMarketDataServiceBasic:
    """Basic service tests."""

    def test_init(self, service):
        """Test service initialization."""
        assert service.db is not None
        assert service.cache_mgr is not None

    def test_get_pair_status_not_found(self, service):
        """Test getting status for non-existent pair."""
        result = service.get_pair_status("NONEXISTENT/USD")
        assert result is None

    def test_get_timeframe_status_not_found(self, service):
        """Test getting status for non-existent timeframe."""
        create_test_status(service.db, "BTC/USDT", "d1")
        result = service.get_timeframe_status("BTC/USDT", "h4")
        assert result is None


class TestGetAllStatuses:
    """Tests for get_all_statuses method."""

    def test_get_all_statuses_empty(self, service):
        """Test getting all statuses when database is empty."""
        result = service.get_all_statuses()
        assert result == {}

    def test_get_all_statuses_single_pair(self, service):
        """Test getting all statuses with single pair."""
        create_test_status(service.db, "BTC/USDT", "d1")
        create_test_status(service.db, "BTC/USDT", "h4")

        result = service.get_all_statuses()

        assert "BTC/USDT" in result
        assert len(result["BTC/USDT"].timeframes) == 2

    def test_get_all_statuses_multiple_pairs(self, service):
        """Test getting all statuses with multiple pairs."""
        for pair in ["BTC/USDT", "ETH/USDT", "XAU/USD"]:
            create_test_status(service.db, pair, "d1")

        result = service.get_all_statuses()
        assert len(result) == 3

    def test_get_all_statuses_filter_quality(self, service):
        """Test filtering by quality."""
        create_test_status(service.db, "BTC/USDT", "d1", quality=DataQuality.GOOD.value)
        create_test_status(service.db, "ETH/USDT", "d1", quality=DataQuality.STALE.value)
        create_test_status(service.db, "XAU/USD", "d1", quality=DataQuality.STALE.value)

        result = service.get_all_statuses(filter_quality=DataQuality.STALE.value)
        assert len(result) == 2
        assert "ETH/USDT" in result
        assert "XAU/USD" in result
        assert "BTC/USDT" not in result


class TestGetPairStatus:
    """Tests for get_pair_status method."""

    def test_get_pair_status(self, service):
        """Test getting status for single pair."""
        create_test_status(service.db, "BTC/USDT", "d1", candle_count=150)
        create_test_status(service.db, "BTC/USDT", "h4", candle_count=100)

        result = service.get_pair_status("BTC/USDT")

        assert result is not None
        assert result.pair == "BTC/USDT"
        assert "d1" in result.timeframes
        assert "h4" in result.timeframes
        assert result.timeframes["d1"]["candle_count"] == 150

    def test_get_pair_status_calculates_overall(self, service):
        """Test that overall status is calculated."""
        create_test_status(service.db, "BTC/USDT", "d1", quality=DataQuality.GOOD.value)
        create_test_status(service.db, "BTC/USDT", "h4", quality=DataQuality.STALE.value)

        result = service.get_pair_status("BTC/USDT")

        # Overall should be worst quality (STALE)
        assert result.overall_quality == DataQuality.STALE.value


class TestUpdateStatus:
    """Tests for update_status method."""

    def test_update_status_create_new(self, service):
        """Test creating new status entry."""
        result = service.update_status(
            pair="BTC/USDT",
            timeframe="d1",
            candle_count=150,
            source="ccxt",
        )

        assert result is not None
        assert result.pair == "BTC/USDT"
        assert result.candle_count == 150
        assert result.source == "ccxt"

    def test_update_status_update_existing(self, service):
        """Test updating existing status entry."""
        create_test_status(service.db, "BTC/USDT", "d1", candle_count=50)

        result = service.update_status(
            pair="BTC/USDT",
            timeframe="d1",
            candle_count=200,
            source="ccxt",
        )

        assert result.candle_count == 200

    def test_update_status_auto_quality(self, service):
        """Test automatic quality calculation."""
        # Excellent: 200+ candles, very fresh
        result = service.update_status(
            pair="BTC/USDT",
            timeframe="d1",
            candle_count=250,
            last_candle_time=datetime.utcnow() - timedelta(hours=10),
        )
        assert result.data_quality == DataQuality.EXCELLENT.value

        # Missing: <50 candles
        result = service.update_status(
            pair="ETH/USDT",
            timeframe="d1",
            candle_count=30,
        )
        assert result.data_quality == DataQuality.MISSING.value


class TestSyncAllStatuses:
    """Tests for sync_all_statuses method."""

    def test_sync_creates_missing_statuses(self, service, test_db):
        """Test sync creates status entries for cache entries."""
        # Add OHLCV cache entries without status
        for i in range(100):
            cache_entry = OHLCVCache(
                symbol="BTC/USDT",
                timeframe="d1",
                timestamp=datetime.utcnow() - timedelta(days=i),
                open=50000 + i,
                high=50100 + i,
                low=49900 + i,
                close=50050 + i,
                volume=1000,
            )
            test_db.add(cache_entry)
        test_db.commit()

        # Sync should create status entry
        stats = service.sync_all_statuses()

        assert stats["created"] >= 1
        assert stats["updated"] == 0

        # Verify status was created
        status = service.get_timeframe_status("BTC/USDT", "d1")
        assert status is not None
        assert status.candle_count == 100

    def test_sync_deletes_orphan_statuses(self, service, test_db):
        """Test sync deletes status entries without cache data."""
        # Create status entry without cache data
        create_test_status(service.db, "NONEXISTENT/USD", "d1")

        stats = service.sync_all_statuses()

        assert stats["deleted"] >= 1

        # Verify status was deleted
        status = service.get_timeframe_status("NONEXISTENT/USD", "d1")
        assert status is None


class TestMTFReadiness:
    """Tests for MTF readiness checks."""

    def test_get_mtf_ready_pairs_ready(self, service):
        """Test getting MTF ready pairs."""
        # Create GOOD quality entries for all SWING timeframes
        for tf in ["w1", "d1", "h4"]:
            create_test_status(service.db, "BTC/USDT", tf, quality=DataQuality.GOOD.value)

        result = service.get_mtf_ready_pairs(trading_style="SWING")

        assert "BTC/USDT" in result

    def test_get_mtf_ready_pairs_not_ready(self, service):
        """Test getting MTF not-ready pairs."""
        # Create STALE quality entries
        for tf in ["w1", "d1", "h4"]:
            create_test_status(service.db, "BTC/USDT", tf, quality=DataQuality.STALE.value)

        result = service.get_mtf_ready_pairs(trading_style="SWING")

        assert "BTC/USDT" not in result

    def test_get_mtf_ready_pairs_missing_timeframe(self, service):
        """Test pairs missing required timeframes."""
        # Only create 2 of 3 required timeframes
        create_test_status(service.db, "BTC/USDT", "d1", quality=DataQuality.GOOD.value)
        create_test_status(service.db, "BTC/USDT", "h4", quality=DataQuality.GOOD.value)

        result = service.get_mtf_ready_pairs(trading_style="SWING")

        assert "BTC/USDT" not in result

    def test_get_stale_pairs(self, service):
        """Test getting stale pairs."""
        create_test_status(service.db, "BTC/USDT", "d1", quality=DataQuality.GOOD.value)
        create_test_status(service.db, "ETH/USDT", "d1", quality=DataQuality.STALE.value)
        create_test_status(service.db, "XAU/USD", "d1", quality=DataQuality.MISSING.value)

        result = service.get_stale_pairs()

        assert "ETH/USDT" in result
        assert "XAU/USD" in result
        assert "BTC/USDT" not in result


class TestSummary:
    """Tests for summary statistics."""

    def test_get_summary(self, service):
        """Test getting summary statistics."""
        create_test_status(service.db, "BTC/USDT", "d1", quality=DataQuality.EXCELLENT.value)
        create_test_status(service.db, "ETH/USDT", "d1", quality=DataQuality.GOOD.value)
        create_test_status(service.db, "XAU/USD", "d1", quality=DataQuality.STALE.value)

        summary = service.get_summary()

        assert summary["total_pairs"] == 3
        assert summary["by_quality"][DataQuality.EXCELLENT.value] == 1
        assert summary["by_quality"][DataQuality.GOOD.value] == 1
        assert summary["by_quality"][DataQuality.STALE.value] == 1
        assert summary["mtf_ready"] == 2  # EXCELLENT and GOOD are ready
        assert summary["needs_refresh"] == 1  # STALE needs refresh


class TestPairStatus:
    """Tests for PairStatus dataclass."""

    def test_pair_status_to_dict(self):
        """Test converting PairStatus to dict."""
        status = PairStatus(
            pair="BTC/USDT",
            overall_quality=DataQuality.GOOD.value,
            timeframes={"d1": {"quality": DataQuality.GOOD.value}},
            mtf_ready=True,
            recommendation="Ready for MTF analysis",
        )

        result = status.to_dict()

        assert result["pair"] == "BTC/USDT"
        assert result["overall_quality"] == "GOOD"
        assert result["mtf_ready"] is True
        assert result["recommendation"] == "Ready for MTF analysis"

    def test_pair_status_default_values(self):
        """Test PairStatus default values."""
        status = PairStatus(pair="BTC/USDT")

        assert status.overall_quality == DataQuality.MISSING.value
        assert status.timeframes == {}
        assert status.mtf_ready is False
        assert status.recommendation == "Insufficient data"


class TestDeletePairStatus:
    """Tests for delete operations."""

    def test_delete_pair_status(self, service):
        """Test deleting all status entries for a pair."""
        create_test_status(service.db, "BTC/USDT", "d1")
        create_test_status(service.db, "BTC/USDT", "h4")
        create_test_status(service.db, "BTC/USDT", "w1")

        count = service.delete_pair_status("BTC/USDT")

        assert count == 3

        # Verify deletion
        result = service.get_pair_status("BTC/USDT")
        assert result is None

    def test_delete_pair_status_partial(self, service):
        """Test deleting one pair doesn't affect others."""
        create_test_status(service.db, "BTC/USDT", "d1")
        create_test_status(service.db, "ETH/USDT", "d1")

        service.delete_pair_status("BTC/USDT")

        # ETH/USDT should still exist
        result = service.get_pair_status("ETH/USDT")
        assert result is not None
