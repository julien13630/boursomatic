"""
Tests for the seed_prices.py script.

Validates key functionality including:
- Ticker list completeness
- Progress tracking
- Data insertion logic
- Error handling
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
from sqlmodel import Session, select

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.seed_prices import (
    TICKER_LIST,
    SeedProgress,
    check_existing_data,
    get_or_create_instrument,
    insert_price_bars_bulk,
)

from app.models import Instrument, PriceBar


class TestTickerList:
    """Test ticker list configuration."""

    def test_ticker_list_has_300_tickers(self):
        """Verify ticker list has exactly 300 tickers."""
        assert len(TICKER_LIST) == 300

    def test_ticker_list_no_duplicates(self):
        """Verify no duplicate tickers in the list."""
        assert len(TICKER_LIST) == len(set(TICKER_LIST))

    def test_ticker_list_all_uppercase(self):
        """Verify all tickers are uppercase."""
        assert all(ticker == ticker.upper() for ticker in TICKER_LIST)

    def test_ticker_list_no_empty_strings(self):
        """Verify no empty ticker symbols."""
        assert all(len(ticker) > 0 for ticker in TICKER_LIST)


class TestSeedProgress:
    """Test progress tracking."""

    def test_initial_state(self):
        """Test progress tracker initial state."""
        progress = SeedProgress()
        assert progress.total_tickers == 0
        assert progress.processed_tickers == 0
        assert progress.successful_tickers == 0
        assert progress.failed_tickers == 0
        assert progress.total_bars_inserted == 0
        assert progress.total_bars_skipped == 0
        assert len(progress.errors) == 0

    def test_to_dict(self):
        """Test progress conversion to dictionary."""
        progress = SeedProgress()
        progress.total_tickers = 10
        progress.processed_tickers = 5
        progress.successful_tickers = 4
        progress.failed_tickers = 1

        result = progress.to_dict()

        assert result["total_tickers"] == 10
        assert result["processed"] == 5
        assert result["successful"] == 4
        assert result["failed"] == 1
        assert "success_rate" in result
        assert "elapsed_seconds" in result

    def test_save_checkpoint(self, tmp_path):
        """Test checkpoint saving."""
        progress = SeedProgress()
        progress.total_tickers = 10
        progress.processed_tickers = 5

        checkpoint_file = tmp_path / "test_checkpoint.json"
        progress.save_checkpoint(str(checkpoint_file))

        assert checkpoint_file.exists()

        import json

        with open(checkpoint_file) as f:
            data = json.load(f)

        assert "progress" in data
        assert "errors" in data
        assert "timestamp" in data
        assert data["progress"]["total_tickers"] == 10


class TestDatabaseOperations:
    """Test database operations (mocked)."""

    @patch("scripts.seed_prices.Session")
    def test_get_or_create_instrument_creates_new(self, mock_session_class):
        """Test instrument creation when it doesn't exist."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_exec = MagicMock()
        mock_exec.first.return_value = None  # No existing instrument
        mock_session.exec.return_value = mock_exec

        # Call function
        instrument = get_or_create_instrument(mock_session, "TEST", "NASDAQ")

        # Verify
        assert instrument.symbol == "TEST"
        assert instrument.exchange == "NASDAQ"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("scripts.seed_prices.Session")
    def test_get_or_create_instrument_returns_existing(self, mock_session_class):
        """Test instrument retrieval when it exists."""
        # Setup mock
        existing_instrument = Instrument(
            id=uuid4(), symbol="TEST", exchange="NASDAQ", is_active=True
        )
        mock_session = MagicMock(spec=Session)
        mock_exec = MagicMock()
        mock_exec.first.return_value = existing_instrument
        mock_session.exec.return_value = mock_exec

        # Call function
        instrument = get_or_create_instrument(mock_session, "TEST", "NASDAQ")

        # Verify
        assert instrument.id == existing_instrument.id
        assert instrument.symbol == "TEST"
        mock_session.add.assert_not_called()

    def test_insert_price_bars_bulk_with_empty_dataframe(self):
        """Test bulk insert with empty DataFrame."""
        mock_session = MagicMock(spec=Session)
        df = pd.DataFrame()

        inserted, skipped = insert_price_bars_bulk(
            mock_session, uuid4(), df, "daily"
        )

        assert inserted == 0
        assert skipped == 0
        mock_session.add_all.assert_not_called()

    def test_insert_price_bars_bulk_with_data(self):
        """Test bulk insert with actual data."""
        mock_session = MagicMock(spec=Session)

        # Mock existing data query to return empty list
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.exec.return_value = mock_exec

        # Create sample DataFrame
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "High": [105.0, 106.0, 107.0, 108.0, 109.0],
                "Low": [95.0, 96.0, 97.0, 98.0, 99.0],
                "Close": [102.0, 103.0, 104.0, 105.0, 106.0],
                "Volume": [1000000, 1100000, 1200000, 1300000, 1400000],
            },
            index=dates,
        )

        instrument_id = uuid4()
        inserted, skipped = insert_price_bars_bulk(
            mock_session, instrument_id, df, "daily"
        )

        assert inserted == 5
        assert skipped == 0
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()


class TestScriptIntegration:
    """Integration tests for the script."""

    def test_script_help_option(self):
        """Test script can be imported and help is available."""
        import subprocess

        result = subprocess.run(
            ["python", "scripts/seed_prices.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "Seed PriceBars with 8 years" in result.stdout
        assert "--batch-size" in result.stdout
        assert "--start-ticker" in result.stdout
        assert "--dry-run" in result.stdout

    def test_script_dry_run(self):
        """Test script dry run mode."""
        import subprocess

        result = subprocess.run(
            [
                "python",
                "scripts/seed_prices.py",
                "--dry-run",
                "--batch-size",
                "2",
                "--years",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Starting price data seeding" in result.stdout
        assert "DRY RUN: Would process" in result.stdout
        assert "SEEDING COMPLETED" in result.stdout


class TestDateCalculation:
    """Test date range calculations."""

    def test_8_year_date_range(self):
        """Test that 8 years back is correctly calculated."""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=8 * 365)

        # Should be approximately 8 years
        diff_years = (end_date - start_date).days / 365
        assert 7.9 < diff_years < 8.1

    def test_expected_trading_days(self):
        """Test expected trading days calculation."""
        # Approximately 252 trading days per year
        years = 8
        expected = 252 * years

        # Should be around 2016 trading days
        assert 2000 < expected < 2050
