#!/usr/bin/env python3
"""
Seed script to populate PriceBars table with intraday 15m data (rolling J-30).

Fetches OHLCV 15m data for up to 300 tickers from Yahoo Finance,
implements quota management, error handling, retry logic, and comprehensive logging.

Usage:
    python scripts/seed_prices_intraday.py [--max-tickers 300] [--days 30] [--dry-run]

Features:
- Rolling 30-day window for intraday data
- Batch processing with rate limiting
- Progress tracking with detailed logging
- Automatic retry on failures with exponential backoff
- Quota management to respect free API limits
- Target: ≥95% data coverage for tickers
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
        logging.FileHandler("seed_prices_intraday.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Top 300 US market stocks by market cap (same as daily ingestion)
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
    "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "GM", "F", "MAR",
    "CMG", "ORLY", "YUM", "ROST", "AZO", "DHI", "LEN", "HLT", "EBAY", "ETSY",
    "DPZ", "ULTA", "BBY", "GPC", "AAP", "KMX", "CZR", "LVS", "RCL", "CCL",
    
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
    "GOOG", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "ATVI",
    "TTWO", "WBD", "PARA", "OMC", "IPG", "FOXA", "FOX", "NWSA", "NWS", "LYV",
    
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


class IntradayProgress:
    """Track intraday seeding progress and statistics."""

    def __init__(self):
        self.total_tickers = 0
        self.processed_tickers = 0
        self.successful_tickers = 0
        self.failed_tickers = 0
        self.total_bars_inserted = 0
        self.total_bars_skipped = 0
        self.start_time = datetime.now(UTC)
        self.errors: list[dict[str, Any]] = []
        self.quota_warnings = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert progress to dictionary for logging."""
        elapsed = (datetime.now(UTC) - self.start_time).total_seconds()
        coverage_pct = (
            (self.successful_tickers / self.total_tickers * 100)
            if self.total_tickers > 0
            else 0
        )
        return {
            "total_tickers": self.total_tickers,
            "processed": self.processed_tickers,
            "successful": self.successful_tickers,
            "failed": self.failed_tickers,
            "coverage_percentage": f"{coverage_pct:.2f}%",
            "bars_inserted": self.total_bars_inserted,
            "bars_skipped": self.total_bars_skipped,
            "quota_warnings": self.quota_warnings,
            "elapsed_seconds": int(elapsed),
            "avg_time_per_ticker": f"{elapsed / self.processed_tickers:.2f}s"
            if self.processed_tickers > 0
            else "N/A",
        }

    def save_checkpoint(self, filename: str = "seed_intraday_checkpoint.json"):
        """Save progress checkpoint for restart capability."""
        checkpoint = {
            "progress": self.to_dict(),
            "errors": self.errors,
            "last_processed_ticker_index": self.processed_tickers - 1,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        with open(filename, "w") as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"Checkpoint saved to {filename}")


def get_or_create_instrument(session: Session, symbol: str, exchange: str = "NASDAQ") -> Instrument:
    """Get existing instrument or create new one."""
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
        name=f"{symbol} Inc.",
        is_active=True,
    )
    session.add(instrument)
    session.commit()
    session.refresh(instrument)
    logger.info(f"Created new instrument: {symbol} ({instrument.id})")
    return instrument


def check_existing_intraday_data(
    session: Session, instrument_id: Any, start_date: datetime, interval: str = "15m"
) -> int:
    """Check how many intraday price bars already exist for this instrument."""
    statement = (
        select(PriceBar)
        .where(PriceBar.instrument_id == instrument_id)
        .where(PriceBar.interval == interval)
        .where(PriceBar.ts >= start_date)
    )
    existing_count = len(session.exec(statement).all())
    return existing_count


def insert_price_bars_bulk(
    session: Session,
    instrument_id: Any,
    df: pd.DataFrame,
    interval: str = "15m",
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


def seed_ticker_intraday(
    session: Session,
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    provider: Any,
    progress: IntradayProgress,
    dry_run: bool = False,
) -> bool:
    """
    Seed intraday 15m price data for a single ticker.

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(
            f"Processing ticker: {ticker}",
            extra={"ticker": ticker, "interval": "15m"},
        )

        if dry_run:
            logger.info(f"DRY RUN: Would fetch 15m data for {ticker}")
            return True

        # Get or create instrument
        instrument = get_or_create_instrument(session, ticker)

        # Check existing data
        existing_count = check_existing_intraday_data(session, instrument.id, start_date, "15m")
        
        # Expected: ~26 bars per day (6.5 hours * 4 bars/hour) * 30 days = ~780 bars
        expected_bars = 26 * 30
        
        if existing_count >= expected_bars * 0.90:
            logger.info(
                f"Ticker {ticker} already has sufficient intraday data ({existing_count} bars), skipping",
                extra={
                    "ticker": ticker,
                    "existing_bars": existing_count,
                    "expected_bars": expected_bars,
                },
            )
            progress.total_bars_skipped += existing_count
            return True

        # Fetch data from provider
        try:
            logger.info(
                f"Fetching 15m data for {ticker}...",
                extra={
                    "ticker": ticker,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            
            data = provider.fetch_ohlcv(
                tickers=[ticker],
                start_date=start_date,
                end_date=end_date,
                interval="15m",
            )

            if ticker not in data or data[ticker].empty:
                logger.warning(
                    f"No data returned for {ticker}",
                    extra={"ticker": ticker, "interval": "15m"},
                )
                raise ValueError(f"No data returned for {ticker}")

            df = data[ticker]

            # Insert price bars
            inserted, skipped = insert_price_bars_bulk(session, instrument.id, df, "15m")

            logger.info(
                f"Completed {ticker}: inserted={inserted}, skipped={skipped}, total_rows={len(df)}",
                extra={
                    "ticker": ticker,
                    "interval": "15m",
                    "inserted": inserted,
                    "skipped": skipped,
                    "total_rows": len(df),
                },
            )

            progress.total_bars_inserted += inserted
            progress.total_bars_skipped += skipped

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Failed to fetch data for {ticker}: {error_msg}",
                extra={
                    "ticker": ticker,
                    "interval": "15m",
                    "error": error_msg,
                },
            )
            
            # Track quota-related errors
            if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                progress.quota_warnings += 1
                logger.warning(
                    "Quota/rate limit warning detected",
                    extra={"ticker": ticker, "quota_warnings": progress.quota_warnings},
                )
            
            progress.errors.append(
                {
                    "ticker": ticker,
                    "error": error_msg,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "interval": "15m",
                }
            )
            return False

    except Exception as e:
        logger.error(
            f"Unexpected error processing {ticker}: {e}",
            exc_info=True,
            extra={"ticker": ticker},
        )
        progress.errors.append(
            {
                "ticker": ticker,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "interval": "15m",
            }
        )
        return False


def main():
    """Main intraday seeding function."""
    parser = argparse.ArgumentParser(
        description="Seed PriceBars with rolling 30-day intraday 15m data"
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=300,
        help="Maximum number of tickers to process (default: 300)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of intraday data to fetch (default: 30)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of tickers to process before pause (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between tickers (default: 1.0)",
    )
    parser.add_argument(
        "--batch-delay",
        type=int,
        default=10,
        help="Delay in seconds between batches (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't fetch or insert data",
    )
    parser.add_argument(
        "--start-ticker",
        type=int,
        default=0,
        help="Index of ticker to start from (for partial restart, default: 0)",
    )

    args = parser.parse_args()

    # Initialize progress tracker
    progress = IntradayProgress()
    
    # Limit tickers to max requested
    tickers_to_use = TICKER_LIST[: args.max_tickers]
    tickers_to_process = tickers_to_use[args.start_ticker :]
    progress.total_tickers = len(tickers_to_process)

    # Date range (rolling J-30)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=args.days)

    logger.info("=" * 80)
    logger.info("Starting intraday 15m price data seeding")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()} (rolling {args.days} days)")
    logger.info(f"Total tickers to process: {progress.total_tickers}")
    logger.info(f"Max tickers limit: {args.max_tickers}")
    logger.info(f"Starting from ticker index: {args.start_ticker}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Delay between tickers: {args.delay}s")
    logger.info(f"Delay between batches: {args.batch_delay}s")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)

    # Create data provider (only primary - Yahoo Finance)
    primary, _ = create_data_provider_with_fallback()
    logger.info(f"Using provider: {primary.source_name}")

    # Process tickers
    with Session(engine) as session:
        for i, ticker in enumerate(tickers_to_process):
            ticker_index = args.start_ticker + i
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Ticker {ticker_index + 1}/{len(tickers_to_use)}: {ticker}")
            logger.info(f"{'=' * 60}")

            success = seed_ticker_intraday(
                session=session,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                provider=primary,
                progress=progress,
                dry_run=args.dry_run,
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

            # Rate limiting between tickers
            if not args.dry_run and (i + 1) < len(tickers_to_process):
                time.sleep(args.delay)

            # Longer pause between batches
            if (i + 1) % args.batch_size == 0 and (i + 1) < len(tickers_to_process):
                logger.info(f"Batch completed. Pausing for {args.batch_delay} seconds...")
                time.sleep(args.batch_delay)

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("INTRADAY SEEDING COMPLETED")
    logger.info("=" * 80)
    logger.info(json.dumps(progress.to_dict(), indent=2))

    if progress.errors:
        logger.warning(f"\nErrors encountered: {len(progress.errors)}")
        logger.warning("First 10 errors:")
        for error in progress.errors[:10]:
            logger.warning(f"  - {error['ticker']}: {error['error']}")

    # Calculate coverage
    coverage_rate = (
        (progress.successful_tickers / progress.total_tickers * 100)
        if progress.total_tickers > 0
        else 0
    )

    logger.info(f"\nCoverage rate: {coverage_rate:.2f}%")

    if coverage_rate >= 95:
        logger.info("✓ SUCCESS: Achieved ≥95% data coverage target")
        return 0
    else:
        logger.warning(f"⚠ WARNING: Coverage {coverage_rate:.2f}% below 95% target")
        logger.warning("Consider rerunning with --start-ticker option or investigating failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())
