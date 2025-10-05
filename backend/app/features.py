"""
Feature engineering pipeline for technical indicators and returns.

Calculates features from OHLCV price data including:
- Returns (ret_1d, ret_5d, ret_20d)
- Technical indicators (RSI, momentum, volatility, ATR)
- Volume metrics (volume z-score)

Handles NaN/border values appropriately with forward-fill and dropna strategies.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_returns(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """
    Calculate percentage returns for specified periods.
    
    Args:
        df: DataFrame with 'c' (close) column
        periods: List of periods to calculate returns for (e.g., [1, 5, 20])
    
    Returns:
        DataFrame with additional ret_Nd columns
    """
    for period in periods:
        col_name = f"ret_{period}d"
        # Calculate percentage return: (close - close_N_days_ago) / close_N_days_ago
        df[col_name] = df["c"].pct_change(periods=period)
    
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Relative Strength Index (RSI).
    
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss over period
    
    Args:
        df: DataFrame with 'c' (close) column
        period: RSI period (default 14)
    
    Returns:
        DataFrame with rsi_{period} column
    """
    # Calculate price changes
    delta = df["c"].diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Calculate exponential moving average of gains and losses
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    df[f"rsi_{period}"] = rsi
    
    return df


def calculate_momentum(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """
    Calculate momentum as rate of change.
    
    Momentum = (close - close_N_days_ago) / close_N_days_ago
    
    Args:
        df: DataFrame with 'c' (close) column
        period: Momentum period (default 5)
    
    Returns:
        DataFrame with momentum_{period}d column
    """
    col_name = f"momentum_{period}d"
    # Momentum is essentially the same as returns over the period
    df[col_name] = df["c"].pct_change(periods=period)
    
    return df


def calculate_volatility(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate rolling volatility (standard deviation of returns).
    
    Args:
        df: DataFrame with 'c' (close) column
        period: Rolling window period (default 20)
    
    Returns:
        DataFrame with vol_{period}d column
    """
    # Calculate daily returns
    returns = df["c"].pct_change()
    
    # Calculate rolling standard deviation
    vol = returns.rolling(window=period, min_periods=period).std()
    
    df[f"vol_{period}d"] = vol
    
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average True Range (ATR).
    
    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    ATR = exponential moving average of True Range
    
    Args:
        df: DataFrame with 'h' (high), 'l' (low), 'c' (close) columns
        period: ATR period (default 14)
    
    Returns:
        DataFrame with atr_{period} column
    """
    # Calculate True Range components
    high_low = df["h"] - df["l"]
    high_close = (df["h"] - df["c"].shift(1)).abs()
    low_close = (df["l"] - df["c"].shift(1)).abs()
    
    # True Range is the maximum of the three
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate ATR as exponential moving average of TR
    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    
    df[f"atr_{period}"] = atr
    
    return df


def calculate_volume_zscore(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate volume z-score (standardized volume).
    
    Z-score = (volume - mean_volume) / std_volume
    
    Args:
        df: DataFrame with 'v' (volume) column
        period: Rolling window for mean and std calculation (default 20)
    
    Returns:
        DataFrame with volume_zscore column
    """
    # Calculate rolling mean and std of volume
    vol_mean = df["v"].rolling(window=period, min_periods=period).mean()
    vol_std = df["v"].rolling(window=period, min_periods=period).std()
    
    # Calculate z-score
    zscore = (df["v"] - vol_mean) / vol_std
    
    df["volume_zscore"] = zscore
    
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all features for a given price DataFrame.
    
    Args:
        df: DataFrame with OHLCV columns (o, h, l, c, v) and timestamp index
    
    Returns:
        DataFrame with all feature columns added
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to compute_features")
        return df
    
    logger.info(f"Computing features for {len(df)} rows")
    
    # Calculate returns
    df = calculate_returns(df, periods=[1, 5, 20])
    
    # Calculate technical indicators
    df = calculate_rsi(df, period=14)
    df = calculate_momentum(df, period=5)
    df = calculate_volatility(df, period=20)
    df = calculate_atr(df, period=14)
    df = calculate_volume_zscore(df, period=20)
    
    return df


def handle_nan_values(df: pd.DataFrame, strategy: str = "drop") -> pd.DataFrame:
    """
    Handle NaN values in the features DataFrame.
    
    Args:
        df: DataFrame with computed features
        strategy: Strategy for handling NaN values
            - 'drop': Drop rows with any NaN values (default)
            - 'ffill': Forward fill NaN values
            - 'bfill': Backward fill NaN values
            - 'zero': Fill NaN values with 0
    
    Returns:
        DataFrame with NaN values handled
    """
    nan_count_before = df.isna().sum().sum()
    
    if nan_count_before > 0:
        logger.info(f"Found {nan_count_before} NaN values before handling")
        logger.debug(f"NaN counts per column:\n{df.isna().sum()}")
    
    if strategy == "drop":
        df_cleaned = df.dropna()
        logger.info(f"Dropped {len(df) - len(df_cleaned)} rows with NaN values")
    elif strategy == "ffill":
        df_cleaned = df.ffill()
        logger.info("Forward filled NaN values")
    elif strategy == "bfill":
        df_cleaned = df.bfill()
        logger.info("Backward filled NaN values")
    elif strategy == "zero":
        df_cleaned = df.fillna(0)
        logger.info("Filled NaN values with 0")
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    nan_count_after = df_cleaned.isna().sum().sum()
    
    if nan_count_after > 0:
        logger.warning(f"Still have {nan_count_after} NaN values after {strategy} strategy")
    else:
        logger.info("All NaN values handled successfully")
    
    return df_cleaned


def compute_features_for_instrument(
    price_df: pd.DataFrame,
    nan_strategy: str = "drop",
) -> pd.DataFrame:
    """
    Complete feature engineering pipeline for a single instrument.
    
    Args:
        price_df: DataFrame with OHLCV data (columns: o, h, l, c, v)
                 Should have timestamp as index
        nan_strategy: Strategy for handling NaN values
    
    Returns:
        DataFrame with all features computed and NaN values handled
    """
    logger.info(f"Starting feature computation for {len(price_df)} price bars")
    
    # Make a copy to avoid modifying original
    df = price_df.copy()
    
    # Log initial shape
    logger.info(f"Initial shape: {df.shape}")
    
    # Compute all features
    df = compute_features(df)
    
    # Log shape after feature computation
    logger.info(f"Shape after feature computation: {df.shape}")
    
    # Handle NaN values
    df = handle_nan_values(df, strategy=nan_strategy)
    
    # Log final shape
    logger.info(f"Final shape: {df.shape}")
    logger.info(f"Rows dropped: {len(price_df) - len(df)}")
    
    # Verify no NaN values remain
    nan_count = df.isna().sum().sum()
    if nan_count > 0:
        logger.error(f"Feature computation completed but {nan_count} NaN values remain!")
        logger.error(f"NaN counts per column:\n{df.isna().sum()}")
    else:
        logger.info("✓ Feature computation completed with no NaN values")
    
    return df


def get_feature_columns() -> list[str]:
    """
    Get list of feature column names.
    
    Returns:
        List of feature column names
    """
    return [
        "ret_1d",
        "ret_5d",
        "ret_20d",
        "rsi_14",
        "momentum_5d",
        "vol_20d",
        "atr_14",
        "volume_zscore",
    ]


def validate_features(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validate feature DataFrame and return statistics.
    
    Args:
        df: DataFrame with computed features
    
    Returns:
        Dictionary with validation statistics
    """
    feature_cols = get_feature_columns()
    
    stats = {
        "total_rows": len(df),
        "nan_counts": {},
        "valid_rows": 0,
        "coverage_pct": 0.0,
    }
    
    # Check which feature columns exist
    existing_cols = [col for col in feature_cols if col in df.columns]
    missing_cols = [col for col in feature_cols if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"Missing feature columns: {missing_cols}")
    
    # Count NaN values per column
    for col in existing_cols:
        nan_count = df[col].isna().sum()
        stats["nan_counts"][col] = int(nan_count)
    
    # Count rows with all features valid (no NaN)
    if existing_cols:
        stats["valid_rows"] = int(df[existing_cols].notna().all(axis=1).sum())
        stats["coverage_pct"] = (stats["valid_rows"] / len(df) * 100) if len(df) > 0 else 0.0
    
    # Summary statistics for each feature
    stats["summary"] = {}
    for col in existing_cols:
        stats["summary"][col] = {
            "mean": float(df[col].mean()) if df[col].notna().any() else None,
            "std": float(df[col].std()) if df[col].notna().any() else None,
            "min": float(df[col].min()) if df[col].notna().any() else None,
            "max": float(df[col].max()) if df[col].notna().any() else None,
        }
    
    return stats
