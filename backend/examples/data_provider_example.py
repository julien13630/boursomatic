#!/usr/bin/env python3
"""
Example script demonstrating DataProvider usage.

This script shows how to use the Yahoo and Stooq data providers
to fetch market data with fallback support.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.data_provider import create_data_provider_with_fallback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Demonstrate data provider usage."""
    
    # Create providers
    logger.info("Creating data providers...")
    primary, fallback = create_data_provider_with_fallback()
    
    # Define date range (last 30 days)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=30)
    
    # List of tickers to fetch
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    logger.info(f"Fetching data for {tickers} from {start_date.date()} to {end_date.date()}")
    
    # Try primary provider (Yahoo Finance)
    try:
        logger.info("Using primary provider (Yahoo Finance)...")
        data = primary.fetch_ohlcv(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        # Display results
        for ticker, df in data.items():
            logger.info(f"{ticker}: {len(df)} rows fetched")
            if not df.empty:
                logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}")
                logger.info(f"  Last close: ${df['Close'].iloc[-1]:.2f}")
                
    except Exception as e:
        logger.error(f"Primary provider failed: {e}")
        logger.info("Trying fallback provider (Stooq)...")
        
        try:
            data = fallback.fetch_ohlcv(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date
            )
            
            for ticker, df in data.items():
                logger.info(f"{ticker}: {len(df)} rows fetched (fallback)")
                
        except Exception as fallback_error:
            logger.error(f"Fallback provider also failed: {fallback_error}")
            return 1
    
    # Fetch fundamental data for one ticker
    logger.info("\nFetching fundamental data for AAPL...")
    try:
        fundamentals = primary.fetch_fundamentals("AAPL")
        logger.info(f"Company name: {fundamentals.get('name')}")
        logger.info(f"Sector: {fundamentals.get('sector')}")
        market_cap = fundamentals.get('market_cap')
        logger.info(f"Market cap: ${market_cap:,.0f}" if market_cap else "N/A")
        pe_ratio = fundamentals.get('pe_ratio')
        logger.info(f"P/E ratio: {pe_ratio:.2f}" if pe_ratio else "N/A")
        
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals: {e}")
    
    logger.info("\nExample completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
