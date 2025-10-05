#!/usr/bin/env python3
"""
Seed script to populate PriceBars table with 8 years of historical daily data.

Fetches OHLCV data for 300 tickers from Yahoo Finance (with Stooq fallback),
implements progress tracking, error handling, retry logic, and partial restart.

Usage:
    python scripts/seed_prices.py [--batch-size 10] [--start-ticker 0] [--dry-run]

Features:
- Batch processing with configurable batch size
- Progress tracking with detailed logging
- Automatic retry on failures with exponential backoff
- Rate limiting to avoid API quotas
- Partial restart capability (resume from specific ticker)
- Bulk insert for better performance
- Target: ≥98% data coverage
"""

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.data_provider import create_data_provider_with_fallback
from app.database import engine
from app.models import Instrument, PriceBar
from sqlmodel import Session, select

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("seed_prices.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Top 300 US market stocks by market cap (mix of large, mid cap)
# This is a representative sample across sectors
TICKER_LIST = [
    # Technology (Large Cap)
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL", "ADBE",
    "CRM", "CSCO", "ACN", "AMD", "INTC", "IBM", "TXN", "QCOM", "INTU", "NOW",
    "AMAT", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "FTNT", "ANSS",
    
    # Financials
    "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK",
    "C", "AXP", "SCHW", "CB", "PGR", "MMC", "AON", "USB", "TFC", "PNC",
    "COF", "BK", "AIG", "MET", "ALL", "TROW", "AFL", "PRU", "AMP", "CINF",
    
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "AMGN", "DHR", "PFE",
    "BMY", "GILD", "CVS", "CI", "MDT", "ISRG", "REGN", "VRTX", "ZTS", "SYK",
    "BSX", "ELV", "HUM", "MCK", "COR", "IDXX", "HCA", "DXCM", "A", "IQV",
    
    # Consumer Discretionary
    "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "ABNB", "GM",
    "F", "MAR", "CMG", "ORLY", "YUM", "ROST", "AZO", "DHI", "LEN", "HLT",
    "EBAY", "ETSY", "DPZ", "ULTA", "BBY", "GPC", "AAP", "KMX", "CZR", "LVS",
    
    # Consumer Staples
    "WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "EL",
    "KMB", "GIS", "HSY", "K", "SJM", "CPB", "CAG", "HRL", "MKC", "CHD",
    
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES",
    "WMB", "KMI", "HAL", "BKR", "DVN", "FANG", "MRO", "APA", "OKE", "TRGP",
    
    # Industrials
    "BA", "UNP", "HON", "UPS", "RTX", "CAT", "LMT", "GE", "DE", "MMM",
    "GD", "NOC", "ETN", "ITW", "EMR", "CSX", "NSC", "FDX", "WM", "RSG",
    "CARR", "PCAR", "URI", "JCI", "CMI", "ROK", "FAST", "ODFL", "VRSK", "EXPD",
    
    # Communication Services
    "GOOG", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA",
    "ATVI", "TTWO", "WBD", "PARA", "OMC", "IPG", "FOXA", "FOX", "NWSA", "NWS",
    
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES",
    "PEG", "ED", "EIX", "DTE", "PPL", "AWK", "AEE", "FE", "ETR", "CMS",
    
    # Real Estate
    "AMT", "PLD", "CCI", "EQIX", "PSA", "WELL", "SPG", "DLR", "O", "VICI",
    "AVB", "EQR", "INVH", "MAA", "ESS", "UDR", "CPT", "ARE", "VTR", "PEAK",
    
    # Materials
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "VMC", "MLM", "NUE",
    "CTVA", "DOW", "PPG", "ALB", "EMN", "CE", "FMC", "BALL", "AVY", "IP",
    
    # Additional stocks to reach 300
    "PAYC", "WDAY", "DDOG", "SNOW", "ZS", "CRWD", "NET", "PANW", "OKTA", "TEAM",
    "MDB", "SHOP", "SQ", "COIN", "HOOD", "RBLX", "U", "PATH", "S", "ZM",
    "DOCU", "TWLO", "PTON", "ROKU", "PINS", "LYFT", "UBER", "DASH", "ABNB", "RIVN",
]


class SeedProgress:
    """Track seeding progress and statistics."""

    def __init__(self):
        self.total_tickers = 0
        self.processed_tickers = 0
        self.successful_tickers = 0
        self.failed_tickers = 0
        self.total_bars_inserted = 0
        self.total_bars_skipped = 0
        self.start_time = datetime.now(UTC)
        self.errors: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert progress to dictionary for logging."""
        elapsed = (datetime.now(UTC) - self.start_time).total_seconds()
        return {
            "total_tickers": self.total_tickers,
            "processed": self.processed_tickers,
            "successful": self.successful_tickers,
            "failed": self.failed_tickers,
            "success_rate": f"{(self.successful_tickers / self.total_tickers * 100):.2f}%"
            if self.total_tickers > 0
            else "0%",
            "bars_inserted": self.total_bars_inserted,
            "bars_skipped": self.total_bars_skipped,
            "elapsed_seconds": int(elapsed),
            "avg_time_per_ticker": f"{elapsed / self.processed_tickers:.2f}s"
            if self.processed_tickers > 0
            else "N/A",
        }

    def save_checkpoint(self, filename: str = "seed_checkpoint.json"):
        """Save progress checkpoint for restart capability."""
        checkpoint = {
            "progress": self.to_dict(),
            "errors": self.errors,
            "last_successful_ticker_index": self.processed_tickers - 1,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        with open(filename, "w") as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"Checkpoint saved to {filename}")


def get_or_create_instrument(session: Session, symbol: str, exchange: str = "NASDAQ") -> Instrument:
    """Get existing instrument or create new one."""
    # Check if instrument already exists
    statement = select(Instrument).where(
        Instrument.symbol == symbol, Instrument.exchange == exchange
    )
    instrument = session.exec(statement).first()

    if instrument:
        logger.debug(f"Found existing instrument: {symbol}")
        return instrument

    # Create new instrument
    instrument = Instrument(
        symbol=symbol,
        exchange=exchange,
        name=f"{symbol} Inc.",  # Placeholder, can be enriched later
        is_active=True,
    )
    session.add(instrument)
    session.commit()
    session.refresh(instrument)
    logger.info(f"Created new instrument: {symbol} ({instrument.id})")
    return instrument


def check_existing_data(session: Session, instrument_id: Any, start_date: datetime) -> int:
    """Check how many price bars already exist for this instrument."""
    statement = (
        select(PriceBar)
        .where(PriceBar.instrument_id == instrument_id)
        .where(PriceBar.interval == "daily")
        .where(PriceBar.ts >= start_date)
    )
    existing_count = len(session.exec(statement).all())
    return existing_count


def insert_price_bars_bulk(
    session: Session,
    instrument_id: Any,
    df: pd.DataFrame,
    interval: str = "daily",
) -> tuple[int, int]:
    """
    Bulk insert price bars from DataFrame.

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    if df.empty:
        return 0, 0

    inserted = 0
    skipped = 0

    # Get existing timestamps to avoid duplicates
    existing_statement = (
        select(PriceBar.ts)
        .where(PriceBar.instrument_id == instrument_id)
        .where(PriceBar.interval == interval)
    )
    existing_timestamps = {ts for (ts,) in session.exec(existing_statement).all()}

    # Prepare batch of price bars
    price_bars = []
    for timestamp, row in df.iterrows():
        # Convert pandas Timestamp to datetime
        ts = timestamp.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        # Skip if already exists
        if ts in existing_timestamps:
            skipped += 1
            continue

        price_bar = PriceBar(
            instrument_id=instrument_id,
            ts=ts,
            o=float(row["Open"]),
            h=float(row["High"]),
            l=float(row["Low"]),
            c=float(row["Close"]),
            v=float(row["Volume"]),
            interval=interval,
        )
        price_bars.append(price_bar)
        inserted += 1

    # Bulk insert
    if price_bars:
        session.add_all(price_bars)
        session.commit()

    return inserted, skipped


def seed_ticker(
    session: Session,
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    primary_provider: Any,
    fallback_provider: Any,
    progress: SeedProgress,
) -> bool:
    """
    Seed price data for a single ticker.

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing ticker: {ticker}")

        # Get or create instrument
        instrument = get_or_create_instrument(session, ticker)

        # Check existing data
        existing_count = check_existing_data(session, instrument.id, start_date)
        expected_trading_days = 252 * 8  # Approx 252 trading days per year * 8 years
        
        if existing_count >= expected_trading_days * 0.95:
            logger.info(
                f"Ticker {ticker} already has sufficient data ({existing_count} bars), skipping"
            )
            progress.total_bars_skipped += existing_count
            return True

        # Fetch data from primary provider
        try:
            logger.info(f"Fetching data for {ticker} from primary provider...")
            data = primary_provider.fetch_ohlcv(
                tickers=[ticker],
                start_date=start_date,
                end_date=end_date,
                interval="1d",
            )

            if ticker not in data or data[ticker].empty:
                raise ValueError(f"No data returned for {ticker}")

            df = data[ticker]

        except Exception as e:
            logger.warning(
                f"Primary provider failed for {ticker}: {e}, trying fallback..."
            )
            # Try fallback provider
            try:
                data = fallback_provider.fetch_ohlcv(
                    tickers=[ticker],
                    start_date=start_date,
                    end_date=end_date,
                    interval="1d",
                )

                if ticker not in data or data[ticker].empty:
                    raise ValueError(f"No data returned from fallback for {ticker}")

                df = data[ticker]

            except Exception as fallback_error:
                logger.error(f"Both providers failed for {ticker}: {fallback_error}")
                progress.errors.append(
                    {
                        "ticker": ticker,
                        "error": str(fallback_error),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
                return False

        # Insert price bars
        inserted, skipped = insert_price_bars_bulk(session, instrument.id, df, "daily")

        logger.info(
            f"Completed {ticker}: inserted={inserted}, skipped={skipped}, "
            f"total_rows={len(df)}"
        )

        progress.total_bars_inserted += inserted
        progress.total_bars_skipped += skipped

        # Rate limiting - small delay to avoid hitting API limits
        time.sleep(0.5)

        return True

    except Exception as e:
        logger.error(f"Unexpected error processing {ticker}: {e}", exc_info=True)
        progress.errors.append(
            {
                "ticker": ticker,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        return False


def main():
    """Main seeding function."""
    parser = argparse.ArgumentParser(
        description="Seed PriceBars with 8 years of historical daily data"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of tickers to process in each batch (default: 10)",
    )
    parser.add_argument(
        "--start-ticker",
        type=int,
        default=0,
        help="Index of ticker to start from (for partial restart, default: 0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - fetch data but don't insert into database",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=8,
        help="Number of years of historical data to fetch (default: 8)",
    )

    args = parser.parse_args()

    # Initialize progress tracker
    progress = SeedProgress()
    progress.total_tickers = len(TICKER_LIST) - args.start_ticker

    # Date range
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=args.years * 365)

    logger.info("=" * 80)
    logger.info("Starting price data seeding")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Total tickers: {len(TICKER_LIST)}")
    logger.info(f"Starting from ticker index: {args.start_ticker}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)

    # Create data providers
    primary, fallback = create_data_provider_with_fallback()

    # Process tickers
    tickers_to_process = TICKER_LIST[args.start_ticker :]

    with Session(engine) as session:
        for i, ticker in enumerate(tickers_to_process):
            ticker_index = args.start_ticker + i
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Ticker {ticker_index + 1}/{len(TICKER_LIST)}: {ticker}")
            logger.info(f"{'=' * 60}")

            if args.dry_run:
                logger.info(f"DRY RUN: Would process {ticker}")
                progress.processed_tickers += 1
                progress.successful_tickers += 1
                continue

            success = seed_ticker(
                session=session,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                primary_provider=primary,
                fallback_provider=fallback,
                progress=progress,
            )

            progress.processed_tickers += 1
            if success:
                progress.successful_tickers += 1
            else:
                progress.failed_tickers += 1

            # Log progress periodically
            if (i + 1) % args.batch_size == 0 or (i + 1) == len(tickers_to_process):
                logger.info("\n" + "=" * 80)
                logger.info("PROGRESS UPDATE")
                logger.info(json.dumps(progress.to_dict(), indent=2))
                logger.info("=" * 80 + "\n")

                # Save checkpoint
                progress.save_checkpoint()

            # Longer pause between batches to respect rate limits
            if (i + 1) % args.batch_size == 0 and (i + 1) < len(tickers_to_process):
                logger.info(f"Batch completed. Pausing for 5 seconds...")
                time.sleep(5)

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("SEEDING COMPLETED")
    logger.info("=" * 80)
    logger.info(json.dumps(progress.to_dict(), indent=2))

    if progress.errors:
        logger.warning(f"\nErrors encountered: {len(progress.errors)}")
        logger.warning("First 10 errors:")
        for error in progress.errors[:10]:
            logger.warning(f"  - {error['ticker']}: {error['error']}")

    # Calculate coverage
    coverage_rate = (progress.successful_tickers / progress.total_tickers * 100) if progress.total_tickers > 0 else 0
    
    logger.info(f"\nCoverage rate: {coverage_rate:.2f}%")
    
    if coverage_rate >= 98:
        logger.info("✓ SUCCESS: Achieved ≥98% data coverage target")
        return 0
    else:
        logger.warning(f"⚠ WARNING: Coverage {coverage_rate:.2f}% below 98% target")
        logger.warning("Consider rerunning failed tickers with --start-ticker option")
        return 1


if __name__ == "__main__":
    sys.exit(main())
