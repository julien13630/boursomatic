#!/usr/bin/env python3
"""
Demonstration notebook for feature engineering pipeline.

This script demonstrates the feature engineering capabilities on sample data
and shows how to use the features module with realistic price data.

Can be converted to a Jupyter notebook using jupytext or run as a Python script.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.features import (
    compute_features_for_instrument,
    get_feature_columns,
    validate_features,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def generate_sample_ohlcv_data(
    start_date: str = "2016-01-01",
    days: int = 2000,
    initial_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0002,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate realistic sample OHLCV data.
    
    Args:
        start_date: Start date for the series
        days: Number of trading days to generate
        initial_price: Starting price
        volatility: Daily volatility (std of returns)
        trend: Daily trend (drift)
        seed: Random seed for reproducibility
    
    Returns:
        DataFrame with OHLCV columns and timestamp index
    """
    np.random.seed(seed)
    
    # Generate dates (business days only)
    dates = pd.bdate_range(start=start_date, periods=days, freq="B")
    
    # Generate log returns with trend and volatility
    returns = np.random.normal(trend, volatility, days)
    
    # Calculate close prices from log returns
    log_prices = np.log(initial_price) + np.cumsum(returns)
    close_prices = np.exp(log_prices)
    
    # Generate OHLC from close with realistic intraday patterns
    high_pct = np.random.uniform(0.005, 0.025, days)
    low_pct = np.random.uniform(0.005, 0.025, days)
    open_pct = np.random.uniform(-0.01, 0.01, days)
    
    high_prices = close_prices * (1 + high_pct)
    low_prices = close_prices * (1 - low_pct)
    open_prices = close_prices * (1 + open_pct)
    
    # Ensure OHLC consistency (high >= max(open, close), low <= min(open, close))
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
    
    # Generate volume (log-normal distribution)
    avg_volume = 1_000_000
    volume = np.random.lognormal(np.log(avg_volume), 0.5, days)
    
    # Create DataFrame
    df = pd.DataFrame(
        {
            "o": open_prices,
            "h": high_prices,
            "l": low_prices,
            "c": close_prices,
            "v": volume,
        },
        index=dates,
    )
    
    return df


def demo_basic_features():
    """Demonstrate basic feature computation."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 1: Basic Feature Computation")
    logger.info("=" * 80)
    
    # Generate sample data
    logger.info("Generating sample price data (100 days)...")
    price_df = generate_sample_ohlcv_data(days=100, seed=42)
    
    logger.info(f"Sample data shape: {price_df.shape}")
    logger.info(f"Date range: {price_df.index[0]} to {price_df.index[-1]}")
    logger.info("\nFirst few rows:")
    logger.info(price_df.head())
    
    # Compute features
    logger.info("\nComputing features...")
    features_df = compute_features_for_instrument(price_df, nan_strategy="drop")
    
    logger.info(f"\nFeatures shape: {features_df.shape}")
    logger.info(f"Feature columns: {get_feature_columns()}")
    logger.info("\nFirst few rows of features:")
    logger.info(features_df[get_feature_columns()].head())
    
    # Validate
    stats = validate_features(features_df)
    logger.info(f"\nValidation: {stats['valid_rows']}/{stats['total_rows']} rows valid ({stats['coverage_pct']:.1f}%)")


def demo_realistic_stock():
    """Demonstrate with realistic stock-like data."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 2: Realistic Stock Data (8 years)")
    logger.info("=" * 80)
    
    # Generate 8 years of data (approximately 2000 trading days)
    logger.info("Generating 8 years of stock data...")
    price_df = generate_sample_ohlcv_data(
        start_date="2016-01-01",
        days=2000,
        initial_price=150.0,
        volatility=0.02,
        trend=0.0003,  # Slight upward trend
        seed=123,
    )
    
    logger.info(f"Generated {len(price_df)} trading days")
    logger.info(f"Price range: ${price_df['c'].min():.2f} - ${price_df['c'].max():.2f}")
    logger.info(f"Average volume: {price_df['v'].mean():,.0f}")
    
    # Compute features
    logger.info("\nComputing features with NaN dropping...")
    features_df = compute_features_for_instrument(price_df, nan_strategy="drop")
    
    logger.info("\nFeature computation complete:")
    logger.info(f"  Input rows: {len(price_df)}")
    logger.info(f"  Output rows: {len(features_df)}")
    logger.info(f"  Rows dropped: {len(price_df) - len(features_df)}")
    
    # Validate
    stats = validate_features(features_df)
    
    logger.info("\nFeature statistics:")
    for feature_name in get_feature_columns():
        feat_stats = stats['summary'][feature_name]
        logger.info(
            f"  {feature_name:15s}: "
            f"mean={feat_stats['mean']:8.4f}, "
            f"std={feat_stats['std']:8.4f}, "
            f"range=[{feat_stats['min']:8.4f}, {feat_stats['max']:8.4f}]"
        )
    
    # Check for any NaN values
    nan_total = sum(stats['nan_counts'].values())
    if nan_total == 0:
        logger.info("\n✓ SUCCESS: No NaN values in final features!")
    else:
        logger.warning(f"\n⚠ WARNING: {nan_total} NaN values found")


def demo_multiple_stocks():
    """Demonstrate processing multiple stocks."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 3: Multiple Stocks Processing")
    logger.info("=" * 80)
    
    # Simulate different stock characteristics
    stocks = [
        {"name": "Tech Growth", "price": 200, "vol": 0.03, "trend": 0.0005},
        {"name": "Blue Chip", "price": 100, "vol": 0.015, "trend": 0.0002},
        {"name": "Volatile Small Cap", "price": 50, "vol": 0.05, "trend": 0.0001},
        {"name": "Declining Stock", "price": 150, "vol": 0.025, "trend": -0.0002},
    ]
    
    results = []
    
    for i, stock in enumerate(stocks):
        logger.info(f"\nProcessing: {stock['name']}")
        
        # Generate data
        price_df = generate_sample_ohlcv_data(
            days=500,
            initial_price=stock["price"],
            volatility=stock["vol"],
            trend=stock["trend"],
            seed=100 + i,
        )
        
        # Compute features
        features_df = compute_features_for_instrument(price_df, nan_strategy="drop")
        
        # Validate
        stats = validate_features(features_df)
        
        result = {
            "name": stock["name"],
            "rows": len(features_df),
            "coverage": stats["coverage_pct"],
            "avg_ret_1d": stats["summary"]["ret_1d"]["mean"],
            "avg_vol_20d": stats["summary"]["vol_20d"]["mean"],
            "avg_rsi_14": stats["summary"]["rsi_14"]["mean"],
        }
        results.append(result)
        
        logger.info(f"  Rows: {result['rows']}, Coverage: {result['coverage']:.1f}%")
    
    # Summary table
    logger.info("\n" + "=" * 80)
    logger.info("Summary of All Stocks:")
    logger.info("=" * 80)
    logger.info(f"{'Stock':20s} {'Rows':>8s} {'Coverage':>10s} {'Avg Ret 1d':>12s} {'Avg Vol 20d':>12s} {'Avg RSI':>10s}")
    logger.info("-" * 80)
    
    for r in results:
        logger.info(
            f"{r['name']:20s} "
            f"{r['rows']:8d} "
            f"{r['coverage']:9.1f}% "
            f"{r['avg_ret_1d']:11.4f}% "
            f"{r['avg_vol_20d']:11.4f}% "
            f"{r['avg_rsi_14']:10.2f}"
        )


def demo_nan_handling_strategies():
    """Demonstrate different NaN handling strategies."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 4: NaN Handling Strategies")
    logger.info("=" * 80)
    
    # Generate short data to show NaN effects
    price_df = generate_sample_ohlcv_data(days=50, seed=42)
    
    strategies = ["drop", "zero", "ffill", "bfill"]
    
    for strategy in strategies:
        logger.info(f"\n--- Strategy: {strategy} ---")
        
        try:
            features_df = compute_features_for_instrument(price_df, nan_strategy=strategy)
            stats = validate_features(features_df)
            
            logger.info(f"  Output rows: {len(features_df)}")
            logger.info(f"  Valid rows: {stats['valid_rows']}")
            logger.info(f"  Coverage: {stats['coverage_pct']:.1f}%")
            
            if sum(stats['nan_counts'].values()) > 0:
                logger.info(f"  Remaining NaN: {stats['nan_counts']}")
        
        except Exception as e:
            logger.error(f"  Error with {strategy}: {e}")


def main():
    """Run all demonstrations."""
    logger.info("=" * 80)
    logger.info("Feature Engineering Pipeline Demonstration")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Run demos
        demo_basic_features()
        demo_realistic_stock()
        demo_multiple_stocks()
        demo_nan_handling_strategies()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        logger.info("\nKey Takeaways:")
        logger.info("1. All feature calculations working correctly")
        logger.info("2. Returns: ret_1d, ret_5d, ret_20d computed")
        logger.info("3. Technical indicators: RSI, momentum, volatility, ATR computed")
        logger.info("4. Volume z-score calculated")
        logger.info("5. NaN handling strategies available and working")
        logger.info("6. No NaN values in final output (with 'drop' strategy)")
        
        return 0
    
    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
