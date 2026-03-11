"""
Market Data Status Dashboard Panel for TA-DSS.

This panel displays the status of cached market data for all watchlist pairs,
showing data quality, candle counts, and freshness across timeframes.

Features:
- Color-coded quality badges (EXCELLENT/GOOD/STALE/MISSING)
- Timeframe breakdown per pair
- MTF readiness indicator
- Manual refresh controls
- Summary statistics

Usage:
    Import in ui.py:
    >>> from src.ui_market_data import display_market_data_page
    >>> display_market_data_page()
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# Quality badge colors
QUALITY_COLORS = {
    "EXCELLENT": "success",  # Green
    "GOOD": "primary",       # Blue
    "STALE": "warning",      # Yellow/Orange
    "MISSING": "danger",     # Red
}

# Quality badge icons
QUALITY_ICONS = {
    "EXCELLENT": "🟢",
    "GOOD": "🟢",
    "STALE": "🟡",
    "MISSING": "🔴",
}


def _get_api_base_url() -> str:
    """Get API base URL from environment or default."""
    import os
    from pathlib import Path

    if hasattr(st, "session_state") and "api_base_url_override" in st.session_state:
        override = st.session_state.api_base_url_override
        if override and "VM_EXTERNAL_IP" not in override:
            return override
        del st.session_state.api_base_url_override

    # Try environment variable first
    api_url = os.getenv("API_BASE_URL", "")
    if api_url and "VM_EXTERNAL_IP" not in api_url:
        return api_url

    # Try to read from .env file
    env_file = Path(__file__).parent.parent / ".env"
    vm_ip = None
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        k, v = key.strip(), value.strip()
                        if k == "API_BASE_URL" and v and not v.startswith("your_") and "VM_EXTERNAL_IP" not in v:
                            return v
                        if k == "VM_EXTERNAL_IP" and v and "VM_EXTERNAL_IP" not in v:
                            vm_ip = v
        except Exception:
            pass

    if vm_ip:
        return f"http://{vm_ip}:8000/api/v1"

    # Default to localhost
    return "http://localhost:8000/api/v1"


def _get_headers() -> Dict[str, str]:
    """Get request headers with API key if configured."""
    import os
    from pathlib import Path
    
    headers = {"Content-Type": "application/json"}
    
    # Try environment variable first
    api_key = os.getenv("API_SECRET_KEY")
    
    # Try to read from .env file if not in environment
    if not api_key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key.strip() == "API_SECRET_KEY":
                                api_key = value.strip()
                                break
            except Exception:
                pass
    
    # Try streamlit secrets as fallback
    if not api_key:
        try:
            api_key = st.secrets.get("api_key", None)
        except Exception:
            pass
    
    if api_key:
        headers["X-API-Key"] = api_key
    
    return headers


def _fetch_market_data_status() -> Optional[Dict[str, Any]]:
    """Fetch all market data status from API."""
    base_url = _get_api_base_url()
    try:
        response = requests.get(
            f"{base_url}/market-data/status",
            headers=_get_headers(),
            timeout=10,
        )
        
        # Handle 404 - endpoint not deployed yet
        if response.status_code == 404:
            logger.warning("Market data API endpoint not found - feature not deployed yet")
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch market data status: {e}")
        return None


def _fetch_pair_status(pair: str) -> Optional[Dict[str, Any]]:
    """Fetch status for a specific pair."""
    base_url = _get_api_base_url()
    try:
        response = requests.get(
            f"{base_url}/market-data/status/{pair}",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch status for {pair}: {e}")
        return None


def _fetch_summary() -> Optional[Dict[str, Any]]:
    """Fetch summary statistics."""
    base_url = _get_api_base_url()
    try:
        response = requests.get(
            f"{base_url}/market-data/summary",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch summary: {e}")
        return None


def _fetch_watchlist(trading_style: str = "SWING") -> Optional[Dict[str, Any]]:
    """Fetch watchlist with status."""
    base_url = _get_api_base_url()
    try:
        response = requests.get(
            f"{base_url}/market-data/watchlist?trading_style={trading_style.upper()}",
            headers=_get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch watchlist: {e}")
        return None


def _refresh_pair(pair: str, timeframes: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Trigger refresh for a specific pair."""
    base_url = _get_api_base_url()
    payload = {"pair": pair}
    if timeframes:
        payload["timeframes"] = timeframes
    
    try:
        response = requests.post(
            f"{base_url}/market-data/refresh",
            headers=_get_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to refresh {pair}: {e}")
        return None


def _refresh_all_stale(trading_style: str = "SWING") -> Optional[Dict[str, Any]]:
    """Trigger refresh for all stale pairs."""
    base_url = _get_api_base_url()
    
    try:
        response = requests.post(
            f"{base_url}/market-data/refresh-all",
            headers=_get_headers(),
            json={"trading_style": trading_style},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to refresh all stale pairs: {e}")
        return None


def _quality_badge(quality: str) -> str:
    """Create a colored badge for quality level."""
    icon = QUALITY_ICONS.get(quality, "⚪")
    return f"{icon} **{quality}**"


def _normalize_timeframe(tf: str) -> str:
    """
    Normalize timeframe to standard format.
    
    Converts variations like '1week' → 'w1', '1d' → 'd1', etc.
    """
    tf = tf.lower().strip()
    
    # Mapping of variations to standard format
    normalization = {
        '1week': 'w1', '1w': 'w1', 'week': 'w1',
        '1month': 'M1', '1M': 'M1', 'month': 'M1',
        '1day': 'd1', '1d': 'd1', 'day': 'd1',
        '1hour': 'h1', '1h': 'h1', 'hour': 'h1',
        '4h': 'h4', '2h': 'h2', '6h': 'h6', '8h': 'h8', '12h': 'h12',
        '15m': 'm15', '30m': 'm30', '5m': 'm5', '1m': 'm1',
    }
    
    return normalization.get(tf, tf)


def _get_timeframe_sort_key(tf: str) -> tuple:
    """
    Get sort key for timeframe (longest first).
    
    Order: M1 > w1 > d1 > h12 > h8 > h6 > h4 > h2 > h1 > m30 > m15 > m5 > m1
    """
    tf = _normalize_timeframe(tf)
    
    # Define order (higher timeframes first)
    order = {
        'M1': 0, 'w1': 1, 'd1': 2,
        'h12': 3, 'h8': 4, 'h6': 5, 'h4': 6, 'h2': 7, 'h1': 8,
        'm30': 9, 'm15': 10, 'm5': 11, 'm1': 12,
    }
    
    return (order.get(tf, 99), tf)


def _merge_timeframe_data(timeframes: dict) -> dict:
    """
    Merge duplicate timeframe entries, keeping the best (newest/highest count) data.
    
    Args:
        timeframes: Raw timeframe data from API
        
    Returns:
        Normalized and deduplicated timeframe data
    """
    normalized_tfs = {}
    
    for tf, tf_data in timeframes.items():
        norm_tf = _normalize_timeframe(tf)
        
        # If this normalized timeframe doesn't exist yet, add it
        if norm_tf not in normalized_tfs:
            normalized_tfs[norm_tf] = tf_data.copy()
        else:
            # Merge: keep the one with higher candle count and newer fetched_at
            existing = normalized_tfs[norm_tf]
            
            # Prefer higher candle count
            if tf_data.get('candle_count', 0) > existing.get('candle_count', 0):
                normalized_tfs[norm_tf] = tf_data.copy()
            
            # Prefer better quality
            quality_order = {'EXCELLENT': 4, 'GOOD': 3, 'STALE': 2, 'MISSING': 1}
            if quality_order.get(tf_data.get('quality', 'MISSING'), 0) > quality_order.get(existing.get('quality', 'MISSING'), 0):
                # Copy data but keep the better quality
                normalized_tfs[norm_tf] = tf_data.copy()
            
            # Prefer newer fetched_at
            tf_fetched = tf_data.get('fetched_at', '')
            existing_fetched = existing.get('fetched_at', '')
            if tf_fetched > existing_fetched:
                # Update fetched_at to newest
                normalized_tfs[norm_tf]['fetched_at'] = tf_fetched
    
    return normalized_tfs


def _display_summary_cards(summary: Dict[str, Any]) -> None:
    """Display summary statistics as metric cards."""
    cols = st.columns(4)
    
    total = summary.get("total_pairs", 0)
    mtf_ready = summary.get("mtf_ready", 0)
    by_quality = summary.get("by_quality", {})
    
    with cols[0]:
        st.metric(
            label="Total Pairs",
            value=total,
        )
    
    with cols[1]:
        st.metric(
            label="MTF Ready",
            value=mtf_ready,
            delta=f"{round(mtf_ready/total*100) if total > 0 else 0}%",
        )
    
    with cols[2]:
        excellent = by_quality.get("EXCELLENT", 0)
        good = by_quality.get("GOOD", 0)
        st.metric(
            label="Good Data",
            value=excellent + good,
            delta=f"{excellent} excellent",
        )
    
    with cols[3]:
        stale = by_quality.get("STALE", 0)
        missing = by_quality.get("MISSING", 0)
        st.metric(
            label="Needs Refresh",
            value=stale + missing,
            delta=f"{missing} missing" if missing > 0 else None,
        )


def _display_pair_row(pair_data: Dict[str, Any], key: str) -> None:
    """Display a single pair as a table row."""
    pair = pair_data.get("pair", "Unknown")
    quality = pair_data.get("overall_quality", "MISSING")
    mtf_ready = pair_data.get("mtf_ready", False)
    timeframes = pair_data.get("timeframes", {})
    
    # Merge duplicates and normalize timeframes
    normalized_tfs = _merge_timeframe_data(timeframes)
    
    # Sort by timeframe (longest first)
    sorted_tfs = sorted(normalized_tfs.keys(), key=_get_timeframe_sort_key)
    
    # Format timeframe info
    tf_info = []
    for tf in sorted_tfs[:5]:  # Show max 5 timeframes
        tf_data = normalized_tfs[tf]
        tf_quality = tf_data.get("quality", "MISSING")
        tf_icon = QUALITY_ICONS.get(tf_quality, "⚪")
        tf_info.append(f"{tf.upper()}: {tf_icon}")
    
    tf_str = " | ".join(tf_info) if tf_info else "No data"
    
    # Create columns
    col1, col2, col3, col4 = st.columns([2, 1, 3, 1])
    
    with col1:
        st.markdown(f"**{pair}**")
    
    with col2:
        st.markdown(_quality_badge(quality))
    
    with col3:
        st.markdown(f"<small>{tf_str}</small>", unsafe_allow_html=True)
    
    with col4:
        if mtf_ready:
            st.success("✅ Ready")
        else:
            st.error("❌ Not Ready")


def _display_pair_details(pair_data: Dict[str, Any]) -> None:
    """Display detailed view for a single pair."""
    pair = pair_data.get("pair", "Unknown")
    quality = pair_data.get("overall_quality", "MISSING")
    mtf_ready = pair_data.get("mtf_ready", False)
    recommendation = pair_data.get("recommendation", "")
    timeframes = pair_data.get("timeframes", {})
    
    st.markdown(f"### {pair}")
    
    # Status banner
    if mtf_ready:
        st.success(f"✅ {_quality_badge(quality)} - Ready for MTF analysis")
    elif quality == "MISSING":
        st.error(f"🔴 **MISSING** - No data available")
    else:
        st.warning(f"🟡 {_quality_badge(quality)} - {recommendation}")
    
    # Timeframe details table
    if timeframes:
        st.markdown("#### Timeframe Details")
        
        # Merge duplicates and normalize
        normalized_tfs = _merge_timeframe_data(timeframes)
        
        # Sort by timeframe (longest first)
        sorted_tfs = sorted(normalized_tfs.keys(), key=_get_timeframe_sort_key)
        
        tf_data = []
        for tf in sorted_tfs:
            data = normalized_tfs[tf]
            candles = data.get("candle_count", 0)
            tf_quality = data.get("quality", "MISSING")
            last_update = data.get("last_candle_time", "Unknown")
            source = data.get("source", "N/A")
            
            # Parse and format timestamp
            if last_update and last_update != "Unknown":
                try:
                    dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                    last_update = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            
            tf_data.append({
                "Timeframe": tf.upper(),
                "Quality": QUALITY_ICONS.get(tf_quality, "⚪") + f" {tf_quality}",
                "Candles": candles,
                "Last Update": last_update,
                "Source": source if source else "N/A",
            })
        
        st.table(tf_data)
    else:
        st.info("No timeframe data available")


def _display_refresh_controls() -> None:
    """Display refresh control panel."""
    st.markdown("### 🔄 Refresh Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Refresh Single Pair**")
        pair_to_refresh = st.selectbox(
            "Select pair",
            options=["BTC/USDT", "ETH/USDT", "XAU/USD", "XAG/USD"],
            key="refresh_pair_select",
        )
        
        if st.button("Refresh Pair", key="refresh_single_btn"):
            with st.spinner(f"Refreshing {pair_to_refresh}..."):
                result = _refresh_pair(pair_to_refresh)
                if result and result.get("status") in ("success", "partial"):
                    st.success(f"✅ Refreshed {pair_to_refresh}")
                    if result.get("refreshed"):
                        for tf in result["refreshed"]:
                            st.write(f"  - {tf['timeframe']}: {tf['candles_fetched']} candles")
                    st.rerun()
                else:
                    st.error(f"Failed to refresh: {result.get('errors', 'Unknown error')}")
    
    with col2:
        st.markdown("**Refresh All Stale Pairs**")
        trading_style = st.selectbox(
            "Trading style",
            options=["SWING", "INTRADAY", "DAY", "POSITION", "SCALPING"],
            index=0,
            key="refresh_all_style",
        )
        
        if st.button("Refresh All Stale", key="refresh_all_btn", type="primary"):
            with st.spinner(f"Refreshing all stale pairs ({trading_style} timeframes)..."):
                result = _refresh_all_stale(trading_style)
                if result:
                    summary = result.get("summary", {})
                    st.success(
                        f"✅ Complete: {summary.get('refreshed', 0)} refreshed, "
                        f"{summary.get('errors', 0)} errors"
                    )
                    st.rerun()


def display_market_data_page() -> None:
    """
    Main display function for Market Data Status page.
    
    This is the entry point for the Streamlit page.
    """
    st.set_page_config(
        page_title="Market Data Status",
        page_icon="📊",
        layout="wide",
    )
    
    st.title("📊 Market Data Status")
    st.markdown("""
    Monitor the quality and freshness of cached market data for all watchlist pairs.
    **Green** = Good data ready for MTF analysis | **Yellow** = Stale, refresh recommended | **Red** = Missing, refresh required
    """)
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh every 30s", value=False)
    
    # Trading style filter
    trading_style = st.sidebar.selectbox(
        "Trading Style",
        options=["SWING", "INTRADAY", "DAY", "POSITION", "SCALPING"],
        index=0,
    )
    
    # Quality filter
    quality_filter = st.sidebar.multiselect(
        "Filter by Quality",
        options=["EXCELLENT", "GOOD", "STALE", "MISSING"],
        default=["EXCELLENT", "GOOD", "STALE", "MISSING"],
    )
    
    # Fetch data
    status_data = _fetch_market_data_status()
    summary_data = _fetch_summary()
    watchlist_data = _fetch_watchlist(trading_style)

    # Debug info
    st.caption(f"API URL: {_get_api_base_url()}")
    
    if status_data is None:
        # Try to determine the issue
        test_url = f"{_get_api_base_url()}/market-data/status"
        st.error("### ❌ Failed to fetch market data status")
        st.info(f"""
            **API Endpoint:** `{test_url}`
            
            **Troubleshooting:**
            1. Check if the API server is running on the VM
            2. Verify your API key is correct in .env file
            3. Check firewall rules allow port 8000
            
            **Test the API directly:**
            ```bash
            curl "{test_url}" -H "X-API-Key: YOUR_API_KEY"
            ```
        """)
        
        # Show last error from logger
        st.warning("Check the terminal/console for detailed error logs")
        
        # Don't show demo data - let user troubleshoot
        return
    
    # Display summary cards
    if summary_data:
        _display_summary_cards(summary_data)
    
    st.divider()
    
    # View mode selector
    view_mode = st.radio(
        "View Mode",
        options=["Table", "Cards", "Details"],
        horizontal=True,
    )
    
    # Filter pairs by quality
    filtered_pairs = {}
    for pair, data in status_data.get("pairs", {}).items():
        if data.get("overall_quality") in quality_filter:
            filtered_pairs[pair] = data
    
    if view_mode == "Table":
        # Table view
        st.markdown("### All Pairs")
        
        if filtered_pairs:
            for pair, data in filtered_pairs.items():
                _display_pair_row(data, pair)
                st.divider()
        else:
            st.info("No pairs match the selected filters")
    
    elif view_mode == "Cards":
        # Card view
        st.markdown("### All Pairs")
        
        if not filtered_pairs:
            st.info("No pairs match the selected filters")
            return
        
        # Create cards with better layout
        for pair, data in filtered_pairs.items():
            with st.container(border=True):
                quality = data.get("overall_quality", "MISSING")
                mtf_ready = data.get("mtf_ready", False)
                
                # Header row
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.markdown(f"#### {pair}")
                with col_h2:
                    if mtf_ready:
                        st.success("✅ MTF Ready")
                    else:
                        st.warning("⚠️ Not Ready")
                
                # Quality badge
                st.markdown(_quality_badge(quality))
                
                # Timeframe summary (merged and normalized)
                timeframes = data.get("timeframes", {})
                if timeframes:
                    # Merge duplicates and normalize
                    normalized_tfs = _merge_timeframe_data(timeframes)
                    
                    # Sort and show all
                    sorted_tfs = sorted(normalized_tfs.keys(), key=_get_timeframe_sort_key)
                    
                    st.markdown("**Timeframes:**")
                    for tf in sorted_tfs:
                        tf_data = normalized_tfs[tf]
                        tf_quality = tf_data.get('quality', 'MISSING')
                        tf_candles = tf_data.get('candle_count', 0)
                        tf_icon = QUALITY_ICONS.get(tf_quality, '⚪')
                        st.caption(f"{tf_icon} {tf.upper()}: {tf_candles} candles ({tf_quality})")
                
                # Expand for details
                with st.expander("📊 View Full Details"):
                    _display_pair_details(data)
    
    elif view_mode == "Details":
        # Details view - show one pair at a time
        st.markdown("### Pair Details")

        if filtered_pairs:
            selected_pair = st.selectbox(
                "Select pair",
                options=list(filtered_pairs.keys()),
            )

            if selected_pair:
                # Use data we already have (faster)
                pair_data = filtered_pairs[selected_pair]
                
                # Display the data
                _display_pair_details(pair_data)
                
                st.divider()
                
                # Quick refresh button
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown("")
                with col2:
                    if st.button("🔄 Refresh", key=f"refresh_{selected_pair}"):
                        with st.spinner(f"Refreshing {selected_pair}..."):
                            result = _refresh_pair(selected_pair)
                            if result:
                                refreshed = result.get('refreshed', [])
                                errors = result.get('errors', [])
                                if refreshed:
                                    st.success(f"✅ Refreshed {len(refreshed)} timeframe(s)")
                                    for r in refreshed:
                                        st.write(f"  - {r['timeframe'].upper()}: {r['candles_fetched']} candles")
                                if errors:
                                    st.warning(f"⚠️ {len(errors)} failed")
                                st.rerun()
                            else:
                                st.error("Refresh failed")
        else:
            st.info("No pairs match the selected filters")
    
    st.divider()
    
    # Refresh controls
    _display_refresh_controls()
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


# For testing standalone
if __name__ == "__main__":
    display_market_data_page()
