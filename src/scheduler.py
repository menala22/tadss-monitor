"""
Background Scheduler for TA-DSS.

This module provides automated position monitoring using APScheduler.
It periodically checks all open positions, calculates technical signals,
and sends Telegram alerts on significant changes.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.monitor import PositionMonitor
from src.database import get_db_context
from src.models.position_model import Position, PositionStatus
from src.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def _load_pair_data_from_universal(
    pair: str,
    config,
    db,
) -> Optional[Dict[str, Any]]:
    """
    Load MTF data for a pair from ohlcv_universal table.

    Args:
        pair: Trading pair symbol (e.g., 'BTC/USDT').
        config: MTFTimeframeConfig with htf_timeframe, mtf_timeframe, ltf_timeframe.
        db: SQLAlchemy database session.

    Returns:
        Dict with 'htf', 'mtf', 'ltf' DataFrames, or None if data unavailable.
    """
    from src.models.ohlcv_universal_model import OHLCVUniversal
    import pandas as pd

    def get_timeframe_data(tf: str) -> Optional[pd.DataFrame]:
        """Fetch data for a single timeframe."""
        candles = (
            db.query(OHLCVUniversal)
            .filter(
                OHLCVUniversal.symbol == pair,
                OHLCVUniversal.timeframe == tf,
            )
            .order_by(OHLCVUniversal.timestamp.desc())
            .limit(200)
            .all()
        )

        if not candles:
            return None

        # Convert to DataFrame
        data = [{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume or 0,
        } for c in candles]

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df

    # Load all three timeframes from config
    htf_data = get_timeframe_data(config.htf_timeframe)
    mtf_data = get_timeframe_data(config.mtf_timeframe)
    ltf_data = get_timeframe_data(config.ltf_timeframe)

    if htf_data is None or mtf_data is None or ltf_data is None:
        logger.warning(f"Missing data for {pair}: htf={htf_data is not None}, mtf={mtf_data is not None}, ltf={ltf_data is not None}")
        return None

    return {
        'htf': htf_data,
        'mtf': mtf_data,
        'ltf': ltf_data,
    }


class SchedulerManager:
    """
    Manages the APScheduler lifecycle and job registration.

    This class handles:
    1. Initializing the AsyncIOScheduler
    2. Registering the monitoring job using PositionMonitor
    3. Starting/stopping the scheduler
    4. Running in a separate thread to not block FastAPI

    Attributes:
        scheduler: APScheduler instance.
        monitor: PositionMonitor instance.
    """

    def __init__(self):
        """Initialize the scheduler manager."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.monitor: Optional[PositionMonitor] = None
        self._running = False

    def _get_open_positions_count(self) -> int:
        """Return the number of currently open positions."""
        try:
            with get_db_context() as db:
                return (
                    db.query(Position)
                    .filter(Position.status == PositionStatus.OPEN)
                    .count()
                )
        except Exception:
            return 0

    def _send_startup_message(self) -> None:
        """Send a Telegram message when the system starts."""
        try:
            notifier = TelegramNotifier()
            if not notifier.enabled:
                return

            count = self._get_open_positions_count()
            next_run = self.get_next_run_time()
            next_run_str = next_run.strftime("%H:%M UTC") if next_run else "unknown"

            message = (
                "✅ *TA-DSS Started*\n\n"
                f"Monitoring *{count}* open position(s)\n"
                f"Next check: `{next_run_str}`\n"
                f"Heartbeat: daily at `07:00 GMT+7`\n\n"
                f"_🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
            )
            notifier.send_custom_message(message)
            logger.info("Startup Telegram message sent")
        except Exception as e:
            logger.warning(f"Failed to send startup message: {e}")

    def _send_daily_heartbeat(self) -> None:
        """Send a daily Telegram heartbeat to confirm the system is running."""
        try:
            notifier = TelegramNotifier()
            if not notifier.enabled:
                return

            count = self._get_open_positions_count()
            next_run = self.get_next_run_time()
            next_run_str = next_run.strftime("%H:%M UTC") if next_run else "unknown"

            message = (
                "💓 *TA-DSS Heartbeat*\n\n"
                "System is running normally\n"
                f"Monitoring *{count}* open position(s)\n"
                f"Next check: `{next_run_str}`\n\n"
                f"_🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"
            )
            notifier.send_custom_message(message)
            logger.info("Daily heartbeat sent")
        except Exception as e:
            logger.warning(f"Failed to send daily heartbeat: {e}")

    async def _run_market_data_prefetch(self) -> None:
        """
        Run smart fetch for all watchlist pairs via MarketDataOrchestrator.

        This job runs every hour at :20 to keep the ohlcv_universal cache fresh.
        It uses smart fetch logic to only fetch stale/missing data.
        
        SPREAD FETCH: To avoid Twelve Data rate limit (8 calls/min), fetches are
        spread across time with a delay between each API call. This prevents burst
        requests that exceed the free tier limits.

        Defined as async so AsyncIOScheduler awaits it directly, avoiding the
        asyncio executor Future wrapping that caused CancelledError (BUG-029).
        The blocking DB/network work runs in a thread via asyncio.to_thread().
        """
        import asyncio
        import time

        def _sync_prefetch() -> None:
            try:
                from src.services.market_data_orchestrator import MarketDataOrchestrator

                logger.info("Market data prefetch job STARTED")

                with get_db_context() as db:
                    orchestrator = MarketDataOrchestrator(db)
                    
                    # SPREAD FETCH: Get stale items first, then fetch with delays
                    stale_items = orchestrator.get_stale_items()
                    
                    if not stale_items:
                        logger.info("Market data prefetch: No stale data, skipping")
                        return
                    
                    logger.info(f"Market data prefetch: {len(stale_items)} stale items to fetch")
                    
                    # Fetch with rate limiting: 12 seconds between Twelve Data calls
                    # This keeps us at ~5 calls/minute (under 8 limit with margin)
                    for i, (symbol, timeframe) in enumerate(stale_items):
                        if i > 0:
                            # Check if this is a Twelve Data pair
                            provider = orchestrator.get_optimal_provider(symbol)
                            if provider == 'twelvedata':
                                # Rate limit: 12 second delay between Twelve Data calls
                                delay = 12.0
                                logger.debug(
                                    f"Rate limit delay: waiting {delay}s before fetching "
                                    f"{symbol} {timeframe} (Twelve Data)"
                                )
                                time.sleep(delay)
                            else:
                                # Small delay for other providers too (be polite)
                                time.sleep(1.0)
                        
                        logger.info(f"Fetching {symbol} {timeframe} ({i+1}/{len(stale_items)})")
                        orchestrator.fetch_if_needed(symbol, timeframe)

                    logger.info("Market data prefetch job DONE")
                    
            except Exception as exc:
                logger.error(f"Market data prefetch job FAILED: {exc}", exc_info=True)

        await asyncio.to_thread(_sync_prefetch)

    def _run_mtf_hourly_scan(self) -> None:
        """
        Run MTF opportunity scan every hour at :20.

        This job uses the upgraded 4-layer MTF framework:
        1. Load watchlist pairs with their configured trading styles
        2. Fetch data from ohlcv_universal table (read-only, no live API calls)
        3. For each pair and trading style combination:
           a. Layer 1: Classify MTF context (ADX, ATR, EMA distance)
           b. Layer 2: Run context-gated setup detection
           c. Layer 3: Score pullback quality (5 factors)
           d. Layer 4: Calculate weighted alignment + position sizing
        4. Filter opportunities (exclude TRENDING_EXTENSION, weighted < 0.50)
        5. Save all opportunities to database
        6. Send Telegram alert for high-conviction (weighted >= 0.60)

        Schedule: Every hour at :20 minutes (XX:20 UTC)
        """
        try:
            logger.info("MTF hourly scan job STARTED")
            from src.services.mtf_opportunity_scanner import MTFOpportunityScanner
            from src.services.mtf_opportunity_service import MTFOpportunityService
            from src.services.mtf_notifier import send_new_opportunity_alert
            from src.models.mtf_watchlist_model import MTFWatchlistItem
            from src.models.mtf_models import TradingStyle

            with get_db_context() as db:
                # Get watchlist items with trading styles
                watchlist_items = db.query(MTFWatchlistItem).order_by(MTFWatchlistItem.added_at).all()
                if not watchlist_items:
                    logger.warning("MTF scan: No pairs in watchlist")
                    return

                # Initialize service
                opportunity_service = MTFOpportunityService(db)

                # Track opportunities for alerting
                new_opportunities = []
                total_scanned = 0

                # Always scan SWING + INTRADAY for every pair regardless of watchlist setting
                DEFAULT_SCAN_STYLES = ["SWING", "INTRADAY"]

                for item in watchlist_items:
                    pair = item.pair
                    for trading_style_str in DEFAULT_SCAN_STYLES:
                        try:
                            trading_style = TradingStyle[trading_style_str.upper()]
                        except KeyError:
                            logger.warning(f"Invalid trading style '{trading_style_str}' for {pair}, skipping")
                            continue

                        total_scanned += 1

                        try:
                            # Initialize scanner for this trading style
                            scanner = MTFOpportunityScanner(
                                min_alignment=2,
                                min_rr_ratio=2.0,
                                trading_style=trading_style,
                            )

                            # Load data from ohlcv_universal table
                            data = _load_pair_data_from_universal(pair, scanner.config, db)

                            if data is None:
                                logger.debug(f"MTF scan: No data for {pair} ({trading_style.value}), skipping")
                                continue

                            # Run MTF analysis
                            alignment = scanner.analyzer.analyze_pair(
                                pair=pair,
                                htf_data=data["htf"],
                                mtf_data=data["mtf"],
                                ltf_data=data["ltf"],
                            )

                            # Check if should save
                            if opportunity_service.should_save_opportunity(alignment):
                                # Detect patterns
                                patterns = scanner._detect_patterns(
                                    htf_bias=alignment.htf_bias,
                                    mtf_setup=alignment.mtf_setup,
                                    ltf_entry=alignment.ltf_entry,
                                )

                                # Detect divergence
                                divergence_result = scanner.divergence_detector.detect_divergence(data["mtf"])
                                divergence = divergence_result.latest_type.value if divergence_result.divergences else None

                                # Save opportunity with HTF/MTF data for target calculation
                                opp = opportunity_service.save_opportunity(
                                    pair=pair,
                                    alignment=alignment,
                                    trading_style=trading_style,
                                    patterns=patterns,
                                    divergence=divergence,
                                    htf_data=data["htf"],
                                    mtf_data=data["mtf"],
                                )

                                # Track for alerting
                                new_opportunities.append(opp)

                        except Exception as e:
                            logger.error(f"MTF scan: Error analyzing {pair} ({trading_style.value}): {e}", exc_info=True)
                            continue

                # Send alerts for high-conviction opportunities (no throttling)
                alerts_sent = 0
                for opp in new_opportunities:
                    if opp.weighted_score >= 0.60:  # Alert threshold
                        try:
                            sent = send_new_opportunity_alert(opp)
                            if sent:
                                alerts_sent += 1
                        except Exception as e:
                            logger.error(f"MTF scan: Failed to send alert for {opp.pair}: {e}", exc_info=True)

                logger.info(
                    f"MTF scan complete: {total_scanned} pair/style combinations, "
                    f"{len(new_opportunities)} opportunities saved, "
                    f"{alerts_sent} alerts sent"
                )

        except Exception as exc:
            logger.error(f"MTF hourly scan failed: {exc}", exc_info=True)

    def _cleanup_expired_opportunities(self) -> None:
        """
        Auto-close MTF opportunities older than 24 hours.

        This job runs daily at 01:00 UTC to clean up expired opportunities.
        """
        try:
            from src.services.mtf_opportunity_service import MTFOpportunityService

            with get_db_context() as db:
                service = MTFOpportunityService(db)
                count = service.cleanup_expired_opportunities(expiry_hours=24)

                if count > 0:
                    logger.info(f"Expired {count} MTF opportunities (older than 24h)")
                else:
                    logger.debug("MTF opportunity cleanup: No expired opportunities")

        except Exception as exc:
            logger.error(f"MTF opportunity cleanup failed: {exc}", exc_info=True)

    def start(self) -> None:
        """
        Start the background scheduler.

        This initializes the scheduler, registers the monitoring job
        using PositionMonitor, and starts the scheduler in a separate thread.

        The scheduler runs independently and does not block the main thread.
        
        Note: First run is delayed by 10 minutes to avoid API congestion
        at round hour boundaries when many services refresh data.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return

        # Initialize position monitor
        self.monitor = PositionMonitor(
            telegram_enabled=settings.telegram_enabled,
        )

        self.scheduler = AsyncIOScheduler(
            timezone=settings.timezone,
            job_defaults={
                "coalesce": True,  # Combine missed executions
                "max_instances": 1,  # Only one job at a time
                "misfire_grace_time": 60,  # 60s grace for missed jobs
            },
        )

        # Add monitoring job with 10-minute offset from round hour
        # This avoids API congestion when many services refresh at :00
        # Fixed interval: Every hour at :10 minutes (XX:10 UTC)
        self.scheduler.add_job(
            func=self.monitor.check_all_positions,
            trigger='cron',
            minute=10,  # Always run at :10 past the hour
            hour='*',   # Every hour
            id="position_monitoring",
            name="Monitor Open Positions",
            replace_existing=True,
            max_instances=1,
        )

        # Daily heartbeat: 00:00 UTC = 07:00 GMT+7
        self.scheduler.add_job(
            func=self._send_daily_heartbeat,
            trigger='cron',
            hour=0,
            minute=0,
            id="daily_heartbeat",
            name="Daily System Heartbeat",
            replace_existing=True,
            max_instances=1,
        )

        # Market data prefetch: every hour at :15
        # Runs at :15 to keep ohlcv_universal fresh for MTF scanning.
        # Uses smart fetch logic to only fetch stale/missing data.
        # Note: May cause API rate limiting if many symbols need refresh.
        self.scheduler.add_job(
            func=self._run_market_data_prefetch,
            trigger='cron',
            minute=15,
            hour='*',
            id="market_data_prefetch",
            name="Market Data Prefetch",
            replace_existing=True,
            max_instances=1,
        )

        # MTF hourly scan: every hour at :20
        # Runs at :20 to scan for MTF opportunities using upgraded 4-layer framework.
        # Saves all opportunities to database and sends Telegram alerts for high-conviction.
        self.scheduler.add_job(
            func=self._run_mtf_hourly_scan,
            trigger='cron',
            minute=20,
            hour='*',
            id="mtf_hourly_scan",
            name="MTF Hourly Opportunity Scan",
            replace_existing=True,
            max_instances=1,
        )

        # MTF opportunity cleanup: daily at 01:00 UTC
        # Auto-expires opportunities older than 24 hours.
        self.scheduler.add_job(
            func=self._cleanup_expired_opportunities,
            trigger='cron',
            hour=1,
            minute=0,
            id="mtf_opportunity_cleanup",
            name="MTF Opportunity Auto-Expiration",
            replace_existing=True,
            max_instances=1,
        )

        # Log all scheduled jobs for debugging
        logger.info("=" * 50)
        logger.info("SCHEDULED JOBS:")
        for job in self.scheduler.get_jobs():
            # APScheduler 4.x uses different API - just log name and trigger
            logger.info(f"  - {job.name}: {job.trigger}")
        logger.info("=" * 50)

        logger.info(
            "Scheduled 'position_monitoring' job "
            "(runs every hour at :10 minutes past the hour)"
        )
        logger.info(
            "Scheduled 'daily_heartbeat' job "
            "(runs daily at 00:00 UTC / 07:00 GMT+7)"
        )
        logger.info(
            "Scheduled 'market_data_prefetch' job "
            "(runs every hour at :15 minutes past the hour)"
        )
        logger.info(
            "Scheduled 'mtf_hourly_scan' job "
            "(runs every hour at :20 minutes past the hour)"
        )
        logger.info(
            "Scheduled 'mtf_opportunity_cleanup' job "
            "(runs daily at 01:00 UTC - auto-expires opportunities older than 24h)"
        )

        # Start scheduler in background thread
        self.scheduler.start()
        self._running = True

        logger.info("Scheduler started successfully (first run in 10 minutes)")

        # Send startup notification
        self._send_startup_message()

    def stop(self) -> None:
        """
        Stop the background scheduler.

        This gracefully shuts down the scheduler and waits for
        any running jobs to complete.
        """
        if not self._running:
            logger.warning("Scheduler not running")
            return

        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None

        self._running = False
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """
        Check if scheduler is currently running.

        Returns:
            True if scheduler is active, False otherwise.
        """
        return self._running

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time for the monitoring job.

        Returns:
            Next run time as datetime, or None if not scheduled.
        """
        if not self.scheduler or not self._running:
            return None

        job = self.scheduler.get_job("position_monitoring")
        return job.next_run_time if job else None

    def run_now(self) -> Dict[str, Any]:
        """
        Run the monitoring check immediately (without waiting for schedule).

        Returns:
            Dictionary with check results.
        """
        if not self.monitor:
            self.monitor = PositionMonitor(telegram_enabled=settings.telegram_enabled)

        return self.monitor.check_all_positions()


# Global scheduler manager instance
_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """
    Get or create the global scheduler manager.

    Returns:
        SchedulerManager instance.
    """
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager


def start_scheduler() -> None:
    """
    Initialize and start the background scheduler.

    This function should be called during FastAPI startup
    (e.g., in the lifespan event handler).

    The scheduler runs in a separate thread and does not block
    the main FastAPI application.

    Example:
        from src.scheduler import start_scheduler

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            start_scheduler()
            yield
            # Shutdown
            stop_scheduler()
    """
    global _scheduler_manager

    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()

    _scheduler_manager.start()

    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    """
    Stop the background scheduler.

    This function should be called during FastAPI shutdown
    to gracefully terminate background jobs.
    """
    global _scheduler_manager

    if _scheduler_manager:
        _scheduler_manager.stop()
        _scheduler_manager = None

    logger.info("Background scheduler stopped")


def get_scheduler_status() -> dict[str, Any]:
    """
    Get current scheduler status.

    Returns:
        Dictionary with scheduler status information.
    """
    global _scheduler_manager

    if _scheduler_manager is None:
        return {
            "running": False,
            "next_run_time": None,
            "job_count": 0,
        }

    return {
        "running": _scheduler_manager.is_running(),
        "next_run_time": _scheduler_manager.get_next_run_time(),
        "job_count": 3,  # position_monitoring + daily_heartbeat + mtf_cache_prefetch
    }


def run_monitoring_check_now() -> Dict[str, Any]:
    """
    Run the monitoring check immediately (without waiting for schedule).

    This is useful for testing or manual triggers.

    Returns:
        Dictionary with check results.

    Example:
        from src.scheduler import run_monitoring_check_now
        results = run_monitoring_check_now()
        print(f"Checked {results['total']} positions")
    """
    global _scheduler_manager

    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()

    if not _scheduler_manager.monitor:
        _scheduler_manager.monitor = PositionMonitor(
            telegram_enabled=settings.telegram_enabled
        )

    return _scheduler_manager.run_now()
