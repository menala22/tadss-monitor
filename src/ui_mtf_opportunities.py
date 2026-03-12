"""
MTF Opportunities Dashboard Page for TA-DSS.

Streamlit component for displaying MTF trading opportunities identified by the
hourly automated scanning system.

Features:
- Filter panel (pair, context, weighted score, status)
- Opportunities table with quality badges
- Detail view with 4-layer framework breakdown
- Statistics cards
- Action buttons (close, delete)

Usage:
    from src.ui_mtf_opportunities import render_mtf_opportunities_page

    # In main ui.py
    if page == "💼 MTF Opportunities":
        render_mtf_opportunities_page()
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

logger = logging.getLogger(__name__)


# =============================================================================
# API Configuration
# =============================================================================


def _get_api_base_url() -> str:
    """Get API base URL from environment or .env file."""
    if hasattr(st, "session_state") and "api_base_url_override" in st.session_state:
        override = st.session_state.api_base_url_override
        if override and "VM_EXTERNAL_IP" not in override:
            return override
        del st.session_state.api_base_url_override

    url = os.getenv("API_BASE_URL", "")
    if url and "VM_EXTERNAL_IP" not in url:
        return url

    # Try .env file
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
    """Get auth headers for API requests."""
    key = os.getenv("API_SECRET_KEY", "")

    if not key:
        env_paths = [
            Path(__file__).parent.parent / ".env",
            Path(__file__).parent / ".env",
            Path.cwd() / ".env",
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


# =============================================================================
# Main Page Render
# =============================================================================


def render_mtf_opportunities_page():
    """
    Render the MTF Opportunities dashboard page.

    Features:
    - Statistics cards
    - Filter panel
    - Opportunities table
    - Detail view (expandable)
    """
    st.title("💼 MTF Current Opportunities")
    st.caption("Automated MTF Scanning - Updated hourly at :30")

    # Initialize session state
    if "mtf_opp_filters" not in st.session_state:
        st.session_state.mtf_opp_filters = {
            "status": "ACTIVE",
            "min_weighted_score": 0.60,
            "mtf_context": None,
            "htf_bias": None,
            "pair": None,
        }
    if "mtf_opp_results" not in st.session_state:
        st.session_state.mtf_opp_results = None
    if "mtf_opp_last_refresh" not in st.session_state:
        st.session_state.mtf_opp_last_refresh = None

    # ========================================================================
    # Statistics Cards
    # ========================================================================

    st.subheader("📊 Overview")

    stats_cols = st.columns(4)

    # Fetch statistics
    try:
        stats_response = requests.get(
            f"{_get_api_base_url()}/mtf-opportunities/stats",
            headers=_get_api_headers(),
            timeout=10,
        )
        if stats_response.status_code == 200:
            stats_data = stats_response.json().get("statistics", {})

            with stats_cols[0]:
                st.metric(
                    "Active Opportunities",
                    stats_data.get("by_status", {}).get("active", 0),
                )

            with stats_cols[1]:
                high_conviction = stats_data.get("high_conviction", 0)
                st.metric("High Conviction (≥0.75)", high_conviction)

            with stats_cols[2]:
                buy_signals = stats_data.get("by_recommendation", {}).get("buy_signals", 0)
                sell_signals = stats_data.get("by_recommendation", {}).get("sell_signals", 0)
                st.metric("Buy / Sell Signals", f"{buy_signals} / {sell_signals}")

            with stats_cols[3]:
                today_count = stats_data.get("today_count", 0)
                st.metric("Today's Opportunities", today_count)

        else:
            logger.warning(f"Failed to fetch stats: {stats_response.status_code}")
            for col in stats_cols:
                col.metric("N/A", "-")

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        for col in stats_cols:
            col.metric("Error", "-")

    st.divider()

    # ========================================================================
    # Filter Panel
    # ========================================================================

    st.subheader("🎛️ Filters")

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)

    with filter_col1:
        status_filter = st.selectbox(
            "Status",
            options=["ACTIVE", "CLOSED", "EXPIRED", "ALL"],
            index=0,
            key="mtf_opp_status_filter",
        )

    with filter_col2:
        min_weighted = st.slider(
            "Min Weighted Score",
            min_value=0.0,
            max_value=1.0,
            value=0.60,
            step=0.05,
            key="mtf_opp_min_weighted",
            help="Minimum confidence score (0.0-1.0)"
        )

    with filter_col3:
        context_filter = st.selectbox(
            "MTF Context",
            options=["ALL", "TRENDING_PULLBACK", "BREAKING_OUT", "REVERSING", "CONSOLIDATING"],
            index=0,
            key="mtf_opp_context_filter",
        )

    with filter_col4:
        bias_filter = st.selectbox(
            "HTF Bias",
            options=["ALL", "BULLISH", "BEARISH"],
            index=0,
            key="mtf_opp_bias_filter",
        )

    with filter_col5:
        pair_search = st.text_input(
            "Pair Search",
            placeholder="e.g. BTC",
            key="mtf_opp_pair_search",
            help="Search by pair symbol"
        )

    # Apply button
    filter_cols = st.columns([4, 1])
    with filter_cols[1]:
        apply_filters = st.button("🔍 Apply Filters", use_container_width=True, type="primary")

    # Update session state
    if apply_filters or st.session_state.mtf_opp_results is None:
        st.session_state.mtf_opp_filters = {
            "status": status_filter if status_filter != "ALL" else None,
            "min_weighted_score": min_weighted,
            "mtf_context": context_filter if context_filter != "ALL" else None,
            "htf_bias": bias_filter if bias_filter != "ALL" else None,
            "pair": pair_search if pair_search else None,
        }
        st.session_state.mtf_opp_results = None  # Trigger refresh

    # ========================================================================
    # Fetch and Display Opportunities
    # ========================================================================

    if st.session_state.mtf_opp_results is None:
        with st.spinner("Loading opportunities..."):
            try:
                # Build query parameters
                params = {
                    "limit": 100,
                }

                if st.session_state.mtf_opp_filters["status"]:
                    params["status"] = st.session_state.mtf_opp_filters["status"]

                if st.session_state.mtf_opp_filters["min_weighted_score"]:
                    params["min_weighted_score"] = st.session_state.mtf_opp_filters["min_weighted_score"]

                if st.session_state.mtf_opp_filters["mtf_context"]:
                    params["mtf_context"] = st.session_state.mtf_opp_filters["mtf_context"]

                if st.session_state.mtf_opp_filters["htf_bias"]:
                    params["htf_bias"] = st.session_state.mtf_opp_filters["htf_bias"]

                if st.session_state.mtf_opp_filters["pair"]:
                    params["pair"] = st.session_state.mtf_opp_filters["pair"]

                # Fetch opportunities
                response = requests.get(
                    f"{_get_api_base_url()}/mtf-opportunities",
                    params=params,
                    headers=_get_api_headers(),
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()
                
                # Extract opportunities from response
                # API returns: {"opportunities": [...], "pagination": {...}, "filters": {...}}
                if isinstance(data, dict) and "opportunities" in data:
                    st.session_state.mtf_opp_results = data.get("opportunities", [])
                elif isinstance(data, list):
                    # Fallback if API returns list directly
                    st.session_state.mtf_opp_results = data
                else:
                    st.error(f"Unexpected API response format: {type(data)}")
                    st.session_state.mtf_opp_results = []
                
                st.session_state.mtf_opp_last_refresh = datetime.utcnow()

            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
                st.session_state.mtf_opp_results = []
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Check that the server is running.")
                st.session_state.mtf_opp_results = []
            except Exception as e:
                st.error(f"Error loading opportunities: {e}")
                st.session_state.mtf_opp_results = []

    # Display results
    if st.session_state.mtf_opp_results is not None:
        # Show debug info at the top
        st.info(f"📊 Loaded {len(st.session_state.mtf_opp_results)} opportunities from API")
        
        if len(st.session_state.mtf_opp_results) > 0:
            # Show first opportunity as JSON for debugging
            with st.expander("🐛 DEBUG: Click to see raw API data"):
                st.write("**First opportunity from API:**")
                st.json(st.session_state.mtf_opp_results[0])
            
            _display_opportunities_table(st.session_state.mtf_opp_results)
        else:
            st.warning("No opportunities found. Try lowering the filters or wait for next scan at :30")
    else:
        _display_no_opportunities()

    # ========================================================================
    # Last Refresh Info
    # ========================================================================

    if st.session_state.mtf_opp_last_refresh:
        st.divider()
        st.caption(
            f"🕐 Last refresh: {st.session_state.mtf_opp_last_refresh.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        st.caption("💡 Data refreshes automatically every hour at :30")


# =============================================================================
# Opportunities Table Display
# =============================================================================


def _display_opportunities_table(opportunities: List[Dict[str, Any]]):
    """
    Display opportunities in a table with quality badges.

    Args:
        opportunities: List of opportunity dictionaries.
    """
    st.subheader(f"📋 Opportunities ({len(opportunities)} found)")

    if not opportunities:
        st.info("No opportunities found matching your filters.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(opportunities)

    # Quality badge mapping
    def get_quality_badge(weighted_score):
        if weighted_score >= 0.75:
            return "🟢 HIGHEST"
        elif weighted_score >= 0.60:
            return "🟡 GOOD"
        elif weighted_score >= 0.50:
            return "🟠 MODERATE"
        else:
            return "🔴 AVOID"

    def get_context_emoji(context):
        emojis = {
            "TRENDING_PULLBACK": "📈",
            "TRENDING_EXTENSION": "⏳",
            "BREAKING_OUT": "🚀",
            "CONSOLIDATING": "↔️",
            "REVERSING": "🔄",
        }
        return emojis.get(context, "📊")

    # Add badges
    df["Quality"] = df["weighted_score"].apply(get_quality_badge)
    df["Context_Display"] = df["mtf_context"].apply(lambda x: f"{get_context_emoji(x)} {x}")

    # Recommendation emoji
    def get_rec_emoji(rec):
        return "🟢" if rec == "BUY" else ("🔴" if rec == "SELL" else "⚪")

    df["Rec_Display"] = df["recommendation"].apply(lambda x: f"{get_rec_emoji(x)} {x}")

    # Display table with selected columns
    display_cols = [
        "id",
        "pair",
        "trading_style",
        "Quality",
        "htf_bias",
        "Context_Display",
        "Rec_Display",
        "weighted_score",
        "position_size_pct",
        "entry_price",
        "entry_timestamp",
        "rr_ratio",
        "status",
    ]

    # Rename for display
    rename_map = {
        "htf_bias": "HTF Bias",
        "Context_Display": "MidTF Context",
        "Rec_Display": "Recommendation",
        "trading_style": "Style",
        "weighted_score": "Weighted",
        "position_size_pct": "Position %",
        "entry_price": "Entry",
        "entry_timestamp": "Entry Time",
        "rr_ratio": "R:R",
    }

    display_df = df[[c for c in display_cols if c in df.columns]].copy()
    display_df = display_df.rename(columns=rename_map)

    # Sort by entry_timestamp descending (newest first)
    if "Entry Time" in display_df.columns:
        display_df = display_df.sort_values("Entry Time", ascending=False, na_position="last")

    # Format numbers
    if "Weighted" in display_df.columns:
        display_df["Weighted"] = display_df["Weighted"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")

    if "Position %" in display_df.columns:
        display_df["Position %"] = display_df["Position %"].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else "-")

    # Format Entry price: 5 decimals for forex pairs, 2 decimals for others
    def format_price(price, pair_str):
        """Format price with 5 decimals for forex pairs, 2 for others."""
        if pd.isna(price):
            return "-"
        # Forex pairs: contain EUR, GBP, JPY, CHF, CAD, AUD, NZD (not USD - too common in commodities)
        forex_keywords = ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
        pair_upper = pair_str.upper() if pair_str else ""
        is_forex = any(kw in pair_upper for kw in forex_keywords)
        if is_forex:
            return f"${price:,.5f}"
        else:
            return f"${price:,.2f}"

    # Use raw entry_price column from df (before renaming) for formatting
    if "entry_price" in df.columns and "pair" in df.columns:
        display_df["Entry"] = df.apply(
            lambda row: format_price(row["entry_price"], row["pair"]),
            axis=1
        )

    if "R:R" in display_df.columns:
        display_df["R:R"] = display_df["R:R"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")

    # Format Entry Time as readable datetime
    if "Entry Time" in display_df.columns:
        def format_timestamp(ts):
            if pd.isna(ts) or ts is None:
                return "-"
            try:
                from datetime import datetime
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return ts.strftime("%m-%d %H:%M")
            except Exception:
                return "-"
        display_df["Entry Time"] = display_df["Entry Time"].apply(format_timestamp)

    # Display as interactive table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", format="%d"),
            "pair": st.column_config.TextColumn("Pair"),
            "Style": st.column_config.TextColumn("Style"),
            "Quality": st.column_config.TextColumn("Quality"),
            "HTF Bias": st.column_config.TextColumn("HTF Bias"),
            "MidTF Context": st.column_config.TextColumn("MidTF Context"),
            "Recommendation": st.column_config.TextColumn("Rec"),
            "Weighted": st.column_config.TextColumn("Weighted"),
            "Position %": st.column_config.TextColumn("Position"),
            "Entry": st.column_config.TextColumn("Entry"),
            "Entry Time": st.column_config.TextColumn("Entry Time"),
            "R:R": st.column_config.TextColumn("R:R"),
            "status": st.column_config.TextColumn("Status"),
        },
    )

    # Detail view
    st.divider()
    st.subheader("🔍 Opportunity Details")

    # Select opportunity to view
    opportunity_ids = [int(op["id"]) for op in opportunities]
    selected_id = st.selectbox(
        "Select opportunity to view details:",
        options=opportunity_ids,
        format_func=lambda x: f"ID {x} - {next(op['pair'] for op in opportunities if op['id'] == x)}",
        key="mtf_opp_detail_select",
    )

    if selected_id:
        selected_opp = next((op for op in opportunities if op["id"] == selected_id), None)
        if selected_opp:
            _display_opportunity_detail(selected_opp)


def _display_opportunity_detail(opportunity: Dict[str, Any]):
    """
    Display detailed view of a single opportunity.

    Args:
        opportunity: Opportunity dictionary.
    """
    st.markdown(f"### {opportunity['pair']} - ID {opportunity['id']}")

    # Top row: Key metrics
    col1, col2, col3, col4 = st.columns(4)

    # Calculate quality from weighted_score (new framework - consistent with table)
    weighted = opportunity.get("weighted_score")
    if weighted:
        if weighted >= 0.75:
            quality_display = "🟢 HIGHEST"
        elif weighted >= 0.60:
            quality_display = "🟡 GOOD"
        elif weighted >= 0.50:
            quality_display = "🟠 MODERATE"
        else:
            quality_display = "🔴 AVOID"
    else:
        quality_display = "⚪ N/A"

    with col1:
        st.metric("Quality", quality_display)

    with col2:
        st.metric("Weighted Score", f"{weighted:.2f}" if weighted else "N/A")

    with col3:
        position = opportunity.get("position_size_pct")
        st.metric("Position Size", f"{position:.0f}%" if position else "N/A")

    with col4:
        st.metric("Status", opportunity.get("status", "N/A"))

    st.divider()

    # 4-Layer Framework Breakdown
    st.markdown("#### 🏗️ 4-Layer Framework Analysis")

    layer_cols = st.columns(4)

    # HTF Bias
    with layer_cols[0]:
        st.markdown("**HTF Bias (Trend)**")
        htf_bias = opportunity.get("htf_bias", "N/A")
        htf_emoji = "🟢" if htf_bias == "BULLISH" else ("🔴" if htf_bias == "BEARISH" else "⚪")
        st.markdown(f"{htf_emoji} {htf_bias}")

        # Price Structure and Confidence (derived from alignment)
        # Note: price_structure is not stored in DB, but we can show weighted alignment as confidence
        weighted = opportunity.get("weighted_score")
        if weighted:
            confidence_pct = round(weighted * 100)
            st.caption(f"Confidence: {confidence_pct}%")
        
        # Show structure based on HTF bias + context combination
        context = opportunity.get("mtf_context", "")
        if htf_bias == "BULLISH":
            if context in ["TRENDING_PULLBACK", "TRENDING_EXTENSION"]:
                structure_display = "HH/HL (Uptrend)"
            elif context == "REVERSING":
                structure_display = "Potential Reversal"
            else:
                structure_display = "Consolidating"
        elif htf_bias == "BEARISH":
            if context in ["TRENDING_PULLBACK", "TRENDING_EXTENSION"]:
                structure_display = "LH/LL (Downtrend)"
            elif context == "REVERSING":
                structure_display = "Potential Reversal"
            else:
                structure_display = "Consolidating"
        else:
            structure_display = "RANGE"
        
        st.caption(f"Structure: {structure_display}")

    # Layer 1: Context
    with layer_cols[1]:
        st.markdown("**Layer 1: Context**")
        context = opportunity.get("mtf_context", "N/A")
        context_emoji = {
            "TRENDING_PULLBACK": "📈",
            "TRENDING_EXTENSION": "⏳",
            "BREAKING_OUT": "🚀",
            "CONSOLIDATING": "↔️",
            "REVERSING": "🔄",
        }.get(context, "📊")
        st.markdown(f"{context_emoji} {context}")

        # Context metrics
        context_adx = opportunity.get("context_adx")
        context_dist = opportunity.get("context_distance_atr")
        if context_adx:
            st.caption(f"ADX: {context_adx:.1f}")
        if context_dist:
            st.caption(f"Distance: {context_dist:.2f} ATR")

    # Layer 3: Pullback Quality
    with layer_cols[2]:
        st.markdown("**Layer 3: Pullback Quality**")
        
        # Try nested structure first (from to_dict)
        pullback_quality = opportunity.get("pullback_quality", {})
        
        # If nested is empty or None, try flat structure (from API summary)
        if not pullback_quality or not isinstance(pullback_quality, dict):
            pullback_quality = {
                "total_score": opportunity.get("pullback_quality_score"),
                "distance_score": opportunity.get("pullback_distance_score"),
                "rsi_score": opportunity.get("pullback_rsi_score"),
                "volume_score": opportunity.get("pullback_volume_score"),
                "confluence_score": opportunity.get("pullback_confluence_score"),
                "structure_score": opportunity.get("pullback_structure_score"),
            }
        
        # Display if we have data
        if pullback_quality and pullback_quality.get("total_score") is not None:
            total = pullback_quality["total_score"]
            if total > 0:
                st.markdown(f"**{total:.2f}/1.00**")
                
                # Show breakdown in caption
                breakdown = []
                if pullback_quality.get("distance_score"):
                    breakdown.append(f"Dist: {pullback_quality['distance_score']:.2f}")
                if pullback_quality.get("rsi_score"):
                    breakdown.append(f"RSI: {pullback_quality['rsi_score']:.2f}")
                if pullback_quality.get("volume_score"):
                    breakdown.append(f"Vol: {pullback_quality['volume_score']:.2f}")
                if pullback_quality.get("confluence_score"):
                    breakdown.append(f"Conf: {pullback_quality['confluence_score']:.2f}")
                if pullback_quality.get("structure_score"):
                    breakdown.append(f"Struct: {pullback_quality['structure_score']:.2f}")
                
                if breakdown:
                    st.caption(" • ".join(breakdown))
            else:
                st.markdown("N/A")
        else:
            st.markdown("N/A")

    # Layer 4: Weighted Alignment
    with layer_cols[3]:
        st.markdown("**Layer 4: Weighted**")
        weighted = opportunity.get("weighted_score")
        if weighted:
            st.markdown(f"**{weighted:.2f}**")
            st.caption(f"{weighted:.0%} confidence")
        else:
            st.markdown("N/A")

    st.divider()

    # Trade Parameters
    st.markdown("#### 💰 Trade Parameters")

    trade_cols = st.columns(4)

    # Helper function for forex price formatting
    def format_price_detail(price, pair_str):
        """Format price with 5 decimals for forex pairs, 2 for others."""
        if price is None:
            return "N/A"
        # Forex pairs: contain EUR, GBP, JPY, CHF, CAD, AUD, NZD (not USD - too common in commodities)
        forex_keywords = ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
        pair_upper = pair_str.upper() if pair_str else ""
        is_forex = any(kw in pair_upper for kw in forex_keywords)
        if is_forex:
            return f"${price:,.5f}"
        else:
            return f"${price:,.2f}"

    pair_str = opportunity.get("pair", "")

    with trade_cols[0]:
        entry = opportunity.get("entry_price")
        st.metric("Entry Price", format_price_detail(entry, pair_str))
        
        # Display entry timestamp if available (LTF confirmation candle)
        entry_timestamp = opportunity.get("entry_timestamp")
        if entry_timestamp:
            try:
                from datetime import datetime, timezone
                ts = datetime.fromisoformat(entry_timestamp.replace("Z", "+00:00"))
                st.caption(f"🕐 Signal: {ts.strftime('%Y-%m-%d %H:%M UTC')}")
            except Exception:
                pass

    with trade_cols[1]:
        stop = opportunity.get("stop_loss")
        st.metric("Stop Loss", format_price_detail(stop, pair_str))

    with trade_cols[2]:
        target = opportunity.get("target_price")
        target_method = opportunity.get("target_method", "N/A")
        st.metric("Target Price", format_price_detail(target, pair_str))
        if target_method and target_method != "N/A":
            st.caption(f"Method: {target_method}")

    with trade_cols[3]:
        rr = opportunity.get("rr_ratio")
        st.metric("R:R Ratio", f"{rr:.1f}:1" if rr else "N/A")

    # Risk calculation
    if opportunity.get("entry_price") and opportunity.get("stop_loss"):
        risk = abs(opportunity["entry_price"] - opportunity["stop_loss"])
        st.caption(f"Risk per unit: {format_price_detail(risk, pair_str)}")

    st.divider()

    # Alternative Targets
    st.markdown("#### 🎯 All Target Methods")

    alt_targets = opportunity.get("alternative_targets", {})
    
    # Check if we have valid alternative targets
    has_alt_targets = alt_targets and isinstance(alt_targets, dict) and len(alt_targets) > 0
    
    if has_alt_targets:
        # Check if at least one method has valid data
        has_valid_data = any("error" not in data and data.get("target_price") for data in alt_targets.values())
        
        if has_valid_data:
            # Create table of all targets
            alt_df_data = {
                "Method": [],
                "Target Price": [],
                "R:R Ratio": [],
                "Confidence": [],
                "Description": [],
            }

            for method, data in alt_targets.items():
                if "error" not in data and data.get("target_price"):
                    alt_df_data["Method"].append(method)
                    # Use forex-aware formatting
                    alt_df_data["Target Price"].append(format_price_detail(data.get('target_price', 0), pair_str))
                    alt_df_data["R:R Ratio"].append(f"{data.get('rr_ratio', 0):.2f}:1")
                    alt_df_data["Confidence"].append(data.get('confidence', 0))
                    desc = data.get('description', '')
                    alt_df_data["Description"].append(desc[:50] + '...' if len(desc) > 50 else desc)

            if alt_df_data["Method"]:
                import pandas as pd
                alt_df = pd.DataFrame(alt_df_data)
                st.dataframe(
                    alt_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Method": st.column_config.TextColumn("Method"),
                        "Target Price": st.column_config.TextColumn("Target"),
                        "R:R Ratio": st.column_config.TextColumn("R:R"),
                        "Confidence": st.column_config.ProgressColumn(
                            "Confidence",
                            min_value=0,
                            max_value=1,
                            format="%.2f"
                        ),
                        "Description": st.column_config.TextColumn("Description"),
                    }
                )

                # Highlight best targets
                best_rr_col, best_conf_col = st.columns(2)
                with best_rr_col:
                    if alt_df_data["R:R Ratio"]:
                        best_rr_idx = max(range(len(alt_df_data["R:R Ratio"])), 
                                         key=lambda i: float(alt_df_data["R:R Ratio"][i].replace(':1', '')) if alt_df_data["R:R Ratio"][i] != "N/A" else 0)
                        st.success(f"🏆 Best R:R: **{alt_df_data['Method'][best_rr_idx]}** ({alt_df_data['R:R Ratio'][best_rr_idx]})")
                with best_conf_col:
                    if alt_df_data["Confidence"]:
                        best_conf_idx = max(range(len(alt_df_data["Confidence"])), 
                                           key=lambda i: float(alt_df_data["Confidence"][i]) if alt_df_data["Confidence"][i] else 0)
                        st.info(f"⭐ Highest Confidence: **{alt_df_data['Method'][best_conf_idx]}** ({alt_df_data['Confidence'][best_conf_idx]:.0%})")
        else:
            st.info("⚠️ Alternative targets exist but have no valid data - run new scan to recalculate")
    else:
        st.info("ℹ️ Alternative targets not available - run new scan to calculate")

    st.divider()

    # Additional Info
    st.markdown("#### 📝 Additional Information")

    info_cols = st.columns(2)

    with info_cols[0]:
        st.markdown(f"**Trading Style:** {opportunity.get('trading_style', 'N/A')}")
        st.markdown(f"**MTF Setup:** {opportunity.get('mtf_setup', 'N/A')}")
        st.markdown(f"**LTF Entry:** {opportunity.get('ltf_entry', 'N/A')}")

    with info_cols[1]:
        divergence = opportunity.get("divergence")
        if divergence:
            st.warning(f"⚠️ **Divergence:** {divergence.replace('_', ' ').title()}")
        else:
            st.info("No divergence detected")

    # Patterns
    legacy = opportunity.get("legacy_fields", {})
    patterns = opportunity.get("patterns", [])
    if patterns:
        st.markdown("**Patterns Detected:**")
        for pattern in patterns:
            st.markdown(f"- {pattern}")

    # Actions
    st.divider()
    st.markdown("#### ⚙️ Actions")

    action_cols = st.columns(3)

    with action_cols[0]:
        if st.button("🔒 Close Opportunity", use_container_width=True, key=f"close_{opportunity['id']}"):
            st.session_state.selected_opp_id = opportunity["id"]
            st.session_state.show_close_confirm = True

    with action_cols[1]:
        if st.button("🗑️ Delete Opportunity", use_container_width=True, key=f"delete_{opportunity['id']}"):
            st.session_state.selected_opp_id = opportunity["id"]
            st.session_state.show_delete_confirm = True

    with action_cols[2]:
        if st.button("📊 Refresh", use_container_width=True, key=f"refresh_{opportunity['id']}"):
            st.session_state.mtf_opp_results = None
            st.rerun()

    # Handle close/delete confirmation
    if st.session_state.get("show_close_confirm"):
        _show_close_confirmation(st.session_state.selected_opp_id)

    if st.session_state.get("show_delete_confirm"):
        _show_delete_confirmation(st.session_state.selected_opp_id)


def _show_close_confirmation(opportunity_id: int):
    """Show close confirmation dialog."""
    st.warning("⚠️ Confirm Close Opportunity")

    reason = st.selectbox(
        "Reason for closing:",
        options=["MANUAL", "TARGET_HIT", "STOP_HIT", "INVALID"],
        key=f"close_reason_{opportunity_id}",
    )

    confirm_cols = st.columns(2)

    with confirm_cols[0]:
        if st.button("Confirm Close", type="primary", key=f"confirm_close_{opportunity_id}"):
            try:
                response = requests.post(
                    f"{_get_api_base_url()}/mtf-opportunities/{opportunity_id}/close",
                    params={"reason": reason},
                    headers=_get_api_headers(),
                    timeout=10,
                )
                response.raise_for_status()

                st.success(f"Opportunity {opportunity_id} closed ({reason})")
                st.session_state.show_close_confirm = False
                st.session_state.mtf_opp_results = None  # Trigger refresh
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Failed to close: {e}")

    with confirm_cols[1]:
        if st.button("Cancel", key=f"cancel_close_{opportunity_id}"):
            st.session_state.show_close_confirm = False
            st.rerun()


def _show_delete_confirmation(opportunity_id: int):
    """Show delete confirmation dialog."""
    st.error("⚠️ Confirm Delete Opportunity")
    st.markdown("This action **cannot be undone**.")

    confirm_cols = st.columns(2)

    with confirm_cols[0]:
        if st.button("Confirm Delete", type="primary", key=f"confirm_delete_{opportunity_id}"):
            try:
                response = requests.delete(
                    f"{_get_api_base_url()}/mtf-opportunities/{opportunity_id}",
                    headers=_get_api_headers(),
                    timeout=10,
                )
                response.raise_for_status()

                st.success(f"Opportunity {opportunity_id} deleted")
                st.session_state.show_delete_confirm = False
                st.session_state.mtf_opp_results = None  # Trigger refresh
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Failed to delete: {e}")

    with confirm_cols[1]:
        if st.button("Cancel", key=f"cancel_delete_{opportunity_id}"):
            st.session_state.show_delete_confirm = False
            st.rerun()


def _display_no_opportunities():
    """Display instructions when no opportunities are found."""
    st.info("""
    ### 📭 No Opportunities Found

    No MTF opportunities match your current filters. Try:

    1. **Lowering the minimum weighted score** (currently 0.60)
    2. **Changing the status filter** to view CLOSED or EXPIRED
    3. **Removing context or bias filters**
    4. **Waiting for the next hourly scan** at :30

    ---

    #### 💡 How It Works

    The MTF system scans automatically every hour at :30 and:
    - Uses the **upgraded 4-layer MTF framework** for analysis
    - Saves opportunities meeting minimum criteria (weighted ≥ 0.50, R:R ≥ 2.0)
    - Sends Telegram alerts for high-conviction setups (weighted ≥ 0.60)
    - Auto-expires opportunities after 24 hours

    **Next scan:** Wait for the next :30 mark
    """)
