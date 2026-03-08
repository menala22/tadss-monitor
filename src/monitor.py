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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.data_fetcher import DataFetcher, DataFetchError
from src.database import get_db_context
from src.models.position_model import Position, PositionStatus
from src.models.signal_change_model import SignalChange, SignalType
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

# =============================================================================
# SMART SCANNING CONFIGURATION
# =============================================================================

# Check intervals in minutes for each timeframe
# Positions are only checked if enough time has passed since last check
TIMEFRAME_CHECK_INTERVAL = {
    'm1': 1,       # 1 minute
    'm5': 5,       # 5 minutes
    'm15': 15,     # 15 minutes
    'm30': 30,     # 30 minutes
    'h1': 60,      # 1 hour
    'h2': 120,     # 2 hours
    'h4': 240,     # 4 hours
    'h6': 360,     # 6 hours
    'h8': 480,     # 8 hours
    'h12': 720,    # 12 hours
    'd1': 1440,    # 24 hours
    'd3': 4320,    # 3 days
    'd5': 7200,    # 5 days
    'w1': 10080,   # 7 days
    'M1': 43200,   # 30 days
}


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
    ):
        """
        Initialize the position monitor.

        Args:
            telegram_enabled: Whether to send Telegram alerts.
                Defaults to settings.telegram_enabled.
        """
        self.telegram_enabled = (
            telegram_enabled
            if telegram_enabled is not None
            else settings.telegram_enabled
        )

        self._technical_analyzer = TechnicalAnalyzer()
        self._telegram_notifier = TelegramNotifier()

        logger.info(
            f"PositionMonitor initialized "
            f"(telegram={self.telegram_enabled})"
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

    def _should_check_position(self, position: Position) -> tuple[bool, int]:
        """
        Check if position should be scanned based on timeframe.
        
        Implements smart scanning strategy to reduce API calls.

        Args:
            position: Position to check.

        Returns:
            Tuple of (should_check: bool, minutes_until_next_check: int)
        """
        # Get check interval for this timeframe
        interval_minutes = TIMEFRAME_CHECK_INTERVAL.get(position.timeframe, 60)
        
        # If never checked, should check now
        if position.last_checked_at is None:
            return True, interval_minutes
        
        # Calculate time since last check
        time_since_last_check = datetime.utcnow() - position.last_checked_at
        minutes_since_last_check = time_since_last_check.total_seconds() / 60
        
        # Check if enough time has passed
        if minutes_since_last_check >= interval_minutes:
            return True, interval_minutes
        else:
            minutes_remaining = int(interval_minutes - minutes_since_last_check)
            return False, minutes_remaining

    def _fetch_position_data(
        self,
        position: Position,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market data and calculate signals for a position.
        
        Uses ohlcv_universal table as primary data source (read-only).
        Falls back to DataFetcher API only if data is missing from universal.

        Args:
            position: Position to analyze.

        Returns:
            Dictionary with data and signals, or None if fetch failed.
        """
        try:
            # Try to get data from ohlcv_universal first (read-only, no API calls)
            df = self._get_data_from_universal(position.pair, position.timeframe, limit=100)
            
            # Fallback to API if universal has no data
            if df is None or df.empty:
                logger.warning(
                    f"No data in ohlcv_universal for {position.pair} {position.timeframe}, "
                    f"fetching from API..."
                )
                source = self._get_data_source_for_pair(position.pair)
                fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=1.0)
                df = fetcher.get_ohlcv(
                    symbol=position.pair,
                    timeframe=position.timeframe,
                    limit=100,
                )
                fetcher.close()
                
                if df is None or df.empty:
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

    def _get_data_from_universal(
        self,
        pair: str,
        timeframe: str,
        limit: int = 100,
    ):
        """
        Get OHLCV data from ohlcv_universal table (read-only).
        
        Args:
            pair: Trading pair symbol.
            timeframe: Timeframe.
            limit: Number of candles to fetch.
            
        Returns:
            DataFrame with OHLCV data, or None if not found.
        """
        import pandas as pd
        from sqlalchemy import func
        from src.models.ohlcv_universal_model import OHLCVUniversal
        from src.database import get_db_context
        
        try:
            with get_db_context() as db:
                candles = db.query(OHLCVUniversal).filter(
                    OHLCVUniversal.symbol == pair,
                    OHLCVUniversal.timeframe == timeframe,
                ).order_by(
                    OHLCVUniversal.timestamp.desc()
                ).limit(limit).all()
                
                if not candles:
                    return None
                
                # Convert to DataFrame
                data = [c.to_dict() for c in candles]
                df = pd.DataFrame(data)
                
                # Sort by timestamp ascending
                df = df.sort_values('timestamp').reset_index(drop=True)
                df.set_index('timestamp', inplace=True)
                
                # Select OHLCV columns
                columns = ['open', 'high', 'low', 'close', 'volume']
                df = df[columns]
                
                return df
                
        except Exception as e:
            logger.error(f"Failed to get data from universal for {pair} {timeframe}: {e}")
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
        # Count bullish vs bearish signals (6 indicators including OTT)
        signal_keys = ["MA10", "MA20", "MA50", "MACD", "RSI", "OTT"]
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

    def calculate_initial_signals(
        self,
        position: Position,
    ) -> Optional[Dict[str, str]]:
        """
        Calculate initial MA10, OTT, and overall status for a new position.

        This is called when a position is first created to establish baseline
        signal values, so that alerts can be triggered on the first monitoring check.

        Args:
            position: Position to calculate signals for.

        Returns:
            Dictionary with signal values, or None if calculation failed:
            {
                'ma10': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
                'ott': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
                'overall': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
            }
        """
        try:
            # Fetch market data
            source = self._get_data_source_for_pair(position.pair)
            fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=1.0)
            df = fetcher.get_ohlcv(
                symbol=position.pair,
                timeframe=position.timeframe,
                limit=100,
            )
            fetcher.close()

            if df.empty:
                logger.warning(f"No data for initial signals calculation: {position.pair}")
                return None

            # Calculate signals
            signal = self._technical_analyzer.analyze_position(
                df=df,
                pair=position.pair,
                position_type=PositionType(position.position_type.value),
                timeframe=position.timeframe,
            )

            # Extract signal values
            ma10_status = signal.signal_states.get("MA10", "NEUTRAL")
            ott_status = signal.signal_states.get("OTT", "NEUTRAL")

            # Convert enum to string value
            if hasattr(ma10_status, 'value'):
                ma10_status = ma10_status.value
            if hasattr(ott_status, 'value'):
                ott_status = ott_status.value

            return {
                'ma10': ma10_status,
                'ott': ott_status,
                'overall': signal.overall_signal.value,
            }

        except Exception as e:
            logger.error(f"Failed to calculate initial signals for {position.pair}: {e}")
            return None

    def _should_send_alert(
        self,
        position: Position,
        current_status: str,
        pnl_pct: float,
        signal_states: dict,
    ) -> tuple[bool, str]:
        """
        Determine if an alert should be sent.

        Alerts are sent when:
        1. Overall status changed from previous check
        2. MA10 changed status (tracked independently)
        3. OTT changed status (tracked independently)

        Args:
            position: Position to check.
            current_status: Current overall signal status.
            pnl_pct: PnL percentage (not used for alerts).
            signal_states: Dictionary of current signal states.

        Returns:
            Tuple of (should_send: bool, reason: str).
        """
        previous_status = position.last_signal_status
        previous_ma10 = position.last_ma10_status
        previous_ott = position.last_ott_status

        # Get current important indicators status
        current_ma10 = signal_states.get("MA10", "NEUTRAL")
        current_ott = signal_states.get("OTT", "NEUTRAL")

        # Extract string value from SignalState enum if present
        if hasattr(current_ma10, 'value'):
            current_ma10 = current_ma10.value
        if hasattr(current_ott, 'value'):
            current_ott = current_ott.value

        # Check 1: Overall status change
        if previous_status and current_status != previous_status:
            return (
                True,
                f"Status changed: {previous_status} → {current_status}",
            )

        # Check 2: MA10 change (tracked independently)
        if previous_ma10 and current_ma10 != previous_ma10:
            return (
                True,
                f"MA10 Changed: {previous_ma10} → {current_ma10}",
            )

        # Check 3: OTT change (tracked independently)
        if previous_ott and current_ott != previous_ott:
            return (
                True,
                f"OTT Changed: {previous_ott} → {current_ott}",
            )

        # No significant change
        logger.debug(
            f"No alert needed for {position.pair} "
            f"(status: {current_status}, PnL: {pnl_pct:.1f}%)"
        )
        return False, "No significant change"

    def _log_signal_changes(
        self,
        db: Session,
        position: Position,
        current_price: float,
        pnl_pct: float,
        current_ma10: str,
        current_ott: str,
        current_overall: str,
        alert_triggered: bool,
    ) -> None:
        """
        Log MA10, OTT, and overall signal changes to signal_changes table.

        This method tracks all signal status changes for historical analysis
        and backtesting purposes.

        Args:
            db: Database session.
            position: Position being checked.
            current_price: Current market price.
            pnl_pct: PnL percentage.
            current_ma10: Current MA10 status.
            current_ott: Current OTT status.
            current_overall: Current overall status.
            alert_triggered: Whether this check triggered an alert.
        """
        try:
            # Check MA10 change
            if position.last_ma10_status and position.last_ma10_status != current_ma10:
                change = SignalChange.create_change(
                    pair=position.pair,
                    timeframe=position.timeframe,
                    signal_type=SignalType.MA10,
                    previous_status=position.last_ma10_status,
                    current_status=current_ma10,
                    price_at_change=current_price,
                    price_movement_pct=pnl_pct,
                    position_type=position.position_type.value,
                    triggered_alert=alert_triggered and f"MA10" in str(current_ma10),
                )
                db.add(change)
                logger.debug(
                    f"Signal change logged: {position.pair} MA10 "
                    f"{position.last_ma10_status} → {current_ma10}"
                )

            # Check OTT change
            if position.last_ott_status and position.last_ott_status != current_ott:
                change = SignalChange.create_change(
                    pair=position.pair,
                    timeframe=position.timeframe,
                    signal_type=SignalType.OTT,
                    previous_status=position.last_ott_status,
                    current_status=current_ott,
                    price_at_change=current_price,
                    price_movement_pct=pnl_pct,
                    position_type=position.position_type.value,
                    triggered_alert=alert_triggered and f"OTT" in str(current_ott),
                )
                db.add(change)
                logger.debug(
                    f"Signal change logged: {position.pair} OTT "
                    f"{position.last_ott_status} → {current_ott}"
                )

            # Check overall status change
            if position.last_signal_status and position.last_signal_status != current_overall:
                change = SignalChange.create_change(
                    pair=position.pair,
                    timeframe=position.timeframe,
                    signal_type=SignalType.OVERALL,
                    previous_status=position.last_signal_status,
                    current_status=current_overall,
                    price_at_change=current_price,
                    price_movement_pct=pnl_pct,
                    position_type=position.position_type.value,
                    triggered_alert=alert_triggered,
                )
                db.add(change)
                logger.debug(
                    f"Signal change logged: {position.pair} OVERALL "
                    f"{position.last_signal_status} → {current_overall}"
                )

        except Exception as e:
            logger.error(f"Failed to log signal changes for {position.pair}: {e}")

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

            # Check if alert should be sent (pass signal_states for important indicators check)
            should_alert, reason = self._should_send_alert(
                position=position,
                current_status=current_status,
                pnl_pct=pnl_pct,
                signal_states=signal.signal_states,
            )

            if should_alert:
                logger.info(
                    f"Alert triggered for {position.pair}: {reason}"
                )

                # Format and send Telegram alert with database logging
                if self.telegram_enabled:
                    # Convert signal_states enums to plain strings before passing to notifier
                    signal_states_str = {
                        k: (v.value if hasattr(v, 'value') else str(v))
                        for k, v in signal.signal_states.items()
                    }
                    # Use send_position_alert which logs to database.
                    # Pass reason so notifier skips its own anti-spam gate.
                    self._telegram_notifier.send_position_alert(
                        position={
                            'pair': position.pair,
                            'position_type': position.position_type.value,
                            'entry_price': position.entry_price,
                            'timeframe': position.timeframe,
                        },
                        signals=signal_states_str,
                        previous_status=position.last_signal_status,
                        current_price=current_price,
                        is_daily_summary=False,
                        reason=reason,
                    )
                    logger.info(f"Telegram alert sent for {position.pair}")
                else:
                    logger.info("Telegram disabled, skipping alert")

                result["alert_sent"] = True

            # Update database with latest status and important indicators
            position.update_signal_status(current_status)

            # Update MA10 and OTT status independently (tracked separately)
            ma10_status = signal.signal_states.get("MA10", "NEUTRAL")
            ott_status = signal.signal_states.get("OTT", "NEUTRAL")

            # Extract string value from SignalState enum if present
            if hasattr(ma10_status, 'value'):
                ma10_status = ma10_status.value
            if hasattr(ott_status, 'value'):
                ott_status = ott_status.value

            # Log signal changes to signal_changes table
            self._log_signal_changes(
                db=db,
                position=position,
                current_price=current_price,
                pnl_pct=pnl_pct,
                current_ma10=ma10_status,
                current_ott=ott_status,
                current_overall=current_status,
                alert_triggered=should_alert,
            )

            position.last_ma10_status = ma10_status
            position.last_ott_status = ott_status
            position.last_checked_at = datetime.utcnow()

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

                # Check each position with smart scanning
                skipped_count = 0
                for position in open_positions:
                    # Smart scanning: check if enough time has passed
                    should_check, minutes_remaining = self._should_check_position(position)
                    
                    if not should_check:
                        # Skip this position (not time yet)
                        skipped_count += 1
                        logger.debug(
                            f"Skipping {position.pair} ({position.timeframe}) - "
                            f"next check in {minutes_remaining} minutes"
                        )
                        continue
                    
                    # Check this position
                    result = self._check_single_position(position, db)
                    results["results"].append(result)

                    if result["success"]:
                        results["successful"] += 1
                        if result.get("alert_sent"):
                            results["alerts_sent"] += 1
                    else:
                        results["errors"] += 1

                # Log skipped positions
                if skipped_count > 0:
                    logger.info(f"Skipped {skipped_count} positions (smart scanning)")

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
