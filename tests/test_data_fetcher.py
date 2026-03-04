"""
Pytest test cases for the DataFetcher module.

Tests for DataFetcher class, retry logic, and data validation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data_fetcher import DataFetcher, DataFetchError


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV DataFrame for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0 + i * 0.5 for i in range(100)],
            "High": [105.0 + i * 0.5 for i in range(100)],
            "Low": [95.0 + i * 0.5 for i in range(100)],
            "Close": [102.0 + i * 0.5 for i in range(100)],
            "Volume": [1000000 + i * 10000 for i in range(100)],
        },
        index=dates,
    )


@pytest.fixture
def sample_ohlcv_with_nulls():
    """Create sample OHLCV DataFrame with null values."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, None, 102.0, 103.0, None, 105.0, 106.0, 107.0, 108.0, 109.0],
            "High": [105.0, 106.0, None, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0],
            "Low": [95.0, 96.0, 97.0, None, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
            "Close": [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
            "Volume": [1000000] * 10,
        },
        index=dates,
    )
    return df


@pytest.fixture
def empty_dataframe():
    """Create empty DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def fetcher_yfinance():
    """Create DataFetcher with yfinance source."""
    return DataFetcher(source="yfinance", retry_attempts=2, retry_delay=0.1)


@pytest.fixture
def fetcher_ccxt():
    """Create DataFetcher with ccxt source."""
    return DataFetcher(source="ccxt", retry_attempts=2, retry_delay=0.1)


# =============================================================================
# Test Cases: Initialization
# =============================================================================


class TestDataFetcherInitialization:
    """Test DataFetcher initialization."""

    def test_init_yfinance(self):
        """Test initialization with yfinance source."""
        fetcher = DataFetcher(source="yfinance")
        assert fetcher.source == "yfinance"
        assert fetcher.retry_attempts == 3
        assert fetcher.retry_delay == 1.0

    def test_init_ccxt(self):
        """Test initialization with ccxt source."""
        fetcher = DataFetcher(source="ccxt")
        assert fetcher.source == "ccxt"
        assert fetcher._exchange is not None

    def test_init_invalid_source(self):
        """Test initialization with invalid source."""
        with pytest.raises(ValueError, match="Invalid source"):
            DataFetcher(source="invalid")

    def test_init_custom_retry(self):
        """Test initialization with custom retry settings."""
        fetcher = DataFetcher(source="yfinance", retry_attempts=5, retry_delay=2.0)
        assert fetcher.retry_attempts == 5
        assert fetcher.retry_delay == 2.0

    def test_init_creates_log_directory(self, tmp_path):
        """Test that log directory is created."""
        log_dir = tmp_path / "custom_logs"
        fetcher = DataFetcher(source="yfinance", log_dir=str(log_dir))
        assert log_dir.exists()
        assert (log_dir / "data_fetch.log").exists()


# =============================================================================
# Test Cases: Data Validation
# =============================================================================


class TestDataValidation:
    """Test data validation and cleaning."""

    def test_validate_empty_dataframe_raises_error(self, fetcher_yfinance, empty_dataframe):
        """Test that empty DataFrame raises DataFetchError."""
        with pytest.raises(DataFetchError, match="empty"):
            fetcher_yfinance._validate_and_clean(empty_dataframe, "TEST")

    def test_validate_drops_null_values(self, fetcher_yfinance, sample_ohlcv_with_nulls):
        """Test that rows with null values are dropped."""
        original_len = len(sample_ohlcv_with_nulls)
        cleaned = fetcher_yfinance._validate_and_clean(sample_ohlcv_with_nulls, "TEST")
        assert len(cleaned) < original_len
        assert cleaned["Close"].isnull().sum() == 0

    def test_validate_sorts_chronologically(self, fetcher_yfinance):
        """Test that data is sorted by datetime."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")[::-1]  # Reversed
        df = pd.DataFrame(
            {
                "Open": range(10),
                "High": range(10),
                "Low": range(10),
                "Close": range(10),
                "Volume": range(10),
            },
            index=dates,
        )
        cleaned = fetcher_yfinance._validate_and_clean(df, "TEST")
        assert cleaned.index.is_monotonic_increasing

    def test_validate_sets_datetime_index(self, fetcher_yfinance):
        """Test that Datetime column becomes index."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "Datetime": dates,
                "Open": range(10),
                "High": range(10),
                "Low": range(10),
                "Close": range(10),
                "Volume": range(10),
            },
        )
        cleaned = fetcher_yfinance._validate_and_clean(df, "TEST")
        assert isinstance(cleaned.index, pd.DatetimeIndex)

    def test_validate_missing_critical_columns(self, fetcher_yfinance):
        """Test that missing critical columns raise error."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "Open": range(10),
                "Volume": range(10),
            },
            index=dates,
        )
        with pytest.raises(DataFetchError, match="Missing critical columns"):
            fetcher_yfinance._validate_and_clean(df, "TEST")


# =============================================================================
# Test Cases: Retry Logic
# =============================================================================


class TestRetryLogic:
    """Test retry logic and exponential backoff."""

    @patch("yfinance.Ticker")
    def test_retry_on_failure(self, mock_ticker, fetcher_yfinance):
        """Test that fetcher retries on failure."""
        # Mock ticker to fail once, succeed on second attempt
        mock_instance = MagicMock()
        mock_instance.history.side_effect = [
            Exception("API Error 1"),
            pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [105.0],
                    "Low": [95.0],
                    "Close": [102.0],
                    "Volume": [1000000],
                },
                index=pd.date_range("2024-01-01", periods=1),
            ),
        ]
        mock_ticker.return_value = mock_instance

        # Should succeed after retry
        df = fetcher_yfinance.get_ohlcv("AAPL", "1d", limit=1)
        assert len(df) == 1
        assert mock_instance.history.call_count == 2

    @patch("yfinance.Ticker")
    def test_all_retries_fail_raises_error(self, mock_ticker, fetcher_yfinance):
        """Test that DataFetchError is raised after all retries fail."""
        mock_instance = MagicMock()
        mock_instance.history.side_effect = Exception("Persistent API Error")
        mock_ticker.return_value = mock_instance

        with pytest.raises(DataFetchError) as exc_info:
            fetcher_yfinance.get_ohlcv("AAPL", "1d", limit=1)

        assert exc_info.value.attempts == fetcher_yfinance.retry_attempts
        assert "AAPL" in str(exc_info.value)

    @patch("yfinance.Ticker")
    def test_exponential_backoff(self, mock_ticker, fetcher_yfinance):
        """Test that retry delay increases exponentially."""
        import time

        mock_instance = MagicMock()
        mock_instance.history.side_effect = Exception("API Error")
        mock_ticker.return_value = mock_instance

        start = time.time()
        try:
            fetcher_yfinance.get_ohlcv("AAPL", "1d", limit=1)
        except DataFetchError:
            pass
        elapsed = time.time() - start

        # Expected delay: 0.1 seconds (for 1 retry with base 0.1)
        # Allow some tolerance for execution time
        assert elapsed >= 0.08


# =============================================================================
# Test Cases: get_ohlcv Method
# =============================================================================


class TestGetOHLCV:
    """Test get_ohlcv method."""

    @patch("yfinance.Ticker")
    def test_get_ohlcv_yfinance_success(self, mock_ticker, sample_ohlcv_data):
        """Test successful yfinance fetch."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_ohlcv_data
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance")
        df = fetcher.get_ohlcv("AAPL", "1d", limit=100)

        assert len(df) == 100
        assert isinstance(df.index, pd.DatetimeIndex)
        assert "Close" in df.columns

    @patch("ccxt.binance")
    def test_get_ohlcv_ccxt_success(self, mock_binance, sample_ohlcv_data):
        """Test successful CCXT fetch."""
        mock_exchange = MagicMock()
        # CCXT returns list of [timestamp, open, high, low, close, volume]
        ohlcv_list = [
            [
                int(pd.Timestamp(row.name).timestamp() * 1000),
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Volume"],
            ]
            for _, row in sample_ohlcv_data.head(10).iterrows()
        ]
        mock_exchange.fetch_ohlcv.return_value = ohlcv_list
        mock_binance.return_value = mock_exchange

        fetcher = DataFetcher(source="ccxt")
        df = fetcher.get_ohlcv("BTCUSD", "1d", limit=10)

        assert len(df) == 10
        assert "Close" in df.columns
        mock_exchange.fetch_ohlcv.assert_called_once()

    def test_get_ohlcv_invalid_timeframe(self, fetcher_yfinance):
        """Test handling of invalid timeframe."""
        # Invalid timeframe should raise DataFetchError after retries
        # (validate_timeframe will fail, but we still retry)
        with pytest.raises(DataFetchError) as exc_info:
            fetcher_yfinance.get_ohlcv("AAPL", "invalid_tf", limit=1)

        assert "invalid_tf" in str(exc_info.value)
        assert exc_info.value.attempts == fetcher_yfinance.retry_attempts


# =============================================================================
# Test Cases: Logging
# =============================================================================


class TestLogging:
    """Test logging functionality."""

    @patch("yfinance.Ticker")
    def test_logs_fetch_attempts(self, mock_ticker, fetcher_yfinance, tmp_path):
        """Test that fetch attempts are logged."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [95.0],
                "Close": [102.0],
                "Volume": [1000000],
            },
            index=pd.date_range("2024-01-01", periods=1),
        )
        mock_ticker.return_value = mock_instance

        fetcher_yfinance.log_dir = tmp_path / "logs"
        fetcher_yfinance._setup_logging()

        df = fetcher_yfinance.get_ohlcv("AAPL", "1d", limit=1)

        # Check log file exists
        log_file = fetcher_yfinance.log_dir / "data_fetch.log"
        assert log_file.exists()

        # Check log content
        log_content = log_file.read_text()
        assert "AAPL" in log_content
        assert "Successfully fetched" in log_content

    @patch("yfinance.Ticker")
    def test_logs_errors(self, mock_ticker, fetcher_yfinance, tmp_path):
        """Test that errors are logged."""
        mock_instance = MagicMock()
        mock_instance.history.side_effect = Exception("Test Error")
        mock_ticker.return_value = mock_instance

        fetcher_yfinance.log_dir = tmp_path / "logs"
        fetcher_yfinance._setup_logging()
        fetcher_yfinance.retry_attempts = 1

        try:
            fetcher_yfinance.get_ohlcv("AAPL", "1d", limit=1)
        except DataFetchError:
            pass

        log_file = fetcher_yfinance.log_dir / "data_fetch.log"
        log_content = log_file.read_text()
        assert "Error" in log_content or "failed" in log_content.lower()


# =============================================================================
# Test Cases: get_current_price Method
# =============================================================================


class TestGetCurrentPrice:
    """Test get_current_price method."""

    @patch("yfinance.Ticker")
    def test_get_current_price_success(self, mock_ticker):
        """Test successful price fetch."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [95.0],
                "Close": [102.5],
                "Volume": [1000000],
            },
            index=pd.date_range("2024-01-01", periods=1),
        )
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance")
        price = fetcher.get_current_price("AAPL")

        assert price == 102.5
        assert isinstance(price, float)

    @patch("yfinance.Ticker")
    def test_get_current_price_failure(self, mock_ticker):
        """Test price fetch failure."""
        mock_instance = MagicMock()
        mock_instance.history.side_effect = Exception("API Error")
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance", retry_attempts=1)

        with pytest.raises(DataFetchError, match="Price fetch failed"):
            fetcher.get_current_price("AAPL")


# =============================================================================
# Test Cases: Cleanup
# =============================================================================


class TestCleanup:
    """Test cleanup and resource management."""

    @patch("ccxt.binance")
    def test_close_ccxt_exchange(self, mock_binance):
        """Test that CCXT exchange is properly closed."""
        mock_exchange = MagicMock()
        mock_binance.return_value = mock_exchange

        fetcher = DataFetcher(source="ccxt")
        fetcher.close()

        mock_exchange.close.assert_called_once()
        assert fetcher._exchange is None

    def test_close_yfinance_no_op(self):
        """Test that close is safe for yfinance (no-op)."""
        fetcher = DataFetcher(source="yfinance")
        fetcher.close()  # Should not raise


# =============================================================================
# Test Cases: DataFrame Structure
# =============================================================================


class TestDataFrameStructure:
    """Test returned DataFrame structure."""

    @patch("yfinance.Ticker")
    def test_dataframe_columns(self, mock_ticker, sample_ohlcv_data):
        """Test that DataFrame has correct columns."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_ohlcv_data
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance")
        df = fetcher.get_ohlcv("AAPL", "1d", limit=100)

        expected_columns = ["Open", "High", "Low", "Close", "Volume"]
        assert list(df.columns) == expected_columns

    @patch("yfinance.Ticker")
    def test_dataframe_index_is_datetime(self, mock_ticker, sample_ohlcv_data):
        """Test that DataFrame index is Datetime."""
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_ohlcv_data
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance")
        df = fetcher.get_ohlcv("AAPL", "1d", limit=100)

        assert isinstance(df.index, pd.DatetimeIndex)

    @patch("yfinance.Ticker")
    def test_dataframe_sorted_chronologically(self, mock_ticker):
        """Test that DataFrame is sorted chronologically."""
        # Create unsorted data
        dates = pd.date_range("2024-01-01", periods=10, freq="D")[::-1]
        df = pd.DataFrame(
            {
                "Open": range(10),
                "High": range(10),
                "Low": range(10),
                "Close": range(10),
                "Volume": range(10),
            },
            index=dates,
        )

        mock_instance = MagicMock()
        mock_instance.history.return_value = df
        mock_ticker.return_value = mock_instance

        fetcher = DataFetcher(source="yfinance")
        result = fetcher.get_ohlcv("AAPL", "1d", limit=10)

        assert result.index.is_monotonic_increasing
