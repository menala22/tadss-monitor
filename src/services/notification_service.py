"""
Telegram Notification Service for TA-DSS.

This module provides Telegram bot integration for sending
position health alerts to users.
"""

import logging
from typing import Optional

import requests
from telegram.error import TelegramError

from src.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Telegram bot service for sending notifications.

    This class handles:
    1. Bot initialization
    2. Message sending with retry logic
    3. Error handling and logging

    Attributes:
        bot_token: Telegram bot token from settings.
        chat_id: Target chat ID from settings.
        enabled: Whether Telegram is configured and enabled.
        api_url: Telegram Bot API endpoint.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        """
        Initialize the Telegram service.

        Args:
            bot_token: Telegram bot token. Defaults to settings.telegram_bot_token.
            chat_id: Target chat ID. Defaults to settings.telegram_chat_id.
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        if self.enabled:
            logger.info("Telegram service initialized")
        else:
            logger.debug(
                "Telegram not configured (missing bot_token or chat_id)"
            )

    def send_message(
        self,
        message: str,
        parse_mode: str = "Markdown",
        retry_count: int = 0,
    ) -> bool:
        """
        Send a message to the configured chat.

        Args:
            message: Message text to send (supports Markdown formatting).
            parse_mode: Message parsing mode. Defaults to 'Markdown'.
            retry_count: Current retry attempt (0 = first attempt).

        Returns:
            True if message sent successfully, False otherwise.

        Example:
            telegram = TelegramService()
            success = telegram.send_message("🚨 Position Alert: BTCUSD turned BEARISH")
        """
        if not self.enabled:
            logger.debug("Telegram not enabled, skipping message")
            return False

        try:
            # Send message using Telegram Bot API
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
            }
            
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram message sent to chat {self.chat_id}")
                return True
            else:
                error_msg = result.get('description', 'Unknown error')
                raise TelegramError(f"Telegram API error: {error_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending Telegram message: {e}")
            
            # Retry once on network errors
            if retry_count < 1:
                logger.info("Retrying Telegram message...")
                return self.send_message(message, parse_mode, retry_count + 1)
            
            return False

        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    def send_test_message(self) -> bool:
        """
        Send a test message to verify Telegram configuration.

        Returns:
            True if test message sent successfully, False otherwise.
        """
        test_message = (
            "✅ *TA-DSS Test Message*\n\n"
            "Telegram notifications are working correctly!\n\n"
            "_You will receive alerts when:_\n"
            "• Position health changes (HEALTHY → WARNING/CRITICAL)\n"
            "• Price moves >5% against your position\n"
            "• Technical signals diverge from your position"
        )

        return self.send_message(test_message)

    def format_position_alert(
        self,
        pair: str,
        position_type: str,
        health_status: str,
        current_price: float,
        entry_price: float,
        reason: str,
    ) -> str:
        """
        Format a position alert message.

        Args:
            pair: Trading pair symbol.
            position_type: LONG or SHORT.
            health_status: HEALTHY, WARNING, or CRITICAL.
            current_price: Current market price.
            entry_price: Position entry price.
            reason: Reason for the alert.

        Returns:
            Formatted message string.
        """
        # Emoji based on health status
        emoji_map = {
            "HEALTHY": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🚨",
        }
        emoji = emoji_map.get(health_status, "📊")

        # Calculate PnL
        if position_type == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        pnl_sign = "+" if pnl_pct >= 0 else ""

        message = (
            f"{emoji} *Position Alert*\n\n"
            f"*Pair:* {pair}\n"
            f"*Direction:* {position_type}\n"
            f"*Status:* {health_status}\n\n"
            f"*Prices:*\n"
            f"Entry: ${entry_price:,.2f}\n"
            f"Current: ${current_price:,.2f}\n"
            f"PnL: {pnl_sign}{pnl_pct:.2f}%\n\n"
            f"*Reason:* {reason}\n\n"
            f"_Check your dashboard for details._"
        )

        return message

    def __del__(self) -> None:
        """Destructor to ensure resources are released."""
        pass


def send_alert(message: str) -> bool:
    """
    Convenience function to send an alert message.

    This is a shortcut for creating a TelegramService instance
    and sending a message.

    Args:
        message: Message text to send.

    Returns:
        True if sent successfully, False otherwise.

    Example:
        from src.services.notification_service import send_alert
        send_alert("🚨 Critical alert for BTCUSD")
    """
    telegram = TelegramService()
    success = telegram.send_message(message)
    telegram.close()
    return success


def test_telegram_config() -> bool:
    """
    Test if Telegram configuration is valid.

    Returns:
        True if configuration is valid and test message sent, False otherwise.
    """
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    if not settings.telegram_chat_id:
        logger.error("TELEGRAM_CHAT_ID not configured")
        return False

    telegram = TelegramService()

    if not telegram.enabled:
        logger.error("Telegram service not enabled")
        return False

    success = telegram.send_test_message()
    telegram.close()

    return success
