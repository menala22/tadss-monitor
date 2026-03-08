"""
Tests for Market Data API Routes (Direct Route Testing).

Since TestClient has compatibility issues, we test the route functions directly
by mocking the database session and verifying the response structure.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.api.routes_market_data import (
    get_all_status,
    get_pair_status,
    get_summary,
    refresh_pair_data,
    get_watchlist_with_status,
)
from src.models.market_data_status_model import DataQuality
from src.services.market_data_service import MarketDataService, PairStatus


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def mock_service():
    """Create a mock MarketDataService."""
    service = MagicMock(spec=MarketDataService)
    return service


class TestGetAllStatusEndpoint:
    """Tests for GET /api/v1/market-data/status endpoint."""

    def test_get_all_status_empty(self, mock_db):
        """Test getting all statuses when empty."""
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_all_statuses', return_value={}):
                response = get_all_status(db=mock_db)
                
                assert "summary" in response
                assert "pairs" in response
                assert response["summary"]["total_pairs"] == 0

    def test_get_all_status_with_data(self, mock_db):
        """Test getting all statuses with data."""
        # Create mock PairStatus objects
        btc_status = PairStatus(pair="BTC/USDT", overall_quality="GOOD", mtf_ready=True)
        btc_status.timeframes = {"d1": {"quality": "GOOD", "candle_count": 150}}
        
        eth_status = PairStatus(pair="ETH/USDT", overall_quality="EXCELLENT", mtf_ready=True)
        eth_status.timeframes = {"d1": {"quality": "EXCELLENT", "candle_count": 250}}
        
        statuses = {"BTC/USDT": btc_status, "ETH/USDT": eth_status}
        
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_all_statuses', return_value=statuses):
                response = get_all_status(db=mock_db)
                
                assert response["summary"]["total_pairs"] == 2
                assert "BTC/USDT" in response["pairs"]
                assert "ETH/USDT" in response["pairs"]

    def test_get_all_status_filter_quality(self, mock_db):
        """Test filtering by quality."""
        stale_status = PairStatus(pair="XAU/USD", overall_quality="STALE", mtf_ready=False)
        stale_status.timeframes = {"d1": {"quality": "STALE"}}
        
        statuses = {"XAU/USD": stale_status}
        
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_all_statuses', return_value=statuses):
                response = get_all_status(filter_quality="STALE", db=mock_db)
                
                assert response["summary"]["total_pairs"] == 1
                assert "XAU/USD" in response["pairs"]


class TestGetPairStatusEndpoint:
    """Tests for GET /api/v1/market-data/status/{pair} endpoint."""

    def test_get_pair_status_exists(self, mock_db):
        """Test getting status for existing pair."""
        status = PairStatus(pair="BTC/USDT", overall_quality="GOOD", mtf_ready=True)
        status.timeframes = {
            "d1": {"quality": "GOOD", "candle_count": 150},
            "h4": {"quality": "EXCELLENT", "candle_count": 200},
        }
        
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_pair_status', return_value=status):
                response = get_pair_status(pair="BTC/USDT", db=mock_db)
                
                assert response["pair"] == "BTC/USDT"
                assert response["overall_quality"] == "GOOD"
                assert response["mtf_ready"] is True
                assert len(response["timeframes"]) == 2

    def test_get_pair_status_not_found(self, mock_db):
        """Test getting status for non-existent pair."""
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_pair_status', return_value=None):
                response = get_pair_status(pair="NONEXISTENT/USD", db=mock_db)
                
                assert response["pair"] == "NONEXISTENT/USD"
                assert response["overall_quality"] == "MISSING"
                assert response["timeframes"] == {}


class TestGetSummaryEndpoint:
    """Tests for GET /api/v1/market-data/summary endpoint."""

    def test_get_summary(self, mock_db):
        """Test getting summary statistics."""
        summary_data = {
            "total_pairs": 5,
            "mtf_ready": 3,
            "by_quality": {
                "EXCELLENT": 2,
                "GOOD": 2,
                "STALE": 1,
                "MISSING": 0,
            },
            "needs_refresh": 2,
        }
        
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_summary', return_value=summary_data):
                response = get_summary(db=mock_db)
                
                assert response["total_pairs"] == 5
                assert response["mtf_ready"] == 3
                assert response["by_quality"]["EXCELLENT"] == 2


class TestRefreshPairEndpoint:
    """Tests for POST /api/v1/market-data/refresh endpoint."""

    def test_refresh_pair_missing_pair(self, mock_db):
        """Test refresh with missing pair field."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            refresh_pair_data(request={}, db=mock_db)
        
        assert exc_info.value.status_code == 400
        assert "pair" in exc_info.value.detail.lower()

    def test_refresh_pair_with_timeframes(self, mock_db):
        """Test refresh with specified timeframes."""
        request = {
            "pair": "BTC/USDT",
            "timeframes": ["d1", "h4"],
        }
        
        # Mock the service and fetcher
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'get_pair_status') as mock_get:
                mock_get.return_value = PairStatus(pair="BTC/USDT", overall_quality="GOOD")
                
                # Since we can't easily mock DataFetcher without API keys,
                # we test the validation logic only
                with patch('src.api.routes_market_data._fetch_and_save_data') as mock_fetch:
                    mock_fetch.return_value = {
                        "success": True,
                        "candles_fetched": 100,
                        "last_candle_time": datetime.utcnow().isoformat(),
                    }
                    
                    with patch.object(MarketDataService, 'update_status') as mock_update:
                        mock_update.return_value = MagicMock(data_quality="GOOD")
                        
                        response = refresh_pair_data(request=request, db=mock_db)
                        
                        assert response["status"] in ("success", "partial")
                        assert response["pair"] == "BTC/USDT"


class TestGetWatchlistEndpoint:
    """Tests for GET /api/v1/market-data/watchlist endpoint."""

    def test_get_watchlist_with_status(self, mock_db):
        """Test getting watchlist with status."""
        # Mock watchlist
        with patch('src.api.routes_market_data.get_watchlist', return_value=["BTC/USDT", "ETH/USDT"]):
            # Mock service
            btc_status = PairStatus(pair="BTC/USDT", overall_quality="GOOD", mtf_ready=True)
            btc_status.timeframes = {"d1": {"quality": "GOOD"}, "h4": {"quality": "GOOD"}}
            
            with patch.object(MarketDataService, '__init__', return_value=None):
                with patch.object(MarketDataService, 'get_pair_status', side_effect=[btc_status, None]):
                    response = get_watchlist_with_status(trading_style="SWING", db=mock_db)
                    
                    assert response["count"] == 2
                    assert response["trading_style"] == "SWING"
                    assert len(response["watchlist"]) == 2

    def test_get_watchlist_invalid_style(self, mock_db):
        """Test getting watchlist with invalid trading style."""
        # The route uses MTF_TIMEFRAMES.get() which returns default for invalid styles
        # So it won't raise an exception, just use default timeframes
        with patch('src.api.routes_market_data.get_watchlist', return_value=[]):
            with patch.object(MarketDataService, '__init__', return_value=None):
                with patch.object(MarketDataService, 'get_pair_status', return_value=None):
                    response = get_watchlist_with_status(trading_style="INVALID", db=mock_db)
                    
                    # Should use default SWING timeframes
                    assert response["trading_style"] == "INVALID"
                    assert response["timeframes"] == ["w1", "d1", "h4"]  # Default SWING


class TestDeletePairStatusEndpoint:
    """Tests for DELETE /api/v1/market-data/status/{pair} endpoint."""

    def test_delete_pair_status(self, mock_db):
        """Test deleting status for a pair."""
        with patch.object(MarketDataService, '__init__', return_value=None):
            with patch.object(MarketDataService, 'delete_pair_status', return_value=2):
                response = delete_pair_status(pair="BTC/USDT", db=mock_db)
                
                assert response["deleted"] == "BTC/USDT"
                assert response["entries_removed"] == 2


# Import the delete function at module level
from src.api.routes_market_data import delete_pair_status


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_format_pair_status_none(self):
        """Test formatting None status."""
        from src.api.routes_market_data import _format_pair_status
        
        result = _format_pair_status("BTC/USDT", None)
        
        assert result["pair"] == "BTC/USDT"
        assert result["overall_quality"] == "MISSING"
        assert result["mtf_ready"] is False

    def test_format_pair_status_exists(self):
        """Test formatting existing status."""
        from src.api.routes_market_data import _format_pair_status
        
        status = PairStatus(
            pair="BTC/USDT",
            overall_quality="GOOD",
            timeframes={"d1": {"quality": "GOOD"}},
            mtf_ready=True,
            recommendation="Ready for MTF analysis",
        )
        
        result = _format_pair_status("BTC/USDT", status)
        
        assert result["overall_quality"] == "GOOD"
        assert result["mtf_ready"] is True
        assert result["recommendation"] == "Ready for MTF analysis"
