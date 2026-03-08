"""
Market Data Service for TA-DSS.

This service provides a high-level API for managing market data cache status.
It handles:
1. Status tracking - Query data quality for pairs/timeframes
2. Status updates - Refresh status after fetching data
3. Bulk operations - Get all statuses, filter by quality
4. Integration - Sync with OHLCV cache manager

Usage:
    from src.services.market_data_service import MarketDataService
    from src.database import get_db_context

    with get_db_context() as db:
        service = MarketDataService(db)
        
        # Get status for all pairs
        statuses = service.get_all_statuses()
        
        # Get status for single pair
        pair_status = service.get_pair_status("BTC/USDT")
        
        # Update status after fetch
        service.update_status("BTC/USDT", "d1", candle_count=150, source="ccxt")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.models.market_data_status_model import (
    MarketDataStatus,
    DataQuality,
)
from src.models.ohlcv_cache_model import OHLCVCache
from src.services.ohlcv_cache_manager import OHLCVCacheManager

logger = logging.getLogger(__name__)


@dataclass
class PairStatus:
    """
    Aggregated status for a single pair across all timeframes.

    Attributes:
        pair: Trading pair symbol.
        overall_quality: Worst quality across all timeframes.
        timeframes: Dict of timeframe → detailed status.
        mtf_ready: Whether pair has sufficient data for MTF analysis.
        recommendation: Human-readable recommendation.
    """
    pair: str
    overall_quality: str = DataQuality.MISSING.value
    timeframes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    mtf_ready: bool = False
    recommendation: str = "Insufficient data"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "pair": self.pair,
            "overall_quality": self.overall_quality,
            "timeframes": self.timeframes,
            "mtf_ready": self.mtf_ready,
            "recommendation": self.recommendation,
        }


class MarketDataService:
    """
    Service for managing market data cache status.

    This service provides methods to:
    1. Query data status for pairs and timeframes
    2. Update status after fetching new data
    3. Sync status with actual OHLCV cache contents
    4. Get aggregated status for dashboard display

    Attributes:
        db: SQLAlchemy database session.
        cache_mgr: OHLCV cache manager for data operations.
    """

    # MTF timeframes by trading style
    MTF_TIMEFRAMES = {
        "SWING": ["w1", "d1", "h4"],
        "INTRADAY": ["d1", "h4", "h1"],
        "DAY": ["h4", "h1", "m15"],
        "POSITION": ["M1", "w1", "d1"],
        "SCALPING": ["h1", "m15", "m5"],
    }

    def __init__(self, db: Session):
        """
        Initialize the market data service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db
        self.cache_mgr = OHLCVCacheManager(db)

    def get_all_statuses(
        self,
        filter_quality: Optional[str] = None,
    ) -> Dict[str, PairStatus]:
        """
        Get status for all pairs in the database.

        Args:
            filter_quality: Optional quality filter (e.g., "STALE", "MISSING").

        Returns:
            Dict of pair → PairStatus.

        Example:
            >>> statuses = service.get_all_statuses()
            >>> for pair, status in statuses.items():
            ...     print(f"{pair}: {status.overall_quality}")
        """
        query = self.db.query(MarketDataStatus)

        if filter_quality:
            query = query.filter(MarketDataStatus.data_quality == filter_quality)

        rows = query.all()

        # Group by pair
        pair_statuses: Dict[str, PairStatus] = {}

        for row in rows:
            if row.pair not in pair_statuses:
                pair_statuses[row.pair] = PairStatus(pair=row.pair)

            pair_statuses[row.pair].timeframes[row.timeframe] = {
                "candle_count": row.candle_count,
                "last_candle_time": row.last_candle_time.isoformat() if row.last_candle_time else None,
                "quality": row.data_quality,
                "source": row.source,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }

        # Calculate overall quality and MTF readiness
        for pair_status in pair_statuses.values():
            self._calculate_overall_status(pair_status)

        return pair_statuses

    def get_pair_status(self, pair: str) -> Optional[PairStatus]:
        """
        Get status for a specific pair across all timeframes.

        Args:
            pair: Trading pair symbol (e.g., "BTC/USDT").

        Returns:
            PairStatus object or None if pair not found.

        Example:
            >>> status = service.get_pair_status("BTC/USDT")
            >>> if status:
            ...     print(f"Quality: {status.overall_quality}")
            ...     print(f"MTF Ready: {status.mtf_ready}")
        """
        rows = self.db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == pair
        ).all()

        if not rows:
            return None

        pair_status = PairStatus(pair=pair)

        for row in rows:
            pair_status.timeframes[row.timeframe] = {
                "candle_count": row.candle_count,
                "last_candle_time": row.last_candle_time.isoformat() if row.last_candle_time else None,
                "quality": row.data_quality,
                "source": row.source,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }

        self._calculate_overall_status(pair_status)
        return pair_status

    def get_timeframe_status(
        self,
        pair: str,
        timeframe: str,
    ) -> Optional[MarketDataStatus]:
        """
        Get status for a specific pair and timeframe.

        Args:
            pair: Trading pair symbol.
            timeframe: Timeframe (e.g., "d1", "h4").

        Returns:
            MarketDataStatus object or None if not found.
        """
        return self.db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == pair,
            MarketDataStatus.timeframe == timeframe,
        ).first()

    def update_status(
        self,
        pair: str,
        timeframe: str,
        candle_count: int,
        last_candle_time: Optional[datetime] = None,
        source: Optional[str] = None,
        data_quality: Optional[str] = None,
    ) -> MarketDataStatus:
        """
        Update or create status entry for a pair/timeframe.

        Args:
            pair: Trading pair symbol.
            timeframe: Timeframe.
            candle_count: Number of cached candles.
            last_candle_time: Timestamp of most recent candle.
            source: Data source (ccxt, twelvedata, gateio).
            data_quality: Quality assessment (auto-calculated if None).

        Returns:
            Updated MarketDataStatus object.

        Example:
            >>> status = service.update_status(
            ...     pair="BTC/USDT",
            ...     timeframe="d1",
            ...     candle_count=150,
            ...     source="ccxt",
            ... )
        """
        # Calculate quality if not provided
        if data_quality is None:
            age_hours = self._calculate_age_hours(last_candle_time)
            data_quality = MarketDataStatus.assess_quality(
                candle_count=candle_count,
                age_hours=age_hours,
                timeframe=timeframe,
            ).value

        # Find existing or create new
        status = self.get_timeframe_status(pair, timeframe)

        if status:
            # Update existing
            status.candle_count = candle_count
            status.last_candle_time = last_candle_time
            status.fetched_at = datetime.utcnow()
            status.data_quality = data_quality
            if source:
                status.source = source
        else:
            # Create new
            status = MarketDataStatus(
                pair=pair,
                timeframe=timeframe,
                candle_count=candle_count,
                last_candle_time=last_candle_time,
                data_quality=data_quality,
                source=source,
            )
            self.db.add(status)

        self.db.commit()
        self.db.refresh(status)

        logger.debug(
            f"Updated status: {pair} {timeframe} - "
            f"{candle_count} candles, quality={data_quality}"
        )

        return status

    def update_status_from_cache(
        self,
        pair: str,
        timeframe: str,
        df: pd.DataFrame,
        source: Optional[str] = None,
    ) -> MarketDataStatus:
        """
        Update status after fetching/saving OHLCV data.

        Args:
            pair: Trading pair symbol.
            timeframe: Timeframe.
            df: OHLCV DataFrame that was saved.
            source: Data source used.

        Returns:
            Updated MarketDataStatus object.
        """
        candle_count = len(df)
        last_candle_time = df.index.max() if len(df) > 0 else None

        return self.update_status(
            pair=pair,
            timeframe=timeframe,
            candle_count=candle_count,
            last_candle_time=last_candle_time,
            source=source,
        )

    def sync_all_statuses(self) -> Dict[str, int]:
        """
        Sync all status entries with actual OHLCV cache contents.

        This scans the OHLCV cache and updates status entries to match.
        Useful for initial population or recovery from inconsistencies.

        Returns:
            Dict with counts of updated/created/deleted entries.

        Example:
            >>> stats = service.sync_all_statuses()
            >>> print(f"Updated: {stats['updated']}, Created: {stats['created']}")
        """
        stats = {"updated": 0, "created": 0, "deleted": 0}

        # Get all unique pair/timeframe combinations from cache
        cache_entries = (
            self.db.query(
                OHLCVCache.symbol,
                OHLCVCache.timeframe,
            )
            .distinct()
            .all()
        )

        # Build set of (pair, timeframe) in cache
        cache_keys = {(entry.symbol, entry.timeframe) for entry in cache_entries}

        # Update or create status for each cache entry
        for symbol, timeframe in cache_keys:
            # Get candle count and last candle time from cache
            cache_data = (
                self.db.query(OHLCVCache)
                .filter(
                    OHLCVCache.symbol == symbol,
                    OHLCVCache.timeframe == timeframe,
                )
                .all()
            )

            if not cache_data:
                continue

            candle_count = len(cache_data)
            last_candle_time = max(c.timestamp for c in cache_data)
            age_hours = self._calculate_age_hours(last_candle_time)
            quality = MarketDataStatus.assess_quality(
                candle_count=candle_count,
                age_hours=age_hours,
                timeframe=timeframe,
            ).value

            # Update or create status
            status = self.get_timeframe_status(symbol, timeframe)

            if status:
                status.candle_count = candle_count
                status.last_candle_time = last_candle_time
                status.data_quality = quality
                status.fetched_at = datetime.utcnow()
                stats["updated"] += 1
            else:
                status = MarketDataStatus(
                    pair=symbol,
                    timeframe=timeframe,
                    candle_count=candle_count,
                    last_candle_time=last_candle_time,
                    data_quality=quality,
                    source=None,  # Unknown source for existing cache
                )
                self.db.add(status)
                stats["created"] += 1

        self.db.commit()

        # Delete status entries for pairs/timeframes not in cache
        all_statuses = self.db.query(MarketDataStatus).all()
        for status in all_statuses:
            if (status.pair, status.timeframe) not in cache_keys:
                self.db.delete(status)
                stats["deleted"] += 1

        self.db.commit()

        logger.info(
            f"Status sync complete: {stats['updated']} updated, "
            f"{stats['created']} created, {stats['deleted']} deleted"
        )

        return stats

    def get_statuses_by_quality(
        self,
        quality: str,
    ) -> List[PairStatus]:
        """
        Get all pairs with a specific quality level.

        Args:
            quality: Quality level to filter by.

        Returns:
            List of PairStatus objects.
        """
        all_statuses = self.get_all_statuses(filter_quality=quality)
        return list(all_statuses.values())

    def get_stale_pairs(self) -> List[str]:
        """
        Get list of pairs with any STALE or MISSING timeframe.

        Returns:
            List of pair symbols needing refresh.
        """
        stale_statuses = self.get_all_statuses()
        stale_pairs = []

        for pair, status in stale_statuses.items():
            if status.overall_quality in (DataQuality.STALE.value, DataQuality.MISSING.value):
                stale_pairs.append(pair)

        return stale_pairs

    def get_mtf_ready_pairs(
        self,
        trading_style: str = "SWING",
    ) -> List[str]:
        """
        Get pairs with sufficient data for MTF analysis.

        Args:
            trading_style: Trading style (SWING, INTRADAY, etc.).

        Returns:
            List of pair symbols ready for MTF scanning.
        """
        required_timeframes = self.MTF_TIMEFRAMES.get(trading_style, ["w1", "d1", "h4"])
        all_statuses = self.get_all_statuses()
        ready_pairs = []

        for pair, status in all_statuses.items():
            # Check if all required timeframes have GOOD+ quality
            has_all_timeframes = all(
                tf in status.timeframes for tf in required_timeframes
            )
            if not has_all_timeframes:
                continue

            min_quality = min(
                status.timeframes[tf]["quality"]
                for tf in required_timeframes
            )
            if min_quality in (DataQuality.GOOD.value, DataQuality.EXCELLENT.value):
                ready_pairs.append(pair)

        return ready_pairs

    def _calculate_overall_status(self, pair_status: PairStatus) -> None:
        """
        Calculate overall quality and MTF readiness for a pair.

        Args:
            pair_status: PairStatus object to update.
        """
        if not pair_status.timeframes:
            pair_status.overall_quality = DataQuality.MISSING.value
            pair_status.mtf_ready = False
            pair_status.recommendation = "No data available"
            return

        # Overall quality is the worst quality across timeframes
        quality_order = {
            DataQuality.EXCELLENT.value: 4,
            DataQuality.GOOD.value: 3,
            DataQuality.STALE.value: 2,
            DataQuality.MISSING.value: 1,
        }

        min_quality_value = min(
            quality_order.get(tf["quality"], 1)
            for tf in pair_status.timeframes.values()
        )

        pair_status.overall_quality = {
            4: DataQuality.EXCELLENT.value,
            3: DataQuality.GOOD.value,
            2: DataQuality.STALE.value,
            1: DataQuality.MISSING.value,
        }[min_quality_value]

        # MTF ready if all timeframes have GOOD+ quality
        all_good = all(
            tf["quality"] in (DataQuality.GOOD.value, DataQuality.EXCELLENT.value)
            for tf in pair_status.timeframes.values()
        )
        pair_status.mtf_ready = all_good

        # Generate recommendation
        if pair_status.mtf_ready:
            pair_status.recommendation = "Ready for MTF analysis"
        elif pair_status.overall_quality == DataQuality.STALE.value:
            pair_status.recommendation = "Refresh recommended before scanning"
        else:
            pair_status.recommendation = "Refresh required - insufficient data"

    def _calculate_age_hours(
        self,
        last_candle_time: Optional[datetime],
    ) -> float:
        """
        Calculate hours since last candle.

        Args:
            last_candle_time: Timestamp of last candle.

        Returns:
            Hours since last candle (large number if None).
        """
        if last_candle_time is None:
            return 9999  # Very old

        age = datetime.utcnow() - last_candle_time
        return age.total_seconds() / 3600

    def delete_pair_status(self, pair: str) -> int:
        """
        Delete all status entries for a pair.

        Args:
            pair: Trading pair symbol.

        Returns:
            Number of entries deleted.
        """
        count = self.db.query(MarketDataStatus).filter(
            MarketDataStatus.pair == pair
        ).delete()
        self.db.commit()
        logger.info(f"Deleted {count} status entries for {pair}")
        return count

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all market data.

        Returns:
            Dict with summary statistics.

        Example:
            >>> summary = service.get_summary()
            >>> print(f"Total pairs: {summary['total_pairs']}")
            >>> print(f"Excellent: {summary['by_quality']['EXCELLENT']}")
        """
        all_statuses = self.get_all_statuses()

        by_quality = {
            DataQuality.EXCELLENT.value: 0,
            DataQuality.GOOD.value: 0,
            DataQuality.STALE.value: 0,
            DataQuality.MISSING.value: 0,
        }

        for status in all_statuses.values():
            by_quality[status.overall_quality] = by_quality.get(status.overall_quality, 0) + 1

        return {
            "total_pairs": len(all_statuses),
            "mtf_ready": sum(1 for s in all_statuses.values() if s.mtf_ready),
            "by_quality": by_quality,
            "needs_refresh": sum(1 for s in all_statuses.values() if not s.mtf_ready),
        }
