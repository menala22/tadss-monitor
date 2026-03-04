#!/usr/bin/env python3
"""
TA-DSS Position Monitor for GitHub Actions.

This script is designed to run on GitHub Actions scheduled workflows.
It checks all open positions and sends Telegram alerts on signal changes.

Usage:
    python scripts/github_monitor.py

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram bot token (required)
    TELEGRAM_CHAT_ID: Telegram chat ID (required)
    DATABASE_URL: Database connection string (default: sqlite:///./data/positions.db)
    APP_ENV: Application environment (default: production)
    LOG_LEVEL: Logging level (default: INFO)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitor import PositionMonitor
from src.config import settings

# Setup logging for GitHub Actions
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Run position monitoring check on GitHub Actions.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    logger.info("=" * 60)
    logger.info("TA-DSS Position Monitor - GitHub Actions")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}Z")
    logger.info("=" * 60)

    # Check Telegram configuration
    if not settings.telegram_enabled:
        logger.error("❌ Telegram not configured!")
        logger.error("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        logger.error("   in GitHub Secrets (Settings → Secrets and variables → Actions)")
        return 1

    logger.info("✅ Telegram configured")

    try:
        # Initialize monitor
        monitor = PositionMonitor(telegram_enabled=True)
        logger.info("✅ PositionMonitor initialized")

        # Run monitoring check
        logger.info("🔍 Starting position check...")
        results = monitor.check_all_positions()

        # Log summary
        logger.info("=" * 60)
        logger.info("📊 SCAN SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Total positions: {results.get('total', 0)}")
        logger.info(f"   Successful: {results.get('successful', 0)}")
        logger.info(f"   Alerts sent: {results.get('alerts_sent', 0)}")
        logger.info(f"   Errors: {results.get('errors', 0)}")
        logger.info("=" * 60)

        # Check for errors
        if results.get('errors', 0) > 0:
            logger.warning(f"⚠️ {results['errors']} error(s) occurred during scan")
            # Log individual errors
            for result in results.get('results', []):
                if result.get('error'):
                    logger.warning(f"   - {result.get('pair', 'Unknown')}: {result['error']}")

        # Check if database exists
        db_path = Path("data/positions.db")
        if not db_path.exists():
            logger.warning("⚠️ Database not found at data/positions.db")
            logger.warning("   This is normal if no positions have been created yet.")
            logger.warning("   Create positions via API or Dashboard first.")

        logger.info(f"✅ Scan completed at {datetime.utcnow().isoformat()}Z")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
