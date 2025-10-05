#!/usr/bin/env python3
"""
Test script to validate feature engineering on real ticker data.

Fetches price data for sample tickers and computes features,
logging statistics and validating completeness.
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import engine
from app.features import (
    compute_features_for_instrument,
    get_feature_columns,
    validate_features,
)
from app.models import Instrument, PriceBar
from sqlmodel import Session, select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_features.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def fetch_price_data(session: Session, instrument_id, interval: str = "daily") -> pd.DataFrame:
    """
    Fetch price data for an instrument from the database.
    
    Args:
        session: Database session
        instrument_id: Instrument UUID
        interval: Price bar interval (default: 'daily')
    
    Returns:
        DataFrame with OHLCV data
    """
    statement = (
        select(PriceBar)
        .where(PriceBar.instrument_id == instrument_id)
        .where(PriceBar.interval == interval)
        .order_by(PriceBar.ts)
    )
    
    price_bars = session.exec(statement).all()
    
    if not price_bars:
        return pd.DataFrame()
    
    # Convert to DataFrame
    data = []
    for bar in price_bars:
        data.append({
            "ts": bar.ts,
            "o": bar.o,
            "h": bar.h,
            "l": bar.l,
            "c": bar.c,
            "v": bar.v,
        })
    
    df = pd.DataFrame(data)
    df.set_index("ts", inplace=True)
    df.sort_index(inplace=True)
    
    return df


def test_features_for_ticker(session: Session, symbol: str, exchange: str = "NASDAQ") -> dict:
    """
    Test feature computation for a single ticker.
    
    Args:
        session: Database session
        symbol: Ticker symbol
        exchange: Exchange name
    
    Returns:
        Dictionary with test results
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing features for {symbol} ({exchange})")
    logger.info(f"{'='*80}")
    
    # Get instrument
    statement = (
        select(Instrument)
        .where(Instrument.symbol == symbol)
        .where(Instrument.exchange == exchange)
    )
    instrument = session.exec(statement).first()
    
    if not instrument:
        logger.warning(f"Instrument {symbol} not found in database")
        return {
            "symbol": symbol,
            "exchange": exchange,
            "status": "not_found",
        }
    
    # Fetch price data
    price_df = fetch_price_data(session, instrument.id)
    
    if price_df.empty:
        logger.warning(f"No price data found for {symbol}")
        return {
            "symbol": symbol,
            "exchange": exchange,
            "status": "no_data",
        }
    
    logger.info(f"Fetched {len(price_df)} price bars")
    logger.info(f"Date range: {price_df.index[0]} to {price_df.index[-1]}")
    
    # Compute features
    try:
        features_df = compute_features_for_instrument(price_df, nan_strategy="drop")
        
        logger.info(f"Computed features: {len(features_df)} rows")
        
        # Validate features
        stats = validate_features(features_df)
        
        logger.info("Validation results:")
        logger.info(f"  Total rows: {stats['total_rows']}")
        logger.info(f"  Valid rows: {stats['valid_rows']}")
        logger.info(f"  Coverage: {stats['coverage_pct']:.2f}%")
        
        if stats['nan_counts']:
            logger.info(f"  NaN counts: {stats['nan_counts']}")
        
        # Log summary statistics for each feature
        logger.info("\nFeature statistics:")
        for feature_name in get_feature_columns():
            if feature_name in features_df.columns:
                feat_stats = stats['summary'][feature_name]
                logger.info(
                    f"  {feature_name:15s}: "
                    f"mean={feat_stats['mean']:8.4f}, "
                    f"std={feat_stats['std']:8.4f}, "
                    f"min={feat_stats['min']:8.4f}, "
                    f"max={feat_stats['max']:8.4f}"
                )
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "status": "success",
            "price_bars": len(price_df),
            "feature_rows": len(features_df),
            "valid_rows": stats['valid_rows'],
            "coverage_pct": stats['coverage_pct'],
            "nan_counts": stats['nan_counts'],
        }
    
    except Exception as e:
        logger.error(f"Error computing features for {symbol}: {e}", exc_info=True)
        return {
            "symbol": symbol,
            "exchange": exchange,
            "status": "error",
            "error": str(e),
        }


def main():
    """Main test function."""
    logger.info("Starting feature engineering validation test")
    logger.info(f"Timestamp: {datetime.now(UTC).isoformat()}")
    
    # Sample tickers to test (mix of different sectors)
    test_tickers = [
        ("AAPL", "NASDAQ"),    # Technology
        ("MSFT", "NASDAQ"),    # Technology
        ("JPM", "NYSE"),       # Financials
        ("JNJ", "NYSE"),       # Healthcare
        ("XOM", "NYSE"),       # Energy
        ("WMT", "NYSE"),       # Consumer Staples
    ]
    
    results = []
    
    with Session(engine) as session:
        for symbol, exchange in test_tickers:
            result = test_features_for_ticker(session, symbol, exchange)
            results.append(result)
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = sum(1 for r in results if r.get("status") == "error")
    not_found_count = sum(1 for r in results if r.get("status") == "not_found")
    no_data_count = sum(1 for r in results if r.get("status") == "no_data")
    
    logger.info(f"Total tickers tested: {len(results)}")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info(f"  Not found: {not_found_count}")
    logger.info(f"  No data: {no_data_count}")
    
    # Detailed results table
    if success_count > 0:
        logger.info("\nSuccessful ticker results:")
        logger.info(
            f"{'Symbol':10s} {'Price Bars':>12s} {'Feature Rows':>14s} "
            f"{'Coverage':>10s} {'NaN Count':>10s}"
        )
        logger.info("-" * 60)
        
        for result in results:
            if result.get("status") == "success":
                total_nan = sum(result.get("nan_counts", {}).values())
                logger.info(
                    f"{result['symbol']:10s} "
                    f"{result['price_bars']:12d} "
                    f"{result['feature_rows']:14d} "
                    f"{result['coverage_pct']:9.2f}% "
                    f"{total_nan:10d}"
                )
    
    # Check if all tickers passed
    if success_count == len(test_tickers):
        logger.info("\n✓ ALL TESTS PASSED - Features computed successfully for all tickers")
        return 0
    else:
        logger.warning(f"\n⚠ SOME TESTS FAILED - {error_count + not_found_count + no_data_count} ticker(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
