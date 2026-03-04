"""
Pytest test cases for the Signal Engine module.

Tests for evaluate_position_health function and related utilities.
"""

from dataclasses import dataclass

import pytest

from src.services.signal_engine import (
    PositionHealth,
    PositionHealthResult,
    evaluate_portfolio_health,
    evaluate_position_health,
    format_alert_message,
    should_send_alert,
)
from src.services.technical_analyzer import SignalState


# =============================================================================
# Test Fixtures
# =============================================================================


@dataclass
class MockPosition:
    """Mock position object for testing."""

    id: int
    pair: str
    position_type: str
    entry_price: float = 0.0


@pytest.fixture
def long_position():
    """Create a mock LONG position."""
    return MockPosition(id=1, pair="BTCUSD", position_type="LONG", entry_price=50000.0)


@pytest.fixture
def short_position():
    """Create a mock SHORT position."""
    return MockPosition(id=2, pair="ETHUSD", position_type="SHORT", entry_price=3000.0)


@pytest.fixture
def bullish_signals():
    """Create bullish signal state."""
    return {
        "MA10": SignalState.BULLISH,
        "MA20": SignalState.BULLISH,
        "MA50": SignalState.BULLISH,
        "MACD": SignalState.BULLISH,
        "RSI": SignalState.BULLISH,
        "values": {"RSI": 60.0, "MACD_hist": 100.0},
    }


@pytest.fixture
def bearish_signals():
    """Create bearish signal state."""
    return {
        "MA10": SignalState.BEARISH,
        "MA20": SignalState.BEARISH,
        "MA50": SignalState.BEARISH,
        "MACD": SignalState.BEARISH,
        "RSI": SignalState.BEARISH,
        "values": {"RSI": 40.0, "MACD_hist": -100.0},
    }


@pytest.fixture
def mixed_signals():
    """Create mixed signal state."""
    return {
        "MA10": SignalState.BULLISH,
        "MA20": SignalState.BEARISH,
        "MA50": SignalState.BEARISH,
        "MACD": SignalState.BULLISH,
        "RSI": SignalState.NEUTRAL,
        "values": {"RSI": 50.0, "MACD_hist": 0.0},
    }


@pytest.fixture
def overbought_signals():
    """Create overbought signal state (RSI > 70)."""
    return {
        "MA10": SignalState.BULLISH,
        "MA20": SignalState.BULLISH,
        "MA50": SignalState.BULLISH,
        "MACD": SignalState.BULLISH,
        "RSI": SignalState.OVERBOUGHT,
        "values": {"RSI": 75.0, "MACD_hist": 150.0},
    }


@pytest.fixture
def oversold_signals():
    """Create oversold signal state (RSI < 30)."""
    return {
        "MA10": SignalState.BEARISH,
        "MA20": SignalState.BEARISH,
        "MA50": SignalState.BEARISH,
        "MACD": SignalState.BEARISH,
        "RSI": SignalState.OVERSOLD,
        "values": {"RSI": 25.0, "MACD_hist": -150.0},
    }


# =============================================================================
# Test Cases: LONG Position Scenarios
# =============================================================================


class TestLongPositionScenarios:
    """Test evaluate_position_health for LONG positions."""

    def test_long_bullish_signals_healthy(self, long_position, bullish_signals):
        """LONG + Mostly BULLISH signals = HEALTHY."""
        result = evaluate_position_health(long_position, bullish_signals)

        assert result.health_status == PositionHealth.HEALTHY
        assert result.health_score == 1.0
        assert result.alignment_pct == 100.0
        assert result.bullish_signals == 5
        assert result.bearish_signals == 0
        assert result.warning_message is None
        assert "Maintain position" in result.recommended_action

    def test_long_bearish_signals_critical(self, long_position, bearish_signals):
        """LONG + Mostly BEARISH signals = CRITICAL."""
        result = evaluate_position_health(long_position, bearish_signals)

        assert result.health_status == PositionHealth.CRITICAL
        assert result.health_score == 0.0
        assert result.alignment_pct == 0.0
        assert result.bullish_signals == 0
        assert result.bearish_signals == 5
        assert "bearish" in result.warning_message.lower()
        assert "Consider closing" in result.recommended_action

    def test_long_mixed_signals_warning(self, long_position, mixed_signals):
        """LONG + Mixed signals = WARNING."""
        result = evaluate_position_health(long_position, mixed_signals)

        assert result.health_status == PositionHealth.WARNING
        assert result.alignment_pct == 50.0  # 2 bullish out of 4 decisive (2+2)
        assert "Mixed signals" in result.warning_message
        assert "Monitor closely" in result.recommended_action

    def test_long_overbought_warning(self, long_position, overbought_signals):
        """LONG + BULLISH but RSI OVERBOUGHT = WARNING."""
        result = evaluate_position_health(long_position, overbought_signals)

        assert result.health_status == PositionHealth.WARNING
        assert "overbought" in result.warning_message.lower()
        assert "taking partial profits" in result.warning_message.lower()

    def test_long_bearish_oversold_warning(self, long_position, oversold_signals):
        """LONG + BEARISH but RSI OVERSOLD = WARNING (potential bounce)."""
        result = evaluate_position_health(long_position, oversold_signals)

        # Should be WARNING instead of CRITICAL due to oversold condition
        assert result.health_status == PositionHealth.WARNING
        assert "oversold" in result.warning_message.lower()
        assert "bounce" in result.warning_message.lower()


# =============================================================================
# Test Cases: SHORT Position Scenarios
# =============================================================================


class TestShortPositionScenarios:
    """Test evaluate_position_health for SHORT positions."""

    def test_short_bearish_signals_healthy(self, short_position, bearish_signals):
        """SHORT + Mostly BEARISH signals = HEALTHY."""
        result = evaluate_position_health(short_position, bearish_signals)

        assert result.health_status == PositionHealth.HEALTHY
        assert result.health_score == 1.0
        assert result.alignment_pct == 100.0
        assert result.bearish_signals == 5
        assert result.bullish_signals == 0
        assert result.warning_message is None
        assert "Maintain position" in result.recommended_action

    def test_short_bullish_signals_critical(self, short_position, bullish_signals):
        """SHORT + Mostly BULLISH signals = CRITICAL."""
        result = evaluate_position_health(short_position, bullish_signals)

        assert result.health_status == PositionHealth.CRITICAL
        assert result.health_score == 0.0
        assert result.alignment_pct == 0.0
        assert result.bullish_signals == 5
        assert result.bearish_signals == 0
        assert "bullish" in result.warning_message.lower()
        assert "covering" in result.recommended_action.lower()

    def test_short_mixed_signals_warning(self, short_position, mixed_signals):
        """SHORT + Mixed signals = WARNING."""
        result = evaluate_position_health(short_position, mixed_signals)

        assert result.health_status == PositionHealth.WARNING
        assert "Mixed signals" in result.warning_message

    def test_short_oversold_warning(self, short_position, oversold_signals):
        """SHORT + BEARISH but RSI OVERSOLD = WARNING."""
        result = evaluate_position_health(short_position, oversold_signals)

        assert result.health_status == PositionHealth.WARNING
        assert "oversold" in result.warning_message.lower()
        assert "covering partial" in result.warning_message.lower()

    def test_short_bullish_overbought_warning(self, short_position, bullish_signals):
        """SHORT + BULLISH but RSI OVERBOUGHT = WARNING (potential pullback helps short)."""
        # Modify bullish signals to have overbought RSI
        overbought = bullish_signals.copy()
        overbought["RSI"] = SignalState.OVERBOUGHT
        overbought["values"] = {"RSI": 75.0}

        result = evaluate_position_health(short_position, overbought)

        # Overbought RSI is actually GOOD for short positions (potential pullback)
        # So status should be WARNING instead of CRITICAL
        assert result.health_status == PositionHealth.WARNING
        assert "overbought" in result.warning_message.lower()


# =============================================================================
# Test Cases: Health Score Calculations
# =============================================================================


class TestHealthScoreCalculation:
    """Test health score calculation logic."""

    def test_perfect_alignment_score(self, long_position, bullish_signals):
        """Perfect alignment should give score of 1.0."""
        result = evaluate_position_health(long_position, bullish_signals)
        assert result.health_score == 1.0

    def test_no_alignment_score(self, long_position, bearish_signals):
        """No alignment should give score of 0.0."""
        result = evaluate_position_health(long_position, bearish_signals)
        assert result.health_score == 0.0

    def test_partial_alignment_score(self, long_position, mixed_signals):
        """Partial alignment should give score between 0 and 1."""
        result = evaluate_position_health(long_position, mixed_signals)
        assert 0.0 < result.health_score < 1.0


# =============================================================================
# Test Cases: Alert Logic
# =============================================================================


class TestAlertLogic:
    """Test should_send_alert function."""

    def test_healthy_to_warning_sends_alert(self):
        """Status degradation should send alert."""
        assert should_send_alert(PositionHealth.HEALTHY, PositionHealth.WARNING) is True

    def test_warning_to_critical_sends_alert(self):
        """Further degradation should send alert."""
        assert should_send_alert(PositionHealth.WARNING, PositionHealth.CRITICAL) is True

    def test_same_status_no_alert(self):
        """No change should not send alert."""
        assert should_send_alert(PositionHealth.WARNING, PositionHealth.WARNING) is False
        assert should_send_alert(PositionHealth.HEALTHY, PositionHealth.HEALTHY) is False

    def test_improvement_no_alert(self):
        """Status improvement should not send alert."""
        assert should_send_alert(PositionHealth.WARNING, PositionHealth.HEALTHY) is False

    def test_new_position_no_alert(self):
        """New position (None previous) should not send alert."""
        assert should_send_alert(None, PositionHealth.HEALTHY) is False

    def test_critical_always_alert(self):
        """Critical status should always alert."""
        assert should_send_alert(None, PositionHealth.CRITICAL) is True
        assert should_send_alert(PositionHealth.CRITICAL, PositionHealth.CRITICAL) is True


# =============================================================================
# Test Cases: Alert Message Formatting
# =============================================================================


class TestAlertMessageFormatting:
    """Test format_alert_message function."""

    def test_message_contains_required_fields(self, long_position, bearish_signals):
        """Alert message should contain all required fields."""
        result = evaluate_position_health(long_position, bearish_signals)
        message = format_alert_message(result)

        assert "Position Health Alert" in message
        assert "BTCUSD" in message
        assert "LONG" in message
        assert "CRITICAL" in message
        assert "Health Score" in message
        assert "Signals:" in message

    def test_message_contains_emoji(self, long_position, bearish_signals):
        """Alert message should contain appropriate emoji."""
        result = evaluate_position_health(long_position, bearish_signals)
        message = format_alert_message(result)

        assert "🚨" in message  # Critical emoji

    def test_message_contains_warning(self, long_position, bearish_signals):
        """Alert message should contain warning message."""
        result = evaluate_position_health(long_position, bearish_signals)
        message = format_alert_message(result)

        assert "bearish" in message.lower()

    def test_message_contains_action(self, long_position, bearish_signals):
        """Alert message should contain recommended action."""
        result = evaluate_position_health(long_position, bearish_signals)
        message = format_alert_message(result)

        assert "Action:" in message


# =============================================================================
# Test Cases: Portfolio Health
# =============================================================================


class TestPortfolioHealth:
    """Test evaluate_portfolio_health function."""

    def test_portfolio_summary(self, long_position, short_position, bullish_signals, bearish_signals):
        """Portfolio health should provide summary statistics."""
        positions = [long_position, short_position]
        signals_map = {
            1: bullish_signals,  # LONG is healthy
            2: bearish_signals,  # SHORT is healthy
        }

        result = evaluate_portfolio_health(positions, signals_map)

        assert result["summary"]["total_positions"] == 2
        assert result["summary"]["healthy"] == 2
        assert result["summary"]["health_pct"] == 100.0
        assert result["requires_attention"] is False

    def test_portfolio_requires_attention(self, long_position, bearish_signals):
        """Portfolio with critical positions requires attention."""
        positions = [long_position]
        signals_map = {1: bearish_signals}  # LONG + bearish = critical

        result = evaluate_portfolio_health(positions, signals_map)

        assert result["summary"]["critical"] == 1
        assert result["requires_attention"] is True

    def test_portfolio_warning_threshold(self, long_position, mixed_signals):
        """Portfolio with >30% warnings requires attention."""
        # Create 3 positions with mixed signals
        positions = [
            MockPosition(id=i, pair=f"PAIR{i}", position_type="LONG")
            for i in range(3)
        ]
        signals_map = {i: mixed_signals for i in range(3)}

        result = evaluate_portfolio_health(positions, signals_map)

        # All 3 are warnings = 100% > 30%
        assert result["requires_attention"] is True


# =============================================================================
# Test Cases: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_signals(self, long_position):
        """Empty signals dict should handle gracefully."""
        result = evaluate_position_health(long_position, {})

        assert result.health_status == PositionHealth.NEUTRAL
        assert "Insufficient signal data" in result.warning_message
        # Health score is 0.0 when all signals are neutral (no decisive signals)

    def test_partial_signals(self, long_position):
        """Partial signals should handle gracefully."""
        partial_signals = {
            "MA10": SignalState.BULLISH,
            # Missing other signals
        }

        result = evaluate_position_health(long_position, partial_signals)

        assert result.health_status == PositionHealth.HEALTHY
        assert result.bullish_signals == 1

    def test_position_type_case_insensitive(self):
        """Position type should be case insensitive."""
        pos_lower = MockPosition(id=1, pair="BTCUSD", position_type="long")
        pos_upper = MockPosition(id=1, pair="BTCUSD", position_type="LONG")

        signals = {"MA10": SignalState.BULLISH}

        result_lower = evaluate_position_health(pos_lower, signals)
        result_upper = evaluate_position_health(pos_upper, signals)

        assert result_lower.health_status == result_upper.health_status


# =============================================================================
# Test Cases: Result Object
# =============================================================================


class TestPositionHealthResult:
    """Test PositionHealthResult dataclass."""

    def test_to_dict_conversion(self, long_position, bullish_signals):
        """Result should convert to dictionary correctly."""
        result = evaluate_position_health(long_position, bullish_signals)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["position_id"] == 1
        assert result_dict["pair"] == "BTCUSD"
        assert result_dict["position_type"] == "LONG"
        assert result_dict["health_status"] == "HEALTHY"
        assert 0.0 <= result_dict["health_score"] <= 1.0
        assert isinstance(result_dict["bullish_signals"], int)
        assert isinstance(result_dict["bearish_signals"], int)
        assert isinstance(result_dict["neutral_signals"], int)
        assert 0.0 <= result_dict["alignment_pct"] <= 100.0

    def test_result_attributes(self, long_position, bearish_signals):
        """Result should have all required attributes."""
        result = evaluate_position_health(long_position, bearish_signals)

        assert hasattr(result, "position_id")
        assert hasattr(result, "pair")
        assert hasattr(result, "position_type")
        assert hasattr(result, "health_status")
        assert hasattr(result, "health_score")
        assert hasattr(result, "bullish_signals")
        assert hasattr(result, "bearish_signals")
        assert hasattr(result, "neutral_signals")
        assert hasattr(result, "alignment_pct")
        assert hasattr(result, "warning_message")
        assert hasattr(result, "recommended_action")
