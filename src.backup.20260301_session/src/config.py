"""
Application configuration management.

This module loads and validates environment variables using pydantic-settings,
providing a type-safe configuration object for the application.
"""

import logging
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# VALID TIMEFRAMES BY DATA SOURCE
# =============================================================================

# yfinance supported intervals
# See: https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py
VALID_TIMEFRAMES_YFINANCE = {
    "1m",   # 1 minute
    "2m",   # 2 minutes
    "5m",   # 5 minutes
    "15m",  # 15 minutes
    "30m",  # 30 minutes
    "60m",  # 60 minutes (1 hour)
    "1h",   # 1 hour (alias for 60m)
    "1d",   # 1 day
    "5d",   # 5 days
    "1wk",  # 1 week
    "1mo",  # 1 month
    "3mo",  # 3 months
}

# CCXT supported timeframes (common across exchanges)
# See: https://docs.ccxt.com/#/README?id=timeframes
VALID_TIMEFRAMES_CCXT = {
    "1m",    # 1 minute
    "3m",    # 3 minutes
    "5m",    # 5 minutes
    "15m",   # 15 minutes
    "30m",   # 30 minutes
    "1h",    # 1 hour
    "2h",    # 2 hours
    "4h",    # 4 hours
    "6h",    # 6 hours
    "8h",    # 8 hours
    "12h",   # 12 hours
    "1d",    # 1 day
    "3d",    # 3 days
    "1w",    # 1 week
    "1M",    # 1 month
}

# Internal timeframe format used by the application (standardized)
VALID_TIMEFRAMES_INTERNAL = {
    "m1", "m5", "m15", "m30",
    "h1", "h2", "h4", "h6", "h8", "h12",
    "d1", "d3", "d5",
    "w1",
    "M1",
}

# =============================================================================
# TIMEFRAME CONVERSION UTILITIES
# =============================================================================


def normalize_timeframe_to_internal(timeframe: str) -> str:
    """
    Convert various timeframe formats to internal standard format.

    Converts:
    - yfinance format: '1h', '1d', '1wk' → 'h1', 'd1', 'w1'
    - CCXT format: '1h', '4h', '1d' → 'h1', 'h4', 'd1'
    - Internal format: 'h4', 'd1' → 'h4', 'd1' (unchanged)

    Args:
        timeframe: Input timeframe string in any supported format.

    Returns:
        Normalized timeframe in internal format (e.g., 'h4', 'd1').

    Raises:
        ValueError: If the timeframe format cannot be parsed.
    """
    timeframe = timeframe.strip().lower()

    # Already in internal format
    if timeframe in VALID_TIMEFRAMES_INTERNAL:
        return timeframe

    # Handle yfinance multi-character units (wk, mo)
    yf_unit_map = {
        "wk": "w",
        "mo": "M",
    }

    for yf_unit, internal_unit in yf_unit_map.items():
        if timeframe.endswith(yf_unit):
            try:
                value = int(timeframe[:-len(yf_unit)])
                return f"{internal_unit}{value}"
            except ValueError:
                raise ValueError(f"Invalid timeframe format: {timeframe}")

    # Parse standard format (number + single char unit)
    if timeframe and timeframe[-1].isalpha():
        unit = timeframe[-1]
        try:
            value = int(timeframe[:-1])
        except ValueError:
            raise ValueError(f"Invalid timeframe format: {timeframe}")

        # Convert to internal format
        unit_map = {
            "m": "m",   # minutes
            "h": "h",   # hours
            "d": "d",   # days
            "w": "w",   # weeks
            "M": "M",   # months
        }

        if unit in unit_map:
            internal_unit = unit_map[unit]
            return f"{internal_unit}{value}"

    raise ValueError(f"Cannot parse timeframe: {timeframe}")


def normalize_timeframe_to_source(timeframe: str, source: Literal["yfinance", "ccxt"]) -> str:
    """
    Convert internal timeframe format to source-specific format.

    Args:
        timeframe: Internal format timeframe (e.g., 'h4', 'd1').
        source: Target data source ('yfinance' or 'ccxt').

    Returns:
        Timeframe in source-specific format.

    Raises:
        ValueError: If conversion is not possible.
    """
    timeframe = timeframe.strip().lower()

    # First normalize to internal format
    internal = normalize_timeframe_to_internal(timeframe)

    # Parse internal format
    if len(internal) < 2:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    unit = internal[0]
    try:
        value = int(internal[1:])
    except ValueError:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    if source == "yfinance":
        # yfinance uses format: number + unit (e.g., '1h', '1d', '1wk')
        yf_unit_map = {
            "m": "m",
            "h": "h",
            "d": "d",
            "w": "wk",
            "M": "mo",
        }
        yf_unit = yf_unit_map.get(unit, unit)
        return f"{value}{yf_unit}"

    elif source == "ccxt":
        # CCXT uses format: number + unit (e.g., '1h', '4h', '1d')
        ccxt_unit_map = {
            "m": "m",
            "h": "h",
            "d": "d",
            "w": "w",
            "M": "M",
        }
        ccxt_unit = ccxt_unit_map.get(unit, unit)
        return f"{value}{ccxt_unit}"

    raise ValueError(f"Unknown source: {source}")


def validate_timeframe(
    timeframe: str,
    source: Literal["yfinance", "ccxt"] = "yfinance",
    auto_fallback: bool = True,
) -> str:
    """
    Validate and normalize a timeframe for the specified data source.

    This function:
    1. Normalizes the input timeframe to a standard format
    2. Validates it against the source's supported timeframes
    3. Handles special cases (e.g., 'h4' not available in yfinance)
    4. Optionally auto-fallbacks to nearest supported timeframe

    Args:
        timeframe: The timeframe to validate (e.g., 'h4', 'd1', '1h', '4h').
        source: The data source ('yfinance' or 'ccxt'). Defaults to 'yfinance'.
        auto_fallback: If True, automatically fallback to nearest supported
            timeframe when the requested one is unavailable. Defaults to True.

    Returns:
        Normalized timeframe in source-specific format.

    Raises:
        ValueError: If the timeframe is not supported and auto_fallback is False,
            or if no suitable fallback exists.

    Examples:
        >>> validate_timeframe('h4', 'ccxt')
        '4h'
        >>> validate_timeframe('d1', 'yfinance')
        '1d'
        >>> validate_timeframe('h4', 'yfinance')  # Warns, falls back to '1h'
        '1h'
    """
    timeframe = timeframe.strip().lower()

    # Normalize to internal format first
    try:
        internal_tf = normalize_timeframe_to_internal(timeframe)
    except ValueError as e:
        raise ValueError(f"Invalid timeframe format '{timeframe}': {e}")

    # Convert to source-specific format
    source_tf = normalize_timeframe_to_source(internal_tf, source)

    # Get valid timeframes for the source
    valid_tfs = VALID_TIMEFRAMES_YFINANCE if source == "yfinance" else VALID_TIMEFRAMES_CCXT

    # Check if the timeframe is supported
    if source_tf not in valid_tfs:
        # Special handling for '4h' with yfinance
        if source == "yfinance" and internal_tf == "h4":
            logger.warning(
                f"Timeframe '4h' (h4) is not available in yfinance. "
                f"yfinance only supports: 1m, 2m, 5m, 15m, 30m, 1h, 1d, 5d, 1wk, 1mo, 3mo. "
                f"Falling back to '1h' for intraday analysis, or consider using '1d'."
            )
            if auto_fallback:
                logger.info("Auto-fallback: Using '1h' instead of '4h'")
                return "1h"
            else:
                raise ValueError(
                    "Timeframe '4h' is not supported by yfinance. "
                    "Use '1h' for hourly analysis or '1d' for daily. "
                    "For 4-hour charts, use CCXT as the data source."
                )

        # Handle other unsupported timeframes
        if auto_fallback:
            fallback_tf = _get_nearest_timeframe(internal_tf, source)
            if fallback_tf:
                logger.warning(
                    f"Timeframe '{source_tf}' not available for {source}. "
                    f"Falling back to '{fallback_tf}'."
                )
                return fallback_tf

        raise ValueError(
            f"Timeframe '{source_tf}' is not supported by {source}. "
            f"Valid timeframes: {sorted(valid_tfs)}"
        )

    return source_tf


def _get_nearest_timeframe(timeframe: str, source: Literal["yfinance", "ccxt"]) -> str | None:
    """
    Find the nearest supported timeframe for the given input.

    Args:
        timeframe: Internal format timeframe.
        source: The data source.

    Returns:
        Nearest supported timeframe, or None if no suitable fallback exists.
    """
    valid_tfs = VALID_TIMEFRAMES_YFINANCE if source == "yfinance" else VALID_TIMEFRAMES_CCXT

    # Parse the input timeframe
    try:
        internal_tf = normalize_timeframe_to_internal(timeframe)
        unit = internal_tf[0]
        value = int(internal_tf[1:])
    except (ValueError, IndexError):
        return None

    # Convert valid timeframes to minutes for comparison
    def tf_to_minutes(tf: str) -> int:
        tf = tf.lower()
        unit_map = {"m": 1, "h": 60, "d": 1440, "w": 10080, "M": 43200}
        try:
            if tf[-1].isalpha():
                u = tf[-1]
                v = int(tf[:-1])
                return v * unit_map.get(u, 1)
        except (ValueError, IndexError):
            pass
        return 0

    input_minutes = value * {"m": 1, "h": 60, "d": 1440, "w": 10080, "M": 43200}.get(unit, 1)

    # Find nearest timeframe
    min_diff = float("inf")
    nearest_tf = None

    for valid_tf in valid_tfs:
        valid_minutes = tf_to_minutes(valid_tf)
        if valid_minutes == 0:
            continue

        diff = abs(valid_minutes - input_minutes)
        if diff < min_diff:
            min_diff = diff
            nearest_tf = valid_tf

    return nearest_tf


def get_timeframe_minutes(timeframe: str, source: Literal["yfinance", "ccxt"] = "yfinance") -> int:
    """
    Get the number of minutes represented by a timeframe.

    Args:
        timeframe: Timeframe string (any format).
        source: Data source for validation.

    Returns:
        Number of minutes.
    """
    validated_tf = validate_timeframe(timeframe, source)

    # Parse the validated timeframe
    validated_tf = validated_tf.lower()
    unit_map = {"m": 1, "h": 60, "d": 1440, "w": 10080, "M": 43200}

    try:
        if validated_tf[-1].isalpha():
            unit = validated_tf[-1]
            value = int(validated_tf[:-1])
            return value * unit_map.get(unit, 1)
    except (ValueError, IndexError):
        pass

    return 0


# =============================================================================
# APPLICATION SETTINGS
# =============================================================================


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be configured via the .env file or environment variables.
    """

    # ======================================================================
    # APPLICATION
    # ======================================================================
    app_env: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # ======================================================================
    # DATABASE
    # ======================================================================
    database_url: str = "sqlite:///./data/positions.db"

    # ======================================================================
    # TELEGRAM
    # ======================================================================
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # ======================================================================
    # SECURITY
    # ======================================================================
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: List[str] = ["http://localhost:8501", "http://localhost:8000"]

    # ======================================================================
    # SCHEDULER
    # ======================================================================
    monitor_interval: int = 14400  # 4 hours in seconds
    timezone: str = "UTC"

    # ======================================================================
    # DATA SOURCE
    # ======================================================================
    default_data_source: Literal["yfinance", "ccxt"] = "ccxt"

    # ======================================================================
    # RATE LIMITING
    # ======================================================================
    rate_limit: int = 60  # requests per minute

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() == "production"

    @property
    def telegram_enabled(self) -> bool:
        """Check if Telegram notifications are configured."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)


# =============================================================================
# GLOBAL SETTINGS INSTANCE
# =============================================================================

settings = Settings()
