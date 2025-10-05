"""
Data provider abstraction for flexible multi-source market data ingestion.

Supports Yahoo Finance (primary) and Stooq (fallback) for daily OHLCV data.
Implements retry logic, normalized symbols, and structured logging.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import pandas as pd
import requests
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure structured logging
logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """
    Abstract base class for market data providers.

    Provides interface for fetching OHLCV price data and fundamental metrics
    from various sources (Yahoo Finance, Stooq, AlphaVantage, etc.).
    """

    @abstractmethod
    def fetch_ohlcv(
        self,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data for given tickers.

        Args:
            tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"])
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (default: "1d" for daily)

        Returns:
            Dictionary mapping ticker symbols to DataFrames with OHLCV data.
            DataFrame columns: ['Open', 'High', 'Low', 'Close', 'Volume']
            DataFrame index: DatetimeIndex

        Raises:
            ValueError: If tickers list is empty or dates are invalid
            RuntimeError: If data fetch fails after retries
        """

    @abstractmethod
    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """
        Fetch fundamental data for a given ticker.

        Args:
            ticker: Ticker symbol (e.g., "AAPL")

        Returns:
            Dictionary with fundamental metrics (sector, market_cap, pe_ratio, etc.)

        Raises:
            ValueError: If ticker is invalid
            RuntimeError: If data fetch fails
        """

    def normalize_symbol(self, symbol: str, exchange: str | None = None) -> str:  # noqa: ARG002
        """
        Normalize ticker symbol for the specific provider.

        Args:
            symbol: Raw ticker symbol
            exchange: Optional exchange identifier (NYSE, NASDAQ, EURONEXT, etc.)

        Returns:
            Normalized symbol for this provider
        """
        return symbol.upper()


class YahooDataProvider(DataProvider):
    """
    Yahoo Finance data provider implementation.

    Uses yfinance library for fetching daily OHLCV data and fundamentals.
    Supports US markets (NYSE, NASDAQ) and Euronext.
    """

    def __init__(self):
        """Initialize Yahoo Finance data provider."""
        self.source_name = "Yahoo Finance"
        logger.info("Initialized YahooDataProvider")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_ohlcv(
        self,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data from Yahoo Finance.

        Implements retry logic with exponential backoff.
        """
        if not tickers:
            raise ValueError("Tickers list cannot be empty")

        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        logger.info(
            "Fetching OHLCV data",
            extra={
                "source": self.source_name,
                "tickers": tickers,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "interval": interval,
            },
        )

        result = {}

        for ticker in tickers:
            try:
                # Download data using yfinance
                data = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    progress=False,
                    auto_adjust=True,  # Adjust for splits and dividends
                )

                if data.empty:
                    logger.warning(
                        "No data returned",
                        extra={"source": self.source_name, "ticker": ticker},
                    )
                    continue

                # Standardize column names
                data.columns = ["Open", "High", "Low", "Close", "Volume"]

                # Ensure datetime index
                if not isinstance(data.index, pd.DatetimeIndex):
                    data.index = pd.to_datetime(data.index)

                result[ticker] = data

                logger.info(
                    "Successfully fetched data",
                    extra={
                        "source": self.source_name,
                        "ticker": ticker,
                        "rows": len(data),
                        "start": data.index[0].isoformat() if len(data) > 0 else None,
                        "end": data.index[-1].isoformat() if len(data) > 0 else None,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to fetch data",
                    extra={
                        "source": self.source_name,
                        "ticker": ticker,
                        "error": str(e),
                    },
                )
                # Continue with other tickers instead of failing completely
                continue

        return result

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """
        Fetch fundamental data from Yahoo Finance.

        Returns basic company information including sector, market cap, and P/E ratio.
        """
        if not ticker:
            raise ValueError("Ticker cannot be empty")

        logger.info(
            "Fetching fundamentals",
            extra={"source": self.source_name, "ticker": ticker},
        )

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            fundamentals = {
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "exchange": info.get("exchange"),
                "currency": info.get("currency"),
            }

            logger.info(
                "Successfully fetched fundamentals",
                extra={
                    "source": self.source_name,
                    "ticker": ticker,
                    "sector": fundamentals.get("sector"),
                },
            )

            return fundamentals

        except Exception as e:
            logger.error(
                "Failed to fetch fundamentals",
                extra={"source": self.source_name, "ticker": ticker, "error": str(e)},
            )
            raise RuntimeError(f"Failed to fetch fundamentals for {ticker}") from e

    def normalize_symbol(self, symbol: str, exchange: str | None = None) -> str:
        """
        Normalize symbol for Yahoo Finance.

        For Euronext stocks, append exchange suffix (e.g., "MC.PA" for Paris).
        """
        symbol = symbol.upper()

        if exchange and "EURONEXT" in exchange.upper():
            # Add Euronext suffix if not present
            if "PA" in exchange.upper() and not symbol.endswith(".PA"):
                return f"{symbol}.PA"
            if "AS" in exchange.upper() and not symbol.endswith(".AS"):
                return f"{symbol}.AS"
            if "BR" in exchange.upper() and not symbol.endswith(".BR"):
                return f"{symbol}.BR"

        return symbol


class StooqDataProvider(DataProvider):
    """
    Stooq data provider implementation as fallback.

    Uses Stooq's CSV download API for daily OHLCV data.
    Supports US and European markets.
    """

    BASE_URL = "https://stooq.com/q/d/l/"

    def __init__(self):
        """Initialize Stooq data provider."""
        self.source_name = "Stooq"
        logger.info("Initialized StooqDataProvider")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_ohlcv(
        self,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data from Stooq.

        Note: Stooq primarily supports daily data.
        """
        if not tickers:
            raise ValueError("Tickers list cannot be empty")

        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        if interval != "1d":
            logger.warning(
                "Stooq primarily supports daily data",
                extra={"interval": interval},
            )

        logger.info(
            "Fetching OHLCV data",
            extra={
                "source": self.source_name,
                "tickers": tickers,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        )

        result = {}

        for ticker in tickers:
            try:
                # Normalize ticker for Stooq format
                stooq_symbol = self.normalize_symbol(ticker)

                # Build request parameters
                params = {
                    "s": stooq_symbol,
                    "d1": start_date.strftime("%Y%m%d"),
                    "d2": end_date.strftime("%Y%m%d"),
                    "i": "d",  # daily interval
                }

                # Fetch CSV data
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()

                # Parse CSV
                from io import StringIO

                data = pd.read_csv(StringIO(response.text))

                if data.empty or len(data) < 2:  # Stooq returns header even on error
                    logger.warning(
                        "No data returned",
                        extra={"source": self.source_name, "ticker": ticker},
                    )
                    continue

                # Standardize column names (Stooq uses Date,Open,High,Low,Close,Volume)
                if "Date" in data.columns:
                    data["Date"] = pd.to_datetime(data["Date"])
                    data.set_index("Date", inplace=True)
                    data.sort_index(inplace=True)

                # Rename columns to match standard format
                column_mapping = {
                    "Open": "Open",
                    "High": "High",
                    "Low": "Low",
                    "Close": "Close",
                    "Volume": "Volume",
                }
                data = data.rename(columns=column_mapping)

                # Keep only OHLCV columns
                data = data[["Open", "High", "Low", "Close", "Volume"]]

                result[ticker] = data

                logger.info(
                    "Successfully fetched data",
                    extra={
                        "source": self.source_name,
                        "ticker": ticker,
                        "rows": len(data),
                        "start": data.index[0].isoformat() if len(data) > 0 else None,
                        "end": data.index[-1].isoformat() if len(data) > 0 else None,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to fetch data",
                    extra={
                        "source": self.source_name,
                        "ticker": ticker,
                        "error": str(e),
                    },
                )
                continue

        return result

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        """
        Fetch fundamental data from Stooq.

        Note: Stooq has limited fundamental data compared to Yahoo Finance.
        Returns minimal information.
        """
        logger.warning(
            "Stooq has limited fundamental data support",
            extra={"ticker": ticker},
        )

        # Stooq doesn't provide a straightforward API for fundamentals
        # Return minimal data structure
        return {
            "name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "pe_ratio": None,
            "exchange": None,
            "currency": None,
        }

    def normalize_symbol(self, symbol: str, exchange: str | None = None) -> str:
        """
        Normalize symbol for Stooq format.

        Stooq uses different suffixes (e.g., ".US" for US stocks, ".PL" for Polish).
        """
        symbol = symbol.upper()

        # For US stocks, add .US suffix if not present
        if exchange and exchange.upper() in ["NYSE", "NASDAQ"] and not symbol.endswith(".US"):
            return f"{symbol}.US"

        return symbol


def create_data_provider_with_fallback() -> tuple[DataProvider, DataProvider | None]:
    """
    Factory function to create primary and fallback data providers.

    Returns:
        Tuple of (primary_provider, fallback_provider)
        Primary: YahooDataProvider
        Fallback: StooqDataProvider
    """
    primary = YahooDataProvider()
    fallback = StooqDataProvider()

    logger.info(
        "Created data providers with fallback",
        extra={
            "primary": primary.source_name,
            "fallback": fallback.source_name,
        },
    )

    return primary, fallback
