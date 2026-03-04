"""
Pytest test cases for the Telegram Notification module.

Tests for TelegramNotifier class with mocked requests.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.notifier import TelegramNotifier, send_alert, test_notification


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_position():
    """Create a sample position dict."""
    return {
        "pair": "BTCUSD",
        "position_type": "LONG",
        "entry_price": 50000.0,
        "timeframe": "h4",
    }


@pytest.fixture
def bullish_signals():
    """Create bullish signal states."""
    return {
        "MA10": "BULLISH",
        "MA20": "BULLISH",
        "MA50": "BULLISH",
        "MACD": "BULLISH",
        "RSI": "BULLISH",
    }


@pytest.fixture
def bearish_signals():
    """Create bearish signal states."""
    return {
        "MA10": "BEARISH",
        "MA20": "BEARISH",
        "MA50": "BEARISH",
        "MACD": "BEARISH",
        "RSI": "BEARISH",
    }


@pytest.fixture
def notifier():
    """Create a TelegramNotifier instance with test credentials."""
    return TelegramNotifier(
        bot_token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        chat_id="123456789",
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Test TelegramNotifier initialization."""

    def test_init_with_credentials(self):
        """Test initialization with valid credentials."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat_id",
        )
        assert notifier.enabled is True
        assert "test_token" in notifier.api_url

    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        notifier = TelegramNotifier(
            bot_token=None,
            chat_id=None,
        )
        assert notifier.enabled is False

    def test_init_api_url_format(self):
        """Test API URL is correctly formatted."""
        notifier = TelegramNotifier(
            bot_token="my_token",
            chat_id="123",
        )
        assert notifier.api_url == "https://api.telegram.org/botmy_token/sendMessage"


# =============================================================================
# Anti-Spam Logic Tests
# =============================================================================


class TestAntiSpamLogic:
    """Test _should_send_alert anti-spam logic."""

    def test_status_change_triggers_alert(self, notifier, bullish_signals):
        """Test that status change triggers alert."""
        should_send, reason = notifier._should_send_alert(
            signals=bullish_signals,
            previous_status="BEARISH",
            price_movement_pct=2.0,
        )
        assert should_send is True
        assert "changed" in reason.lower()

    def test_no_change_no_alert(self, notifier, bullish_signals):
        """Test that no change means no alert."""
        should_send, reason = notifier._should_send_alert(
            signals=bullish_signals,
            previous_status="BULLISH",
            price_movement_pct=2.0,
        )
        assert should_send is False
        assert "No significant change" in reason

    def test_price_movement_triggers_alert(self, notifier, bullish_signals):
        """Test that >5% price movement triggers alert."""
        should_send, reason = notifier._should_send_alert(
            signals=bullish_signals,
            previous_status="BULLISH",
            price_movement_pct=-6.0,  # 6% against position
        )
        assert should_send is True
        assert "Price moved" in reason

    def test_daily_summary_always_sends(self, notifier, bullish_signals):
        """Test that daily summary always sends."""
        should_send, reason = notifier._should_send_alert(
            signals=bullish_signals,
            previous_status="BULLISH",
            price_movement_pct=0.0,
            is_daily_summary=True,
        )
        assert should_send is True
        assert "Daily" in reason

    def test_mixed_signals_neutral(self, notifier):
        """Test that mixed signals result in NEUTRAL status."""
        mixed_signals = {
            "MA10": "BULLISH",
            "MA20": "BEARISH",
            "MA50": "NEUTRAL",
            "MACD": "BULLISH",
            "RSI": "BEARISH",
        }
        # Mixed signals (2 bullish, 2 bearish, 1 neutral) = NEUTRAL
        # If previous was BULLISH, this is a change
        should_send, reason = notifier._should_send_alert(
            signals=mixed_signals,
            previous_status="BULLISH",
            price_movement_pct=0.0,
        )
        # Status changed from BULLISH to NEUTRAL
        assert should_send is True
        assert "changed" in reason.lower()


# =============================================================================
# Message Formatting Tests
# =============================================================================


class TestMessageFormatting:
    """Test _format_message functionality."""

    def test_long_position_format(self, notifier, sample_position, bullish_signals):
        """Test message formatting for LONG position."""
        message = notifier._format_message(
            position=sample_position,
            signals=bullish_signals,
            current_price=55000.0,
            price_movement_pct=10.0,
            reason="Status changed",
        )

        assert "BTCUSD" in message
        assert "LONG" in message
        assert "$50,000.00" in message
        assert "$55,000.00" in message
        assert "+10.00%" in message
        assert "MA10" in message
        assert "Generated by TA-DSS" in message

    def test_short_position_format(self, notifier, bearish_signals):
        """Test message formatting for SHORT position."""
        short_position = {
            "pair": "ETHUSD",
            "position_type": "SHORT",
            "entry_price": 3000.0,
            "timeframe": "d1",
        }

        message = notifier._format_message(
            position=short_position,
            signals=bearish_signals,
            current_price=2700.0,
            price_movement_pct=10.0,  # Profit for SHORT
            reason="Status changed",
        )

        assert "ETHUSD" in message
        assert "SHORT" in message
        assert "+10.00%" in message

    def test_loss_formatting(self, notifier, sample_position, bearish_signals):
        """Test message formatting with loss."""
        message = notifier._format_message(
            position=sample_position,
            signals=bearish_signals,
            current_price=45000.0,
            price_movement_pct=-10.0,
            reason="Price moved against position",
        )

        assert "-10.00%" in message
        assert "🔴" in message  # Loss emoji

    def test_contradiction_warning_long(self, notifier, bearish_signals):
        """Test contradiction warning for LONG with bearish signals."""
        long_position = {
            "pair": "BTCUSD",
            "position_type": "LONG",
            "entry_price": 50000.0,
            "timeframe": "h4",
        }

        message = notifier._format_message(
            position=long_position,
            signals=bearish_signals,
            current_price=48000.0,
            price_movement_pct=-4.0,
            reason="Signals turned bearish",
        )

        assert "WARNING" in message
        assert "BEARISH on LONG" in message

    def test_contradiction_warning_short(self, notifier, bullish_signals):
        """Test contradiction warning for SHORT with bullish signals."""
        short_position = {
            "pair": "BTCUSD",
            "position_type": "SHORT",
            "entry_price": 50000.0,
            "timeframe": "h4",
        }

        message = notifier._format_message(
            position=short_position,
            signals=bullish_signals,
            current_price=52000.0,
            price_movement_pct=-4.0,  # Loss for SHORT
            reason="Signals turned bullish",
        )

        assert "WARNING" in message
        assert "BULLISH on SHORT" in message

    def test_markdown_formatting(self, notifier, sample_position, bullish_signals):
        """Test that message uses Markdown formatting."""
        message = notifier._format_message(
            position=sample_position,
            signals=bullish_signals,
            current_price=51000.0,
            price_movement_pct=2.0,
            reason="Test",
        )

        # Check for Markdown elements
        assert "*" in message  # Bold
        assert "`" in message  # Code blocks
        assert "_" in message  # Italic


# =============================================================================
# Send Alert Tests
# =============================================================================


class TestSendAlert:
    """Test send_position_alert functionality."""

    @patch("requests.post")
    def test_send_success(self, mock_post, notifier, sample_position, bullish_signals):
        """Test successful alert sending."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BEARISH",  # Changed from BEARISH
            current_price=51000.0,
        )

        assert result is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_send_no_change(self, mock_post, notifier, sample_position, bullish_signals):
        """Test that no alert is sent when nothing changed."""
        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BULLISH",  # Same status
            current_price=51000.0,
        )

        # Should return True (not an error) but not send
        assert result is True
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_send_network_error_with_retry(self, mock_post, notifier, sample_position, bullish_signals):
        """Test retry logic on network error."""
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}

        mock_post.side_effect = [
            requests.exceptions.RequestException("Network error"),
            mock_response,
        ]

        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BEARISH",
            current_price=51000.0,
        )

        assert result is True
        assert mock_post.call_count == 2  # Initial + 1 retry

    @patch("requests.post")
    def test_send_api_error(self, mock_post, notifier, sample_position, bullish_signals):
        """Test handling of Telegram API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": False,
            "description": "Chat not found",
        }
        mock_post.return_value = mock_response

        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BEARISH",
            current_price=51000.0,
        )

        assert result is False

    @patch("requests.post")
    def test_send_disabled(self, sample_position, bullish_signals):
        """Test sending when Telegram is disabled."""
        notifier = TelegramNotifier(bot_token=None, chat_id=None)

        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BEARISH",
            current_price=51000.0,
        )

        assert result is False


# =============================================================================
# Test Message Tests
# =============================================================================


class TestTestMessage:
    """Test send_test_message functionality."""

    @patch("requests.post")
    def test_test_message_success(self, mock_post):
        """Test successful test message."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat",
        )

        result = notifier.send_test_message()
        assert result is True

    @patch("requests.post")
    def test_test_message_not_configured(self, mock_post):
        """Test test message when not configured."""
        notifier = TelegramNotifier(bot_token=None, chat_id=None)

        result = notifier.send_test_message()
        assert result is False
        mock_post.assert_not_called()


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Test send_alert and test_notification functions."""

    @patch("requests.post")
    def test_send_alert(self, mock_post):
        """Test send_alert convenience function."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        result = send_alert("Test message")
        # Will be False because no credentials configured
        assert isinstance(result, bool)

    @patch("requests.post")
    def test_test_notification_not_configured(self, mock_post):
        """Test test_notification when not configured."""
        # This will fail gracefully because no .env configured
        result = test_notification()
        assert result is False
        mock_post.assert_not_called()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for complete alert flow."""

    @patch("requests.post")
    def test_full_alert_flow_long_to_bearish(
        self, mock_post, sample_position, bearish_signals
    ):
        """Test complete alert flow for LONG position turning bearish."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat",
        )

        # LONG position with bearish signals (changed from bullish)
        result = notifier.send_position_alert(
            position=sample_position,
            signals=bearish_signals,
            previous_status="BULLISH",
            current_price=48000.0,  # Loss
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify message content
        call_args = mock_post.call_args
        message = call_args[1]["json"]["text"]
        assert "BTCUSD" in message
        assert "LONG" in message
        assert "WARNING" in message  # Contradiction warning

    @patch("requests.post")
    def test_full_alert_flow_price_crash(
        self, mock_post, sample_position, bullish_signals
    ):
        """Test alert on significant price crash."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat",
        )

        # Same signals but price crashed
        result = notifier.send_position_alert(
            position=sample_position,
            signals=bullish_signals,
            previous_status="BULLISH",
            current_price=45000.0,  # 10% crash
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify message mentions price movement
        call_args = mock_post.call_args
        message = call_args[1]["json"]["text"]
        assert "Price moved" in message or "-10.00%" in message
