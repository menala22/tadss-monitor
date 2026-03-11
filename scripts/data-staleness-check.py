#!/usr/bin/env python3
"""
Data Staleness Check Script for TA-DSS.

Queries production VM for ohlcv_universal and mtf_opportunities table status.
Generates comprehensive report on data freshness and MTF opportunities.

Usage:
    python scripts/data-staleness-check.py [--vm-ip IP] [--api-key KEY] [--output FILE]

Options:
    --vm-ip IP          VM external IP (default: from .env or 34.171.241.166)
    --api-key KEY       API key (default: from .env)
    --output FILE       Save report to file (default: print to stdout)
    --help              Show this help message

Examples:
    # Quick check with defaults
    python scripts/data-staleness-check.py

    # Specify VM IP
    python scripts/data-staleness-check.py --vm-ip 34.171.241.166

    # Save report to file
    python scripts/data-staleness-check.py --output reports/staleness-2026-03-10.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_VM_IP = "34.171.241.166"
DEFAULT_PORT = 8000
ENV_FILE_PATH = Path(__file__).parent.parent / ".env"


def load_env_config() -> Dict[str, str]:
    """Load configuration from .env file."""
    config = {}
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


def get_vm_ip(args) -> str:
    """Get VM IP from args, env, or default."""
    if args.vm_ip:
        return args.vm_ip
    
    # Try .env file
    env_config = load_env_config()
    if "VM_EXTERNAL_IP" in env_config:
        return env_config["VM_EXTERNAL_IP"]
    
    return DEFAULT_VM_IP


def get_api_key(args) -> str:
    """Get API key from args, env, or default."""
    if args.api_key:
        return args.api_key
    
    # Try .env file
    env_config = load_env_config()
    if "API_SECRET_KEY" in env_config:
        return env_config["API_SECRET_KEY"]
    
    # Fallback to hardcoded key (for backward compatibility)
    return "da970a671d81d0d3fe0214eeb6424423da0d214daddde5c58b1dc0a46b2453aa"


# =============================================================================
# DATA FETCHING
# =============================================================================

def fetch_market_data_status(vm_ip: str, api_key: str) -> Optional[Dict]:
    """Fetch market data status from production API."""
    url = f"http://{vm_ip}:{DEFAULT_PORT}/api/v1/market-data/status"
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market data status: {e}", file=sys.stderr)
        return None


def fetch_mtf_opportunities(vm_ip: str, api_key: str, style: str = "SWING") -> Optional[Dict]:
    """Fetch MTF opportunities from production API."""
    url = f"http://{vm_ip}:{DEFAULT_PORT}/api/v1/mtf/opportunities"
    params = {"style": style, "limit": 100}
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching MTF opportunities: {e}", file=sys.stderr)
        return None


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_ohlcv_report(data: Dict) -> str:
    """Generate ohlcv_universal table report."""
    lines = []
    now = datetime.now(timezone.utc)
    
    lines.append("## OHLCV_UNIVERSAL Table Status")
    lines.append("")
    lines.append(f"**Current UTC:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Summary
    summary = data.get("summary", {})
    lines.append("### Summary")
    lines.append("")
    lines.append(f"- **Total Pairs:** {summary.get('total_pairs', 0)}")
    lines.append(f"- **By Quality:** EXCELLENT: {summary.get('by_quality', {}).get('EXCELLENT', 0)}, "
                f"GOOD: {summary.get('by_quality', {}).get('GOOD', 0)}, "
                f"STALE: {summary.get('by_quality', {}).get('STALE', 0)}, "
                f"MISSING: {summary.get('by_quality', {}).get('MISSING', 0)}")
    lines.append(f"- **MTF Ready:** {summary.get('mtf_ready', 0)} pairs")
    lines.append("")
    
    # Group by symbol for better readability
    by_symbol = {}
    for pair_name, pair_data in data.get("pairs", {}).items():
        if pair_name not in by_symbol:
            by_symbol[pair_name] = []
        for tf, tf_data in pair_data.get("timeframes", {}).items():
            latest_dt = datetime.fromisoformat(tf_data["last_candle_time"])
            fetched_dt = datetime.fromisoformat(tf_data["fetched_at"])
            
            # Age = hours since candle closed (not when we fetched it!)
            candle_age_hours = (now - latest_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            fetch_age_hours = (now - fetched_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            
            # Get data source
            source = tf_data.get("source", "unknown")
            
            by_symbol[pair_name].append({
                "timeframe": tf,
                "count": tf_data["candle_count"],
                "latest": latest_dt.strftime("%Y-%m-%d %H:%M"),
                "candle_age_hours": candle_age_hours,
                "fetch_age_hours": fetch_age_hours,
                "source": source,
                "quality": tf_data["quality"],
            })
    
    # Generate table
    lines.append("### Data by Pair")
    lines.append("")
    lines.append("| Symbol | TF | Candles | Latest Candle | Candle Age (h) | Source | Quality |")
    lines.append("|--------|-----|---------|---------------|----------------|--------|---------|")
    
    for symbol in sorted(by_symbol.keys()):
        rows = by_symbol[symbol]
        # Sort by timeframe priority (h1, h4, d1, w1)
        tf_order = {"h1": 0, "h4": 1, "d1": 2, "w1": 3}
        rows.sort(key=lambda x: tf_order.get(x["timeframe"], 99))
        
        for i, row in enumerate(rows):
            quality_icon = {"EXCELLENT": "✅", "GOOD": "⚠️", "STALE": "❌", "MISSING": "🔴"}.get(row["quality"], "")
            source_icon = {"ccxt": "🔵", "twelvedata": "🟣", "gateio": "🟢"}.get(row["source"].lower(), "⚪")
            symbol_display = symbol if i == 0 else ""
            lines.append(f"| {symbol_display:<10} | {row['timeframe']:<4} | {row['count']:<7} | {row['latest']:<13} | {row['candle_age_hours']:<14.1f} | {source_icon} {row['source']} | {quality_icon} {row['quality']} |")
    
    lines.append("")
    
    # Summary by quality
    quality_counts = {}
    for symbol, rows in by_symbol.items():
        for row in rows:
            q = row["quality"]
            quality_counts[q] = quality_counts.get(q, 0) + 1
    
    lines.append("### Quality Distribution")
    lines.append("")
    lines.append("| Quality | Count |")
    lines.append("|---------|-------|")
    for q in ["EXCELLENT", "GOOD", "STALE", "MISSING"]:
        count = quality_counts.get(q, 0)
        icon = {"EXCELLENT": "✅", "GOOD": "⚠️", "STALE": "❌", "MISSING": "🔴"}.get(q, "")
        lines.append(f"| {icon} {q} | {count} |")
    lines.append("")
    
    # Issues summary
    stale_items = []
    for symbol, rows in by_symbol.items():
        for row in rows:
            if row["quality"] in ("STALE", "MISSING"):
                stale_items.append({
                    "item": f"{symbol} {row['timeframe']}",
                    "age": row["candle_age_hours"],
                    "source": row["source"],
                })
    
    if stale_items:
        lines.append("### ⚠️ Stale/Missing Data (Requires Attention)")
        lines.append("")
        lines.append("| Pair/TF | Candle Age (h) | Source | Issue |")
        lines.append("|---------|----------------|--------|-------|")
        for item in sorted(stale_items, key=lambda x: x["age"], reverse=True):
            issue = "Missing" if any(s["item"] == item["item"] and s["age"] > 168 for s in stale_items) else "Stale"
            lines.append(f"| {item['item']} | {item['age']:.1f} | {item['source']} | {issue} |")
        lines.append("")
    
    return "\n".join(lines)


def generate_mtf_report(data: Dict) -> str:
    """Generate mtf_opportunities table report."""
    lines = []
    now = datetime.now(timezone.utc)
    
    lines.append("## MTF_OPPORTUNITIES Table Status")
    lines.append("")
    lines.append(f"**Current UTC:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    opportunities = data.get("opportunities", [])
    lines.append(f"**Total Opportunities:** {len(opportunities)}")
    lines.append("")
    
    if not opportunities:
        lines.append("> 💡 **No opportunities found.**")
        lines.append(">")
        lines.append("> This could mean:")
        lines.append("> - Market is in consolidation phase")
        lines.append("> - Stale data preventing valid setups")
        lines.append("> - Scanner filters are strict (excludes TRENDING_EXTENSION, weighted < 0.50)")
    else:
        # Group by pair
        by_pair = {}
        for opp in opportunities:
            pair = opp["pair"]
            if pair not in by_pair:
                by_pair[pair] = []
            by_pair[pair].append(opp)
        
        lines.append("### Opportunities by Pair")
        lines.append("")
        lines.append("| Pair | Style | Weighted | Context | Setup | Entry | Updated |")
        lines.append("|------|-------|----------|---------|-------|-------|---------|")
        
        for pair, opps in sorted(by_pair.items()):
            for opp in opps:
                updated = opp.get("updated_at", "N/A")[:16].replace("T", " ") if opp.get("updated_at") else "N/A"
                lines.append(
                    f"| {pair} | "
                    f"{opp.get('trading_style', 'N/A')} | "
                    f"{opp.get('weighted_score', 0):.2f} | "
                    f"{opp.get('htf_context', 'N/A')} | "
                    f"{opp.get('mtf_setup_type', 'N/A')} | "
                    f"{opp.get('ltf_entry_signal', 'N/A')} | "
                    f"{updated} |"
                )
        
        lines.append("")
        
        # Summary by conviction
        high = [o for o in opportunities if o.get("weighted_score", 0) >= 0.60]
        medium = [o for o in opportunities if 0.40 <= o.get("weighted_score", 0) < 0.60]
        low = [o for o in opportunities if o.get("weighted_score", 0) < 0.40]
        
        lines.append("### Conviction Distribution")
        lines.append("")
        lines.append("| Level | Count | Criteria |")
        lines.append("|-------|-------|----------|")
        lines.append(f"| 🟢 High | {len(high)} | Weighted ≥ 0.60 |")
        lines.append(f"| 🟡 Medium | {len(medium)} | 0.40 - 0.60 |")
        lines.append(f"| ⚪ Low | {len(low)} | < 0.40 |")
    
    lines.append("")
    
    return "\n".join(lines)


def generate_combined_report(ohlcv_data: Dict, mtf_data: Dict) -> str:
    """Generate combined report for both tables."""
    lines = []
    
    lines.append("# Data Staleness Check Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # OHLCV Universal section
    lines.append(generate_ohlcv_report(ohlcv_data))
    
    # MTF Opportunities section
    lines.append(generate_mtf_report(mtf_data))
    
    # Combined recommendations
    lines.append("---")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")
    
    # Analyze and provide recommendations
    issues = []
    
    # Check for stale OHLCV data
    if ohlcv_data:
        for pair_name, pair_data in ohlcv_data.get("pairs", {}).items():
            for tf, tf_data in pair_data.get("timeframes", {}).items():
                if tf_data["quality"] in ("STALE", "MISSING"):
                    issues.append(f"{pair_name} {tf}: {tf_data['quality']}")
    
    if issues:
        lines.append("### 1. Stale Data Detected")
        lines.append("")
        for issue in issues[:10]:  # Limit to first 10
            lines.append(f"- {issue}")
        if len(issues) > 10:
            lines.append(f"- ... and {len(issues) - 10} more")
        lines.append("")
        lines.append("**Recommended Action:** Deploy rate limit fixes (BUG-030 solutions)")
        lines.append("")
    
    # Check MTF opportunities
    if mtf_data:
        opp_count = len(mtf_data.get("opportunities", []))
        if opp_count == 0:
            lines.append("### 2. No MTF Opportunities")
            lines.append("")
            lines.append("Possible reasons:")
            lines.append("- Market is in consolidation phase")
            lines.append("- Stale data preventing valid setups")
            lines.append("- Scanner filters are strict")
            lines.append("")
            lines.append("**Recommended Action:** Review after deploying rate limit fixes")
            lines.append("")
    
    lines.append("### 3. Next Steps")
    lines.append("")
    lines.append("- Run again after next prefetch job (:20 past the hour)")
    lines.append("- Monitor Twelve Data portal: https://twelvedata.com/dashboard/usage")
    lines.append("- Check logs: `grep \"Rate limit\" logs/data_fetch.log`")
    lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Data Staleness Check for TA-DSS production database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--vm-ip", help="VM external IP address")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", help="Save report to file (default: docs/reports/staleness-YYYY-MM-DD.md)")
    
    args = parser.parse_args()
    
    # Get configuration
    vm_ip = get_vm_ip(args)
    api_key = get_api_key(args)
    
    # Default output path
    if not args.output:
        reports_dir = Path(__file__).parent.parent / "docs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        args.output = reports_dir / f"staleness-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    
    print(f"Checking production database at {vm_ip}...", file=sys.stderr)
    
    # Fetch data
    ohlcv_data = fetch_market_data_status(vm_ip, api_key)
    mtf_data = fetch_mtf_opportunities(vm_ip, api_key, style="SWING")
    
    if not ohlcv_data:
        print("Failed to fetch market data status. Check VM IP and API key.", file=sys.stderr)
        sys.exit(1)
    
    # Generate report
    report = generate_combined_report(ohlcv_data, mtf_data)
    
    # Output
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        print(f"✓ Report saved to: {output_path}", file=sys.stderr)
        print(f"  Open with: open {output_path}", file=sys.stderr)
    else:
        print(report)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
