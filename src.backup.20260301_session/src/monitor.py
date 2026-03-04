"""
Position Monitor for TA-DSS.

This module orchestrates the automated monitoring workflow:
1. Fetches all open positions from database
2. Gets live market data for each position
3. Calculates technical signals
4. Triggers Telegram alerts on significant changes
5. Updates database with latest status

Usage:
    from src.monitor import PositionMonitor
    
    monitor = PositionMonitor()
    monitor.check_all_positions()
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.data_fetcher import DataFetcher, DataFetchError
from src.database import get_db_context
from src.models.position_model import Position, PositionStatus
from src.notifier import TelegramNotifier
from src.services.technical_analyzer import PositionType, TechnicalAnalyzer

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(LOG_DIR / "monitor.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


class PositionMonitor:
    """
    Orchestrates automated position monitoring workflow.

    This class:
    1. Fetches all OPEN positions from database
    2. For each position, fetches live data and calculates signals
    3. Determines overall status (BULLISH/BEARISH/NEUTRAL)
    4. Compares with previous status to prevent spam
    5. Triggers Telegram alerts on significant changes
    6. Updates database with latest status

    Attributes:
        telegram_enabled: Whether Telegram notifications are enabled.
        pnl_warning_threshold: PnL % threshold for warnings (default: -5%).
        pnl_take_profit_threshold: PnL % threshold for take profit warnings (default: +10%).

    Example:
        monitor = PositionMonitor()
        monitor.check_all_positions()
    """

    def __init__(
        self,
        telegram_enabled: Optional[bool] = None,
        pnl_warning_threshold: float = -5.0,
        pnl_take_profit_threshold: float = 10.0,
    ):
        """
        Initialize the position monitor.

        Args:
            telegram_enabled: Whether to send Telegram alerts.
                Defaults to settings.telegram_enabled.
            pnl_warning_threshold: PnL % threshold for stop loss warnings.
                Default is -5.0 (alerts when down 5%).
            pnl_take_profit_threshold: PnL % threshold for take profit warnings.
                Default is +10.0 (alerts when up 10%).
        """
        self.telegram_enabled = (
            telegram_enabled
            if telegram_enabled is not None
            else settings.telegram_enabled
        )
        self.pnl_warning_threshold = pnl_warning_threshold
        self.pnl_take_profit_threshold = pnl_take_profit_threshold

        self._technical_analyzer = TechnicalAnalyzer()
        self._telegram_notifier = TelegramNotifier()

        logger.info(
            f"PositionMonitor initialized "
            f"(telegram={self.telegram_enabled}, "
            f"warning_threshold={self.pnl_warning_threshold}%, "
            f"take_profit_threshold={self.pnl_take_profit_threshold}%)"
        )

    def _get_data_source_for_pair(self, pair: str) -> str:
        """
        Determine data source based on trading pair.

        Args:
            pair: Trading pair symbol.

        Returns:
            'ccxt' for crypto, 'yfinance' for stocks.
        """
        pair_clean = pair.replace("-", "").replace("/", "").replace("_", "")

        # Stock symbols: 1-5 alphabetic characters
        if pair_clean.isalpha() and len(pair_clean) <= 5:
            return "yfinance"

        # Everything else is crypto
        return "ccxt"

    def _fetch_position_data(
        self,
        position: Position,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market data and calculate signals for a position.

        Args:
            position: Position to analyze.

        Returns:
            Dictionary with data and signals, or None if fetch failed.
        """
        try:
            source = self._get_data_source_for_pair(position.pair)
            logger.debug(
                f"Using {source} for position {position.id} ({position.pair})"
            )

            # Fetch market data
            fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=1.0)
            df = fetcher.get_ohlcv(
                symbol=position.pair,
                timeframe=position.timeframe,
                limit=100,
            )
            fetcher.close()

            if df.empty:
                logger.warning(f"No data returned for {position.pair}")
                return None

            current_price = float(df["close"].iloc[-1]) if "close" in df.columns else float(df["Close"].iloc[-1])

            # Calculate technical signals
            signal = self._technical_analyzer.analyze_position(
                df=df,
                pair=position.pair,
                position_type=PositionType(position.position_type.value),
                timeframe=position.timeframe,
            )

            return {
                "position_id": position.id,
                "pair": position.pair,
                "signal": signal,
                "current_price": current_price,
                "data_points": len(df),
            }

        except DataFetchError as e:
            logger.error(f"Data fetch failed for {position.pair}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error analyzing {position.pair}: {e}")
            return None

    def _determine_overall_status(
        self,
        signal_states: Dict[str, Any],
    ) -> str:
        """
        Determine overall signal status from individual signals.

        Args:
            signal_states: Dictionary of signal states from TechnicalAnalyzer.

        Returns:
            Overall status: 'BULLISH', 'BEARISH', or 'NEUTRAL'.
        """
        # Count bullish vs bearish signals
        signal_keys = ["MA10", "MA20", "MA50", "MACD", "RSI"]
        bullish_count = 0
        bearish_count = 0

        for key in signal_keys:
            status = signal_states.get(key)
            if status in ["BULLISH", "OVERBOUGHT"]:
                bullish_count += 1
            elif status in ["BEARISH", "OVERSOLD"]:
                bearish_count += 1

        # Determine majority
        if bullish_count > bearish_count:
            return "BULLISH"
        elif bearish_count > bullish_count:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _calculate_pnl_pct(
        self,
        position: Position,
        current_price: float,
    ) -> float:
        """
        Calculate PnL percentage for a position.

        Args:
            position: Position to calculate PnL for.
            current_price: Current market price.

        Returns:
            PnL percentage (positive = profit, negative = loss).
        """
        entry_price = position.entry_price

        if position.position_type == PositionType.LONG:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        return pnl_pct

    def _should_send_alert(
        self,
        position: Position,
        current_status: str,
        pnl_pct: float,
    ) -> tuple[bool, str]:
        """
        Determine if an alert should be sent.

        Alerts are sent when:
        1. Status changed from previous check
        2. PnL below warning threshold (stop loss)
        3. PnL above take profit threshold

        Args:
            position: Position to check.
            current_status: Current overall signal status.
            pnl_pct: PnL percentage.

        Returns:
            Tuple of (should_send: bool, reason: str).
        """
        previous_status = position.last_signal_status

        # Check for status change
        if previous_status and current_status != previous_status:
            return (
                True,
                f"Status changed: {previous_status} → {current_status}",
            )

        # Check for stop loss warning
        if pnl_pct < self.pnl_warning_threshold:
            return (
                True,
                f"Stop Loss Warning: PnL {pnl_pct:.1f}% (threshold: {self.pnl_warning_threshold}%)",
            )

        # Check for take profit warning
        if pnl_pct > self.pnl_take_profit_threshold:
            return (
                True,
                f"Take Profit Warning: PnL {pnl_pct:.1f}% (threshold: {self.pnl_take_profit_threshold}%)",
            )

        # No significant change
        logger.debug(
            f"No alert needed for {position.pair} "
            f"(status: {current_status}, PnL: {pnl_pct:.1f}%)"
        )
        return False, "No significant change"

    def _check_single_position(
        self,
        position: Position,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Check a single position and update database.

        Args:
            position: Position to check.
            db: Database session.

        Returns:
            Dictionary with check results.
        """
        result = {
            "position_id": position.id,
            "pair": position.pair,
            "success": False,
            "alert_sent": False,
            "error": None,
        }

        try:
            # Fetch data and calculate signals
            data = self._fetch_position_data(position)

            if data is None:
                result["error"] = "Data fetch failed"
                logger.warning(f"Skipping position {position.id} due to data fetch failure")
                return result

            signal = data["signal"]
            current_price = data["current_price"]

            # Determine overall status
            current_status = self._determine_overall_status(signal.signal_states)

            # Calculate PnL
            pnl_pct = self._calculate_pnl_pct(position, current_price)

            # Check if alert should be sent
            should_alert, reason = self._should_send_alert(
                position=position,
                current_status=current_status,
                pnl_pct=pnl_pct,
            )

            if should_alert:
                logger.info(
                    f"Alert triggered for {position.pair}: {reason}"
                )

                # Format and send Telegram alert
                message = self._format_alert_message(
                    position=position,
                    signal_states=signal.signal_states,
                    current_price=current_price,
                    pnl_pct=pnl_pct,
                    reason=reason,
                )

                if self.telegram_enabled:
                    self._telegram_notifier.send_custom_message(message)
                    logger.info(f"Telegram alert sent for {position.pair}")
                else:
                    logger.info("Telegram disabled, skipping alert")

                result["alert_sent"] = True

            # Update database with latest status
            position.update_signal_status(current_status)
            db.commit()

            result["success"] = True
            result["current_status"] = current_status
            result["pnl_pct"] = pnl_pct
            result["current_price"] = current_price

            logger.info(
                f"Checked position {position.id} ({position.pair}): "
                f"status={current_status}, PnL={pnl_pct:.1f}%"
            )

        except Exception as e:
            result["error"] = str(e)
            logger.error(
                f"Error checking position {position.id}: {e}",
                exc_info=True,
            )
            # Don't rollback here - let other positions continue

        return result

    def _format_alert_message(
        self,
        position: Position,
        signal_states: Dict[str, Any],
        current_price: float,
        pnl_pct: float,
        reason: str,
    ) -> str:
        """
        Format Telegram alert message.

        Args:
            position: Position to alert about.
            signal_states: Individual signal states.
            current_price: Current market price.
            pnl_pct: PnL percentage.
            reason: Reason for alert.

        Returns:
            Formatted message string.
        """
        pair = position.pair
        direction = position.position_type.value
        entry_price = position.entry_price
        timeframe = position.timeframe

        # Determine severity emoji
        if "Stop Loss" in reason:
            header_emoji = "🚨"
        elif "Take Profit" in reason:
            header_emoji = "💰"
        elif "changed" in reason:
            header_emoji = "⚠️"
        else:
            header_emoji = "📊"

        # PnL emoji
        pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_sign = "+" if pnl_pct >= 0 else ""

        # Signal emojis
        signal_emojis = {
            "BULLISH": "✅",
            "BEARISH": "❌",
            "NEUTRAL": "➖",
            "OVERBOUGHT": "⚠️",
            "OVERSOLD": "⚠️",
        }

        signals_text = ""
        for key in ["MA10", "MA20", "MA50", "MACD", "RSI"]:
            status = signal_states.get(key, "N/A")
            emoji = signal_emojis.get(status, "❓")
            signals_text += f"{emoji} `{key}: {status}`\n"

        # Contradiction warning
        contradiction_warning = ""
        bullish_ma_count = sum(
            1 for s in [signal_states.get("MA10"), signal_states.get("MA20"), signal_states.get("MA50")]
            if s in ["BULLISH", "OVERBOUGHT"]
        )

        if direction == "LONG" and bullish_ma_count == 0:
            contradiction_warning = "\n🚨 *WARNING:* All MAs BEARISH on LONG position!\n"
        elif direction == "SHORT" and bullish_ma_count == 3:
            contradiction_warning = "\n🚨 *WARNING:* All MAs BULLISH on SHORT position!\n"

        message = (
            f"{header_emoji} *{pair} - {direction} Alert*\n\n"
            f"*Timeframe:* `{timeframe}`\n\n"
            f"*💰 Price:*\n"
            f"Entry: `${entry_price:,.2f}`\n"
            f"Current: `${current_price:,.2f}`\n"
            f"{pnl_emoji} PnL: `{pnl_sign}{pnl_pct:.2f}%`\n\n"
            f"*📈 Signals:*\n"
            f"{signals_text}"
            f"{contradiction_warning}"
            f"\n⚠️ *Reason:* {reason}\n\n"
            f"_Generated by TA-DSS System_\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        return message

    def check_all_positions(self) -> Dict[str, Any]:
        """
        Check all open positions and trigger alerts if needed.

        This is the main entry point for the monitoring workflow.
        It fetches all OPEN positions, analyzes each one, and sends
        Telegram alerts on significant changes.

        Returns:
            Dictionary with summary of checks:
            - total: Total positions checked
            - successful: Number of successful checks
            - alerts_sent: Number of alerts sent
            - errors: Number of errors
            - results: List of individual results

        Example:
            monitor = PositionMonitor()
            results = monitor.check_all_positions()
            print(f"Checked {results['total']} positions")
        """
        logger.info("Starting position monitoring check")

        results = {
            "total": 0,
            "successful": 0,
            "alerts_sent": 0,
            "errors": 0,
            "results": [],
        }

        with get_db_context() as db:
            try:
                # Fetch all open positions
                open_positions = (
                    db.query(Position)
                    .filter(Position.status == PositionStatus.OPEN)
                    .all()
                )

                results["total"] = len(open_positions)
                logger.info(f"Found {results['total']} open positions")

                if not open_positions:
                    logger.info("No open positions to monitor")
                    return results

                # Check each position
                for position in open_positions:
                    result = self._check_single_position(position, db)
                    results["results"].append(result)

                    if result["success"]:
                        results["successful"] += 1
                        if result.get("alert_sent"):
                            results["alerts_sent"] += 1
                    else:
                        results["errors"] += 1

                logger.info(
                    f"Monitoring check completed: "
                    f"{results['successful']}/{results['total']} successful, "
                    f"{results['alerts_sent']} alerts sent, "
                    f"{results['errors']} errors"
                )

            except Exception as e:
                logger.error(f"Error in monitoring check: {e}", exc_info=True)
                results["error"] = str(e)

        return results


def run_monitoring_check() -> Dict[str, Any]:
    """
    Convenience function to run a monitoring check.

    Returns:
        Dictionary with check results.

    Example:
        from src.monitor import run_monitoring_check
        results = run_monitoring_check()
    """
    monitor = PositionMonitor()
    return monitor.check_all_positions()
