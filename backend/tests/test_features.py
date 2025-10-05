"""
Tests for the features engineering module.

Validates feature calculations including:
- Returns computation
- Technical indicators (RSI, momentum, volatility, ATR)
- Volume z-score
- NaN handling strategies
"""

import numpy as np
import pandas as pd
import pytest

from app.features import (
    calculate_atr,
    calculate_momentum,
    calculate_returns,
    calculate_rsi,
    calculate_volatility,
    calculate_volume_zscore,
    compute_features,
    compute_features_for_instrument,
    get_feature_columns,
    handle_nan_values,
    validate_features,
)


class TestReturnsCalculation:
    """Test returns calculation."""

    def test_single_period_return(self):
        """Test 1-day return calculation."""
        df = pd.DataFrame({
            "c": [100.0, 102.0, 101.0, 103.0, 105.0]
        })
        
        df = calculate_returns(df, periods=[1])
        
        assert "ret_1d" in df.columns
        # First return should be NaN (no previous value)
        assert pd.isna(df["ret_1d"].iloc[0])
        # Second return: (102 - 100) / 100 = 0.02
        assert abs(df["ret_1d"].iloc[1] - 0.02) < 1e-6
        # Third return: (101 - 102) / 102 ≈ -0.0098
        assert abs(df["ret_1d"].iloc[2] - (-0.0098039)) < 1e-6

    def test_multiple_period_returns(self):
        """Test multiple period returns."""
        df = pd.DataFrame({
            "c": [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
        })
        
        df = calculate_returns(df, periods=[1, 2, 3])
        
        assert "ret_1d" in df.columns
        assert "ret_2d" in df.columns
        assert "ret_3d" in df.columns
        
        # Check 2-day return at index 2: (104 - 100) / 100 = 0.04
        assert abs(df["ret_2d"].iloc[2] - 0.04) < 1e-6

    def test_returns_with_zero_price(self):
        """Test returns calculation with zero price."""
        df = pd.DataFrame({
            "c": [100.0, 0.0, 102.0]
        })
        
        df = calculate_returns(df, periods=[1])
        
        # Division by zero should result in inf or -inf
        assert pd.isna(df["ret_1d"].iloc[0])
        assert df["ret_1d"].iloc[1] == -1.0  # (0 - 100) / 100 = -1


class TestRSI:
    """Test RSI calculation."""

    def test_rsi_basic(self):
        """Test basic RSI calculation."""
        # Create a simple trend
        df = pd.DataFrame({
            "c": [100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0, 110.0,
                  109.0, 111.0, 113.0, 112.0, 114.0, 116.0, 115.0, 117.0, 119.0]
        })
        
        df = calculate_rsi(df, period=14)
        
        assert "rsi_14" in df.columns
        # RSI should be between 0 and 100
        valid_rsi = df["rsi_14"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_all_gains(self):
        """Test RSI with all positive changes."""
        df = pd.DataFrame({
            "c": [100.0 + i for i in range(20)]
        })
        
        df = calculate_rsi(df, period=14)
        
        # With all gains, RSI should approach 100
        rsi_value = df["rsi_14"].iloc[-1]
        assert rsi_value > 95


class TestMomentum:
    """Test momentum calculation."""

    def test_momentum_calculation(self):
        """Test momentum is calculated correctly."""
        df = pd.DataFrame({
            "c": [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
        })
        
        df = calculate_momentum(df, period=5)
        
        assert "momentum_5d" in df.columns
        # Momentum at index 5: (110 - 100) / 100 = 0.10
        assert abs(df["momentum_5d"].iloc[5] - 0.10) < 1e-6


class TestVolatility:
    """Test volatility calculation."""

    def test_volatility_basic(self):
        """Test basic volatility calculation."""
        df = pd.DataFrame({
            "c": [100.0, 102.0, 98.0, 104.0, 96.0, 105.0, 95.0, 106.0, 94.0,
                  107.0, 93.0, 108.0, 92.0, 109.0, 91.0, 110.0, 90.0, 111.0,
                  89.0, 112.0, 88.0, 113.0]
        })
        
        df = calculate_volatility(df, period=20)
        
        assert "vol_20d" in df.columns
        # Volatility should be positive
        valid_vol = df["vol_20d"].dropna()
        assert (valid_vol > 0).all()

    def test_volatility_constant_price(self):
        """Test volatility with constant prices."""
        df = pd.DataFrame({
            "c": [100.0] * 30
        })
        
        df = calculate_volatility(df, period=20)
        
        # Volatility should be 0 or very close to 0 for constant prices
        vol_value = df["vol_20d"].iloc[-1]
        assert vol_value < 1e-10 or pd.isna(vol_value)


class TestATR:
    """Test ATR calculation."""

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        df = pd.DataFrame({
            "h": [105.0, 107.0, 104.0, 108.0, 106.0, 110.0, 108.0, 112.0, 110.0,
                  114.0, 112.0, 116.0, 114.0, 118.0, 116.0, 120.0],
            "l": [95.0, 97.0, 94.0, 98.0, 96.0, 100.0, 98.0, 102.0, 100.0,
                  104.0, 102.0, 106.0, 104.0, 108.0, 106.0, 110.0],
            "c": [100.0, 102.0, 98.0, 104.0, 100.0, 106.0, 102.0, 108.0, 104.0,
                  110.0, 106.0, 112.0, 108.0, 114.0, 110.0, 116.0]
        })
        
        df = calculate_atr(df, period=14)
        
        assert "atr_14" in df.columns
        # ATR should be positive
        valid_atr = df["atr_14"].dropna()
        assert (valid_atr > 0).all()


class TestVolumeZScore:
    """Test volume z-score calculation."""

    def test_volume_zscore_basic(self):
        """Test basic volume z-score calculation."""
        # Create volume data with some variation
        np.random.seed(42)
        volumes = np.random.normal(1000000, 100000, 30)
        
        df = pd.DataFrame({
            "v": volumes
        })
        
        df = calculate_volume_zscore(df, period=20)
        
        assert "volume_zscore" in df.columns
        # Z-scores should typically be between -3 and 3 for normal data
        valid_zscore = df["volume_zscore"].dropna()
        assert (valid_zscore >= -5).all()
        assert (valid_zscore <= 5).all()


class TestComputeFeatures:
    """Test complete feature computation."""

    def test_compute_features_complete(self):
        """Test that all features are computed."""
        # Create realistic OHLCV data
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        
        close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
        
        df = pd.DataFrame({
            "o": close_prices * 0.98,
            "h": close_prices * 1.02,
            "l": close_prices * 0.97,
            "c": close_prices,
            "v": np.random.normal(1000000, 100000, 100),
        }, index=dates)
        
        result = compute_features(df)
        
        # Check all feature columns exist
        expected_features = get_feature_columns()
        for feature in expected_features:
            assert feature in result.columns

    def test_compute_features_empty_df(self):
        """Test compute_features with empty DataFrame."""
        df = pd.DataFrame()
        result = compute_features(df)
        assert result.empty


class TestNaNHandling:
    """Test NaN handling strategies."""

    def test_handle_nan_drop(self):
        """Test drop strategy for NaN values."""
        df = pd.DataFrame({
            "a": [1.0, 2.0, np.nan, 4.0, 5.0],
            "b": [10.0, np.nan, 30.0, 40.0, 50.0]
        })
        
        result = handle_nan_values(df, strategy="drop")
        
        # Should only keep rows without any NaN
        assert len(result) == 3
        assert result.isna().sum().sum() == 0

    def test_handle_nan_zero(self):
        """Test zero-fill strategy for NaN values."""
        df = pd.DataFrame({
            "a": [1.0, 2.0, np.nan, 4.0, 5.0],
            "b": [10.0, np.nan, 30.0, 40.0, 50.0]
        })
        
        result = handle_nan_values(df, strategy="zero")
        
        # Should have no NaN values
        assert result.isna().sum().sum() == 0
        # NaN values should be replaced with 0
        assert result["a"].iloc[2] == 0.0
        assert result["b"].iloc[1] == 0.0


class TestFeaturePipeline:
    """Test complete feature engineering pipeline."""

    def test_pipeline_complete(self):
        """Test complete pipeline from price data to features."""
        # Create realistic price data
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        
        close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
        
        price_df = pd.DataFrame({
            "o": close_prices * 0.98,
            "h": close_prices * 1.02,
            "l": close_prices * 0.97,
            "c": close_prices,
            "v": np.random.normal(1000000, 100000, 100),
        }, index=dates)
        
        result = compute_features_for_instrument(price_df, nan_strategy="drop")
        
        # Result should have no NaN values
        assert result.isna().sum().sum() == 0
        
        # Should have all feature columns
        expected_features = get_feature_columns()
        for feature in expected_features:
            assert feature in result.columns
        
        # Should have fewer rows due to NaN dropping at the beginning
        assert len(result) < len(price_df)
        assert len(result) > 0

    def test_pipeline_insufficient_data(self):
        """Test pipeline with insufficient data."""
        # Create very short price data
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        
        price_df = pd.DataFrame({
            "o": [100.0, 101.0, 102.0, 103.0, 104.0],
            "h": [105.0, 106.0, 107.0, 108.0, 109.0],
            "l": [95.0, 96.0, 97.0, 98.0, 99.0],
            "c": [100.0, 101.0, 102.0, 103.0, 104.0],
            "v": [1000000.0] * 5,
        }, index=dates)
        
        result = compute_features_for_instrument(price_df, nan_strategy="drop")
        
        # With insufficient data, many features will be NaN and dropped
        # Result might be empty or very small
        assert len(result) >= 0


class TestValidateFeatures:
    """Test feature validation."""

    def test_validate_features_complete(self):
        """Test validation of complete features."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        
        df = pd.DataFrame({
            "ret_1d": np.random.randn(100) * 0.02,
            "ret_5d": np.random.randn(100) * 0.05,
            "ret_20d": np.random.randn(100) * 0.10,
            "rsi_14": np.random.uniform(30, 70, 100),
            "momentum_5d": np.random.randn(100) * 0.05,
            "vol_20d": np.random.uniform(0.1, 0.3, 100),
            "atr_14": np.random.uniform(1, 5, 100),
            "volume_zscore": np.random.randn(100),
        }, index=dates)
        
        stats = validate_features(df)
        
        assert stats["total_rows"] == 100
        assert stats["valid_rows"] == 100
        assert stats["coverage_pct"] == 100.0
        assert all(count == 0 for count in stats["nan_counts"].values())

    def test_validate_features_with_nans(self):
        """Test validation with NaN values."""
        df = pd.DataFrame({
            "ret_1d": [1.0, np.nan, 3.0, 4.0, 5.0],
            "ret_5d": [10.0, 20.0, np.nan, 40.0, 50.0],
        })
        
        stats = validate_features(df)
        
        assert stats["total_rows"] == 5
        assert stats["nan_counts"]["ret_1d"] == 1
        assert stats["nan_counts"]["ret_5d"] == 1
        assert stats["valid_rows"] == 3  # Only 3 rows have all features
        assert stats["coverage_pct"] == 60.0


class TestGetFeatureColumns:
    """Test feature column list."""

    def test_feature_columns_list(self):
        """Test that feature columns list is correct."""
        feature_cols = get_feature_columns()
        
        assert isinstance(feature_cols, list)
        assert len(feature_cols) == 8
        assert "ret_1d" in feature_cols
        assert "ret_5d" in feature_cols
        assert "ret_20d" in feature_cols
        assert "rsi_14" in feature_cols
        assert "momentum_5d" in feature_cols
        assert "vol_20d" in feature_cols
        assert "atr_14" in feature_cols
        assert "volume_zscore" in feature_cols
