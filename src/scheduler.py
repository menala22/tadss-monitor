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

        # Initialize scheduler
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

        logger.info(
            "Scheduled 'position_monitoring' job "
            "(runs every hour at :10 minutes past the hour)"
        )
        logger.info(
            "Scheduled 'daily_heartbeat' job "
            "(runs daily at 00:00 UTC / 07:00 GMT+7)"
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
        "job_count": 2,  # position_monitoring + daily_heartbeat
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
