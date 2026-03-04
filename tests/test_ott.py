"""
Test script for OTT (Optimized Trend Tracker) indicator implementation.

This script tests:
1. OTT calculation with various MA types
2. OTT signal generation
3. Integration with existing indicators
4. Edge cases (insufficient data, NaN handling)
"""

import pandas as pd
import numpy as np
from src.services.technical_analyzer import TechnicalAnalyzer, PositionType


def generate_sample_data(periods: int = 100, trend: str = "up") -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing.
    
    Args:
        periods: Number of data points.
        trend: "up", "down", or "sideways"
    
    Returns:
        DataFrame with OHLCV columns.
    """
    np.random.seed(42)
    
    # Generate base price
    if trend == "up":
        base = np.linspace(100, 150, periods) + np.random.randn(periods) * 2
    elif trend == "down":
        base = np.linspace(150, 100, periods) + np.random.randn(periods) * 2
    else:  # sideways
        base = np.ones(periods) * 125 + np.random.randn(periods) * 3
    
    # Create OHLCV
    df = pd.DataFrame({
        'open': base + np.random.randn(periods) * 0.5,
        'high': base + np.abs(np.random.randn(periods) * 1.5),
        'low': base - np.abs(np.random.randn(periods) * 1.5),
        'close': base + np.random.randn(periods) * 0.5,
        'volume': np.random.randint(1000, 10000, periods),
    })
    
    # Ensure high >= close, open, low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def test_ott_calculation():
    """Test OTT calculation with default parameters."""
    print("\n" + "="*60)
    print("TEST 1: OTT Calculation (Default VAR MA)")
    print("="*60)
    
    df = generate_sample_data(periods=100, trend="up")
    analyzer = TechnicalAnalyzer(ott_period=2, ott_percent=1.4, ott_ma_type="VAR")
    
    # Calculate indicators
    df_with_indicators = analyzer.calculate_indicators(df)
    
    # Check OTT columns exist
    assert "OTT" in df_with_indicators.columns, "OTT column missing"
    assert "OTT_MT" in df_with_indicators.columns, "OTT_MT column missing"
    assert "OTT_Trend" in df_with_indicators.columns, "OTT_Trend column missing"
    assert "OTT_MAvg" in df_with_indicators.columns, "OTT_MAvg column missing"
    
    # Check for NaN values (should have some valid data)
    valid_ott = df_with_indicators["OTT"].dropna()
    assert len(valid_ott) > 0, "All OTT values are NaN"
    
    # Print latest values
    latest = df_with_indicators.iloc[-1]
    print(f"✓ OTT calculated successfully")
    print(f"  - OTT Value: {latest['OTT']:.4f}")
    print(f"  - OTT MT: {latest['OTT_MT']:.4f}")
    print(f"  - OTT Trend: {latest['OTT_Trend']}")
    print(f"  - MAvg: {latest['OTT_MAvg']:.4f}")
    print(f"  - Close Price: {latest['close']:.4f}")
    
    return True


def test_ott_signals():
    """Test OTT signal generation."""
    print("\n" + "="*60)
    print("TEST 2: OTT Signal Generation")
    print("="*60)
    
    # Test with uptrend
    df_up = generate_sample_data(periods=100, trend="up")
    analyzer = TechnicalAnalyzer()
    df_up = analyzer.calculate_indicators(df_up)
    signals_up = analyzer.generate_signal_states(df_up)
    
    print(f"✓ Uptrend scenario:")
    print(f"  - OTT Signal: {signals_up['OTT']}")
    print(f"  - OTT Value: {signals_up['values']['OTT']}")
    print(f"  - OTT Trend: {signals_up['values']['OTT_Trend']}")
    
    # Test with downtrend
    df_down = generate_sample_data(periods=100, trend="down")
    df_down = analyzer.calculate_indicators(df_down)
    signals_down = analyzer.generate_signal_states(df_down)
    
    print(f"✓ Downtrend scenario:")
    print(f"  - OTT Signal: {signals_down['OTT']}")
    print(f"  - OTT Value: {signals_down['values']['OTT']}")
    print(f"  - OTT Trend: {signals_down['values']['OTT_Trend']}")
    
    # Test with sideways
    df_side = generate_sample_data(periods=100, trend="sideways")
    df_side = analyzer.calculate_indicators(df_side)
    signals_side = analyzer.generate_signal_states(df_side)
    
    print(f"✓ Sideways scenario:")
    print(f"  - OTT Signal: {signals_side['OTT']}")
    print(f"  - OTT Value: {signals_side['values']['OTT']}")
    print(f"  - OTT Trend: {signals_side['values']['OTT_Trend']}")
    
    return True


def test_ott_ma_types():
    """Test OTT with different MA types."""
    print("\n" + "="*60)
    print("TEST 3: OTT with Different MA Types")
    print("="*60)
    
    df = generate_sample_data(periods=100, trend="up")
    
    ma_types = ["SMA", "EMA", "WMA", "VAR", "WWMA", "ZLEMA", "TSF"]
    
    for ma_type in ma_types:
        analyzer = TechnicalAnalyzer(ott_ma_type=ma_type)
        df_with_ott = analyzer.calculate_indicators(df)
        
        latest = df_with_ott.iloc[-1]
        ott_value = latest['OTT']
        trend = latest['OTT_Trend']
        
        if isinstance(ott_value, float) and not pd.isna(ott_value):
            ott_str = f"{ott_value:.4f}"
        else:
            ott_str = str(ott_value)
        
        print(f"✓ {ma_type:6s}: OTT={ott_str}, Trend={trend}")
    
    return True


def test_ott_integration():
    """Test OTT integration with full analysis."""
    print("\n" + "="*60)
    print("TEST 4: OTT Integration (Full Analysis)")
    print("="*60)
    
    df = generate_sample_data(periods=100, trend="up")
    analyzer = TechnicalAnalyzer()
    
    # Perform full analysis
    signal = analyzer.analyze_position(
        df=df,
        pair="BTCUSD",
        position_type=PositionType.LONG,
        timeframe="h4"
    )
    
    print(f"✓ Full analysis completed:")
    print(f"  - Pair: {signal.pair}")
    print(f"  - Overall Signal: {signal.overall_signal}")
    print(f"  - Bullish Count: {signal.bullish_count}")
    print(f"  - Bearish Count: {signal.bearish_count}")
    print(f"  - Neutral Count: {signal.neutral_count}")
    print(f"  - Confidence: {signal.confidence_score:.2f}")
    print(f"  - OTT in indicators: {'OTT' in signal.indicators}")
    print(f"  - OTT Value: {signal.indicators.get('OTT')}")
    print(f"  - OTT Trend: {signal.indicators.get('OTT_Trend')}")
    
    # Check OTT is in signal_states
    assert 'OTT' in signal.signal_states, "OTT missing from signal_states"
    print(f"  - OTT Signal State: {signal.signal_states['OTT']}")
    
    return True


def test_ott_insufficient_data():
    """Test OTT with insufficient data."""
    print("\n" + "="*60)
    print("TEST 5: OTT with Insufficient Data")
    print("="*60)
    
    # Very small dataset
    df = generate_sample_data(periods=5, trend="up")
    analyzer = TechnicalAnalyzer()
    
    df_with_ott = analyzer.calculate_indicators(df)
    signals = analyzer.generate_signal_states(df_with_ott)
    
    print(f"✓ Insufficient data handled:")
    print(f"  - OTT Signal: {signals['OTT']}")
    print(f"  - OTT Value: {signals['values']['OTT']}")
    
    # Note: OTT can calculate with small datasets (unlike MACD/RSI which need more periods)
    # The test just verifies it doesn't crash
    print(f"  - Note: OTT can calculate with small datasets (iterative calculation)")
    
    return True


def test_ott_warnings():
    """Test OTT-based warnings."""
    print("\n" + "="*60)
    print("TEST 6: OTT Warnings")
    print("="*60)
    
    # Create downtrend scenario for LONG position
    df = generate_sample_data(periods=100, trend="down")
    analyzer = TechnicalAnalyzer()
    df_with_ott = analyzer.calculate_indicators(df)
    signals = analyzer.generate_signal_states(df_with_ott)
    
    warning = analyzer._check_warnings(signals, PositionType.LONG)
    
    print(f"✓ LONG position in downtrend:")
    print(f"  - OTT Signal: {signals['OTT']}")
    print(f"  - Warning: {warning}")
    
    # Create uptrend scenario for SHORT position
    df = generate_sample_data(periods=100, trend="up")
    df_with_ott = analyzer.calculate_indicators(df)
    signals = analyzer.generate_signal_states(df_with_ott)
    
    warning = analyzer._check_warnings(signals, PositionType.SHORT)
    
    print(f"✓ SHORT position in uptrend:")
    print(f"  - OTT Signal: {signals['OTT']}")
    print(f"  - Warning: {warning}")
    
    return True


def test_ott_summary():
    """Test OTT in indicator summary."""
    print("\n" + "="*60)
    print("TEST 7: OTT in Indicator Summary")
    print("="*60)
    
    df = generate_sample_data(periods=100, trend="up")
    analyzer = TechnicalAnalyzer()
    df_with_ott = analyzer.calculate_indicators(df)
    
    summary = analyzer.get_indicator_summary(df_with_ott)
    
    print(f"✓ Indicator summary:")
    print(f"  - OTT in summary: {'OTT' in summary.get('trend', {})}")
    if 'OTT' in summary.get('trend', {}):
        ott_summary = summary['trend']['OTT']
        print(f"  - OTT Value: {ott_summary.get('value')}")
        print(f"  - OTT Trend: {ott_summary.get('trend')}")
        print(f"  - OTT Interpretation: {ott_summary.get('interpretation')}")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("OTT (Optimized Trend Tracker) Implementation Tests")
    print("="*60)
    
    tests = [
        ("OTT Calculation", test_ott_calculation),
        ("OTT Signals", test_ott_signals),
        ("OTT MA Types", test_ott_ma_types),
        ("OTT Integration", test_ott_integration),
        ("OTT Insufficient Data", test_ott_insufficient_data),
        ("OTT Warnings", test_ott_warnings),
        ("OTT Summary", test_ott_summary),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ {name} FAILED: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       Error: {error}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return passed == total


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/Users/aiagent/Documents/No.3 - Qwen - Trading Order Monitoring system/trading-order-monitoring-system')
    
    success = main()
    sys.exit(0 if success else 1)
