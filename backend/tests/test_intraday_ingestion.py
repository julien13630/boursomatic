"""
Unit tests for intraday 15m data ingestion functionality.

Tests the intraday seeding script and 15m interval support.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from app.data_provider import YahooDataProvider


def utc_datetime(*args):
    """Create a UTC datetime for testing purposes."""
    return datetime(*args, tzinfo=UTC)


class TestIntradayDataProvider:
    """Test intraday 15m interval support."""

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_interval(self, mock_download):
        """Fetch OHLCV with 15m interval successfully."""
        # Create mock 15m data (26 bars per day for market hours)
        dates = pd.date_range(
            "2024-01-02 09:30:00", periods=26, freq="15min", tz="America/New_York"
        )
        mock_data = pd.DataFrame(
            {
                "Open": [100.0 + i * 0.1 for i in range(26)],
                "High": [100.5 + i * 0.1 for i in range(26)],
                "Low": [99.5 + i * 0.1 for i in range(26)],
                "Close": [100.2 + i * 0.1 for i in range(26)],
                "Volume": [10000 + i * 100 for i in range(26)],
            },
            index=dates,
        )
        mock_download.return_value = mock_data

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            tickers=["AAPL"],
            start_date=utc_datetime(2024, 1, 2),
            end_date=utc_datetime(2024, 1, 3),
            interval="15m",
        )

        assert "AAPL" in result
        assert len(result["AAPL"]) == 26
        assert list(result["AAPL"].columns) == ["Open", "High", "Low", "Close", "Volume"]

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_multiple_days(self, mock_download):
        """Fetch 15m data for multiple days."""
        # Create 3 days of 15m data (78 bars)
        dates = pd.date_range(
            "2024-01-02 09:30:00", periods=78, freq="15min", tz="America/New_York"
        )
        mock_data = pd.DataFrame(
            {
                "Open": [100.0 + i * 0.05 for i in range(78)],
                "High": [100.3 + i * 0.05 for i in range(78)],
                "Low": [99.7 + i * 0.05 for i in range(78)],
                "Close": [100.1 + i * 0.05 for i in range(78)],
                "Volume": [8000 + i * 50 for i in range(78)],
            },
            index=dates,
        )
        mock_download.return_value = mock_data

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            tickers=["MSFT"],
            start_date=utc_datetime(2024, 1, 2),
            end_date=utc_datetime(2024, 1, 5),
            interval="15m",
        )

        assert "MSFT" in result
        assert len(result["MSFT"]) == 78

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_rolling_30_days(self, mock_download):
        """Fetch 15m data for rolling 30-day window."""
        # Approximate 30 days * 26 bars/day = 780 bars
        num_bars = 780
        dates = pd.date_range(
            "2024-01-02 09:30:00", periods=num_bars, freq="15min", tz="America/New_York"
        )
        mock_data = pd.DataFrame(
            {
                "Open": [150.0 + (i % 100) * 0.1 for i in range(num_bars)],
                "High": [150.5 + (i % 100) * 0.1 for i in range(num_bars)],
                "Low": [149.5 + (i % 100) * 0.1 for i in range(num_bars)],
                "Close": [150.2 + (i % 100) * 0.1 for i in range(num_bars)],
                "Volume": [15000 + (i % 1000) * 10 for i in range(num_bars)],
            },
            index=dates,
        )
        mock_download.return_value = mock_data

        provider = YahooDataProvider()
        
        end_date = utc_datetime(2024, 2, 15)
        start_date = end_date - timedelta(days=30)
        
        result = provider.fetch_ohlcv(
            tickers=["GOOGL"],
            start_date=start_date,
            end_date=end_date,
            interval="15m",
        )

        assert "GOOGL" in result
        assert len(result["GOOGL"]) == num_bars
        # Verify columns are standardized
        expected_cols = ["Open", "High", "Low", "Close", "Volume"]
        assert all(col in result["GOOGL"].columns for col in expected_cols)

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_empty_data(self, mock_download):
        """Handle empty data for 15m interval gracefully."""
        mock_download.return_value = pd.DataFrame()

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            tickers=["INVALID"],
            start_date=utc_datetime(2024, 1, 1),
            end_date=utc_datetime(2024, 1, 2),
            interval="15m",
        )

        # Should return empty dict, ticker not included
        assert "INVALID" not in result

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_batch_tickers(self, mock_download):
        """Fetch 15m data for multiple tickers in batch."""
        def mock_download_side_effect(ticker, start, end, interval, progress, auto_adjust):  # noqa: ARG001
            dates = pd.date_range(
                "2024-01-02 09:30:00", periods=26, freq="15min", tz="America/New_York"
            )
            return pd.DataFrame(
                {
                    "Open": [100.0 + i for i in range(26)],
                    "High": [101.0 + i for i in range(26)],
                    "Low": [99.0 + i for i in range(26)],
                    "Close": [100.5 + i for i in range(26)],
                    "Volume": [10000 + i * 100 for i in range(26)],
                },
                index=dates,
            )

        mock_download.side_effect = mock_download_side_effect

        provider = YahooDataProvider()
        tickers = ["AAPL", "MSFT", "GOOGL"]
        result = provider.fetch_ohlcv(
            tickers=tickers,
            start_date=utc_datetime(2024, 1, 2),
            end_date=utc_datetime(2024, 1, 3),
            interval="15m",
        )

        # All tickers should be fetched
        for ticker in tickers:
            assert ticker in result
            assert len(result[ticker]) == 26

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_15m_partial_failure(self, mock_download):
        """Continue processing other tickers when one fails."""
        call_count = [0]
        
        def mock_download_side_effect(ticker, start, end, interval, progress, auto_adjust):  # noqa: ARG001
            call_count[0] += 1
            if call_count[0] == 2:  # Second ticker fails
                raise Exception("API Error")
            
            dates = pd.date_range(
                "2024-01-02 09:30:00", periods=26, freq="15min", tz="America/New_York"
            )
            return pd.DataFrame(
                {
                    "Open": [100.0] * 26,
                    "High": [101.0] * 26,
                    "Low": [99.0] * 26,
                    "Close": [100.5] * 26,
                    "Volume": [10000] * 26,
                },
                index=dates,
            )

        mock_download.side_effect = mock_download_side_effect

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            tickers=["AAPL", "FAIL", "GOOGL"],
            start_date=utc_datetime(2024, 1, 2),
            end_date=utc_datetime(2024, 1, 3),
            interval="15m",
        )

        # First and third ticker should succeed
        assert "AAPL" in result
        assert "FAIL" not in result  # Failed ticker not in result
        assert "GOOGL" in result

    def test_fetch_ohlcv_15m_validates_dates(self):
        """Validate that date validation works for 15m interval."""
        provider = YahooDataProvider()

        # Start date after end date should raise error
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            provider.fetch_ohlcv(
                tickers=["AAPL"],
                start_date=utc_datetime(2024, 1, 5),
                end_date=utc_datetime(2024, 1, 1),
                interval="15m",
            )

    def test_fetch_ohlcv_15m_validates_tickers(self):
        """Validate that empty ticker list raises error."""
        provider = YahooDataProvider()

        with pytest.raises(ValueError, match="Tickers list cannot be empty"):
            provider.fetch_ohlcv(
                tickers=[],
                start_date=utc_datetime(2024, 1, 1),
                end_date=utc_datetime(2024, 1, 5),
                interval="15m",
            )

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_supports_various_intervals(self, mock_download):
        """Test that provider supports various intervals including 15m."""
        dates_daily = pd.date_range("2024-01-01", periods=5, freq="D")
        dates_15m = pd.date_range(
            "2024-01-01 09:30:00", periods=26, freq="15min", tz="America/New_York"
        )
        
        def mock_download_side_effect(ticker, start, end, interval, progress, auto_adjust):  # noqa: ARG001
            if interval == "1d":
                return pd.DataFrame(
                    {"Open": [100.0]*5, "High": [101.0]*5, "Low": [99.0]*5, 
                     "Close": [100.5]*5, "Volume": [1000000]*5},
                    index=dates_daily,
                )
            if interval == "15m":
                return pd.DataFrame(
                    {"Open": [100.0]*26, "High": [101.0]*26, "Low": [99.0]*26,
                     "Close": [100.5]*26, "Volume": [10000]*26},
                    index=dates_15m,
                )
            return pd.DataFrame()

        mock_download.side_effect = mock_download_side_effect
        provider = YahooDataProvider()

        # Test daily
        result_daily = provider.fetch_ohlcv(
            tickers=["AAPL"],
            start_date=utc_datetime(2024, 1, 1),
            end_date=utc_datetime(2024, 1, 6),
            interval="1d",
        )
        assert "AAPL" in result_daily
        assert len(result_daily["AAPL"]) == 5

        # Test 15m
        result_15m = provider.fetch_ohlcv(
            tickers=["AAPL"],
            start_date=utc_datetime(2024, 1, 1),
            end_date=utc_datetime(2024, 1, 2),
            interval="15m",
        )
        assert "AAPL" in result_15m
        assert len(result_15m["AAPL"]) == 26
