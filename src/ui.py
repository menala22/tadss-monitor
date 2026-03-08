"""
TA-DSS Position Monitor Dashboard

Streamlit-based user interface for monitoring trading positions with real-time
technical analysis signals and Telegram alert management.

Usage:
    cd trading-order-monitoring-system
    streamlit run src/ui.py --server.port 8503
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Add project root to Python path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.database import get_db_context
from src.models.position_model import Position, PositionStatus, PositionType
from src.services.technical_analyzer import TechnicalAnalyzer
from src.data_fetcher import DataFetcher
from src.ui_mtf_scanner import render_mtf_scanner_page
from src.ui_market_data import display_market_data_page

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# API Base URL - supports environment variable for production deployment
# Reads from .env file: API_BASE_URL or VM_EXTERNAL_IP
# Default: Production mode (Google Cloud VM)
# Fallback: http://localhost:8000/api/v1 (local development)

# Try to load from .env file first
def _load_env_var_from_file(target_key: str) -> str | None:
    """Load a single env var from the .env file if it exists."""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == target_key:
                            v = value.strip()
                            return v if v and not v.startswith('your_') else None
        except Exception:
            pass
    return None


def _load_api_url_from_env() -> str | None:
    """Load API URL from .env file (checks API_BASE_URL then VM_EXTERNAL_IP)."""
    api_url = _load_env_var_from_file('API_BASE_URL')
    if api_url:
        return api_url
    vm_ip = _load_env_var_from_file('VM_EXTERNAL_IP')
    if vm_ip:
        return f"http://{vm_ip}:8000/api/v1"
    return None


# Priority: 1) Environment variable, 2) .env file, 3) Default localhost
API_BASE_URL = os.getenv("API_BASE_URL") or _load_api_url_from_env() or "http://localhost:8000/api/v1"
API_SECRET_KEY = os.getenv("API_SECRET_KEY") or _load_env_var_from_file('API_SECRET_KEY')


def get_api_headers() -> dict:
    """Return auth headers for API requests. Empty dict if no key configured."""
    if API_SECRET_KEY:
        return {"X-API-Key": API_SECRET_KEY}
    return {}
DASHBOARD_VERSION = "v1.0.0"
AUTO_REFRESH_INTERVAL_SECONDS = 3600  # 1 hour


def get_current_api_url() -> str:
    """
    Get the current API URL, considering session state overrides.

    Priority:
    1. Session state override (from Settings page toggle)
    2. Environment variable API_BASE_URL
    3. Default localhost

    Returns:
        Current API base URL.
    """
    # Check for session state override (from Settings page)
    if hasattr(st, "session_state") and "api_base_url_override" in st.session_state:
        return st.session_state.api_base_url_override
    return API_BASE_URL

# =============================================================================
# Caching Functions
# =============================================================================

@st.cache_data(ttl=30)
def fetch_open_positions_cached() -> Optional[List[Dict[str, Any]]]:
    """
    Fetch open positions from API with caching.

    Cache TTL: 30 seconds to balance freshness and performance.

    Returns:
        List of position dictionaries, or None if API is unavailable.
    """
    try:
        response = requests.get(
            f"{get_current_api_url()}/positions/open",
            headers=get_api_headers(),
            timeout=60,  # Increased from 10 to 60 seconds (API can be slow)
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def fetch_open_positions_from_api() -> Optional[List[Dict[str, Any]]]:
    """
    Fetch open positions from API WITHOUT caching.

    Use this for main dashboard to ensure fresh data.
    The cached version is only for sidebar stats.

    Returns:
        List of position dictionaries, or None if API is unavailable.
    """
    try:
        response = requests.get(
            f"{get_current_api_url()}/positions/open",
            headers=get_api_headers(),
            timeout=60,  # Increased from 10 to 60 seconds
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


@st.cache_data(ttl=60)
def get_system_info_cached() -> Dict[str, Any]:
    """
    Fetch system information from API with caching.

    Cache TTL: 60 seconds (system info doesn't change often).

    Returns:
        Dictionary with system information.
    """
    try:
        response = requests.get(
            f"{get_current_api_url()}/positions/scheduler/status",
            headers=get_api_headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {
            "running": False,
            "next_run_time": None,
            "job_count": 0,
        }


def test_api_connection(api_url: str = None) -> tuple[bool, str]:
    """
    Test connection to the API server.

    Args:
        api_url: Optional API URL to test (uses current if not provided).

    Returns:
        Tuple of (success: bool, message: str)
    """
    test_url = api_url if api_url else get_current_api_url()
    # Health endpoint is at the root (e.g. http://host:8000/health),
    # not under /api/v1 — strip the API path prefix.
    health_base = test_url.split("/api/")[0] if "/api/" in test_url else test_url
    try:
        response = requests.get(f"{health_base}/health", timeout=5)
        response.raise_for_status()
        return True, f"✅ Connected to {test_url}"
    except requests.exceptions.ConnectionError:
        return False, f"❌ Connection failed: {test_url}"
    except requests.exceptions.Timeout:
        return False, f"❌ Timeout: {test_url}"
    except requests.exceptions.HTTPError as e:
        return False, f"❌ HTTP error {e.response.status_code}: {test_url}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def fetch_position_with_signals_simple(position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch position data with signals - SIMPLIFIED and FAST.

    This version uses current_price from API cache (no additional API calls).
    Shows basic position info on the main table.

    Args:
        position: Position dictionary from API (includes current_price from cache).

    Returns:
        Dictionary with basic position data including current price.
    """
    try:
        entry_price = position.get("entry_price", 0)
        position_type = position.get("position_type", "LONG")
        pair = position.get("pair", "")
        timeframe = position.get("timeframe", "h4")
        
        # Use current_price from API response (already from cache!)
        # This avoids making additional API calls per position
        current_price = position.get("current_price")
        
        if current_price is None:
            # Fallback to entry price if no cache available
            current_price = entry_price
        
        # Calculate PnL
        if position_type == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Use stored signal status from DB (set by scheduler, no live API call needed)
        last_signal = position.get("last_signal_status")  # "BULLISH", "BEARISH", or None
        signal_summary = last_signal if last_signal in ("BULLISH", "BEARISH") else "NEUTRAL"

        # Derive health from signal alignment with position direction
        if signal_summary == "BULLISH":
            health_status = "HEALTHY" if position_type == "LONG" else "CRITICAL"
        elif signal_summary == "BEARISH":
            health_status = "CRITICAL" if position_type == "LONG" else "HEALTHY"
        else:
            health_status = "NEUTRAL"

        bullish_count = bearish_count = neutral_count = 0
        signal_states = {}

        return {
            "position": position,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
            "overall_status": signal_summary,
            "health_status": health_status,
            "signals": signal_states,
            "indicator_values": {},
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
        }

    except Exception as e:
        logger.error(f"Error processing position {position.get('pair')}: {e}")
        return None


def fetch_position_with_signals(position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch position data with full signals (for detail view).
    
    This fetches live market data and calculates signals.
    Only called when viewing a single position detail.
    
    Args:
        position: Position dictionary from API.
    
    Returns:
        Dictionary with position data, signals, and PnL.
    """
    try:
        # Determine data source
        pair = position.get("pair", "")
        pair_clean = pair.replace("-", "").replace("/", "").replace("_", "").upper()
        
        # Crypto pairs: contain crypto symbols or end with USD/USDT
        crypto_keywords = ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "LTC", "BCH", "LINK", "AVAX", "MATIC", "UNI", "ATOM"]
        is_likely_crypto = any(keyword in pair_clean for keyword in crypto_keywords) or pair_clean.endswith("USD") or pair_clean.endswith("USDT")
        
        # Default to CCXT for crypto, yfinance for stocks
        source = "ccxt" if is_likely_crypto else "yfinance"

        # Fetch market data (limit to 50 candles for speed)
        fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=0.5)
        df = fetcher.get_ohlcv(
            symbol=pair,
            timeframe=position.get("timeframe", "h4"),
            limit=50,  # Reduced from 100 for speed
        )
        fetcher.close()

        if df.empty:
            return None

        # Normalize columns
        df = df.rename(columns={col: col.lower() for col in df.columns})
        current_price = float(df["close"].iloc[-1])

        # Calculate signals
        analyzer = TechnicalAnalyzer()
        signal = analyzer.analyze_position(
            df=df,
            pair=pair,
            position_type=PositionType[position.get("position_type", "LONG")],
            timeframe=position.get("timeframe", "h4"),
        )

        # Calculate PnL
        entry_price = position.get("entry_price", current_price)
        position_type = position.get("position_type", "LONG")

        if position_type == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Use signal's built-in counts (includes OTT - 6 indicators total)
        bullish_count = signal.bullish_count
        bearish_count = signal.bearish_count
        neutral_count = signal.neutral_count
        signal_states = signal.signal_states

        # Determine overall status based on signal (uses 6 indicators including OTT)
        overall_status = signal.overall_signal.value

        # Calculate alignment percentage using 6 indicators (includes OTT)
        is_long = position_type == "LONG"
        total_signals = bullish_count + bearish_count + neutral_count
        total_decisive = bullish_count + bearish_count

        if total_decisive == 0:
            # No decisive signals = NEUTRAL
            health_status = "NEUTRAL"
        else:
            # Calculate alignment with position direction
            if is_long:
                aligned_count = bullish_count  # LONG wants bullish signals
            else:
                aligned_count = bearish_count  # SHORT wants bearish signals

            alignment_pct = (aligned_count / total_decisive) * 100

            # Use signal engine health logic (more stable)
            rsi_state = signal_states.get("RSI")
            is_overbought = rsi_state == "OVERBOUGHT" or (hasattr(rsi_state, 'value') and rsi_state.value == "OVERBOUGHT")
            is_oversold = rsi_state == "OVERSOLD" or (hasattr(rsi_state, 'value') and rsi_state.value == "OVERSOLD")

            if alignment_pct >= 60:
                # Mostly aligned = HEALTHY (check for extreme RSI)
                if (is_long and is_overbought) or (not is_long and is_oversold):
                    health_status = "WARNING"
                else:
                    health_status = "HEALTHY"
            elif alignment_pct <= 20:
                # Mostly against position = CRITICAL (check for extreme RSI)
                if (is_long and is_oversold) or (not is_long and is_overbought):
                    health_status = "WARNING"
                else:
                    health_status = "CRITICAL"
            else:
                # Mixed signals (21-59% alignment) = WARNING
                health_status = "WARNING"

        return {
            "position": position,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
            "overall_status": overall_status,
            "health_status": health_status,
            "signals": signal_states,
            "indicator_values": signal.indicators,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
        }

    except Exception as e:
        logger.error(f"Error fetching signals for {position.get('pair')}: {e}")
        return None

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="TA-DSS Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-repo/ta-dss",
        "Report a bug": "https://github.com/your-repo/ta-dss/issues",
        "About": "# TA-DSS Position Monitor\n\nAutomated trading position monitoring with technical analysis.",
    },
)

# =============================================================================
# Custom CSS Styling
# =============================================================================

st.markdown(
    """
    <style>
    /* Hide Streamlit menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Improve metric card styling */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }

    /* Metric value font size */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }

    /* Metric label font size */
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #666;
    }

    /* Table container styling */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }

    /* Table selected row effect */
    div[data-testid="stDataFrame"] tr[aria-selected="true"] {
        background-color: #e3f2fd !important;
    }

    /* Button styling */
    div.stButton > button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }

    /* Status badge colors */
    .status-healthy {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }

    .status-neutral {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }

    .status-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }

    .status-critical {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    
    /* Footer styling */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        color: #666;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #e0e0e0;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        div[data-testid="stMetricValue"] {
            font-size: 18px;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 12px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Helper Functions
# =============================================================================


def get_db_session() -> Any:
    """Get database session context."""
    return get_db_context()


def refresh_position_signals(position_id: int) -> Optional[Dict[str, Any]]:
    """
    Manually refresh signals for a specific position.

    This calls the monitoring system to fetch fresh data and update signals.

    Args:
        position_id: ID of position to refresh.

    Returns:
        Updated position data with fresh signals, or None if failed.
    """
    try:
        # For now, we fetch fresh data directly
        # In production, this would call a refresh endpoint
        response = requests.get(
            f"{get_current_api_url()}/positions/{position_id}",
            headers=get_api_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to refresh position {position_id}: {e}")
        return None


def fetch_position_with_signals(position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch current market data and calculate signals for a position.

    Args:
        position: Position dictionary from API.

    Returns:
        Dictionary with position data, signals, and PnL.
    """
    try:
        # Determine data source
        pair = position.get("pair", "")
        pair_clean = pair.replace("-", "").replace("/", "").replace("_", "")
        source = "ccxt" if not (pair_clean.isalpha() and len(pair_clean) <= 5) else "yfinance"

        # Fetch market data
        fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=1.0)
        df = fetcher.get_ohlcv(
            symbol=pair,
            timeframe=position.get("timeframe", "h4"),
            limit=100,
        )
        fetcher.close()

        if df.empty:
            return None

        # Normalize column names
        df = df.rename(columns={col: col.lower() for col in df.columns})
        current_price = float(df["close"].iloc[-1])

        # Calculate signals
        analyzer = TechnicalAnalyzer()
        signal = analyzer.analyze_position(
            df=df,
            pair=pair,
            position_type=PositionType[position.get("position_type", "LONG")],
            timeframe=position.get("timeframe", "h4"),
        )

        # Calculate PnL
        entry_price = position.get("entry_price", current_price)
        position_type = position.get("position_type", "LONG")

        if position_type == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Use signal's built-in counts (includes OTT - 6 indicators total)
        bullish_count = signal.bullish_count
        bearish_count = signal.bearish_count
        neutral_count = signal.neutral_count
        signal_states = signal.signal_states

        # Determine overall status based on signal (uses 6 indicators including OTT)
        overall_status = signal.overall_signal.value

        # Calculate alignment percentage using 6 indicators (includes OTT)
        is_long = position_type == "LONG"
        total_signals = bullish_count + bearish_count + neutral_count
        total_decisive = bullish_count + bearish_count

        if total_decisive == 0:
            # No decisive signals = NEUTRAL
            health_status = "NEUTRAL"
        else:
            # Calculate alignment with position direction
            if is_long:
                aligned_count = bullish_count  # LONG wants bullish signals
            else:
                aligned_count = bearish_count  # SHORT wants bearish signals

            alignment_pct = (aligned_count / total_decisive) * 100

            # Use signal engine health logic (more stable)
            rsi_state = signal_states.get("RSI")
            is_overbought = rsi_state == "OVERBOUGHT" or (hasattr(rsi_state, 'value') and rsi_state.value == "OVERBOUGHT")
            is_oversold = rsi_state == "OVERSOLD" or (hasattr(rsi_state, 'value') and rsi_state.value == "OVERSOLD")

            if alignment_pct >= 60:
                # Mostly aligned = HEALTHY (check for extreme RSI)
                if (is_long and is_overbought) or (not is_long and is_oversold):
                    health_status = "WARNING"
                else:
                    health_status = "HEALTHY"
            elif alignment_pct <= 20:
                # Mostly against position = CRITICAL (check for extreme RSI)
                if (is_long and is_oversold) or (not is_long and is_overbought):
                    health_status = "WARNING"
                else:
                    health_status = "CRITICAL"
            else:
                # Mixed signals (21-59% alignment) = WARNING
                health_status = "WARNING"

        return {
            "position": position,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
            "overall_status": overall_status,
            "health_status": health_status,
            "signals": signal_states,
            "indicator_values": signal.indicators,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
        }

    except Exception as e:
        logger.error(f"Error fetching signals for {position.get('pair')}: {e}")
        return None


def render_sidebar() -> str:
    """
    Render sidebar navigation.

    Returns:
        Current page selection from session state.
    """
    with st.sidebar:
        # Use emoji instead of external image (more reliable)
        st.markdown("# 📊 TA-DSS")
        st.caption("Trading Position Monitor")
        st.title("🧭 Navigation")

        # Navigation options
        page = st.radio(
            "Select Page",
            ["📋 Open Positions", "➕ Add New Position", "🔍 MTF Scanner", "📈 Market Data", "⚙️ Settings"],
            index=0,
            label_visibility="collapsed",
        )

        st.divider()

        # Manual Refresh Button
        st.subheader("🔄 Refresh")
        
        if st.button("🔄 Refresh All Signals", use_container_width=True, key="sidebar_refresh"):
            st.session_state.manual_refresh_requested = True
            st.rerun()
        
        # Auto-refresh Toggle
        st.subheader("⚡ Auto-Refresh")

        auto_refresh = st.checkbox(
            f"🔁 Auto-refresh every {AUTO_REFRESH_INTERVAL_SECONDS // 60} min",
            value=st.session_state.get("auto_refresh_enabled", False),
            key="auto_refresh_checkbox",
            help=f"Automatically refresh position data every {AUTO_REFRESH_INTERVAL_SECONDS} seconds",
        )
        
        if auto_refresh != st.session_state.get("auto_refresh_enabled", False):
            st.session_state.auto_refresh_enabled = auto_refresh
            st.rerun()
        
        # Show countdown if auto-refresh is enabled
        if st.session_state.get("auto_refresh_enabled", False):
            if "last_refresh_time" not in st.session_state:
                st.session_state.last_refresh_time = time.time()

            elapsed = time.time() - st.session_state.last_refresh_time
            remaining = max(0, AUTO_REFRESH_INTERVAL_SECONDS - elapsed)

            # Only show progress bar if less than 5 minutes remaining (avoid very long bars)
            if remaining < 300:
                st.progress(remaining / 300)
                st.caption(f"Next refresh in: {int(remaining // 60)}m {int(remaining % 60)}s")
            else:
                minutes_left = int(remaining // 60)
                st.caption(f"Next refresh in: {minutes_left}m")
        
        st.divider()

        # Quick stats
        st.subheader("📊 Quick Stats")
        try:
            # Use cached function for sidebar stats (performance)
            api_positions = fetch_open_positions_cached()
            
            if api_positions is not None:
                long_count = sum(1 for p in api_positions if p.get("position_type") == "LONG")
                short_count = sum(1 for p in api_positions if p.get("position_type") == "SHORT")

                st.metric("Total Open", len(api_positions))
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Long", long_count)
                with col2:
                    st.metric("Short", short_count)
            else:
                st.warning("Unable to load stats")
        except Exception:
            st.warning("Unable to load stats")

        st.divider()

        # System status
        st.subheader("🖥️ System")
        
        try:
            system_info = get_system_info_cached()
            
            if system_info.get("running", False):
                st.success("✅ Scheduler Running")
                
                next_run = system_info.get("next_run_time")
                if next_run:
                    try:
                        next_run_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                        st.caption(f"Next check: {next_run_dt.strftime('%H:%M:%S')}")
                    except Exception:
                        pass
            else:
                st.warning("⚠️ Scheduler Stopped")
        except Exception:
            st.caption("Status unavailable")
        
        st.caption(f"Version: {DASHBOARD_VERSION}")

        st.divider()

        # Last update time
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.caption(f"Last updated: {now}")

        # Store page in session state
        st.session_state.current_page = page
        return page


def render_summary_cards(positions_data: List[Dict[str, Any]]) -> None:
    """
    Render summary metric cards at top of page.

    Args:
        positions_data: List of position data dictionaries with signals.
    """
    total = len(positions_data)
    long_count = sum(
        1 for pd in positions_data
        if pd["position"].get("position_type") == "LONG"
    )
    short_count = sum(
        1 for pd in positions_data
        if pd["position"].get("position_type") == "SHORT"
    )
    warning_count = sum(1 for pd in positions_data if pd.get("health_status") in ["WARNING", "CRITICAL"])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📋 Total Open",
            value=total,
            delta=None,
        )

    with col2:
        st.metric(
            label="🟢 Long Positions",
            value=long_count,
            delta=None,
        )

    with col3:
        st.metric(
            label="🔴 Short Positions",
            value=short_count,
            delta=None,
        )

    with col4:
        # Color-code warning metric
        if warning_count > 0:
            st.metric(
                label="⚠️ Positions with Warning",
                value=warning_count,
                delta=f"{warning_count} need attention",
                delta_color="inverse",
            )
        else:
            st.metric(
                label="✅ Positions with Warning",
                value=0,
                delta="All clear",
                delta_color="normal",
            )


def render_positions_table(positions_data: List[Dict[str, Any]]) -> None:
    """
    Render positions data table with clickable rows.

    Args:
        positions_data: List of position data dictionaries with signals.
    """
    if not positions_data:
        st.info("📭 No open positions found. Click '➕ Add New Position' to start tracking.")
        return

    # Sort: 1) pair name A→Z, 2) timeframe shortest→longest
    _tf_minutes = {
        'm1': 1, 'm5': 5, 'm15': 15, 'm30': 30,
        'h1': 60, 'h2': 120, 'h4': 240, 'h6': 360, 'h8': 480, 'h12': 720,
        'd1': 1440, 'd3': 4320, 'd5': 7200, 'w1': 10080, 'M1': 43200,
    }
    positions_data = sorted(
        positions_data,
        key=lambda p: (
            p["position"].get("pair", ""),
            _tf_minutes.get(p["position"].get("timeframe", "h1"), 999999),
        ),
    )

    # Prepare data for display
    table_data = []
    for idx, pd in enumerate(positions_data):
        position = pd["position"]
        pnl_pct = pd["pnl_pct"]
        current_price = pd["current_price"]
        health_status = pd.get("health_status", "HEALTHY")
        overall_status = pd.get("overall_status", "NEUTRAL")
        bullish_count = pd.get("bullish_count", 0)
        bearish_count = pd.get("bearish_count", 0)

        # Direction emoji
        direction = position.get("position_type", "LONG")
        direction_emoji = "🟢" if direction == "LONG" else "🔴"

        # PnL color and sign
        pnl_color = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_sign = "+" if pnl_pct >= 0 else ""

        # Health status emoji
        if health_status == "CRITICAL":
            health_emoji = "🔴"
        elif health_status == "WARNING":
            health_emoji = "🟠"
        elif health_status == "NEUTRAL":
            health_emoji = "🟡"
        else:
            health_emoji = "🟢"

        # Signal display
        if overall_status == "BULLISH":
            signal_display = "🟢 Bullish"
        elif overall_status == "BEARISH":
            signal_display = "🔴 Bearish"
        else:
            signal_display = "⚪ Neutral"

        # Timeframe display
        timeframe = position.get("timeframe", "h4").upper()
        if timeframe.endswith("H"):
            timeframe_display = f"{timeframe[:-1]}h"
        elif timeframe.endswith("D"):
            timeframe_display = f"{timeframe[:-1]}d"
        elif timeframe.endswith("W"):
            timeframe_display = f"{timeframe[:-1]}w"
        else:
            timeframe_display = timeframe

        table_data.append({
            "Pair": position.get("pair", "N/A"),
            "Direction": f"{direction_emoji} {direction}",
            "Entry": f"${position.get('entry_price', 0):,.2f}",
            "Current": f"${current_price:,.2f}",
            "PnL": f"{pnl_color} {pnl_sign}{pnl_pct:.2f}%",
            "Timeframe": timeframe_display,
            "Health": f"{health_emoji} {health_status}",
            "Signal": signal_display,
            "_position_id": position.get("id"),
            "_position_data": pd,
        })

    # Display refresh button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh Signals", use_container_width=True, key="refresh_positions"):
            st.session_state.refresh_triggered = True
            st.rerun()

    # Display table with column configuration
    st.subheader("📊 Position Details")
    st.caption("💡 Click a row to select and view details")

    # Configure column styling
    column_config = {
        "Pair": st.column_config.TextColumn("Pair", width="small"),
        "Direction": st.column_config.TextColumn("Direction", width="small"),
        "Entry": st.column_config.TextColumn("Entry", width="medium"),
        "Current": st.column_config.TextColumn("Current", width="medium"),
        "PnL": st.column_config.TextColumn("P&L", width="medium"),
        "Timeframe": st.column_config.TextColumn("Timeframe", width="small"),
        "Health": st.column_config.TextColumn("Health", width="medium"),
        "Signal": st.column_config.TextColumn("Signal", width="medium"),
        "_position_id": None,
        "_position_data": None,
    }

    # Display table with selection enabled
    df = st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        key="positions_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    # Handle row selection
    if df.selection.rows:
        selected_row_index = df.selection.rows[0]
        selected_position = table_data[selected_row_index]
        st.session_state.selected_position_id = selected_position['_position_id']
        st.session_state.selected_position_data = selected_position['_position_data']
        st.rerun()


def render_position_detail(position_data: Dict[str, Any]) -> None:
    """
    Render detailed view for a selected position.
    
    This fetches FRESH market data for the selected position only.
    
    Args:
        position_data: Position data dictionary with signals.
    """
    # Fetch fresh data for this position only (with full signals)
    with st.spinner("🔄 Fetching live market data..."):
        full_position_data = fetch_position_with_signals(position_data["position"])
    
    if not full_position_data:
        st.error("❌ Failed to fetch market data for this position")
        if st.button("← Back to Positions"):
            st.session_state.selected_position_id = None
            st.session_state.selected_position_data = None
            st.rerun()
        return
    
    # Use the fresh data for display
    position = full_position_data["position"]
    pair = position.get("pair", "N/A")
    direction = position.get("position_type", "LONG")
    entry_price = position.get("entry_price", 0)
    current_price = full_position_data["current_price"]
    pnl_pct = full_position_data["pnl_pct"]
    pnl_value = current_price - entry_price if direction == "LONG" else entry_price - current_price
    health_status = full_position_data.get("health_status", "HEALTHY")
    signals = full_position_data.get("signals", {})
    indicator_values = full_position_data.get("indicator_values", {})
    bullish_count = full_position_data.get("bullish_count", 0)
    bearish_count = full_position_data.get("bearish_count", 0)
    neutral_count = full_position_data.get("neutral_count", 0)

    # Calculate time in trade
    entry_time_str = position.get("entry_time", "")
    try:
        entry_time = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
        time_in_trade = datetime.now(timezone.utc) - entry_time
        days = time_in_trade.days
        hours = time_in_trade.seconds // 3600
        time_display = f"{days}d {hours}h" if days > 0 else f"{hours}h"
    except Exception:
        time_display = "N/A"

    # Get timeframe for display
    timeframe = position.get("timeframe", "h4").upper()
    if timeframe.endswith("H"):
        timeframe_display = f"{timeframe[:-1]}h"
    elif timeframe.endswith("D"):
        timeframe_display = f"{timeframe[:-1]}d"
    elif timeframe.endswith("W"):
        timeframe_display = f"{timeframe[:-1]}w"
    else:
        timeframe_display = timeframe

    # Header with timeframe
    st.title(f"📍 {pair} - {direction} {timeframe_display}")

    # Direction emoji
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    st.caption(f"{direction_emoji} {direction} Position • Timeframe: {timeframe_display}")

    st.divider()

    # Large Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Entry Price",
            value=f"${entry_price:,.2f}",
        )

    with col2:
        st.metric(
            label="Current Price",
            value=f"${current_price:,.2f}",
        )

    with col3:
        pnl_sign = "+" if pnl_value >= 0 else ""
        pnl_color = "normal" if pnl_value >= 0 else "inverse"
        st.metric(
            label="Unrealized P&L",
            value=f"{pnl_sign}${pnl_value:,.2f}",
            delta=f"{pnl_sign}{pnl_pct:.2f}%",
            delta_color=pnl_color,
        )

    with col4:
        st.metric(
            label="Time in Trade",
            value=time_display,
        )

    st.divider()

    # Signal Breakdown
    st.subheader("📈 Technical Signals Breakdown")

    # Check for conflicting signals
    is_long = direction == "LONG"
    conflicting_signals = []

    if is_long:
        if signals.get("MA10") in ["BEARISH", "OVERSOLD"]:
            conflicting_signals.append("MA10")
        if signals.get("MA20") in ["BEARISH", "OVERSOLD"]:
            conflicting_signals.append("MA20")
        if signals.get("MA50") in ["BEARISH", "OVERSOLD"]:
            conflicting_signals.append("MA50")
        if signals.get("MACD") in ["BEARISH", "OVERSOLD"]:
            conflicting_signals.append("MACD")
        if signals.get("OTT") == "BEARISH":
            conflicting_signals.append("OTT")
    else:
        if signals.get("MA10") in ["BULLISH", "OVERBOUGHT"]:
            conflicting_signals.append("MA10")
        if signals.get("MA20") in ["BULLISH", "OVERBOUGHT"]:
            conflicting_signals.append("MA20")
        if signals.get("MA50") in ["BULLISH", "OVERBOUGHT"]:
            conflicting_signals.append("MA50")
        if signals.get("MACD") in ["BULLISH", "OVERBOUGHT"]:
            conflicting_signals.append("MACD")
        if signals.get("OTT") == "BULLISH":
            conflicting_signals.append("OTT")

    if conflicting_signals:
        st.error(f"⚠️ **Conflicting Signals:** {', '.join(conflicting_signals)} are against your {direction} position")

    # Create detailed signal breakdown with values
    st.markdown("### Signal Details")
    
    # Use indicator_values from the analyzer (these have the actual numeric values)
    signal_data = []

    # Moving Averages - get values from indicator_values
    # Note: Analyzer returns EMA_10, EMA_20, EMA_50 (not MA10, MA20, MA50)
    ema_map = {"MA10": "EMA_10", "MA20": "EMA_20", "MA50": "EMA_50"}
    
    for ma, ema_key in ema_map.items():
        status = signals.get(ma, "N/A")
        # Get value from indicator_values dict using EMA key
        value = indicator_values.get(ema_key)

        if status in ["BULLISH", "OVERBOUGHT"]:
            emoji = "✅"
        elif status in ["BEARISH", "OVERSOLD"]:
            emoji = "❌"
        else:
            emoji = "➖"

        is_conflicting = ma in conflicting_signals

        # Format value
        if value and isinstance(value, (int, float)):
            value_display = f"${value:,.2f}"
        else:
            value_display = "N/A"

        signal_data.append({
            "Indicator": ma,
            "Status": f"{emoji} {status}",
            "Value": value_display,
            "Conflicting": is_conflicting,
        })
    
    # MACD - get values from indicator_values
    macd_status = signals.get("MACD", "N/A")
    macd_value = indicator_values.get("MACD")
    macd_histogram = indicator_values.get("MACD_histogram")
    
    if macd_status in ["BULLISH", "OVERBOUGHT"]:
        macd_emoji = "✅"
    elif macd_status in ["BEARISH", "OVERSOLD"]:
        macd_emoji = "❌"
    else:
        macd_emoji = "➖"
    
    # Format MACD values
    if macd_value and isinstance(macd_value, (int, float)):
        macd_line_display = f"{macd_value:+.2f}"
    else:
        macd_line_display = "N/A"
    
    if macd_histogram and isinstance(macd_histogram, (int, float)):
        macd_hist_display = f"{macd_histogram:+.2f}"
    else:
        macd_hist_display = "N/A"
    
    is_macd_conflicting = "MACD" in conflicting_signals
    
    signal_data.append({
        "Indicator": "MACD",
        "Status": f"{macd_emoji} {macd_status}",
        "Value": f"Line: {macd_line_display}, Hist: {macd_hist_display}",
        "Conflicting": is_macd_conflicting,
    })
    
    # RSI - get value from indicator_values
    rsi_status = signals.get("RSI", "N/A")
    rsi_value = indicator_values.get("RSI")
    
    if rsi_status in ["BULLISH", "OVERBOUGHT"]:
        rsi_emoji = "✅"
    elif rsi_status in ["BEARISH", "OVERSOLD"]:
        rsi_emoji = "❌"
    else:
        rsi_emoji = "➖"
    
    # Format RSI value
    if rsi_value and isinstance(rsi_value, (int, float)):
        rsi_display = f"{rsi_value:.1f}"
        
        # Add RSI zone indicator
        if rsi_value >= 70:
            rsi_zone = "⚠️ Overbought"
        elif rsi_value <= 30:
            rsi_zone = "⚠️ Oversold"
        elif rsi_value > 50:
            rsi_zone = "🟢 Bullish Zone"
        else:
            rsi_zone = "🔴 Bearish Zone"
    else:
        rsi_display = "N/A"
        rsi_zone = ""
    
    is_rsi_conflicting = "RSI" in conflicting_signals
    
    signal_data.append({
        "Indicator": "RSI",
        "Status": f"{rsi_emoji} {rsi_status}",
        "Value": f"{rsi_display} ({rsi_zone})" if rsi_zone else rsi_display,
        "Conflicting": is_rsi_conflicting,
    })

    # OTT - get value from indicator_values
    ott_status = signals.get("OTT", "N/A")
    ott_value = indicator_values.get("OTT")
    ott_trend = indicator_values.get("OTT_Trend")
    ott_mt = indicator_values.get("OTT_MT")

    if ott_status == "BULLISH":
        ott_emoji = "✅"
    elif ott_status == "BEARISH":
        ott_emoji = "❌"
    else:
        ott_emoji = "➖"

    # Format OTT values
    if ott_value and isinstance(ott_value, (int, float)):
        ott_display = f"${ott_value:,.2f}"
    else:
        ott_display = "N/A"

    if ott_trend and isinstance(ott_trend, (int, float)):
        if ott_trend == 1:
            trend_display = "🟢 Uptrend (1)"
        elif ott_trend == -1:
            trend_display = "🔴 Downtrend (-1)"
        else:
            trend_display = "➖ Neutral"
    else:
        trend_display = "N/A"

    if ott_mt and isinstance(ott_mt, (int, float)):
        mt_display = f"${ott_mt:,.2f}"
    else:
        mt_display = "N/A"

    # Check if OTT is conflicting with position
    is_ott_conflicting = False
    if is_long and ott_status == "BEARISH":
        is_ott_conflicting = True
    elif not is_long and ott_status == "BULLISH":
        is_ott_conflicting = True

    signal_data.append({
        "Indicator": "OTT",
        "Status": f"{ott_emoji} {ott_status}",
        "Value": f"OTT: {ott_display}, MT: {mt_display}, Trend: {trend_display}",
        "Conflicting": is_ott_conflicting,
    })
    
    # Display as a styled table
    import pandas as pd
    signal_df = pd.DataFrame(signal_data)
    
    # Style the dataframe
    def highlight_conflicts(row):
        if row['Conflicting']:
            return ['background-color: #ffebee; color: #c62828; font-weight: bold'] * 4
        else:
            return [''] * 4
    
    styled_df = signal_df.style.apply(highlight_conflicts, axis=1)
    styled_df = styled_df.hide(axis='index')
    styled_df = styled_df.set_properties(**{'text-align': 'left'})
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
    )

    # Additional signal summary
    st.divider()
    st.subheader("📊 Signal Summary (6 Indicators)")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🟢 Bullish Signals", bullish_count)

    with col2:
        st.metric("🔴 Bearish Signals", bearish_count)

    with col3:
        total_signals = bullish_count + bearish_count + neutral_count
        if total_signals > 0:
            bullish_pct = (bullish_count / total_signals) * 100
            st.metric("📈 Bullish %", f"{bullish_pct:.0f}%")
        else:
            st.metric("📈 Bullish %", "N/A")

    # Show indicator count
    st.caption(f"Indicators: MA10, MA20, MA50, MACD, RSI, OTT ({total_signals} total)")
    
    # Health status with explanation
    st.divider()
    st.markdown("### 🏥 Health Status")

    if health_status == "CRITICAL":
        st.error(f"""
        **🔴 CRITICAL**

        Majority of signals are against your {direction} position.

        **Recommendation:** Consider closing or reducing position.
        """)
    elif health_status == "WARNING":
        st.warning(f"""
        **🟠 WARNING**

        Some signals are diverging from your {direction} position.

        **Recommendation:** Monitor closely, consider tightening stop-loss.
        """)
    elif health_status == "NEUTRAL":
        st.info(f"""
        **🟡 NEUTRAL**

        No decisive signals detected.

        **Recommendation:** Wait for clearer market direction.
        """)
    else:
        st.success(f"""
        **🟢 HEALTHY**

        Signals are aligned with your {direction} position.

        **Recommendation:** Maintain position.
        """)

    st.divider()

    # Interactive Candlestick Chart
    st.subheader("📊 Price Chart with EMAs")

    # Fetch candle data with retry logic for different data sources
    df = None
    fetch_error = None

    # Determine data source based on pair format
    pair_clean = pair.replace("-", "").replace("/", "").replace("_", "").upper()
    
    # Crypto pairs: contain crypto symbols or end with USD/USDT
    crypto_keywords = ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "LTC", "BCH", "LINK", "AVAX", "MATIC", "UNI", "ATOM", "XAU", "XAG", "GOLD", "SILVER"]
    is_likely_crypto = any(keyword in pair_clean for keyword in crypto_keywords) or pair_clean.endswith("USD") or pair_clean.endswith("USDT")
    
    # Stock symbols: 1-5 alphabetic characters (e.g., AAPL, TSLA)
    is_likely_stock = not is_likely_crypto and pair_clean.isalpha() and len(pair_clean) <= 5
    
    # Default to CCXT for unknown pairs
    primary_source = "ccxt" if is_likely_crypto else "yfinance"

    # Try primary source first, then fallback
    sources_to_try = [primary_source, "ccxt" if primary_source == "yfinance" else "yfinance"]
    
    for source in sources_to_try:
        try:
            fetcher = DataFetcher(source=source, retry_attempts=2, retry_delay=1.0)
            df = fetcher.get_ohlcv(
                symbol=pair,
                timeframe=position.get("timeframe", "h4"),
                limit=100,
            )
            fetcher.close()
            
            if not df.empty:
                logger.info(f"Chart data fetched successfully from {source} for {pair}")
                break
            else:
                logger.warning(f"Empty data from {source} for {pair}")
        except Exception as e:
            fetch_error = str(e)
            logger.warning(f"Chart fetch failed from {source} for {pair}: {e}")
    
    if df is not None and not df.empty:
        try:
            # Normalize columns - handle both index and column variations
            # Data fetcher returns: Datetime as index, capitalized columns (Open, High, Low, Close, Volume)
            df = df.rename(columns={col: col.lower() for col in df.columns})
            
            # Reset index to get timestamp as a column
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
            
            # Handle both 'Datetime' and 'timestamp' column names
            if 'Datetime' in df.columns and 'timestamp' not in df.columns:
                df = df.rename(columns={'Datetime': 'timestamp'})
            
            # Verify required columns exist
            required_cols = ['timestamp', 'open', 'high', 'low', 'close']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {missing_cols}")
                st.info(f"Available columns: {list(df.columns)}")
                return

            # Create candlestick chart
            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df["timestamp"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price",
                increasing_line_color="green",
                decreasing_line_color="red",
            ))

            # Add EMAs - calculate if not present
            ema_configs = {"EMA_10": 10, "EMA_20": 20, "EMA_50": 50}
            ema_colors = {"EMA_10": "blue", "EMA_20": "orange", "EMA_50": "purple"}
            
            for ema_name, period in ema_configs.items():
                if ema_name not in df.columns:
                    # Calculate EMA if not present
                    import pandas_ta as ta
                    df[ema_name] = ta.ema(df["close"], length=period)
                
                # Add EMA trace if we have valid data
                if ema_name in df.columns and df[ema_name].notna().any():
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"],
                        y=df[ema_name],
                        name=ema_name.replace("_", ""),
                        line=dict(color=ema_colors[ema_name], width=1.5),
                    ))

            # Add entry price line
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=[entry_price] * len(df),
                name="Entry Price",
                line=dict(color="black", width=2, dash="dash"),
            ))

            # Update layout
            fig.update_layout(
                title=f"{pair} Price Chart",
                yaxis_title="Price (USD)",
                xaxis_title="Time",
                height=600,
                xaxis_rangeslider_visible=False,
                legend=dict(x=0, y=1, traceorder="normal"),
            )

            st.plotly_chart(fig, use_container_width=True)

            # Volume chart
            st.markdown("### Volume")
            fig_volume = go.Figure()
            fig_volume.add_trace(go.Bar(
                x=df["timestamp"],
                y=df["volume"],
                name="Volume",
                marker_color="gray",
            ))
            fig_volume.update_layout(
                height=200,
                yaxis_title="Volume",
                xaxis_title="Time",
                showlegend=False,
            )
            st.plotly_chart(fig_volume, use_container_width=True)

        except Exception as e:
            logger.error(f"Error rendering chart: {e}")
            st.error(f"❌ Error rendering chart: {str(e)}")
            with st.expander("🔍 Debug info"):
                st.write(f"DataFrame shape: {df.shape if df is not None else 'None'}")
                st.write(f"DataFrame columns: {list(df.columns) if df is not None else 'None'}")
                st.write(f"DataFrame head: {df.head() if df is not None else 'None'}")
    else:
        st.info(f"📭 Unable to load chart data for {pair}")
        if fetch_error:
            with st.expander("🔍 View error details"):
                st.code(fetch_error)
        st.markdown("""
        **Possible reasons:**
        - Invalid or unsupported trading pair symbol
        - API rate limits or temporary unavailability
        - Insufficient data for the selected timeframe
        
        **Try:**
        - Check if the pair symbol is correct (e.g., BTCUSD, ETHUSD, AAPL)
        - Wait a moment and refresh
        - Check the API logs for more details
        """)

    st.divider()

    # Action Buttons
    st.subheader("⚙️ Actions")

    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        # Close Position Button
        if st.button("🔴 Close Position", use_container_width=True, key="close_position_btn"):
            st.session_state.show_close_confirm = True
            st.rerun()

    with col2:
        # Delete Position Button
        if st.button("🗑️ Delete", use_container_width=True, key="delete_position_btn", type="secondary"):
            st.session_state.show_delete_confirm = True
            st.rerun()

    # Close Position Confirmation Dialog
    if st.session_state.get("show_close_confirm", False):
        st.warning("⚠️ **Are you sure you want to close this position?**")

        confirm_col1, confirm_col2 = st.columns([1, 1])

        with confirm_col1:
            close_price = st.number_input(
                "Close Price",
                value=float(current_price),
                step=0.01,
                key="close_price_input",
            )

        with confirm_col2:
            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("✅ Confirm Close", use_container_width=True, key="confirm_close_btn"):
                    try:
                        # Call API to close position
                        position_id = position.get("id")
                        response = requests.post(
                            f"{get_current_api_url()}/positions/{position_id}/close",
                            json={"close_price": close_price},
                            headers=get_api_headers(),
                            timeout=10,
                        )
                        response.raise_for_status()

                        st.success(f"✅ Position closed successfully at ${close_price:,.2f}!")
                        st.balloons()

                        # Clear selection and refresh
                        st.session_state.selected_position_id = None
                        st.session_state.selected_position_data = None
                        st.session_state.show_close_confirm = False
                        st.session_state.refresh_triggered = True
                        st.rerun()

                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Failed to close position: {str(e)}")
                        logger.error(f"Error closing position: {e}")

            with col_cancel:
                if st.button("❌ Cancel", use_container_width=True, key="cancel_close_btn"):
                    st.session_state.show_close_confirm = False
                    st.rerun()

    # Delete Position Confirmation Dialog
    if st.session_state.get("show_delete_confirm", False):
        st.error("🗑️ **Are you sure you want to DELETE this position?**")
        st.warning("This action cannot be undone. The position will be permanently removed from the database.")

        st.markdown(f"**Position:** {pair} ({direction})")
        st.markdown(f"**Entry Price:** ${entry_price:,.2f}")
        st.markdown(f"**Current PnL:** {pnl_sign}{pnl_pct:.2f}%")

        del_col1, del_col2 = st.columns([1, 1])

        with del_col1:
            if st.button("🗑️ Confirm Delete", use_container_width=True, key="confirm_delete_btn", type="primary"):
                try:
                    # Call API to delete position
                    position_id = position.get("id")
                    response = requests.delete(
                        f"{get_current_api_url()}/positions/{position_id}",
                        headers=get_api_headers(),
                        timeout=10,
                    )
                    response.raise_for_status()

                    st.success("✅ Position deleted successfully!")
                    st.balloons()

                    logger.info(f"Position deleted: ID={position_id}")

                    # Clear selection and redirect
                    st.session_state.selected_position_id = None
                    st.session_state.selected_position_data = None
                    st.session_state.show_delete_confirm = False
                    st.session_state.refresh_triggered = True
                    st.rerun()

                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Failed to delete position: {str(e)}")
                    logger.error(f"Error deleting position: {e}")

        with del_col2:
            if st.button("❌ Cancel", use_container_width=True, key="cancel_delete_btn"):
                st.session_state.show_delete_confirm = False
                st.rerun()

    # Back Button
    st.divider()
    if st.button("← Back to Positions", key="back_to_positions"):
        # Clear ALL position-related session state
        st.session_state.selected_position_id = None
        st.session_state.selected_position_data = None
        st.session_state.show_close_confirm = False
        st.session_state.show_delete_confirm = False
        st.session_state.manual_refresh_requested = True  # Force refresh
        st.rerun()


def render_main_page() -> None:
    """Render the main Open Positions page."""
    st.title("📈 TA-DSS Position Monitor")
    st.subheader("Real-time monitoring of your trading positions")

    # Handle auto-refresh
    if st.session_state.get("auto_refresh_enabled", False):
        current_time = time.time()
        last_refresh = st.session_state.get("last_refresh_time", 0)

        if current_time - last_refresh >= AUTO_REFRESH_INTERVAL_SECONDS:
            st.session_state.last_refresh_time = current_time
            st.session_state.manual_refresh_requested = True
            st.rerun()

    # Handle manual refresh
    if st.session_state.get("manual_refresh_requested", False):
        st.session_state.manual_refresh_requested = False
        st.session_state.show_refresh_toast = True
        # Don't clear cache here - let fetch function handle it
        st.rerun()

    # Check API connection and fetch positions
    # Always fetch fresh data (don't use cache for main positions list)
    api_positions = fetch_open_positions_from_api()
    
    if api_positions is None:
        api_connected = False
    else:
        api_connected = True

    # API Connection Banner
    if not api_connected:
        st.error("""
        ### ⚠️ Backend Connection Lost
        
        Unable to connect to the API server. Please ensure the FastAPI server is running.
        
        **To start the API server:**
        ```bash
        cd trading-order-monitoring-system
        source venv/bin/activate
        uvicorn src.main:app --reload
        ```
        """)
        
        # Retry button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Retry Connection", use_container_width=True, key="retry_connection"):
                st.rerun()
        
        st.divider()
        return

    # Last update timestamp
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Last updated: {now}")

    st.divider()

    # Check if a position is selected for detail view
    if st.session_state.get("selected_position_id") and st.session_state.get("selected_position_data"):
        render_position_detail(st.session_state.selected_position_data)
        return

    # Fetch and process positions with loading spinner
    with st.spinner("🔄 Fetching latest data..."):
        positions_data = []
        for position in api_positions:
            # Use SIMPLE version for main table (fast, no market data)
            pd = fetch_position_with_signals_simple(position)
            if pd:
                positions_data.append(pd)

        # Render summary cards
        render_summary_cards(positions_data)

        st.divider()

        # Render positions table
        render_positions_table(positions_data)
        
        # Show refresh toast if manual refresh was requested
        if st.session_state.get("show_refresh_toast", False):
            st.session_state.show_refresh_toast = False
            st.toast(f"✅ Refreshed {len(positions_data)} positions")


def render_add_position_page() -> None:
    """Render the Add New Position page."""
    st.title("➕ Add New Position")
    st.subheader("Log a new trade for monitoring")

    # Common pairs for dropdown
    COMMON_PAIRS = {
        "🟠 BTC/USD (Bitcoin)": "BTCUSD",
        "🔵 ETH/USD (Ethereum)": "ETHUSD",
        "🟣 SOL/USD (Solana)": "SOLUSD",
        "💎 XAU/USD (Gold)": "XAUUSD",
        "🍎 Apple": "AAPL",
        "🚗 Tesla": "TSLA",
        "🔍 NVIDIA": "NVDA",
        "📈 S&P 500 ETF": "SPY",
        "─── Custom Entry ───": "---custom---",
    }

    # Quick Add Presets
    st.markdown("### ⚡ Quick Add")
    st.caption("Click to auto-fill common pairs")

    preset_col1, preset_col2, preset_col3, preset_col4, preset_col5 = st.columns(5)

    with preset_col1:
        if st.button("🟠 BTCUSD", use_container_width=True, key="preset_btcusd"):
            st.session_state.preset_pair = "BTCUSD"
            st.rerun()

    with preset_col2:
        if st.button("🔵 ETHUSD", use_container_width=True, key="preset_ethusd"):
            st.session_state.preset_pair = "ETHUSD"
            st.rerun()

    with preset_col3:
        if st.button("🟣 SOLUSD", use_container_width=True, key="preset_solusd"):
            st.session_state.preset_pair = "SOLUSD"
            st.rerun()

    with preset_col4:
        if st.button("🍎 AAPL", use_container_width=True, key="preset_aapl"):
            st.session_state.preset_pair = "AAPL"
            st.rerun()

    with preset_col5:
        if st.button("🚗 TSLA", use_container_width=True, key="preset_tsla"):
            st.session_state.preset_pair = "TSLA"
            st.rerun()

    # Clear preset after use
    preset_pair = st.session_state.pop("preset_pair", None)

    # Supported timeframes
    SUPPORTED_TIMEFRAMES = {
        "1 hour": "h1",
        "4 hours": "h4",
        "1 day": "d1",
        "1 week": "w1",
    }

    with st.form("add_position_form", clear_on_submit=True):
        # Row 1: Pair Selection and Direction
        col1, col2 = st.columns(2)

        with col1:
            # Pair selector with dropdown
            st.markdown("**Pair/Symbol**")
            
            # Use selectbox with custom option
            selected_label = st.selectbox(
                "Choose a common pair or enter custom",
                options=list(COMMON_PAIRS.keys()),
                index=None,
                placeholder="Select or scroll for options...",
                key="pair_selector",
                help="Select from common pairs or choose 'Custom Entry' to type your own",
            )
            
            # If custom selected or no selection, show text input
            if selected_label and COMMON_PAIRS.get(selected_label) == "---custom---":
                pair = st.text_input(
                    "Enter custom pair",
                    value=preset_pair if preset_pair else "",
                    placeholder="e.g., BTCUSD, AAPL",
                    key="custom_pair_input",
                )
            elif selected_label:
                pair = COMMON_PAIRS[selected_label]
                st.info(f"Selected: **{pair}**")
            else:
                # No selection from dropdown, show text input for custom
                pair = st.text_input(
                    "Or enter custom pair",
                    value=preset_pair if preset_pair else "",
                    placeholder="e.g., BTCUSD, AAPL",
                    key="pair_input",
                )
            
            # Pair format help
            with st.expander("ℹ️ Pair Format Guide", expanded=False):
                st.markdown("""
                **Crypto pairs** (use CCXT data source):
                - `BTCUSD`, `ETHUSD`, `SOLUSD`, `XAUUSD`
                - Or with dash: `BTC-USD`, `ETH-USD`
                
                **Stock pairs** (use yfinance data source):
                - `AAPL`, `TSLA`, `NVDA`, `MSFT`, `GOOGL`
                - Stock symbols are 1-5 letters
                
                **Invalid formats** (will cause errors):
                - `ETH` (missing quote currency)
                - `XAU` (missing quote currency)
                - `BTC` (missing quote currency)
                """)

        with col2:
            position_type = st.radio(
                "Direction",
                ["LONG 🟢", "SHORT 🔴"],
                help="LONG: You profit if price goes up | SHORT: You profit if price goes down",
                index=0,
            )

        # Row 2: Timeframe and Entry Price
        col3, col4 = st.columns(2)
        
        with col3:
            timeframe_display = st.selectbox(
                "Timeframe",
                options=list(SUPPORTED_TIMEFRAMES.keys()),
                index=1,  # Default to 4 hours
                help="Select the timeframe for technical analysis",
            )
            timeframe = SUPPORTED_TIMEFRAMES[timeframe_display]
        
        with col4:
            entry_price = st.number_input(
                "Entry Price",
                min_value=0.01,
                step=0.01,
                placeholder="e.g., 50000.00",
                help="Price at which you entered the position (required)",
            )

        # Row 3: Entry Date/Time
        col5, col6 = st.columns(2)
        
        with col5:
            entry_date = st.date_input(
                "Entry Date",
                value=datetime.now().date(),
                help="Date when you entered the position",
            )
        
        with col6:
            entry_time = st.time_input(
                "Entry Time",
                value=datetime.now().time(),
                help="Time when you entered the position",
            )

        # Row 4: Notes
        notes = st.text_area(
            "Notes (Optional)",
            placeholder="e.g., Breaking out of resistance, RSI showing bullish divergence...",
            help="Your trade thesis or notes (optional)",
            height=80,
        )

        # Validation errors placeholder
        validation_errors = []

        # Submit button
        submit_button = st.form_submit_button("➕ Add Position", use_container_width=True, type="primary")

        if submit_button:
            # Validation
            if not pair or not pair.strip():
                validation_errors.append("❌ Pair/Symbol cannot be empty")

            # Validate pair format
            pair_clean = pair.strip().upper() if pair else ""
            if pair_clean:
                # Check for invalid short symbols (missing quote currency)
                invalid_short_symbols = ["BTC", "ETH", "SOL", "XAU", "XAG", "DOGE", "ADA", "DOT"]
                if pair_clean in invalid_short_symbols:
                    validation_errors.append(
                        f"❌ Invalid pair format: '{pair_clean}' is missing quote currency. "
                        f"Use '{pair_clean}USD' or '{pair_clean}-USD' instead."
                    )
                
                # Check for valid stock symbol (1-5 letters)
                elif pair_clean.isalpha() and len(pair_clean) <= 5:
                    pass  # Valid stock symbol
                
                # Check for valid crypto format (should have USD, USDT, or similar)
                elif not any(quote in pair_clean for quote in ["USD", "USDT", "USDC", "EUR", "GBP"]):
                    validation_errors.append(
                        f"❌ Invalid pair format: '{pair_clean}'. "
                        f"Crypto pairs should include quote currency (e.g., 'BTCUSD', 'ETH-USD')."
                    )

            if not entry_price or entry_price <= 0:
                validation_errors.append("❌ Entry Price must be greater than 0")

            if timeframe not in SUPPORTED_TIMEFRAMES.values():
                validation_errors.append("❌ Timeframe is not supported")
            
            # Show validation errors
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                try:
                    # Combine date and time
                    entry_dt = datetime.combine(entry_date, entry_time)
                    
                    # Clean pair
                    pair_clean = pair.strip().upper()

                    # Call API to add position
                    payload = {
                        "pair": pair_clean,
                        "entry_price": entry_price,
                        "position_type": position_type.split()[0],  # Remove emoji
                        "timeframe": timeframe,
                        "entry_time": entry_dt.isoformat(),
                    }

                    response = requests.post(
                        f"{get_current_api_url()}/positions/open",
                        json=payload,
                        headers=get_api_headers(),
                        timeout=10,
                    )
                    response.raise_for_status()

                    result = response.json()

                    # Success
                    st.success(f"✅ Position added successfully! (ID: {result.get('id', 'N/A')})")
                    st.balloons()
                    
                    logger.info(f"New position added: {pair_clean} ({position_type}) @ ${entry_price}")

                    # Clear form and redirect
                    st.session_state.current_page = "📋 Open Positions"
                    st.rerun()

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API. Please ensure the FastAPI server is running.")
                    st.info("💡 To start the API server, run: `uvicorn src.main:app --reload`")
                except requests.exceptions.Timeout:
                    st.error("❌ API request timed out. Please try again.")
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 422:
                        st.error(f"❌ Validation error: {e.response.json().get('detail', 'Invalid data')}")
                    else:
                        st.error(f"❌ API error: {e.response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error adding position: {str(e)}")
                    logger.error(f"Error adding position: {e}", exc_info=True)

    # Help section
    with st.expander("ℹ️ How to add a position", expanded=False):
        st.markdown(
            """
            ### Steps to Add a Position:

            1. **Pair/Symbol**: Enter the trading pair (e.g., BTCUSD for crypto, AAPL for stocks)
            2. **Direction**: 
               - 🟢 LONG: You profit if price goes up
               - 🔴 SHORT: You profit if price goes down
            3. **Timeframe**: Select the analysis timeframe
               - 1h: 1 hour (intraday)
               - 4h: 4 hours (swing trading)
               - 1d: Daily (position trading)
               - 1w: Weekly (long-term)
            4. **Entry Price**: The price at which you entered the trade
            5. **Entry Date/Time**: When you opened the position
            6. **Notes** (Optional): Your trade thesis or reasoning

            ### What happens next?

            - The system will monitor your position every 4 hours
            - You'll receive Telegram alerts when:
              - Technical signals change (e.g., BULLISH → BEARISH)
              - Price moves >5% against your position (Stop Loss Warning)
              - Price moves >10% in your favor (Take Profit Warning)
            - View real-time signals and charts in the Position Details view
            """
        )

    # Back button
    st.divider()
    if st.button("← Back to Open Positions", key="back_from_add"):
        st.session_state.current_page = "📋 Open Positions"
        st.rerun()


def render_settings_page() -> None:
    """Render the Settings page."""
    st.title("⚙️ Settings")
    st.subheader("System Configuration & Status")

    # API Connection Settings
    st.subheader("🔗 API Connection")

    # Show current API URL
    st.info(f"**API URL:** `{API_BASE_URL}`")

    # API Mode selector
    st.markdown("**Select API Mode:**")

    # Determine current mode
    is_production = API_BASE_URL != "http://localhost:8000/api/v1"
    current_mode = "production" if is_production else "local"

    # Clear session state override if .env changed (detect IP mismatch)
    import re
    match = re.search(r'http://(\d+\.\d+\.\d+\.\d+):', API_BASE_URL)
    current_vm_ip = match.group(1) if match else None
    
    if current_vm_ip and "api_base_url_override" in st.session_state:
        override_match = re.search(r'http://(\d+\.\d+\.\d+\.\d+):', st.session_state.api_base_url_override)
        if override_match and override_match.group(1) != current_vm_ip:
            # .env has different IP than session state - clear session state
            del st.session_state.api_base_url_override
            st.info(f"🔄 Detected VM IP change. Updated to {current_vm_ip}")
    
    # Store VM IP in session state - always read fresh from .env
    if "vm_external_ip" not in st.session_state or st.session_state.vm_external_ip != current_vm_ip:
        st.session_state.vm_external_ip = current_vm_ip if current_vm_ip else "35.188.118.182"

    # Mode selector using radio buttons
    selected_mode = st.radio(
        "API Connection:",
        options=["local", "production"],
        index=1 if is_production else 0,
        format_func=lambda x: "🌐 Production (Google Cloud)" if x == "production" else "💻 Local Development",
        key="api_mode_selector"
    )

    # Handle mode switch
    if selected_mode != current_mode:
        if selected_mode == "production":
            new_api_url = f"http://{st.session_state.vm_external_ip}:8000/api/v1"
            st.session_state.api_base_url_override = new_api_url
            st.success(f"✅ Switched to **Production Mode**")
            st.info(f"API URL: `{new_api_url}`")
            st.markdown("⚠️ **Note:** You need to restart the dashboard for this change to take effect.")
            st.markdown(
                f"""
                **Or run this command:**
                ```bash
                API_BASE_URL={new_api_url} streamlit run src/ui.py --server.port 8503
                ```
                """
            )
        else:
            st.session_state.api_base_url_override = "http://localhost:8000/api/v1"
            st.success("✅ Switched to **Local Mode**")
            st.info("API URL: `http://localhost:8000/api/v1`")
            st.markdown("⚠️ **Note:** You need to restart the dashboard for this change to take effect.")

    # VM IP configuration (for production mode)
    if selected_mode == "production":
        st.divider()
        st.markdown("**Google Cloud VM Configuration:**")
        new_vm_ip = st.text_input(
            "VM External IP:",
            value=st.session_state.vm_external_ip,
            key="vm_ip_input",
            help="Your Google Cloud VM's external IP address"
        )
        if new_vm_ip != st.session_state.vm_external_ip:
            st.session_state.vm_external_ip = new_vm_ip
            st.success(f"✅ VM IP updated to `{new_vm_ip}`")
            st.info("Switch to Production mode above to use this IP.")

    # Test connection button
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🔌 Test Connection", use_container_width=True):
            with st.spinner("Testing..."):
                # Use the currently selected mode's URL
                # Only use session state override if it's a valid URL
                override = st.session_state.get("api_base_url_override")
                if override and override.startswith("http"):
                    test_url = override
                else:
                    test_url = get_current_api_url()
                
                st.info(f"Testing: {test_url}")  # DEBUG: Show what URL we're testing
                success, message = test_api_connection(test_url)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.divider()

    # Telegram Settings
    st.subheader("📱 Telegram Notifications")

    telegram_configured = bool(settings.telegram_bot_token and settings.telegram_chat_id)

    if telegram_configured:
        st.success("✅ Telegram is configured")
        st.info(f"Bot Token: `{settings.telegram_bot_token[:20]}...`")
        st.info(f"Chat ID: `{settings.telegram_chat_id}`")

        if st.button("📤 Send Test Alert", use_container_width=True):
            with st.spinner("Sending test message..."):
                try:
                    from src.notifier import TelegramNotifier
                    notifier = TelegramNotifier()
                    success = notifier.send_test_message()

                    if success:
                        st.success("✅ Test message sent! Check your Telegram.")
                    else:
                        st.error("❌ Failed to send test message. Check logs/telegram.log")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("⚠️ Telegram is not configured")
        st.markdown(
            """
            To configure Telegram notifications:

            1. Get a bot token from [@BotFather](https://t.me/BotFather)
            2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
            3. Add them to your `.env` file:
               ```
               TELEGRAM_BOT_TOKEN=your_token_here
               TELEGRAM_CHAT_ID=your_chat_id_here
               ```
            4. Restart the application
            """
        )

    st.divider()

    # Monitoring Settings
    st.subheader("⏰ Monitoring Schedule")

    # Get scheduler status from API
    try:
        system_info = get_system_info_cached()

        if system_info.get("running", False):
            st.success("✅ Scheduler is running")

            next_run = system_info.get("next_run_time")
            if next_run:
                try:
                    next_run_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                    st.info(f"Next check: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except Exception:
                    pass
        else:
            st.warning("⚠️ Scheduler is not running")
    except Exception:
        st.warning("⚠️ Unable to get scheduler status")

    st.info("ℹ️ **Schedule:** Every hour at :10 minutes past the hour (XX:10 UTC)")
    st.info("This avoids API congestion at round hour boundaries (:00).")
    
    st.markdown(
        """
        **Note:** The monitoring interval is fixed at 1 hour. To change the schedule,
        modify the cron trigger in `src/scheduler.py`.
        """
    )

    st.divider()

    # Alert Thresholds
    st.subheader("🚨 Alert Thresholds")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Stop Loss Warning", "-5%", "Triggers when PnL < -5%")
    with col2:
        st.metric("Take Profit Warning", "+10%", "Triggers when PnL > +10%")

    st.markdown(
        """
        These thresholds determine when you receive alerts:

        - **Stop Loss Warning**: When your position is down more than 5%
        - **Take Profit Warning**: When your position is up more than 10%

        To customize these, you would need to modify the `PositionMonitor` class in `src/monitor.py`.
        """
    )

    st.divider()

    # System Information
    st.subheader("ℹ️ System Information")

    # Database path
    db_path = settings.database_url.replace("sqlite:///", "")

    # Get position count
    try:
        with get_db_session() as db:
            total_positions = db.query(Position).count()
            open_positions = db.query(Position).filter(Position.status == PositionStatus.OPEN).count()
            closed_positions = db.query(Position).filter(Position.status == PositionStatus.CLOSED).count()
    except Exception:
        total_positions = open_positions = closed_positions = "N/A"

    st.json({
        "Dashboard Version": DASHBOARD_VERSION,
        "Python Version": "3.12.9",
        "FastAPI Version": "0.109.0",
        "Streamlit Version": "1.54.0",
        "Database Type": "SQLite",
        "Database Path": db_path,
        "Total Positions": str(total_positions),
        "Open Positions": str(open_positions),
        "Closed Positions": str(closed_positions),
        "Data Sources": ["yfinance (Stocks)", "CCXT (Crypto)"],
        "Technical Analysis": "pandas_ta",
        "Scheduler": "APScheduler 3.10.4",
    })

    # Data sources status
    st.divider()
    st.subheader("📡 Data Sources")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📈 yfinance (Stocks)")
        st.caption("Status: Available")
        st.caption("No API key required")

    with col2:
        st.markdown("#### 🪙 CCXT (Crypto)")
        st.caption("Status: Available")
        st.caption("Default exchange: Binance")

    st.divider()

    # Performance Settings
    st.subheader("⚡ Performance")

    st.markdown(
        """
        **Caching:**
        - Position data: Cached for 30 seconds
        - System info: Cached for 60 seconds

        **Auto-refresh:**
        - Manual refresh: Available in sidebar
        - Auto-refresh: Toggle in sidebar (30-second intervals)

        **Tips for better performance:**
        - Use auto-refresh sparingly (increases API calls)
        - Clear browser cache if dashboard is slow
        - Ensure API server is on same machine for lowest latency
        """
    )

    st.divider()

    # Quick Links
    st.subheader("🔗 Quick Links")

    # Extract base API URL (without /api/v1) for links
    api_base_server = get_current_api_url().replace("/api/v1", "")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.link_button("📋 API Docs", f"{api_base_server}/docs")

    with col2:
        st.link_button("🏥 Health Check", f"{api_base_server}/health")

    with col3:
        st.link_button("📊 Dashboard", "http://localhost:8503")


def render_footer() -> None:
    """Render footer with timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(
        f"""
        <div class="footer">
            Generated by TA-DSS System • {now} UTC
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Main Application
# =============================================================================


def main():
    """Main application entry point."""
    # Initialize session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "📋 Open Positions"

    if "selected_position_id" not in st.session_state:
        st.session_state.selected_position_id = None

    if "selected_position_data" not in st.session_state:
        st.session_state.selected_position_data = None

    if "show_close_confirm" not in st.session_state:
        st.session_state.show_close_confirm = False

    if "show_delete_confirm" not in st.session_state:
        st.session_state.show_delete_confirm = False

    if "auto_refresh_enabled" not in st.session_state:
        st.session_state.auto_refresh_enabled = False

    if "manual_refresh_requested" not in st.session_state:
        st.session_state.manual_refresh_requested = False

    if "show_refresh_toast" not in st.session_state:
        st.session_state.show_refresh_toast = False

    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = time.time()

    # Render sidebar
    render_sidebar()

    # Render current page
    page = st.session_state.current_page

    if page == "📋 Open Positions":
        render_main_page()
    elif page == "➕ Add New Position":
        render_add_position_page()
    elif page == "🔍 MTF Scanner":
        render_mtf_scanner_page()
    elif page == "📈 Market Data":
        display_market_data_page()
    elif page == "⚙️ Settings":
        render_settings_page()

    # Render footer
    render_footer()


if __name__ == "__main__":
    main()
