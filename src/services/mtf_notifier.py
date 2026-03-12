"""
MTF Opportunity Alerts for TA-DSS.

Extension to notifier.py for sending Telegram alerts about MTF-aligned
trading opportunities.

Features:
- High-conviction opportunity alerts (3/3 alignment)
- Divergence alerts at key levels
- Alert throttling (max 3/day)
- Configurable alert preferences

Usage:
    from src.services.mtf_notifier import send_mtf_opportunity_alert
    
    # Send alert for high-conviction opportunity
    send_mtf_opportunity_alert(
        pair="BTC/USDT",
        quality="HIGHEST",
        alignment_score=3,
        recommendation="BUY",
        entry_price=67500,
        stop_loss=65800,
        target_price=72900,
        rr_ratio=3.2,
    )
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# Alert Throttling
# =============================================================================

# Track sent alerts to prevent spam
_alert_history: List[datetime] = []
_max_alerts_per_day = 3
_last_alert_time: Optional[datetime] = None


def reset_alert_history():
    """Reset alert history (for testing)."""
    global _alert_history, _last_alert_time
    _alert_history = []
    _last_alert_time = None


def _get_alerts_sent_today() -> int:
    """
    Get number of alerts sent in the last 24 hours.
    
    Returns:
        Number of alerts sent.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    
    # Count recent alerts
    recent = [ts for ts in _alert_history if ts > cutoff]
    return len(recent)


def _should_throttle_alert() -> bool:
    """
    Check if alert should be throttled.
    
    Returns:
        True if alert should be blocked (max reached).
    """
    alerts_today = _get_alerts_sent_today()
    return alerts_today >= _max_alerts_per_day


def _record_alert_sent():
    """Record that an alert was sent."""
    global _last_alert_time
    now = datetime.utcnow()
    _alert_history.append(now)
    _last_alert_time = now
    
    # Clean old entries (older than 24 hours)
    cutoff = now - timedelta(hours=24)
    _alert_history[:] = [ts for ts in _alert_history if ts > cutoff]


# =============================================================================
# MTF Alert Functions
# =============================================================================


def send_mtf_opportunity_alert(
    pair: str,
    quality: str,
    alignment_score: int,
    recommendation: str,
    entry_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    target_price: Optional[float] = None,
    rr_ratio: float = 0.0,
    patterns: Optional[List[str]] = None,
    divergence: Optional[str] = None,
    trading_style: str = "SWING",
) -> bool:
    """
    Send Telegram alert for MTF opportunity.
    
    Only sends for high-conviction setups (3/3 alignment) to avoid alert fatigue.
    
    Args:
        pair: Trading pair symbol.
        quality: Opportunity quality (HIGHEST, GOOD, POOR, AVOID).
        alignment_score: Alignment score (0-3).
        recommendation: Trade recommendation (BUY, SELL, WAIT, AVOID).
        entry_price: Entry price (optional).
        stop_loss: Stop loss price (optional).
        target_price: Target price (optional).
        rr_ratio: Risk:reward ratio.
        patterns: List of detected patterns.
        divergence: Divergence type if detected.
        trading_style: Trading style used for scan.
    
    Returns:
        True if alert sent successfully, False otherwise.
    """
    # Only alert for high-conviction opportunities
    if alignment_score < 3:
        logger.debug(f"Skipping alert for {pair} - alignment score {alignment_score} < 3")
        return False
    
    if recommendation not in ("BUY", "SELL"):
        logger.debug(f"Skipping alert for {pair} - recommendation {recommendation}")
        return False
    
    # Check throttling
    if _should_throttle_alert():
        logger.warning(f"Alert throttled for {pair} - max {_max_alerts_per_day}/day reached")
        return False
    
    # Check if Telegram is configured
    if not settings.telegram_enabled:
        logger.warning("Telegram not configured - cannot send MTF alert")
        return False
    
    # Format message
    message = _format_mtf_alert_message(
        pair=pair,
        quality=quality,
        alignment_score=alignment_score,
        recommendation=recommendation,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        rr_ratio=rr_ratio,
        patterns=patterns,
        divergence=divergence,
        trading_style=trading_style,
    )
    
    # Send via Telegram
    try:
        from src.notifier import send_alert
        send_alert(message)
        _record_alert_sent()
        logger.info(f"MTF alert sent for {pair} ({recommendation})")
        return True
    except Exception as e:
        logger.error(f"Failed to send MTF alert: {e}")
        return False


def send_divergence_alert(
    pair: str,
    divergence_type: str,
    timeframe: str,
    rsi_value: float,
    price_level: float,
    confidence: float,
) -> bool:
    """
    Send Telegram alert for RSI divergence at key level.
    
    Args:
        pair: Trading pair symbol.
        divergence_type: Type of divergence (REGULAR_BULLISH, etc.).
        timeframe: Timeframe where divergence detected.
        rsi_value: Current RSI value.
        price_level: Key S/R level price.
        confidence: Divergence confidence score.
    
    Returns:
        True if alert sent successfully.
    """
    # Check throttling
    if _should_throttle_alert():
        logger.warning(f"Divergence alert throttled for {pair}")
        return False
    
    # Check if Telegram is configured
    if not settings.telegram_enabled:
        logger.warning("Telegram not configured - cannot send divergence alert")
        return False
    
    # Only alert for high-confidence divergences
    if confidence < 0.6:
        logger.debug(f"Skipping divergence alert for {pair} - confidence {confidence:.2f} < 0.6")
        return False
    
    # Format message
    emoji = "🟢" if "BULLISH" in divergence_type else "🔴"
    div_name = divergence_type.replace("_", " ").title()
    
    message = (
        f"{emoji} *Divergence Alert*\n\n"
        f"*Pair:* {pair}\n"
        f"*Type:* {div_name}\n"
        f"*Timeframe:* {timeframe}\n"
        f"*RSI:* {rsi_value:.1f}\n"
        f"*Key Level:* ${price_level:,.2f}\n"
        f"*Confidence:* {confidence:.2f}\n\n"
        f"💡 Monitor for potential reversal"
    )
    
    # Send via Telegram
    try:
        from src.notifier import send_alert
        send_alert(message)
        _record_alert_sent()
        logger.info(f"Divergence alert sent for {pair} ({divergence_type})")
        return True
    except Exception as e:
        logger.error(f"Failed to send divergence alert: {e}")
        return False


def send_daily_scan_summary(
    total_scanned: int,
    opportunities_found: int,
    high_conviction: int,
    top_opportunities: List[Dict[str, Any]],
) -> bool:
    """
    Send daily summary of MTF scan results.
    
    Args:
        total_scanned: Number of pairs scanned.
        opportunities_found: Number of opportunities found.
        high_conviction: Number of high-conviction (3/3) opportunities.
        top_opportunities: List of top opportunities.
    
    Returns:
        True if summary sent successfully.
    """
    # Check if Telegram is configured
    if not settings.telegram_enabled:
        logger.warning("Telegram not configured - cannot send daily summary")
        return False
    
    # Format message
    message = (
        f"📊 *Daily MTF Scan Summary*\n\n"
        f"*Pairs Scanned:* {total_scanned}\n"
        f"*Opportunities:* {opportunities_found}\n"
        f"*High Conviction (3/3):* {high_conviction}\n\n"
    )
    
    if top_opportunities:
        message += "*Top Opportunities:*\n"
        for opp in top_opportunities[:3]:  # Top 3
            emoji = "🟢" if opp.get("recommendation") == "BUY" else "🔴"
            message += (
                f"{emoji} {opp['pair']} - {opp['quality']} "
                f"({opp['recommendation']}, R:R {opp['rr_ratio']:.1f})\n"
            )
    else:
        message += "⚠️ No high-conviction opportunities today"
    
    message += "\n💡 Check dashboard for full analysis"
    
    # Send via Telegram
    try:
        from src.notifier import send_alert
        send_alert(message)
        logger.info("Daily MTF scan summary sent")
        return True
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")
        return False


def _format_mtf_alert_message(
    pair: str,
    quality: str,
    alignment_score: int,
    recommendation: str,
    entry_price: Optional[float],
    stop_loss: Optional[float],
    target_price: Optional[float],
    rr_ratio: float,
    patterns: Optional[List[str]],
    divergence: Optional[str],
    trading_style: str,
) -> str:
    """
    Format MTF opportunity alert message for Telegram.
    
    Args:
        pair: Trading pair symbol.
        quality: Opportunity quality.
        alignment_score: Alignment score.
        recommendation: Trade recommendation.
        entry_price: Entry price.
        stop_loss: Stop loss price.
        target_price: Target price.
        rr_ratio: Risk:reward ratio.
        patterns: Detected patterns.
        divergence: Divergence type.
        trading_style: Trading style.
    
    Returns:
        Formatted message string.
    """
    # Emoji based on recommendation
    emoji = "🟢" if recommendation == "BUY" else "🔴"
    
    # Quality indicator
    quality_emoji = {
        "HIGHEST": "⭐⭐⭐",
        "GOOD": "⭐⭐",
        "POOR": "⭐",
        "AVOID": "⚠️",
    }.get(quality, "⭐")
    
    message = (
        f"{emoji} *MTF Opportunity Alert* {quality_emoji}\n\n"
        f"*Pair:* {pair}\n"
        f"*Style:* {trading_style}\n"
        f"*Alignment:* {alignment_score}/3 timeframes\n"
        f"*Recommendation:* {recommendation}\n"
        f"*R:R:* {rr_ratio:.1f}:1\n\n"
    )
    
    # Add trade parameters if available
    if entry_price and stop_loss and target_price:
        message += (
            f"*💰 Trade Setup:*\n"
            f"Entry: ${entry_price:,.2f}\n"
            f"Stop: ${stop_loss:,.2f}\n"
            f"Target: ${target_price:,.2f}\n\n"
        )
    
    # Add patterns if detected
    if patterns:
        message += "*Patterns Detected:*\n"
        for pattern in patterns:
            message += f"• {pattern}\n"
        message += "\n"
    
    # Add divergence if detected
    if divergence:
        div_name = divergence.replace("_", " ").title()
        message += f"⚠️ *Divergence:* {div_name}\n\n"
    
    message += (
        f"💡 *Action:* Review on dashboard before trading\n"
        f"📊 Open: /dashboard"
    )
    
    return message


def get_alert_status() -> Dict[str, Any]:
    """
    Get current alert status.

    Returns:
        Dictionary with alert status information.
    """
    alerts_today = _get_alerts_sent_today()
    remaining = _max_alerts_per_day - alerts_today

    return {
        "alerts_sent_today": alerts_today,
        "alerts_remaining": remaining,
        "max_per_day": _max_alerts_per_day,
        "throttled": remaining <= 0,
        "last_alert_time": _last_alert_time.isoformat() if _last_alert_time else None,
    }


# =============================================================================
# New Opportunity Alert (No Throttling)
# =============================================================================


def send_new_opportunity_alert(opportunity) -> bool:
    """
    Send Telegram alert for new MTF opportunity.

    NO THROTTLING: The upgraded 4-layer MTF framework already filters
    for quality. Users receive all opportunities meeting the minimum
    weighted score threshold (>= 0.60).

    Args:
        opportunity: MTFOpportunity database object with fields:
            - pair, htf_bias, mtf_context, weighted_score
            - position_size_pct, recommendation, rr_ratio
            - entry_price, stop_loss, target_price
            - pullback_quality_score, patterns, divergence

    Returns:
        True if alert sent successfully, False otherwise.

    Example:
        >>> opp = opportunity_service.save_opportunity(...)
        >>> if opp.weighted_score >= 0.60:
        ...     send_new_opportunity_alert(opp)
    """
    # Check if Telegram is configured
    if not settings.telegram_enabled:
        logger.warning("Telegram not configured - cannot send opportunity alert")
        return False

    # Format and send message
    try:
        message = _format_new_opportunity_alert_message(opportunity)
        from src.notifier import send_alert
        send_alert(message)
        logger.info(f"Opportunity alert sent for {opportunity.pair} ({opportunity.recommendation})")
        return True
    except Exception as e:
        logger.error(f"Failed to send opportunity alert: {e}")
        return False


def _format_new_opportunity_alert_message(opportunity) -> str:
    """
    Format new opportunity alert message for Telegram.

    Args:
        opportunity: MTFOpportunity database object.

    Returns:
        Formatted message string.
    """
    # Emoji based on recommendation
    emoji = "🟢" if opportunity.recommendation == "BUY" else "🔴"

    # Quality indicator based on weighted score
    weighted = opportunity.weighted_score or 0.0
    if weighted >= 0.75:
        quality_emoji = "⭐⭐⭐ HIGHEST"
    elif weighted >= 0.60:
        quality_emoji = "⭐⭐ GOOD"
    else:
        quality_emoji = "⭐ MODERATE"

    # Context emoji
    context_emoji = {
        "TRENDING_PULLBACK": "📈",
        "TRENDING_EXTENSION": "⏳",
        "BREAKING_OUT": "🚀",
        "CONSOLIDATING": "↔️",
        "REVERSING": "🔄",
    }.get(opportunity.mtf_context, "📊")

    message = (
        f"{emoji} *MTF Opportunity Alert* {quality_emoji}\n\n"
        f"*Pair:* {opportunity.pair}\n"
        f"*Context:* {context_emoji} {opportunity.mtf_context}\n"
        f"*HTF Bias:* {opportunity.htf_bias}\n"
        f"*Weighted Score:* {weighted:.0%} ({weighted:.2f})\n"
    )

    # Add position size if available
    if opportunity.position_size_pct:
        message += f"*Position Size:* {opportunity.position_size_pct:.0f}% of base risk\n"

    message += f"*Recommendation:* {opportunity.recommendation}\n"
    message += f"*R:R:* {opportunity.rr_ratio:.1f}:1\n\n"

    # Add trade parameters if available
    if opportunity.entry_price and opportunity.stop_loss and opportunity.target_price:
        message += (
            f"*💰 Trade Setup:*\n"
            f"Entry: ${opportunity.entry_price:,.2f}\n"
            f"Stop: ${opportunity.stop_loss:,.2f}\n"
            f"Target: ${opportunity.target_price:,.2f}\n\n"
        )

    # Add pullback quality if available
    if opportunity.pullback_quality_score:
        message += f"*Pullback Quality:* {opportunity.pullback_quality_score:.2f}/1.00\n"
        reasons = []
        if opportunity.pullback_distance_score and opportunity.pullback_distance_score >= 0.8:
            reasons.append("price at EMA21")
        if opportunity.pullback_volume_score and opportunity.pullback_volume_score >= 0.8:
            reasons.append("low pullback volume")
        if opportunity.pullback_rsi_score and opportunity.pullback_rsi_score >= 0.8:
            reasons.append("RSI in compression zone")
        if reasons:
            message += "• " + ", ".join(reasons) + "\n\n"

    # Add patterns if detected (from notes or parse from JSON)
    if opportunity.notes and "patterns" in opportunity.notes.lower():
        message += f"*Patterns:* {opportunity.notes}\n\n"

    # Add divergence if detected
    if opportunity.divergence:
        div_name = opportunity.divergence.replace("_", " ").title()
        message += f"⚠️ *Divergence:* {div_name}\n\n"

    message += (
        f"💡 *Action:* Review on dashboard before trading\n"
        f"📊 Open: /dashboard"
    )

    return message
