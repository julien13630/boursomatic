"""
Unit tests for data providers with mocked responses.

Tests the abstract DataProvider interface, YahooDataProvider, and StooqDataProvider
implementations with proper mocking to avoid actual API calls.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests

from app.data_provider import (
    DataProvider,
    StooqDataProvider,
    YahooDataProvider,
    create_data_provider_with_fallback,
)


# Helper function for creating UTC datetimes in tests
def utc_datetime(*args):
    """Create a UTC datetime for testing purposes."""
    return datetime(*args, tzinfo=UTC)


class TestDataProviderInterface:
    """Test abstract DataProvider interface."""

    def test_cannot_instantiate_abstract_class(self):
        """DataProvider is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataProvider()  # type: ignore

    def test_subclass_must_implement_fetch_ohlcv(self):
        """Subclass must implement fetch_ohlcv method."""

        class IncompleteProvider(DataProvider):
            def fetch_fundamentals(self, ticker: str):  # noqa: ARG002
                return {}

        with pytest.raises(TypeError):
            IncompleteProvider()  # type: ignore

    def test_subclass_must_implement_fetch_fundamentals(self):
        """Subclass must implement fetch_fundamentals method."""

        class IncompleteProvider(DataProvider):
            def fetch_ohlcv(self, tickers, start_date, end_date, interval="1d"):  # noqa: ARG002
                return {}

        with pytest.raises(TypeError):
            IncompleteProvider()  # type: ignore


class TestYahooDataProvider:
    """Test YahooDataProvider implementation."""

    def test_initialization(self):
        """Provider initializes correctly."""
        provider = YahooDataProvider()
        assert provider.source_name == "Yahoo Finance"

    def test_normalize_symbol_us_stock(self):
        """US stocks are normalized without suffix."""
        provider = YahooDataProvider()
        assert provider.normalize_symbol("aapl") == "AAPL"
        assert provider.normalize_symbol("MSFT", "NYSE") == "MSFT"

    def test_normalize_symbol_euronext_paris(self):
        """Euronext Paris stocks get .PA suffix."""
        provider = YahooDataProvider()
        assert provider.normalize_symbol("MC", "EURONEXT_PARIS") == "MC.PA"
        assert provider.normalize_symbol("MC.PA", "EURONEXT_PARIS") == "MC.PA"

    def test_normalize_symbol_euronext_amsterdam(self):
        """Euronext Amsterdam stocks get .AS suffix."""
        provider = YahooDataProvider()
        assert provider.normalize_symbol("ASML", "EURONEXT_AMSTERDAM") == "ASML.AS"

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_success_single_ticker(self, mock_download):
        """Fetch OHLCV for single ticker successfully."""
        # Create mock DataFrame
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        mock_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "High": [101.0, 102.0, 103.0, 104.0, 105.0],
                "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
                "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
                "Volume": [1000000, 1100000, 1200000, 1300000, 1400000],
            },
            index=dates,
        )
        mock_download.return_value = mock_data

        provider = YahooDataProvider()
        start = utc_datetime(2024, 1, 1)
        end = utc_datetime(2024, 1, 5)

        result = provider.fetch_ohlcv(["AAPL"], start, end)

        assert "AAPL" in result
        assert len(result["AAPL"]) == 5
        assert list(result["AAPL"].columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert isinstance(result["AAPL"].index, pd.DatetimeIndex)

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_success_multiple_tickers(self, mock_download):
        """Fetch OHLCV for multiple tickers."""
        dates = pd.date_range("2024-01-01", periods=3, freq="D")

        def mock_download_func(ticker, **kwargs):  # noqa: ARG001
            base_price = 100.0 if ticker == "AAPL" else 200.0
            return pd.DataFrame(
                {
                    "Open": [base_price, base_price + 1, base_price + 2],
                    "High": [base_price + 1, base_price + 2, base_price + 3],
                    "Low": [base_price - 1, base_price, base_price + 1],
                    "Close": [base_price + 0.5, base_price + 1.5, base_price + 2.5],
                    "Volume": [1000000, 1100000, 1200000],
                },
                index=dates,
            )

        mock_download.side_effect = mock_download_func

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            ["AAPL", "MSFT"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 3),
        )

        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result
        assert result["AAPL"]["Close"].iloc[0] == 100.5
        assert result["MSFT"]["Close"].iloc[0] == 200.5

    @patch("app.data_provider.yf.download")
    def test_fetch_ohlcv_empty_data(self, mock_download):
        """Handle empty data response gracefully."""
        mock_download.return_value = pd.DataFrame()

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            ["INVALID"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 5),
        )

        assert result == {}

    def test_fetch_ohlcv_empty_tickers(self):
        """Raise error when tickers list is empty."""
        provider = YahooDataProvider()

        with pytest.raises(ValueError, match="Tickers list cannot be empty"):
            provider.fetch_ohlcv([], utc_datetime(2024, 1, 1), utc_datetime(2024, 1, 5))

    def test_fetch_ohlcv_invalid_dates(self):
        """Raise error when start_date is after end_date."""
        provider = YahooDataProvider()

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            provider.fetch_ohlcv(
                ["AAPL"],
                utc_datetime(2024, 1, 5),
                utc_datetime(2024, 1, 1),
            )

    @patch("app.data_provider.yf.Ticker")
    def test_fetch_fundamentals_success(self, mock_ticker_class):
        """Fetch fundamentals successfully."""
        mock_ticker = Mock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3000000000000,
            "trailingPE": 30.5,
            "exchange": "NASDAQ",
            "currency": "USD",
        }
        mock_ticker_class.return_value = mock_ticker

        provider = YahooDataProvider()
        result = provider.fetch_fundamentals("AAPL")

        assert result["name"] == "Apple Inc."
        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"
        assert result["market_cap"] == 3000000000000
        assert result["pe_ratio"] == 30.5
        assert result["exchange"] == "NASDAQ"
        assert result["currency"] == "USD"

    @patch("app.data_provider.yf.Ticker")
    def test_fetch_fundamentals_partial_data(self, mock_ticker_class):
        """Handle partial fundamental data gracefully."""
        mock_ticker = Mock()
        mock_ticker.info = {
            "shortName": "Apple",
            "sector": "Technology",
            # Missing other fields
        }
        mock_ticker_class.return_value = mock_ticker

        provider = YahooDataProvider()
        result = provider.fetch_fundamentals("AAPL")

        assert result["name"] == "Apple"
        assert result["sector"] == "Technology"
        assert result["market_cap"] is None
        assert result["pe_ratio"] is None

    def test_fetch_fundamentals_empty_ticker(self):
        """Raise error when ticker is empty."""
        provider = YahooDataProvider()

        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            provider.fetch_fundamentals("")

    @patch("app.data_provider.yf.Ticker")
    def test_fetch_fundamentals_api_error(self, mock_ticker_class):
        """Handle API errors when fetching fundamentals."""
        mock_ticker_class.side_effect = Exception("API Error")

        provider = YahooDataProvider()

        with pytest.raises(RuntimeError, match="Failed to fetch fundamentals"):
            provider.fetch_fundamentals("AAPL")


class TestStooqDataProvider:
    """Test StooqDataProvider implementation."""

    def test_initialization(self):
        """Provider initializes correctly."""
        provider = StooqDataProvider()
        assert provider.source_name == "Stooq"

    def test_normalize_symbol_us_stock(self):
        """US stocks get .US suffix."""
        provider = StooqDataProvider()
        assert provider.normalize_symbol("AAPL", "NYSE") == "AAPL.US"
        assert provider.normalize_symbol("AAPL.US", "NYSE") == "AAPL.US"
        assert provider.normalize_symbol("MSFT", "NASDAQ") == "MSFT.US"

    def test_normalize_symbol_other_exchange(self):
        """Non-US stocks remain unchanged."""
        provider = StooqDataProvider()
        assert provider.normalize_symbol("MC", "EURONEXT") == "MC"

    @patch("app.data_provider.requests.get")
    def test_fetch_ohlcv_success(self, mock_get):
        """Fetch OHLCV successfully from Stooq."""
        csv_data = """Date,Open,High,Low,Close,Volume
2024-01-01,100.0,101.0,99.0,100.5,1000000
2024-01-02,101.0,102.0,100.0,101.5,1100000
2024-01-03,102.0,103.0,101.0,102.5,1200000"""

        mock_response = Mock()
        mock_response.text = csv_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        provider = StooqDataProvider()
        result = provider.fetch_ohlcv(
            ["AAPL"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 3),
        )

        assert "AAPL" in result
        assert len(result["AAPL"]) == 3
        assert list(result["AAPL"].columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert result["AAPL"]["Close"].iloc[0] == 100.5

    @patch("app.data_provider.requests.get")
    def test_fetch_ohlcv_empty_response(self, mock_get):
        """Handle empty response from Stooq."""
        mock_response = Mock()
        mock_response.text = "Date,Open,High,Low,Close,Volume\n"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        provider = StooqDataProvider()
        result = provider.fetch_ohlcv(
            ["INVALID"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 3),
        )

        assert result == {}

    @patch("app.data_provider.requests.get")
    def test_fetch_ohlcv_http_error(self, mock_get):
        """Handle HTTP errors gracefully."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        provider = StooqDataProvider()
        result = provider.fetch_ohlcv(
            ["AAPL"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 3),
        )

        # Should return empty dict instead of crashing
        assert result == {}

    def test_fetch_ohlcv_empty_tickers(self):
        """Raise error when tickers list is empty."""
        provider = StooqDataProvider()

        with pytest.raises(ValueError, match="Tickers list cannot be empty"):
            provider.fetch_ohlcv([], utc_datetime(2024, 1, 1), utc_datetime(2024, 1, 5))

    def test_fetch_ohlcv_invalid_dates(self):
        """Raise error when start_date is after end_date."""
        provider = StooqDataProvider()

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            provider.fetch_ohlcv(
                ["AAPL"],
                utc_datetime(2024, 1, 5),
                utc_datetime(2024, 1, 1),
            )

    def test_fetch_fundamentals_limited_support(self):
        """Stooq returns minimal fundamental data."""
        provider = StooqDataProvider()
        result = provider.fetch_fundamentals("AAPL")

        # Should return structure with None values
        assert result["name"] is None
        assert result["sector"] is None
        assert result["market_cap"] is None
        assert "exchange" in result


class TestCreateDataProviderWithFallback:
    """Test factory function for creating providers."""

    def test_creates_primary_and_fallback(self):
        """Factory creates both primary and fallback providers."""
        primary, fallback = create_data_provider_with_fallback()

        assert isinstance(primary, YahooDataProvider)
        assert isinstance(fallback, StooqDataProvider)
        assert primary.source_name == "Yahoo Finance"
        assert fallback.source_name == "Stooq"


class TestRetryLogic:
    """Test retry logic for providers."""

    @patch("app.data_provider.yf.download")
    def test_yahoo_retry_on_failure(self, mock_download):
        """Yahoo provider retries on failure."""
        # Fail twice, succeed on third attempt
        mock_download.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [101.0],
                    "Low": [99.0],
                    "Close": [100.5],
                    "Volume": [1000000],
                },
                index=pd.date_range("2024-01-01", periods=1),
            ),
        ]

        provider = YahooDataProvider()
        result = provider.fetch_ohlcv(
            ["AAPL"],
            utc_datetime(2024, 1, 1),
            utc_datetime(2024, 1, 1),
        )

        # Should succeed after retries
        assert "AAPL" in result
        assert mock_download.call_count == 3

    @patch("app.data_provider.yf.download")
    def test_yahoo_fails_after_max_retries(self, mock_download):
        """Yahoo provider fails after max retries."""
        mock_download.side_effect = Exception("Persistent error")

        provider = YahooDataProvider()

        # Should raise after max retries
        with pytest.raises(Exception, match="Persistent error"):
            provider.fetch_ohlcv(
                ["AAPL"],
                utc_datetime(2024, 1, 1),
                utc_datetime(2024, 1, 1),
            )

        # Should have attempted 3 times
        assert mock_download.call_count == 3
