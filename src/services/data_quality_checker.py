"""
Data Quality Checker for MTF Analysis.

This module validates data quality before generating MTF reports,
ensuring users are warned about insufficient or stale data.

Features:
- Candle count validation (sufficient for full analysis)
- Data freshness check (not stale)
- Timeframe alignment validation
- Overall quality rating (PASS/WARNING/FAIL)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.models.mtf_models import (
    DataQualityReport,
    DataQualityStatus,
    MTFTimeframeConfig,
    TimeframeDataQuality,
)

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Check data quality for MTF analysis.

    The checker validates:
    1. Sufficient candle count for each timeframe
    2. Data freshness (not stale)
    3. Timeframe consistency
    4. Overall MTF readiness

    Attributes:
        htf_required: Minimum HTF candles for full SMA analysis (default 200).
        mtf_required: Minimum MTF candles (default 50).
        ltf_required: Minimum LTF candles (default 50).
        staleness_thresholds: Max hours old per timeframe.
    """

    def __init__(
        self,
        htf_required: int = 200,
        mtf_required: int = 50,
        ltf_required: int = 50,
    ):
        """
        Initialize data quality checker.

        Args:
            htf_required: Minimum HTF candles.
            mtf_required: Minimum MTF candles.
            ltf_required: Minimum LTF candles.
        """
        self.htf_required = htf_required
        self.mtf_required = mtf_required
        self.ltf_required = ltf_required

        # Freshness thresholds by timeframe type
        self.staleness_thresholds = {
            'w1': 240,    # 10 days for weekly
            'd1': 48,     # 2 days for daily
            'h4': 12,     # 12 hours for 4H
            'h1': 4,      # 4 hours for 1H
            'm15': 1,     # 1 hour for 15M
            'm5': 0.5,    # 30 minutes for 5M
        }

    def check_quality(
        self,
        htf_df: pd.DataFrame,
        mtf_df: pd.DataFrame,
        ltf_df: pd.DataFrame,
        config: MTFTimeframeConfig,
    ) -> DataQualityReport:
        """
        Check data quality for all 3 timeframes.

        Args:
            htf_df: HTF OHLCV data.
            mtf_df: MTF OHLCV data.
            ltf_df: LTF OHLCV data.
            config: MTF timeframe configuration.

        Returns:
            DataQualityReport with quality assessment.

        Example:
            >>> checker = DataQualityChecker()
            >>> report = checker.check_quality(htf_df, mtf_df, ltf_df, config)
            >>> print(report.overall_status)
            DataQualityStatus.WARNING
        """
        # Check each timeframe
        htf_quality = self._check_timeframe(
            df=htf_df,
            timeframe=config.htf_timeframe,
            required_count=self.htf_required,
        )

        mtf_quality = self._check_timeframe(
            df=mtf_df,
            timeframe=config.mtf_timeframe,
            required_count=self.mtf_required,
        )

        ltf_quality = self._check_timeframe(
            df=ltf_df,
            timeframe=config.ltf_timeframe,
            required_count=self.ltf_required,
        )

        # Determine overall status
        overall_status = self._determine_overall_status(
            htf_quality, mtf_quality, ltf_quality
        )

        # Check if MTF analysis can proceed
        is_mtf_ready = (
            htf_quality.is_sufficient and
            mtf_quality.is_sufficient and
            ltf_quality.is_sufficient
        )

        # Generate summary
        summary = self._generate_summary(
            htf_quality, mtf_quality, ltf_quality, overall_status
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            htf_quality, mtf_quality, ltf_quality
        )

        return DataQualityReport(
            overall_status=overall_status,
            htf_quality=htf_quality,
            mtf_quality=mtf_quality,
            ltf_quality=ltf_quality,
            has_conflicts=False,  # Would need additional logic
            is_mtf_ready=is_mtf_ready,
            summary=summary,
            recommendations=recommendations,
        )

    def _check_timeframe(
        self,
        df: pd.DataFrame,
        timeframe: str,
        required_count: int,
    ) -> TimeframeDataQuality:
        """
        Check data quality for a single timeframe.

        Args:
            df: OHLCV DataFrame.
            timeframe: Timeframe name.
            required_count: Minimum candles required.

        Returns:
            TimeframeDataQuality object.
        """
        candle_count = len(df)
        is_sufficient = candle_count >= required_count

        # Check freshness
        freshness_hours, max_freshness = self._check_freshness(df, timeframe)
        is_fresh = freshness_hours <= max_freshness

        # Collect issues
        issues = []

        if not is_sufficient:
            missing = required_count - candle_count
            issues.append(f"Need {missing} more candles for full analysis")

        if not is_fresh:
            hours_old = freshness_hours
            issues.append(f"Data is {hours_old:.1f}h old (max: {max_freshness}h)")

        # Determine status
        if is_sufficient and is_fresh:
            status = DataQualityStatus.PASS
        elif is_sufficient or (candle_count >= required_count * 0.5):
            status = DataQualityStatus.WARNING
        else:
            status = DataQualityStatus.FAIL

        return TimeframeDataQuality(
            timeframe=timeframe,
            candle_count=candle_count,
            required_count=required_count,
            is_sufficient=is_sufficient,
            freshness_hours=freshness_hours,
            max_freshness_hours=max_freshness,
            is_fresh=is_fresh,
            status=status,
            issues=issues,
        )

    def _check_freshness(
        self,
        df: pd.DataFrame,
        timeframe: str,
    ) -> Tuple[float, float]:
        """
        Check data freshness.

        Args:
            df: OHLCV DataFrame.
            timeframe: Timeframe name.

        Returns:
            Tuple of (hours_old, max_acceptable_hours).
        """
        if df.empty:
            return float('inf'), 0

        # Get last candle time
        try:
            last_candle_time = df.index[-1]
            if isinstance(last_candle_time, str):
                last_candle_time = pd.to_datetime(last_candle_time)

            # Make timezone-aware if needed
            if last_candle_time.tzinfo is None:
                last_candle_time = last_candle_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            hours_old = (now - last_candle_time).total_seconds() / 3600
        except Exception as e:
            logger.warning(f"Could not parse last candle time: {e}")
            hours_old = 0

        # Get max freshness for this timeframe
        max_freshness = self.staleness_thresholds.get(
            timeframe,
            24  # Default 24 hours
        )

        return max(0, hours_old), max_freshness

    def _determine_overall_status(
        self,
        htf: TimeframeDataQuality,
        mtf: TimeframeDataQuality,
        ltf: TimeframeDataQuality,
    ) -> DataQualityStatus:
        """
        Determine overall data quality status.

        Args:
            htf: HTF quality.
            mtf: MTF quality.
            ltf: LTF quality.

        Returns:
            Overall DataQualityStatus.
        """
        # If any FAIL, overall is FAIL
        if (
            htf.status == DataQualityStatus.FAIL or
            mtf.status == DataQualityStatus.FAIL or
            ltf.status == DataQualityStatus.FAIL
        ):
            return DataQualityStatus.FAIL

        # If any WARNING, overall is WARNING
        if (
            htf.status == DataQualityStatus.WARNING or
            mtf.status == DataQualityStatus.WARNING or
            ltf.status == DataQualityStatus.WARNING
        ):
            return DataQualityStatus.WARNING

        # All PASS
        return DataQualityStatus.PASS

    def _generate_summary(
        self,
        htf: TimeframeDataQuality,
        mtf: TimeframeDataQuality,
        ltf: TimeframeDataQuality,
        status: DataQualityStatus,
    ) -> str:
        """
        Generate human-readable summary.

        Args:
            htf: HTF quality.
            mtf: MTF quality.
            ltf: LTF quality.
            status: Overall status.

        Returns:
            Summary string.
        """
        if status == DataQualityStatus.PASS:
            return "✅ All timeframes have sufficient, fresh data"

        elif status == DataQualityStatus.WARNING:
            issues = []
            if not htf.is_sufficient:
                issues.append(f"HTF needs {htf.required_count - htf.candle_count} more candles")
            if not mtf.is_sufficient:
                issues.append(f"MTF needs {mtf.required_count - mtf.candle_count} more candles")
            if not ltf.is_sufficient:
                issues.append(f"LTF needs {ltf.required_count - ltf.candle_count} more candles")

            if issues:
                return "⚠️ " + ", ".join(issues)
            else:
                return "⚠️ Some data may be stale"

        else:  # FAIL
            return "❌ Insufficient data for reliable MTF analysis"

    def _generate_recommendations(
        self,
        htf: TimeframeDataQuality,
        mtf: TimeframeDataQuality,
        ltf: TimeframeDataQuality,
    ) -> List[str]:
        """
        Generate recommendations to improve data quality.

        Args:
            htf: HTF quality.
            mtf: MTF quality.
            ltf: LTF quality.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        if not htf.is_sufficient:
            missing = htf.required_count - htf.candle_count
            recommendations.append(
                f"Fetch {missing} more HTF candles for full SMA 200 analysis"
            )

        if not mtf.is_sufficient:
            missing = mtf.required_count - mtf.candle_count
            recommendations.append(
                f"Fetch {missing} more MTF candles"
            )

        if not ltf.is_sufficient:
            missing = ltf.required_count - ltf.candle_count
            recommendations.append(
                f"Fetch {missing} more LTF candles"
            )

        if not htf.is_fresh:
            recommendations.append(
                f"Refresh HTF data (currently {htf.freshness_hours:.1f}h old)"
            )

        if not mtf.is_fresh:
            recommendations.append(
                f"Refresh MTF data (currently {mtf.freshness_hours:.1f}h old)"
            )

        if not ltf.is_fresh:
            recommendations.append(
                f"Refresh LTF data (currently {ltf.freshness_hours:.1f}h old)"
            )

        if not recommendations:
            recommendations.append("Data quality is excellent - proceed with analysis")

        return recommendations


def check_data_quality(
    htf_df: pd.DataFrame,
    mtf_df: pd.DataFrame,
    ltf_df: pd.DataFrame,
    config: MTFTimeframeConfig,
) -> DataQualityReport:
    """
    Convenience function to check data quality.

    Args:
        htf_df: HTF OHLCV data.
        mtf_df: MTF OHLCV data.
        ltf_df: LTF OHLCV data.
        config: MTF timeframe configuration.

    Returns:
        DataQualityReport object.

    Example:
        >>> report = check_data_quality(htf_df, mtf_df, ltf_df, config)
        >>> print(report.summary)
    """
    checker = DataQualityChecker()
    return checker.check_quality(htf_df, mtf_df, ltf_df, config)
