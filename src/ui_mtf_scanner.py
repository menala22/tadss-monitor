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
        override = st.session_state.api_base_url_override
        if override and "VM_EXTERNAL_IP" not in override:
            return override
        del st.session_state.api_base_url_override

    url = os.getenv("API_BASE_URL", "")
    if url and "VM_EXTERNAL_IP" not in url:
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
                        if k == "API_BASE_URL" and v and not v.startswith("your_") and "VM_EXTERNAL_IP" not in v:
                            return v
                        if k == "VM_EXTERNAL_IP" and v and "VM_EXTERNAL_IP" not in v:
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
    col1, col2, col3, col4 = st.columns(4)

    # Use weighted_score (0.0-1.0) - consistent with MTF Opportunities page
    high_conviction = sum(1 for r in results if r.get("weighted_score", 0) >= 0.75)
    good_quality = sum(1 for r in results if 0.60 <= r.get("weighted_score", 0) < 0.75)
    buy_signals = sum(1 for r in results if r["recommendation"] == "BUY")
    sell_signals = sum(1 for r in results if r["recommendation"] == "SELL")

    with col1:
        st.metric("High Conviction (≥0.75)", high_conviction)
    with col2:
        st.metric("Good Quality (0.60-0.74)", good_quality)
    with col3:
        st.metric("Buy Signals", buy_signals)
    with col4:
        st.metric("Sell Signals", sell_signals)
    
    st.divider()
    
    # Display opportunities as expandable cards
    for i, opp in enumerate(results):
        # Use weighted_score for quality display - consistent with MTF Opportunities page
        weighted = opp.get("weighted_score", 0)
        if weighted >= 0.75:
            quality_emoji = "🟢 HIGHEST"
        elif weighted >= 0.60:
            quality_emoji = "🟡 GOOD"
        elif weighted >= 0.50:
            quality_emoji = "🟠 MODERATE"
        else:
            quality_emoji = "🔴 AVOID"

        # Get context from notes or use recommendation as fallback
        context = opp.get("mtf_context", "N/A")
        context_emoji = {
            "TRENDING_PULLBACK": "📈",
            "TRENDING_EXTENSION": "⏳",
            "BREAKING_OUT": "🚀",
            "CONSOLIDATING": "↔️",
            "REVERSING": "🔄",
        }.get(context, "📊")

        with st.expander(
            f"{quality_emoji} {context_emoji} **{opp['pair']}** - {opp['recommendation']} (Weighted: {weighted:.2f})",
            expanded=(i == 0),  # Expand first by default
        ):
            # 4-Layer Framework Display
            st.markdown("#### 🏗️ 4-Layer Framework Analysis")
            
            layer_cols = st.columns(4)
            
            # HTF Bias
            with layer_cols[0]:
                st.markdown("**HTF Bias**")
                htf = opp.get("htf_bias", "N/A")
                htf_emoji = "🟢" if htf == "BULLISH" else ("🔴" if htf == "BEARISH" else "⚪")
                st.markdown(f"{htf_emoji} {htf}")
            
            # Layer 1: Context
            with layer_cols[1]:
                st.markdown("**Layer 1: Context**")
                st.markdown(f"{context_emoji} {context}")
                if opp.get("context_adx"):
                    st.caption(f"ADX: {opp['context_adx']:.1f}")
            
            # Layer 3: Pullback Quality
            with layer_cols[2]:
                st.markdown("**Layer 3: Pullback Quality**")
                pq = opp.get("pullback_quality", {})
                if not pq:
                    pq_score = opp.get("pullback_quality_score")
                    if pq_score:
                        st.markdown(f"**{pq_score:.2f}/1.00**")
                elif pq.get("total_score"):
                    st.markdown(f"**{pq['total_score']:.2f}/1.00**")
            
            # Layer 4: Weighted Alignment
            with layer_cols[3]:
                st.markdown("**Layer 4: Weighted Alignment**")
                st.markdown(f"**{weighted:.2f}**")
                st.caption(f"{weighted:.0%} confidence")
                # Show position size recommendation
                if opp.get("position_size_pct"):
                    st.caption(f"Position: {opp['position_size_pct']:.0f}%")
            
            st.divider()
            
            # Trade setup details
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Setup:** {opp.get('mtf_setup', 'N/A')}")
                st.markdown(f"**Entry:** {opp['entry_price']:,.2f}" if opp.get("entry_price") else "**Entry:** Waiting")

            with col2:
                st.markdown(f"**LTF Signal:** {opp.get('ltf_entry', 'N/A')}")
                st.markdown(f"**Stop:** {opp['stop_loss']:,.2f}" if opp.get("stop_loss") else "**Stop:** N/A")

            with col3:
                st.metric("R:R Ratio", f"{opp['rr_ratio']:.1f}:1")
                if opp.get("target_price"):
                    st.markdown(f"**Target:** ${opp['target_price']:,.2f}")

            if opp.get("patterns"):
                st.markdown("**Patterns Detected:**")
                for pattern in opp["patterns"]:
                    st.markdown(f"- {pattern}")
            
            if opp.get("divergence"):
                st.warning(f"⚠️ Divergence: {opp['divergence']}")

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "📈 Save to Opportunities",
                    key=f"save_{opp['pair']}_{i}",
                    use_container_width=True,
                ):
                    st.info(f"Saving {opp['pair']} - Feature coming soon")

            with col2:
                if st.button(
                    "🔔 Set Alert",
                    key=f"alert_{opp['pair']}_{i}",
                    use_container_width=True,
                ):
                    st.info(f"Alert setup for {opp['pair']} - Coming soon")


def _display_pair_analysis(opportunity: Dict[str, Any]):
    """
    Display detailed analysis for a single pair with 4-layer framework.

    Args:
        opportunity: Opportunity dictionary.
    """
    st.subheader(f"📊 {opportunity['pair']} - Detailed 4-Layer Analysis")

    # Top metrics
    weighted = opportunity.get("weighted_score", 0)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Weighted Score", f"{weighted:.2f}")
    
    with col2:
        if opportunity.get("position_size_pct"):
            st.metric("Position Size", f"{opportunity['position_size_pct']:.0f}%")
    
    with col3:
        st.metric("R:R Ratio", f"{opportunity['rr_ratio']:.1f}:1")
    
    with col4:
        quality = "HIGHEST" if weighted >= 0.75 else ("GOOD" if weighted >= 0.60 else ("MODERATE" if weighted >= 0.50 else "AVOID"))
        st.metric("Quality", quality)

    st.divider()

    # 4-Layer Framework Breakdown
    st.markdown("#### 🏗️ 4-Layer Framework")

    layer_cols = st.columns(4)

    with layer_cols[0]:
        st.markdown("**HTF Bias (Trend)**")
        htf_bias = opportunity.get("htf_bias", "N/A")
        htf_emoji = "🟢" if htf_bias == "BULLISH" else ("🔴" if htf_bias == "BEARISH" else "⚪")
        st.markdown(f"{htf_emoji} {htf_bias}")

    with layer_cols[1]:
        st.markdown("**Layer 1: Context**")
        context = opportunity.get("mtf_context", opportunity.get("context", "N/A"))
        context_emoji = {
            "TRENDING_PULLBACK": "📈",
            "TRENDING_EXTENSION": "⏳",
            "BREAKING_OUT": "🚀",
            "CONSOLIDATING": "↔️",
            "REVERSING": "🔄",
        }.get(context, "📊")
        st.markdown(f"{context_emoji} {context}")

    with layer_cols[2]:
        st.markdown("**Layer 3: Pullback Quality**")
        pq = opportunity.get("pullback_quality", {})
        if pq and pq.get("total_score"):
            st.markdown(f"**{pq['total_score']:.2f}/1.00**")
        else:
            pq_score = opportunity.get("pullback_quality_score")
            if pq_score:
                st.markdown(f"**{pq_score:.2f}/1.00**")
            else:
                st.markdown("N/A")

    with layer_cols[3]:
        st.markdown("**Layer 4: Weighted**")
        st.markdown(f"**{weighted:.2f}**")

    st.divider()

    # Trade Parameters
    st.markdown("#### 💰 Trade Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        if opportunity.get("entry_price"):
            st.metric("Entry Price", f"${opportunity['entry_price']:,.2f}")

    with col2:
        if opportunity.get("stop_loss"):
            st.metric("Stop Loss", f"${opportunity['stop_loss']:,.2f}")
            risk = opportunity["entry_price"] - opportunity["stop_loss"]
            st.caption(f"Risk: ${risk:,.2f} per unit")

    with col3:
        if opportunity.get("target_price"):
            st.metric("Target", f"${opportunity['target_price']:,.2f}")
            reward = opportunity["target_price"] - opportunity["entry_price"]
            st.caption(f"Reward: ${reward:,.2f} per unit")

    if opportunity.get("rr_ratio"):
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
