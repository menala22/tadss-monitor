"""
Telegram Notification Service for TA-DSS.

This module provides a lightweight Telegram bot integration using only
the requests library. It sends position health alerts with anti-spam logic
and logs all alerts to the database for audit trail.

Environment Variables Required:
    TELEGRAM_BOT_TOKEN: Bot token from @BotFather
    TELEGRAM_CHAT_ID: Your Telegram chat ID from @userinfobot
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from src.config import settings
from src.database import get_db_context
from src.models.alert_model import AlertHistory, AlertType, AlertStatus

logger = logging.getLogger(__name__)

# Setup dedicated Telegram log file
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
telegram_logger = logging.getLogger("telegram")
telegram_logger.setLevel(logging.INFO)

# File handler for Telegram-specific logs
file_handler = logging.FileHandler(LOG_DIR / "telegram.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
telegram_logger.addHandler(file_handler)


class TelegramNotifier:
    """
    Lightweight Telegram notifier using requests library.

    This class handles:
    1. Loading credentials from environment
    2. Anti-spam logic (only alert on significant changes)
    3. Message formatting with Telegram Markdown
    4. Error handling with retry logic
    5. Logging to telegram.log

    Attributes:
        bot_token: Telegram bot token from settings.
        chat_id: Target chat ID from settings.
        enabled: Whether Telegram is properly configured.
        api_url: Telegram Bot API endpoint.

    Example:
        notifier = TelegramNotifier()
        notifier.send_position_alert(position, signals, previous_status)
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        """
        Initialize the Telegram notifier.

        Args:
            bot_token: Telegram bot token. Defaults to settings.telegram_bot_token.
            chat_id: Target chat ID. Defaults to settings.telegram_chat_id.
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        if self.enabled:
            telegram_logger.info("TelegramNotifier initialized")
        else:
            telegram_logger.warning(
                "Telegram not configured (missing bot_token or chat_id)"
            )

    def _should_send_alert(
        self,
        signals: Dict[str, Any],
        previous_status: Optional[str],
        price_movement_pct: float,
        is_daily_summary: bool = False,
    ) -> tuple[bool, str]:
        """
        Determine if an alert should be sent (anti-spam logic).

        Critical: Only send if:
        1. Overall signal status has changed (e.g., BULLISH → BEARISH)
        2. OR price moved >5% against position
        3. OR it's a daily summary

        Args:
            signals: Current signal states (MA10, MACD, RSI, etc.).
            previous_status: Last recorded signal status from database.
            price_movement_pct: Price movement percentage against position.
            is_daily_summary: Whether this is a daily summary alert.

        Returns:
            Tuple of (should_send: bool, reason: str).

        Example:
            should_send, reason = notifier._should_send_alert(signals, "BULLISH", -6.5)
            # Returns: (True, "Price moved >5% against position")
        """
        # Daily summary always sends
        if is_daily_summary:
            return True, "Daily summary"

        # Get current overall status (majority signal)
        signal_states = [
            signals.get("MA10"),
            signals.get("MA20"),
            signals.get("MA50"),
            signals.get("MACD"),
            signals.get("RSI"),
        ]

        bullish_count = sum(1 for s in signal_states if s in ["BULLISH", "OVERBOUGHT"])
        bearish_count = sum(1 for s in signal_states if s in ["BEARISH", "OVERSOLD"])

        if bullish_count > bearish_count:
            current_status = "BULLISH"
        elif bearish_count > bullish_count:
            current_status = "BEARISH"
        else:
            current_status = "NEUTRAL"

        # Check for status change
        if previous_status and current_status != previous_status:
            return (
                True,
                f"Signal status changed: {previous_status} → {current_status}",
            )

        # Check for significant price movement (>5% against position)
        if price_movement_pct < -5.0:
            return True, f"Price moved {abs(price_movement_pct):.1f}% against position"

        # No significant change
        telegram_logger.debug("No alert needed (no significant change)")
        return False, "No significant change"

    def _format_message(
        self,
        position: Dict[str, Any],
        signals: Dict[str, Any],
        current_price: float,
        price_movement_pct: float,
        reason: str,
    ) -> str:
        """
        Format alert message using Telegram Markdown.

        Message includes:
        - Header with emoji based on severity
        - Pair, direction, timeframe
        - Entry vs current price with PnL%
        - Individual signal statuses
        - Warning if signals contradict position
        - Footer with timestamp

        Args:
            position: Position dict (pair, direction, entry_price, timeframe).
            signals: Signal states dict (MA10, MA20, MA50, MACD, RSI).
            current_price: Current market price.
            price_movement_pct: Price movement percentage.
            reason: Reason for sending this alert.

        Returns:
            Formatted message string with Telegram Markdown.

        Example:
            message = notifier._format_message(position, signals, 51000, 2.5, "Status changed")
        """
        pair = position.get("pair", "UNKNOWN")
        direction = position.get("position_type", "UNKNOWN")
        entry_price = position.get("entry_price", 0)
        timeframe = position.get("timeframe", "N/A")

        # Determine severity emoji
        if "CRITICAL" in reason or price_movement_pct < -5:
            header_emoji = "🚨"
        elif "WARNING" in reason or price_movement_pct < 0:
            header_emoji = "⚠️"
        else:
            header_emoji = "📊"

        # Calculate PnL
        pnl_sign = "+" if price_movement_pct >= 0 else ""
        pnl_emoji = "🟢" if price_movement_pct >= 0 else "🔴"

        # Format individual signals
        signal_emojis = {
            "BULLISH": "✅",
            "BEARISH": "❌",
            "NEUTRAL": "➖",
            "OVERBOUGHT": "⚠️",
            "OVERSOLD": "⚠️",
        }

        signals_text = ""
        for key in ["MA10", "MA20", "MA50", "MACD", "RSI"]:
            status = signals.get(key, "N/A")
            emoji = signal_emojis.get(status, "❓")
            signals_text += f"{emoji} `{key}: {status}`\n"

        # Check for contradiction (position vs signals)
        contradiction_warning = ""
        bullish_count = sum(
            1 for s in [signals.get("MA10"), signals.get("MA20"), signals.get("MA50")]
            if s in ["BULLISH", "OVERBOUGHT"]
        )

        if direction == "LONG" and bullish_count == 0:
            contradiction_warning = (
                "\n🚨 *WARNING:* All MAs BEARISH on LONG position!\n"
            )
        elif direction == "SHORT" and bullish_count == 3:
            contradiction_warning = (
                "\n🚨 *WARNING:* All MAs BULLISH on SHORT position!\n"
            )

        # Build message
        message = (
            f"{header_emoji} *{pair} - {direction} Alert*\n\n"
            f"*Timeframe:* `{timeframe}`\n\n"
            f"*💰 Price:*\n"
            f"Entry: `${entry_price:,.2f}`\n"
            f"Current: `${current_price:,.2f}`\n"
            f"{pnl_emoji} PnL: `{pnl_sign}{price_movement_pct:.2f}%`\n\n"
            f"*📈 Signals:*\n"
            f"{signals_text}"
            f"{contradiction_warning}"
            f"\n⚠️ *Reason:* {reason}\n\n"
            f"_Generated by TA-DSS System_\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        return message

    def send_position_alert(
        self,
        position: Dict[str, Any],
        signals: Dict[str, Any],
        previous_status: Optional[str],
        current_price: float,
        is_daily_summary: bool = False,
    ) -> bool:
        """
        Send a position health alert to Telegram.

        This is the main entry point for sending alerts. It implements
        anti-spam logic, message formatting, and error handling with retry.
        All alerts are logged to the database for audit trail.

        Args:
            position: Position dict with keys:
                - pair: Trading pair (e.g., 'BTCUSD')
                - position_type: 'LONG' or 'SHORT'
                - entry_price: Entry price
                - timeframe: Analysis timeframe
            signals: Signal states dict with keys:
                - MA10, MA20, MA50: Moving average signals
                - MACD: MACD signal
                - RSI: RSI signal
            previous_status: Last recorded overall status (e.g., 'BULLISH').
            current_price: Current market price for PnL calculation.
            is_daily_summary: If True, always send (for daily summaries).

        Returns:
            True if alert sent successfully, False otherwise.

        Example:
            position = {
                'pair': 'BTCUSD',
                'position_type': 'LONG',
                'entry_price': 50000,
                'timeframe': 'h4'
            }
            signals = {
                'MA10': 'BULLISH',
                'MA20': 'BEARISH',
                'MA50': 'BEARISH',
                'MACD': 'BEARISH',
                'RSI': 'NEUTRAL'
            }
            success = notifier.send_position_alert(
                position, signals, 'BULLISH', 48000
            )
        """
        if not self.enabled:
            telegram_logger.debug("Telegram not enabled, skipping alert")
            return False

        # Calculate price movement
        entry_price = position.get("entry_price", current_price)
        direction = position.get("position_type", "LONG")

        if direction == "LONG":
            price_movement_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            price_movement_pct = ((entry_price - current_price) / entry_price) * 100

        # Check anti-spam logic
        should_send, reason = self._should_send_alert(
            signals=signals,
            previous_status=previous_status,
            price_movement_pct=price_movement_pct,
            is_daily_summary=is_daily_summary,
        )

        # Determine alert type and current status
        if is_daily_summary:
            alert_type = AlertType.DAILY_SUMMARY
            current_status = "DAILY_SUMMARY"
        elif abs(price_movement_pct) > 5:
            alert_type = AlertType.PRICE_MOVEMENT
            current_status = "PRICE_MOVEMENT"
        elif should_send and previous_status:
            alert_type = AlertType.SIGNAL_CHANGE
            current_status = reason.split(" → ")[-1] if " → " in reason else "UNKNOWN"
        else:
            alert_type = AlertType.POSITION_HEALTH
            current_status = "HEALTHY"

        # Create alert record (will be logged to database)
        pair = position.get("pair", "UNKNOWN")
        
        if not should_send:
            # Log skipped alert (anti-spam)
            telegram_logger.info(f"No alert needed: {reason}")
            self._log_alert_to_db(
                alert_type=alert_type,
                pair=pair,
                current_status=current_status,
                reason=reason,
                message="Alert skipped - no significant change",
                previous_status=previous_status,
                price_movement_pct=price_movement_pct,
                status=AlertStatus.SKIPPED,
            )
            return True  # Not an error, just no alert needed

        # Format message
        message = self._format_message(
            position=position,
            signals=signals,
            current_price=current_price,
            price_movement_pct=price_movement_pct,
            reason=reason,
        )

        # Send with retry logic and log result
        send_success = self._send_with_retry(
            message=message,
            alert_type=alert_type,
            pair=pair,
            current_status=current_status,
            reason=reason,
            previous_status=previous_status,
            price_movement_pct=price_movement_pct,
        )

        return send_success

    def _send_with_retry(
        self, 
        message: str, 
        retry_count: int = 0,
        alert_type: AlertType = None,
        pair: str = None,
        current_status: str = None,
        reason: str = None,
        previous_status: str = None,
        price_movement_pct: float = None,
    ) -> bool:
        """
        Send message to Telegram with retry logic and log to database.

        Args:
            message: Formatted message to send.
            retry_count: Current retry attempt (0 = first attempt).
            alert_type: Type of alert being sent.
            pair: Trading pair symbol.
            current_status: Current position health status.
            reason: Reason for triggering this alert.
            previous_status: Previous status before change.
            price_movement_pct: Price movement percentage.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }

            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()

            if result.get("ok"):
                telegram_logger.info(f"Alert sent successfully: {message[:50]}...")
                # Log successful alert to database
                self._log_alert_to_db(
                    alert_type=alert_type or AlertType.CUSTOM,
                    pair=pair,
                    current_status=current_status or "UNKNOWN",
                    reason=reason or "Custom message",
                    message=message,
                    previous_status=previous_status,
                    price_movement_pct=price_movement_pct,
                    status=AlertStatus.SENT,
                )
                return True
            else:
                error_msg = result.get("description", "Unknown error")
                raise Exception(f"Telegram API error: {error_msg}")

        except requests.exceptions.RequestException as e:
            telegram_logger.error(f"Network error (attempt {retry_count + 1}): {e}")

            # Retry once
            if retry_count < 1:
                telegram_logger.info("Retrying...")
                return self._send_with_retry(
                    message, 
                    retry_count + 1,
                    alert_type=alert_type,
                    pair=pair,
                    current_status=current_status,
                    reason=reason,
                    previous_status=previous_status,
                    price_movement_pct=price_movement_pct,
                )
            else:
                # Log failed alert to database
                self._log_alert_to_db(
                    alert_type=alert_type or AlertType.CUSTOM,
                    pair=pair,
                    current_status=current_status or "UNKNOWN",
                    reason=reason or "Custom message",
                    message=message,
                    previous_status=previous_status,
                    price_movement_pct=price_movement_pct,
                    status=AlertStatus.FAILED,
                    error_message=str(e),
                )
                return False

        except Exception as e:
            telegram_logger.error(f"Failed to send alert: {e}")
            # Log failed alert to database
            self._log_alert_to_db(
                alert_type=alert_type or AlertType.CUSTOM,
                pair=pair,
                current_status=current_status or "UNKNOWN",
                reason=reason or "Custom message",
                message=message,
                previous_status=previous_status,
                price_movement_pct=price_movement_pct,
                status=AlertStatus.FAILED,
                error_message=str(e),
            )
            return False

    def _log_alert_to_db(
        self,
        alert_type: AlertType,
        pair: str,
        current_status: str,
        reason: str,
        message: str,
        previous_status: Optional[str] = None,
        price_movement_pct: Optional[float] = None,
        status: AlertStatus = AlertStatus.PENDING,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log an alert to the database for audit trail.

        Args:
            alert_type: Type of alert.
            pair: Trading pair symbol.
            current_status: Current position health status.
            reason: Reason for triggering this alert.
            message: Full alert message text.
            previous_status: Previous status before change.
            price_movement_pct: Price movement percentage.
            status: Alert delivery status.
            error_message: Error message if delivery failed.
        """
        try:
            with get_db_context() as db:
                alert = AlertHistory(
                    alert_type=alert_type,
                    pair=pair,
                    current_status=current_status,
                    reason=reason,
                    message=message,
                    previous_status=previous_status,
                    price_movement_pct=price_movement_pct,
                    status=status,
                    error_message=error_message,
                )
                db.add(alert)
                telegram_logger.debug(f"Alert logged to database: {alert_type.value} - {pair}")
        except Exception as e:
            telegram_logger.error(f"Failed to log alert to database: {e}")

    def send_test_message(self) -> bool:
        """
        Send a test message to verify Telegram configuration.

        Returns:
            True if test message sent successfully, False otherwise.
        """
        if not self.enabled:
            telegram_logger.warning("Cannot send test: Telegram not configured")
            return False

        test_message = (
            "✅ *TA-DSS Test Message*\n\n"
            "Telegram notifications are working correctly!\n\n"
            "_You will receive alerts when:_\n"
            "• Position health status changes\n"
            "• Price moves >5% against your position\n"
            "• Daily summary (if enabled)\n\n"
            f"_Bot Token: `{self.bot_token[:20]}...`\n"
            f"Chat ID: `{self.chat_id}`_\n\n"
            f"_Generated by TA-DSS System_\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        return self._send_with_retry(test_message)

    def send_custom_message(self, message: str) -> bool:
        """
        Send a custom message to Telegram.

        Args:
            message: Custom message text (supports Markdown).

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.enabled:
            return False

        return self._send_with_retry(message)


def test_notification() -> bool:
    """
    Test function to verify Telegram configuration works.

    This function creates a notifier instance and sends a test message.
    Use this to verify your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are correct.

    Returns:
        True if test message sent successfully, False otherwise.

    Example:
        from src.notifier import test_notification
        success = test_notification()
        if success:
            print("✅ Telegram configured correctly!")
        else:
            print("❌ Check your .env file")
    """
    print("Testing Telegram notification...")

    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("❌ Telegram not configured")
        print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    success = notifier.send_test_message()

    if success:
        print("✅ Test message sent successfully!")
        print("   Check your Telegram for the message")
    else:
        print("❌ Failed to send test message")
        print("   Check logs/telegram.log for details")

    return success


# Convenience function for quick alerts
def send_alert(message: str) -> bool:
    """
    Send a quick alert message.

    Convenience function for sending simple alerts without
    creating a notifier instance.

    Args:
        message: Message text to send.

    Returns:
        True if sent successfully, False otherwise.
    """
    notifier = TelegramNotifier()
    return notifier.send_custom_message(message)
