"""
Signal Engine for TA-DSS.

This module evaluates position health by comparing technical signals
against the position direction, generating alerts and status updates.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.services.technical_analyzer import SignalState

logger = logging.getLogger(__name__)


class PositionHealth(str, Enum):
    """Position health status levels."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    NEUTRAL = "NEUTRAL"


class PositionType(str, Enum):
    """Position direction."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class PositionHealthResult:
    """
    Result of position health evaluation.

    Attributes:
        position_id: Unique position identifier.
        pair: Trading pair symbol.
        position_type: LONG or SHORT.
        health_status: Overall health assessment.
        health_score: Numeric score 0.0 (critical) to 1.0 (healthy).
        bullish_signals: Count of bullish indicator signals.
        bearish_signals: Count of bearish indicator signals.
        neutral_signals: Count of neutral indicator signals.
        alignment_pct: Percentage of signals aligned with position.
        warning_message: Human-readable warning if any.
        recommended_action: Suggested action based on health.
    """

    position_id: int
    pair: str
    position_type: PositionType
    health_status: PositionHealth
    health_score: float
    bullish_signals: int
    bearish_signals: int
    neutral_signals: int
    alignment_pct: float
    warning_message: Optional[str] = None
    recommended_action: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "position_id": self.position_id,
            "pair": self.pair,
            "position_type": self.position_type.value,
            "health_status": self.health_status.value,
            "health_score": round(self.health_score, 2),
            "bullish_signals": self.bullish_signals,
            "bearish_signals": self.bearish_signals,
            "neutral_signals": self.neutral_signals,
            "alignment_pct": round(self.alignment_pct, 1),
            "warning_message": self.warning_message,
            "recommended_action": self.recommended_action,
        }


def evaluate_position_health(
    position: Any,
    signals: dict[str, Any],
) -> PositionHealthResult:
    """
    Evaluate the health of a trading position based on technical signals.

    Compares the position direction against technical indicator signals to
    determine if the position is healthy, at risk, or critical.

    Health Logic:
    ┌─────────────┬──────────────────┬──────────────────┬──────────────────┐
    │ Position    │ Mostly Bullish   │ Mostly Bearish   │ Mixed/Neutral    │
    ├─────────────┼──────────────────┼──────────────────┼──────────────────┤
    │ LONG        │ HEALTHY          │ WARNING/CRITICAL │ NEUTRAL          │
    │ SHORT       │ WARNING/CRITICAL │ HEALTHY          │ NEUTRAL          │
    └─────────────┴──────────────────┴──────────────────┴──────────────────┘

    Args:
        position: Position object with attributes:
            - id: Position ID
            - pair: Trading pair
            - position_type: 'LONG' or 'SHORT'
            - entry_price: Entry price (optional, for context)
        signals: Dictionary from TechnicalAnalyzer.generate_signal_states():
            {
                'MA10': SignalState,
                'MA20': SignalState,
                'MA50': SignalState,
                'MACD': SignalState,
                'RSI': SignalState,
                'values': {...}
            }

    Returns:
        PositionHealthResult with health assessment and recommendations.

    Example:
        >>> position = Position(id=1, pair='BTCUSD', position_type='LONG', ...)
        >>> signals = analyzer.generate_signal_states(df)
        >>> health = evaluate_position_health(position, signals)
        >>> print(health.health_status)
        PositionHealth.HEALTHY
    """
    # Extract position info
    position_id = getattr(position, 'id', 0)
    pair = getattr(position, 'pair', 'UNKNOWN')
    position_type_str = getattr(position, 'position_type', 'LONG')

    # Handle both string and enum position types
    if isinstance(position_type_str, str):
        position_type = PositionType(position_type_str.upper())
    else:
        position_type = PositionType(position_type_str.value)

    # Count signal states
    signal_keys = ['MA10', 'MA20', 'MA50', 'MACD', 'RSI']
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for key in signal_keys:
        state = signals.get(key)
        if state is None:
            neutral_count += 1
        elif state in (SignalState.BULLISH, SignalState.OVERBOUGHT):
            bullish_count += 1
        elif state in (SignalState.BEARISH, SignalState.OVERSOLD):
            bearish_count += 1
        else:
            neutral_count += 1

    total_signals = bullish_count + bearish_count + neutral_count
    decisive_signals = bullish_count + bearish_count

    # Calculate alignment with position
    if position_type == PositionType.LONG:
        # For LONG: bullish signals are aligned
        aligned_count = bullish_count
        misaligned_count = bearish_count
    else:  # SHORT
        # For SHORT: bearish signals are aligned
        aligned_count = bearish_count
        misaligned_count = bullish_count

    # Calculate alignment percentage (only considering decisive signals)
    if decisive_signals > 0:
        alignment_pct = (aligned_count / decisive_signals) * 100
    else:
        alignment_pct = 50.0  # Neutral when no decisive signals

    # Determine health status
    health_status, warning_message, recommended_action = _determine_health_status(
        position_type=position_type,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
        alignment_pct=alignment_pct,
        signals=signals,
    )

    # Calculate health score (0.0 to 1.0)
    health_score = _calculate_health_score(
        position_type=position_type,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
    )

    return PositionHealthResult(
        position_id=position_id,
        pair=pair,
        position_type=position_type,
        health_status=health_status,
        health_score=health_score,
        bullish_signals=bullish_count,
        bearish_signals=bearish_count,
        neutral_signals=neutral_count,
        alignment_pct=alignment_pct,
        warning_message=warning_message,
        recommended_action=recommended_action,
    )


def _determine_health_status(
    position_type: PositionType,
    bullish_count: int,
    bearish_count: int,
    neutral_count: int,
    alignment_pct: float,
    signals: dict[str, Any],
) -> tuple[PositionHealth, Optional[str], Optional[str]]:
    """
    Determine health status based on signal alignment.

    Args:
        position_type: LONG or SHORT.
        bullish_count: Number of bullish signals.
        bearish_count: Number of bearish signals.
        neutral_count: Number of neutral signals.
        alignment_pct: Percentage of signals aligned with position.
        signals: Full signals dictionary for detailed analysis.

    Returns:
        Tuple of (health_status, warning_message, recommended_action).
    """
    total_decisive = bullish_count + bearish_count

    # No decisive signals = NEUTRAL
    if total_decisive == 0:
        return (
            PositionHealth.NEUTRAL,
            "Insufficient signal data for health assessment",
            "Monitor for signal development",
        )

    # Check for extreme conditions (RSI overbought/oversold)
    rsi_state = signals.get('RSI')
    is_overbought = rsi_state == SignalState.OVERBOUGHT
    is_oversold = rsi_state == SignalState.OVERSOLD

    # LONG position logic
    if position_type == PositionType.LONG:
        if alignment_pct >= 60:
            # Mostly bullish for LONG = HEALTHY
            if is_overbought:
                return (
                    PositionHealth.WARNING,
                    "Position healthy but RSI overbought - consider taking partial profits",
                    "Monitor for reversal signals; consider trailing stop",
                )
            return (
                PositionHealth.HEALTHY,
                None,
                "Maintain position; consider adding on pullbacks",
            )
        elif alignment_pct <= 20:
            # Mostly bearish for LONG = CRITICAL
            if is_oversold:
                return (
                    PositionHealth.WARNING,
                    "Strong bearish signals but RSI oversold - potential bounce",
                    "Consider reducing position on any bounce",
                )
            return (
                PositionHealth.CRITICAL,
                "Strong bearish divergence - position at significant risk",
                "Consider closing position or tightening stop-loss",
            )
        else:
            # Mixed signals = WARNING
            return (
                PositionHealth.WARNING,
                "Mixed signals - market direction unclear",
                "Monitor closely; reduce position size if uncertainty persists",
            )

    # SHORT position logic
    else:  # PositionType.SHORT
        if alignment_pct >= 60:
            # Mostly bearish for SHORT = HEALTHY
            if is_oversold:
                return (
                    PositionHealth.WARNING,
                    "Position healthy but RSI oversold - consider covering partial",
                    "Monitor for bounce; consider trailing stop",
                )
            return (
                PositionHealth.HEALTHY,
                None,
                "Maintain position; consider adding on rallies",
            )
        elif alignment_pct <= 20:
            # Mostly bullish for SHORT = CRITICAL
            if is_overbought:
                return (
                    PositionHealth.WARNING,
                    "Strong bullish signals but RSI overbought - potential pullback",
                    "Consider covering position on any pullback",
                )
            return (
                PositionHealth.CRITICAL,
                "Strong bullish divergence - short position at significant risk",
                "Consider covering position or tightening stop-loss",
            )
        else:
            # Mixed signals = WARNING
            return (
                PositionHealth.WARNING,
                "Mixed signals - market direction unclear",
                "Monitor closely; reduce position size if uncertainty persists",
            )


def _calculate_health_score(
    position_type: PositionType,
    bullish_count: int,
    bearish_count: int,
    neutral_count: int,
) -> float:
    """
    Calculate numeric health score from 0.0 (critical) to 1.0 (healthy).

    Args:
        position_type: LONG or SHORT.
        bullish_count: Number of bullish signals.
        bearish_count: Number of bearish signals.
        neutral_count: Number of neutral signals.

    Returns:
        Health score between 0.0 and 1.0.
    """
    total = bullish_count + bearish_count + neutral_count

    if total == 0:
        return 0.5  # Neutral when no data

    # For LONG: bullish signals increase score
    # For SHORT: bearish signals increase score
    if position_type == PositionType.LONG:
        favorable = bullish_count
        unfavorable = bearish_count
    else:
        favorable = bearish_count
        unfavorable = bullish_count

    # Base score from favorable ratio
    base_score = favorable / total

    # Penalty for neutral signals (uncertainty)
    neutral_penalty = (neutral_count / total) * 0.3

    # Final score
    score = max(0.0, min(1.0, base_score - neutral_penalty))

    return score


def evaluate_portfolio_health(
    positions: list[Any],
    signals_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate health of entire portfolio of positions.

    Args:
        positions: List of position objects.
        signals_map: Dictionary mapping position_id to signals dict.

    Returns:
        Portfolio health summary with individual position assessments.
    """
    results = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    neutral_count = 0

    for position in positions:
        pos_id = getattr(position, 'id', 0)
        signals = signals_map.get(pos_id, {})

        if not signals:
            logger.warning(f"No signals available for position {pos_id}")
            continue

        result = evaluate_position_health(position, signals)
        results.append(result)

        # Count by status
        if result.health_status == PositionHealth.HEALTHY:
            healthy_count += 1
        elif result.health_status == PositionHealth.WARNING:
            warning_count += 1
        elif result.health_status == PositionHealth.CRITICAL:
            critical_count += 1
        else:
            neutral_count += 1

    total = len(results) if results else 1

    return {
        "summary": {
            "total_positions": len(results),
            "healthy": healthy_count,
            "warning": warning_count,
            "critical": critical_count,
            "neutral": neutral_count,
            "health_pct": round((healthy_count / total) * 100, 1),
            "risk_pct": round(((warning_count + critical_count) / total) * 100, 1),
        },
        "positions": [r.to_dict() for r in results],
        "requires_attention": critical_count > 0 or warning_count > len(results) * 0.3,
    }


def should_send_alert(
    previous_health: Optional[PositionHealth],
    current_health: PositionHealth,
    is_critical: bool = False,
) -> bool:
    """
    Determine if a Telegram alert should be sent.

    Alerts are sent when:
    1. Health status changes (e.g., HEALTHY → WARNING)
    2. Status is CRITICAL (always alert)
    3. Status degrades by more than one level

    Args:
        previous_health: Previous health status (None if new position).
        current_health: Current health status.
        is_critical: Override for critical conditions.

    Returns:
        True if alert should be sent, False otherwise.

    Example:
        >>> should_send_alert(PositionHealth.HEALTHY, PositionHealth.WARNING)
        True
        >>> should_send_alert(PositionHealth.WARNING, PositionHealth.WARNING)
        False
    """
    # Always alert on critical
    if current_health == PositionHealth.CRITICAL or is_critical:
        return True

    # No previous status = new position, no alert needed
    if previous_health is None:
        return False

    # Alert on status change
    if previous_health != current_health:
        # Check if it's a significant change
        severity_order = [
            PositionHealth.HEALTHY,
            PositionHealth.NEUTRAL,
            PositionHealth.WARNING,
            PositionHealth.CRITICAL,
        ]

        prev_idx = severity_order.index(previous_health)
        curr_idx = severity_order.index(current_health)

        # Alert if degradation (higher index = worse)
        if curr_idx > prev_idx:
            return True

    return False


def format_alert_message(health_result: PositionHealthResult) -> str:
    """
    Format a Telegram alert message for position health change.

    Args:
        health_result: Position health evaluation result.

    Returns:
        Formatted message string for Telegram.
    """
    emoji_map = {
        PositionHealth.HEALTHY: "✅",
        PositionHealth.WARNING: "⚠️",
        PositionHealth.CRITICAL: "🚨",
        PositionHealth.NEUTRAL: "➖",
    }

    emoji = emoji_map.get(health_result.health_status, "📊")

    message = (
        f"{emoji} *Position Health Alert*\n\n"
        f"*Pair:* {health_result.pair}\n"
        f"*Direction:* {health_result.position_type.value}\n"
        f"*Status:* {health_result.health_status.value}\n"
        f"*Health Score:* {health_result.health_score:.2f}\n"
        f"*Alignment:* {health_result.alignment_pct:.1f}%\n\n"
        f"*Signals:* 🟢{health_result.bullish_signals} 🔴{health_result.bearish_signals} ⚪{health_result.neutral_signals}\n"
    )

    if health_result.warning_message:
        message += f"\n⚠️ {health_result.warning_message}\n"

    if health_result.recommended_action:
        message += f"\n💡 *Action:* {health_result.recommended_action}\n"

    return message
