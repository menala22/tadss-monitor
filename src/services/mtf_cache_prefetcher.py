"""
MTF Cache Prefetcher for TA-DSS.

Background job that pre-populates the OHLCV cache for all watchlist pairs and
MTF timeframes. The MTF scanner reads the cache only; this prefetcher keeps
the cache fresh so every scan is instant and zero live API calls happen from
the dashboard.

Architecture (mirrors positions):
    Scheduler (every 2 hours at :20)
      → reads watchlist from DB
      → for each pair × timeframe:
          → skips if cache is still fresh
          → fetches from DataFetcher if stale
          → DataFetcher saves to cache automatically
          → also saves under internal-format key for MTF route reads

    MTF scan (user-triggered, cache-only):
      → reads from SQLite cache
      → returns "no data" if empty/stale — never blocks on live fetch
"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from src.data_fetcher import DataFetcher, DataFetchError
from src.models.mtf_models import MTFTimeframeConfig, TradingStyle
from src.models.mtf_watchlist_model import get_watchlist
from src.services.ohlcv_cache_manager import OHLCVCacheManager

logger = logging.getLogger(__name__)

# Internal timeframe → DataFetcher API format
_TF_API_MAP: Dict[str, str] = {
    "m1": "1m",  "m5": "5m",  "m15": "15m", "m30": "30m",
    "h1": "1h",  "h2": "2h",  "h4": "4h",   "h6": "6h",  "h12": "12h",
    "d1": "1d",
    "w1": "1w",
    "M1": "1M",
}

# Candle limits per timeframe role
_ROLE_LIMITS: Dict[str, int] = {"htf": 250, "mtf": 150, "ltf": 100}

# Styles to prefetch (SWING + INTRADAY covers w1, d1, h4, h1)
# DAY and SCALPING use minute-level TFs — too frequent for a 2-hour job.
_PREFETCH_STYLES: List[TradingStyle] = [TradingStyle.SWING, TradingStyle.INTRADAY]


def _collect_timeframes(styles: List[TradingStyle]) -> Dict[str, int]:
    """
    Return {internal_tf: candle_limit} for all timeframes needed across styles.

    Each TF gets the highest limit required across all roles.
    """
    tf_limits: Dict[str, int] = {}
    for style in styles:
        config = MTFTimeframeConfig.get_config(style)
        for role, internal_tf in [
            ("htf", config.htf_timeframe),
            ("mtf", config.mtf_timeframe),
            ("ltf", config.ltf_timeframe),
        ]:
            limit = _ROLE_LIMITS[role]
            tf_limits[internal_tf] = max(tf_limits.get(internal_tf, 0), limit)
    return tf_limits


def prefetch_mtf_cache(db: Session) -> Dict[str, int]:
    """
    Pre-populate the OHLCV cache for all watchlist pairs and MTF timeframes.

    Skips any pair×timeframe whose cache is still within the freshness window.
    DataFetcher.get_ohlcv() saves to the cache automatically; this function
    also saves under the internal-format key so MTF route cache reads find it.

    Args:
        db: SQLAlchemy session (caller manages commit/rollback lifecycle).

    Returns:
        {"fetched": N, "skipped": N, "errors": N}
    """
    cache_mgr = OHLCVCacheManager(db)
    fetcher = DataFetcher()

    pairs = get_watchlist(db)
    tf_limits = _collect_timeframes(_PREFETCH_STYLES)

    stats = {"fetched": 0, "skipped": 0, "errors": 0}

    logger.info(
        f"MTF prefetch starting: {len(pairs)} pairs, "
        f"{len(tf_limits)} timeframes — "
        f"{', '.join(tf_limits.keys())}"
    )

    for pair in pairs:
        for internal_tf, limit in tf_limits.items():
            api_tf = _TF_API_MAP.get(internal_tf, internal_tf)

            # Use normalized (stored) key for timestamp lookup
            normalized_tf = cache_mgr._normalize_timeframe_for_cache(internal_tf)
            last_ts = cache_mgr.get_last_cached_timestamp(pair, normalized_tf)

            if cache_mgr._is_cache_fresh(last_ts, internal_tf):
                logger.debug(f"Prefetch skip (fresh): {pair} {internal_tf}")
                stats["skipped"] += 1
                continue

            logger.info(
                f"Prefetching {pair} {internal_tf} "
                f"(api={api_tf}, limit={limit})"
            )
            try:
                df = fetcher.get_ohlcv(pair, api_tf, limit=limit)
                if df is None or df.empty:
                    logger.warning(f"Empty response for {pair} {internal_tf}")
                    stats["errors"] += 1
                    continue

                # DataFetcher already saves under the API-format key.
                # Also save under the internal-format key so that
                # _load_pair_data's get_cached_ohlcv(pair, "h4") normalises
                # "h4" → "4h" and finds the data.
                cache_mgr.save_ohlcv(pair, internal_tf, df)
                stats["fetched"] += 1

            except (DataFetchError, Exception) as exc:
                logger.warning(f"Prefetch failed for {pair} {internal_tf}: {exc}")
                stats["errors"] += 1

    logger.info(
        f"MTF prefetch complete: "
        f"{stats['fetched']} fetched, "
        f"{stats['skipped']} skipped, "
        f"{stats['errors']} errors"
    )
    return stats
