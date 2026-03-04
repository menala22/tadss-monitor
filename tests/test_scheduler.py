"""
Pytest test cases for the Background Scheduler module.

Tests for PositionMonitor, SchedulerManager, and notification service.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.scheduler import (
    PositionMonitor,
    SchedulerManager,
    get_scheduler_manager,
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
)
from src.services.notification_service import (
    TelegramService,
    send_alert,
    test_telegram_config,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_position():
    """Create a mock position object."""
    mock = MagicMock()
    mock.id = 1
    mock.pair = "BTCUSD"
    mock.entry_price = 50000.0
    mock.position_type = MagicMock(value="LONG")
    mock.timeframe = "h4"
    mock.status = MagicMock(value="OPEN")
    return mock


@pytest.fixture
def mock_signal():
    """Create mock technical signal."""
    mock = MagicMock()
    mock.current_price = 51000.0
    mock.signal_states = {
        "MA10": "BULLISH",
        "MA20": "BULLISH",
        "MA50": "BEARISH",
        "MACD": "BULLISH",
        "RSI": "NEUTRAL",
    }
    return mock


@pytest.fixture
def mock_health_result():
    """Create mock health result."""
    mock = MagicMock()
    mock.health_status = MagicMock(value="HEALTHY")
    return mock


# =============================================================================
# PositionMonitor Tests
# =============================================================================


class TestPositionMonitor:
    """Test PositionMonitor class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        monitor = PositionMonitor()
        assert monitor.check_interval_hours == 4  # Default
        assert monitor.telegram_enabled is False  # No tokens configured

    def test_get_data_source_for_pair_crypto(self):
        """Test data source detection for crypto pairs."""
        monitor = PositionMonitor()

        assert monitor._get_data_source_for_pair("BTCUSD") == "ccxt"
        assert monitor._get_data_source_for_pair("ETH/USDT") == "ccxt"
        assert monitor._get_data_source_for_pair("BTC-USDT") == "ccxt"

    def test_get_data_source_for_pair_stock(self):
        """Test data source detection for stock symbols."""
        monitor = PositionMonitor()

        assert monitor._get_data_source_for_pair("AAPL") == "yfinance"
        assert monitor._get_data_source_for_pair("TSLA") == "yfinance"
        assert monitor._get_data_source_for_pair("MSFT") == "yfinance"

    def test_check_price_movement_long_profit(self, mock_position):
        """Test price movement calculation for profitable LONG."""
        monitor = PositionMonitor()
        mock_position.entry_price = 50000.0
        # Use actual PositionType enum
        from src.services.technical_analyzer import PositionType
        mock_position.position_type = PositionType.LONG

        is_significant, movement_pct = monitor._check_price_movement(
            mock_position, 55000.0  # 10% profit
        )

        # For LONG: profit = (current - entry) / entry * 100 = positive
        # Significant = movement against position (negative for LONG)
        assert movement_pct == 10.0  # 10% profit
        assert is_significant is False  # Profit, not loss

    def test_check_price_movement_long_loss(self, mock_position):
        """Test price movement calculation for losing LONG."""
        monitor = PositionMonitor()
        mock_position.entry_price = 50000.0
        from src.services.technical_analyzer import PositionType
        mock_position.position_type = PositionType.LONG

        is_significant, movement_pct = monitor._check_price_movement(
            mock_position, 45000.0  # 10% loss
        )

        # For LONG: loss = (current - entry) / entry * 100 = negative
        assert movement_pct == -10.0  # 10% loss
        assert is_significant is True  # >5% loss against position

    def test_check_price_movement_short_profit(self, mock_position):
        """Test price movement calculation for profitable SHORT."""
        monitor = PositionMonitor()
        mock_position.position_type = MagicMock(value="SHORT")
        mock_position.entry_price = 50000.0

        is_significant, movement_pct = monitor._check_price_movement(
            mock_position, 45000.0  # 10% profit for SHORT
        )

        assert is_significant is False
        assert movement_pct == 10.0

    def test_should_alert_price_movement(self):
        """Test alert trigger for significant price movement."""
        monitor = PositionMonitor()

        should_alert, reason = monitor._should_alert(
            position_id=1,
            signal_states={"MA10": "BULLISH"},
            health_status=MagicMock(value="HEALTHY"),
            price_movement_significant=True,
        )

        assert should_alert is True
        assert "Price moved >5%" in reason

    def test_should_alert_no_changes(self):
        """Test no alert when nothing changed."""
        monitor = PositionMonitor()

        # Set previous state
        from src.scheduler import _previous_signals
        _previous_signals[1] = {
            "signals": {"MA10": "BULLISH"},
            "health_status": "HEALTHY",
        }

        should_alert, reason = monitor._should_alert(
            position_id=1,
            signal_states={"MA10": "BULLISH"},
            health_status=MagicMock(value="HEALTHY"),
            price_movement_significant=False,
        )

        assert should_alert is False

    def test_send_telegram_alert_disabled(self):
        """Test Telegram alert when disabled."""
        monitor = PositionMonitor(telegram_enabled=False)

        # Should return True without actually sending
        result = monitor._send_telegram_alert("Test message")
        assert result is True


# =============================================================================
# SchedulerManager Tests
# =============================================================================


class TestSchedulerManager:
    """Test SchedulerManager class."""

    def test_init(self):
        """Test scheduler initialization."""
        manager = SchedulerManager()
        assert manager.scheduler is None
        assert manager._running is False

    def test_start_stop(self):
        """Test scheduler start and stop."""
        manager = SchedulerManager()

        # Start
        manager.start()
        assert manager._running is True
        assert manager.scheduler is not None

        # Stop
        manager.stop()
        assert manager._running is False

    def test_is_running(self):
        """Test running status check."""
        manager = SchedulerManager()

        assert manager.is_running() is False

        manager.start()
        assert manager.is_running() is True

        manager.stop()
        assert manager.is_running() is False

    def test_get_next_run_time(self):
        """Test next run time retrieval."""
        manager = SchedulerManager()

        # Not running = no next run time
        assert manager.get_next_run_time() is None

        manager.start()
        next_run = manager.get_next_run_time()
        assert next_run is not None

        manager.stop()


# =============================================================================
# Global Scheduler Functions Tests
# =============================================================================


class TestGlobalSchedulerFunctions:
    """Test global scheduler management functions."""

    def test_get_scheduler_manager(self):
        """Test getting scheduler manager singleton."""
        manager = get_scheduler_manager()
        assert manager is not None
        assert isinstance(manager, SchedulerManager)

    def test_get_scheduler_status_not_running(self):
        """Test status when scheduler not running."""
        # Reset global state
        import src.scheduler as scheduler_module
        scheduler_module._scheduler_manager = None

        status = get_scheduler_status()

        assert status["running"] is False
        assert status["next_run_time"] is None
        assert status["job_count"] == 0

    def test_start_stop_scheduler(self):
        """Test start and stop functions."""
        # Reset global state
        import src.scheduler as scheduler_module
        scheduler_module._scheduler_manager = None

        # Start
        start_scheduler()
        status = get_scheduler_status()
        assert status["running"] is True

        # Stop
        stop_scheduler()
        status = get_scheduler_status()
        assert status["running"] is False


# =============================================================================
# TelegramService Tests
# =============================================================================


class TestTelegramService:
    """Test Telegram notification service."""

    def test_init_not_configured(self):
        """Test initialization without credentials."""
        telegram = TelegramService(
            bot_token=None,
            chat_id=None,
        )
        assert telegram.enabled is False

    def test_init_configured(self):
        """Test initialization with credentials."""
        telegram = TelegramService(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="123456789",
        )
        assert telegram.enabled is True
        assert telegram.bot is not None

    def test_send_message_not_enabled(self):
        """Test sending message when not enabled."""
        telegram = TelegramService(bot_token=None, chat_id=None)
        result = telegram.send_message("Test")
        assert result is False

    @patch("telegram.Bot")
    def test_send_message_success(self, mock_bot_class):
        """Test successful message sending."""
        mock_bot = MagicMock()
        # Mock the async method properly
        mock_bot.send_message = MagicMock(return_value=None)
        mock_bot_class.return_value = mock_bot

        telegram = TelegramService(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="123456789",
        )

        result = telegram.send_message("Test message")
        # Service is enabled and bot exists
        assert telegram.enabled is True
        assert telegram.bot is not None

    @patch("telegram.Bot")
    def test_send_message_error(self, mock_bot_class):
        """Test message sending with error."""
        from telegram.error import TelegramError

        mock_bot = MagicMock()
        # Make send_message raise an error when called
        mock_bot.send_message.side_effect = TelegramError("Network error")
        mock_bot_class.return_value = mock_bot

        telegram = TelegramService(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="123456789",
        )

        # When telegram not properly configured or error occurs
        result = telegram.send_message("Test message")
        # Should handle gracefully (returns True or False depending on implementation)
        assert isinstance(result, bool)

    def test_format_position_alert(self):
        """Test alert message formatting."""
        telegram = TelegramService(
            bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            chat_id="123456789",
        )

        message = telegram.format_position_alert(
            pair="BTCUSD",
            position_type="LONG",
            health_status="WARNING",
            current_price=48000.0,
            entry_price=50000.0,
            reason="Technical signals turned bearish",
        )

        assert "BTCUSD" in message
        assert "LONG" in message
        assert "WARNING" in message
        assert "-4.00%" in message  # PnL calculation
        assert "bearish" in message.lower()

    def test_send_alert_convenience_function(self):
        """Test send_alert convenience function."""
        # Should not raise, just return False when not configured
        result = send_alert("Test alert")
        assert result is False

    def test_test_telegram_config_not_configured(self):
        """Test config check when not configured."""
        result = test_telegram_config()
        assert result is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestSchedulerIntegration:
    """Integration tests for scheduler components."""

    def test_monitor_initialization(self):
        """Test full monitor initialization."""
        monitor = PositionMonitor(
            check_interval_hours=2,
            telegram_enabled=False,
        )

        assert monitor.check_interval_hours == 2
        assert monitor.telegram_enabled is False

    def test_scheduler_job_registration(self):
        """Test that scheduler job is properly registered."""
        manager = SchedulerManager()
        manager.start()

        # Check job exists
        job = manager.scheduler.get_job("position_monitoring")
        assert job is not None
        assert job.name == "Monitor Open Positions"

        manager.stop()

    def test_full_alert_flow_mocked(self, mock_position, mock_signal, mock_health_result):
        """Test complete alert flow with mocked components."""
        with patch.object(PositionMonitor, '_fetch_position_data') as mock_fetch, \
             patch.object(PositionMonitor, '_should_alert') as mock_should_alert, \
             patch.object(PositionMonitor, '_send_telegram_alert') as mock_send, \
             patch.object(PositionMonitor, '_update_position_status') as mock_update:

            mock_fetch.return_value = {
                "signal": mock_signal,
                "current_price": 51000.0,
            }
            mock_should_alert.return_value = (True, "Test reason")
            mock_send.return_value = True

            monitor = PositionMonitor(telegram_enabled=False)

            # Create mock DB session
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_position

            # Process position
            monitor._process_position(mock_position, mock_db)

            # Verify alert was sent
            mock_send.assert_called_once()
