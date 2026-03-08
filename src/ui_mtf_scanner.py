"""
MTF Scanner Dashboard Panel for TA-DSS.

Streamlit components for MTF (Multi-Timeframe) analysis scanner.
Displays trading opportunities with alignment scores, patterns, and key levels.

Usage:
    from src.ui_mtf_scanner import render_mtf_scanner_page
    
    # In main ui.py
    if page == "🔍 MTF Scanner":
        render_mtf_scanner_page()
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st


def _get_api_base_url() -> str:
    """Read API base URL — mirrors ui.py priority: session override → env var → .env file → localhost."""
    if hasattr(st, "session_state") and "api_base_url_override" in st.session_state:
        return st.session_state.api_base_url_override

    url = os.getenv("API_BASE_URL", "")
    if url:
        return url

    # Fall back to .env file (same logic as ui.py _load_api_url_from_env)
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
    ]
    vm_ip = None
    for env_file in env_paths:
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k == "API_BASE_URL" and v and not v.startswith("your_"):
                            return v
                        if k == "VM_EXTERNAL_IP" and v:
                            vm_ip = v
            except Exception:
                pass
        if vm_ip:
            break

    if vm_ip:
        return f"http://{vm_ip}:8000/api/v1"

    return "http://localhost:8000/api/v1"


def _get_api_headers() -> dict:
    """Return auth headers for API requests (mirrors ui.py: env var then .env file)."""
    key = os.getenv("API_SECRET_KEY", "")
    
    if not key:
        # Try multiple paths for .env file
        env_paths = [
            Path(__file__).parent.parent / ".env",  # src/../.env
            Path(__file__).parent / ".env",  # src/.env
            Path.cwd() / ".env",  # Current working directory
        ]
        
        for env_file in env_paths:
            if env_file.exists():
                try:
                    with open(env_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                if k.strip() == "API_SECRET_KEY":
                                    key = v.strip()
                                    break
                    if key:
                        break
                except Exception:
                    pass
    
    return {"X-API-Key": key} if key else {}

logger = logging.getLogger(__name__)


# =============================================================================
# MTF Scanner Page
# =============================================================================


def render_mtf_scanner_page():
    """
    Render the MTF Scanner page.
    
    Features:
    - Trading style selector
    - Min alignment filter
    - Min R:R filter
    - Opportunity table
    - Detailed pair analysis
    """
    st.title("🔍 MTF Opportunity Scanner")
    st.caption("Multi-Timeframe Analysis - Scan for high-probability trading opportunities")
    
    # Initialize session state for MTF scanner
    if "mtf_trading_style" not in st.session_state:
        st.session_state.mtf_trading_style = "SWING"
    if "mtf_min_alignment" not in st.session_state:
        st.session_state.mtf_min_alignment = 2
    if "mtf_min_rr_ratio" not in st.session_state:
        st.session_state.mtf_min_rr_ratio = 2.0
    if "mtf_scan_results" not in st.session_state:
        st.session_state.mtf_scan_results = None
    if "mtf_last_scan_time" not in st.session_state:
        st.session_state.mtf_last_scan_time = None
    
    # ========================================================================
    # Filters Panel
    # ========================================================================
    
    st.subheader("🎛️ Scan Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        trading_style = st.selectbox(
            "Trading Style",
            options=["POSITION", "SWING", "INTRADAY", "DAY", "SCALPING"],
            index=1,  # Default to SWING
            key="mtf_trading_style",
            help="Determines timeframe combination (e.g., SWING = Weekly→Daily→4H)",
        )
    
    with col2:
        min_alignment = st.slider(
            "Min Alignment",
            min_value=0,
            max_value=3,
            value=2,
            key="mtf_min_alignment",
            help="Minimum number of aligned timeframes (0-3)",
        )
    
    with col3:
        min_rr_ratio = st.number_input(
            "Min R:R",
            min_value=0.5,
            max_value=10.0,
            value=2.0,
            step=0.5,
            key="mtf_min_rr_ratio",
            help="Minimum risk:reward ratio",
        )
    
    with col4:
        st.write("")  # Spacer
        st.write("")  # Spacer
        scan_button = st.button(
            "🔍 Scan Now",
            use_container_width=True,
            type="primary",
        )
    
    # ========================================================================
    # Watchlist Management
    # ========================================================================

    with st.expander("📋 Manage Watchlist", expanded=False):
        _display_watchlist_management()

    # Display timeframe info for selected style
    timeframe_info = _get_timeframe_info(trading_style)
    st.caption(
        f"⏱️ Timeframes: **HTF**: {timeframe_info['htf']} (Bias) | "
        f"**MTF**: {timeframe_info['mtf']} (Setup) | "
        f"**LTF**: {timeframe_info['ltf']} (Entry)"
    )
    
    # ========================================================================
    # Scan Execution — fire immediately on button click, no stale check
    # ========================================================================

    if scan_button:
        with st.spinner("Scanning for opportunities..."):
            try:
                response = requests.get(
                    f"{_get_api_base_url()}/mtf/opportunities",
                    params={
                        "trading_style": trading_style,
                        "min_alignment": min_alignment,
                        "min_rr_ratio": min_rr_ratio,
                        "check_status": False,
                    },
                    headers=_get_api_headers(),
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.mtf_scan_results = data.get("opportunities", [])
                st.session_state.mtf_last_scan_time = datetime.utcnow()

                summary = data.get("summary", {})
                scanned = summary.get("pairs_scanned", 0)
                no_data = summary.get("pairs_no_data", 0)
                found = summary.get("opportunities_found", 0)

                st.success(f"Scan complete: {found} opportunities from {scanned} pairs scanned.")

                if no_data > 0:
                    st.warning(f"{no_data} pair(s) had no data — run a data refresh first.")

            except requests.exceptions.Timeout:
                st.error("Scan timed out (>120s). Try again.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Check that the server is running.")
            except requests.exceptions.HTTPError as exc:
                st.error(f"API error {exc.response.status_code}: {exc.response.text[:200]}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
    
    # ========================================================================
    # Results Display
    # ========================================================================
    
    if st.session_state.mtf_scan_results:
        _display_scan_results(
            results=st.session_state.mtf_scan_results,
            trading_style=trading_style,
        )
    else:
        _display_scan_instructions()
    
    # ========================================================================
    # Last Scan Info
    # ========================================================================
    
    if st.session_state.mtf_last_scan_time:
        st.divider()
        st.caption(
            f"🕐 Last scan: {st.session_state.mtf_last_scan_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )


def _get_timeframe_info(trading_style: str) -> Dict[str, str]:
    """
    Get timeframe combination for trading style.
    
    Args:
        trading_style: Selected trading style.
    
    Returns:
        Dictionary with htf, mtf, ltf timeframes.
    """
    configs = {
        "POSITION": {"htf": "Monthly", "mtf": "Weekly", "ltf": "Daily"},
        "SWING": {"htf": "Weekly", "mtf": "Daily", "ltf": "4H"},
        "INTRADAY": {"htf": "Daily", "mtf": "4H", "ltf": "1H"},
        "DAY": {"htf": "4H", "mtf": "1H", "ltf": "15M"},
        "SCALPING": {"htf": "1H", "mtf": "15M", "ltf": "5M"},
    }
    return configs.get(trading_style, configs["SWING"])




def _display_scan_instructions():
    """Display instructions when no scan has been run."""
    st.info("""
    ### 🔍 How to Use the MTF Scanner
    
    1. **Select Trading Style** - Choose your preferred timeframe combination
    2. **Set Filters** - Minimum alignment score and R:R ratio
    3. **Click Scan** - Scan all pairs for MTF-aligned opportunities
    4. **Review Results** - Analyze opportunities with detailed breakdown
    5. **Take Action** - Use signals to inform your trading decisions
    
    ---
    
    #### 📊 Alignment Scores
    
    | Score | Quality | Action |
    |-------|---------|--------|
    | 3/3 | HIGHEST | Trade aggressively |
    | 2/3 | GOOD | Standard risk |
    | 1/3 | POOR | Avoid or reduce size |
    | 0/3 | AVOID | Do not trade |
    
    #### 🎯 Patterns Detected
    
    - **HTF Support + LTF Reversal** - Bounce off key level with confirmation
    - **HTF Trend + MTF Pullback + LTF Entry** - Trend continuation setup
    - **MTF Divergence at HTF Level** - Momentum reversal at key level
    - **All 3 TFs Aligned** - Maximum confluence
    """)


def _display_scan_results(
    results: List[Dict[str, Any]],
    trading_style: str,
):
    """
    Display scan results in table and cards.
    
    Args:
        results: List of opportunity dictionaries.
        trading_style: Selected trading style.
    """
    st.subheader(f"📊 Scan Results ({len(results)} opportunities)")
    
    if not results:
        st.warning("No opportunities found matching your filters. Try relaxing the criteria.")
        return
    
    # Convert to DataFrame for display
    df = pd.DataFrame(results)
    
    # Quality color mapping
    quality_colors = {
        "HIGHEST": "🟢",
        "GOOD": "🟡",
        "POOR": "🟠",
        "AVOID": "🔴",
    }
    
    # Display summary cards
    col1, col2, col3 = st.columns(3)
    
    high_conviction = sum(1 for r in results if r["quality"] == "HIGHEST")
    buy_signals = sum(1 for r in results if r["recommendation"] == "BUY")
    sell_signals = sum(1 for r in results if r["recommendation"] == "SELL")
    
    with col1:
        st.metric("High Conviction (3/3)", high_conviction)
    with col2:
        st.metric("Buy Signals", buy_signals)
    with col3:
        st.metric("Sell Signals", sell_signals)
    
    st.divider()
    
    # Display opportunities as expandable cards
    for i, opp in enumerate(results):
        quality_emoji = quality_colors.get(opp["quality"], "⚪")
        
        with st.expander(
            f"{quality_emoji} **{opp['pair']}** - {opp['quality']} ({opp['alignment_score']}/3) - {opp['recommendation']}",
            expanded=(i == 0),  # Expand first by default
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**HTF Bias:** {opp['htf_bias']}")
                st.markdown(f"**MTF Setup:** {opp['mtf_setup']}")
                st.markdown(f"**LTF Entry:** {opp['ltf_entry']}")
            
            with col2:
                if opp["entry_price"]:
                    st.markdown(f"**Entry:** ${opp['entry_price']:,.2f}")
                    st.markdown(f"**Stop:** ${opp['stop_loss']:,.2f}")
                    st.markdown(f"**Target:** ${opp['target_price']:,.2f}")
                else:
                    st.info("Waiting for entry signal")
            
            with col3:
                st.metric("R:R Ratio", f"{opp['rr_ratio']:.1f}")
                if opp.get("divergence"):
                    st.warning(f"⚠️ Divergence: {opp['divergence']}")
            
            if opp.get("patterns"):
                st.markdown("**Patterns Detected:**")
                for pattern in opp["patterns"]:
                    st.markdown(f"- {pattern}")
            
            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "📈 Analyze Pair",
                    key=f"analyze_{opp['pair']}_{i}",
                    use_container_width=True,
                ):
                    st.session_state.selected_mtf_pair = opp["pair"]
                    _display_pair_analysis(opp)
            
            with col2:
                if st.button(
                    "🔔 Set Alert",
                    key=f"alert_{opp['pair']}_{i}",
                    use_container_width=True,
                ):
                    st.info(f"Alert setup for {opp['pair']} - Coming in Session 5")


def _display_pair_analysis(opportunity: Dict[str, Any]):
    """
    Display detailed analysis for a single pair.
    
    Args:
        opportunity: Opportunity dictionary.
    """
    st.subheader(f"📊 {opportunity['pair']} - Detailed Analysis")
    
    # MTF Breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📈 Higher Timeframe (Bias)")
        st.markdown(f"**Direction:** {opportunity['htf_bias']}")
        st.markdown("**Tools:** 50/200 SMA, Price Structure")
        st.caption("Determines overall trend direction")
    
    with col2:
        st.markdown("#### 📊 Middle Timeframe (Setup)")
        st.markdown(f"**Setup:** {opportunity['mtf_setup']}")
        st.markdown("**Tools:** 20/50 SMA, RSI Divergence")
        st.caption("Identifies tradeable pattern")
    
    with col3:
        st.markdown("#### 📉 Lower Timeframe (Entry)")
        st.markdown(f"**Signal:** {opportunity['ltf_entry']}")
        st.markdown("**Tools:** 20 EMA, Candlestick Patterns")
        st.caption("Precise entry timing")
    
    st.divider()
    
    # Trade Parameters
    if opportunity["entry_price"]:
        st.markdown("#### 💰 Trade Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Entry Price", f"${opportunity['entry_price']:,.2f}")
        
        with col2:
            st.metric("Stop Loss", f"${opportunity['stop_loss']:,.2f}")
            risk = opportunity["entry_price"] - opportunity["stop_loss"]
            st.caption(f"Risk: ${risk:,.2f} per unit")
        
        with col3:
            st.metric("Target", f"${opportunity['target_price']:,.2f}")
            reward = opportunity["target_price"] - opportunity["entry_price"]
            st.caption(f"Reward: ${reward:,.2f} per unit")
        
        st.progress(min(1.0, opportunity["rr_ratio"] / 5.0))
        st.caption(f"R:R Ratio: {opportunity['rr_ratio']:.1f}:1")


# =============================================================================
# Watchlist Management
# =============================================================================


def _display_watchlist_management():
    """
    Show the current watchlist and controls to add/remove pairs.

    Calls:
      GET    /mtf/watchlist          — list pairs
      POST   /mtf/watchlist          — add pair
      DELETE /mtf/watchlist/{pair}   — remove pair
    """
    base_url = _get_api_base_url()
    headers = _get_api_headers()

    # Fetch current watchlist
    try:
        resp = requests.get(f"{base_url}/mtf/watchlist", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        watchlist = data.get("watchlist", [])
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API.")
        return
    except Exception as exc:
        st.error(f"Failed to load watchlist: {exc}")
        return

    # Display current pairs with remove buttons
    if watchlist:
        st.markdown(f"**{len(watchlist)} pair(s) in watchlist:**")
        for item in watchlist:
            pair = item["pair"] if isinstance(item, dict) else item
            col_pair, col_remove = st.columns([4, 1])
            with col_pair:
                st.write(pair)
            with col_remove:
                if st.button("Remove", key=f"wl_remove_{pair}"):
                    try:
                        r = requests.delete(
                            f"{base_url}/mtf/watchlist/{pair}",
                            headers=headers,
                            timeout=10,
                        )
                        r.raise_for_status()
                        st.success(f"Removed {pair}")
                        st.rerun()
                    except requests.exceptions.HTTPError as exc:
                        st.error(f"Error: {exc.response.text[:200]}")
                    except Exception as exc:
                        st.error(f"Error: {exc}")
    else:
        st.info("Watchlist is empty. Add pairs below.")

    st.divider()

    # Add new pair
    col_input, col_add = st.columns([3, 1])
    with col_input:
        new_pair = st.text_input(
            "Add pair",
            placeholder="e.g. SOL/USDT",
            label_visibility="collapsed",
            key="wl_new_pair",
        )
    with col_add:
        if st.button("Add", use_container_width=True, key="wl_add_btn"):
            if new_pair.strip():
                try:
                    r = requests.post(
                        f"{base_url}/mtf/watchlist",
                        json={"pair": new_pair.strip()},
                        headers=headers,
                        timeout=10,
                    )
                    r.raise_for_status()
                    st.success(f"Added {new_pair.strip().upper()}")
                    st.rerun()
                except requests.exceptions.HTTPError as exc:
                    st.error(f"Error: {exc.response.text[:200]}")
                except Exception as exc:
                    st.error(f"Error: {exc}")
            else:
                st.warning("Enter a pair symbol first.")
