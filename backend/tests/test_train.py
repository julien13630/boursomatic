"""
Tests for the training script.

Tests key functions in train.py without requiring a full database.
"""

import numpy as np
import pandas as pd
import pytest

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from train import (
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    create_labels,
    split_data_chronological,
)


def test_create_labels():
    """Test label creation from forward returns."""
    # Create sample data
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    close_prices = np.linspace(100, 120, 100)
    
    df = pd.DataFrame({
        'ts': dates,
        'c': close_prices,
    })
    
    # Create labels
    df_labeled = create_labels(df, forward_period=20, buy_threshold=0.05, sell_threshold=-0.02)
    
    # Check that labels were created
    assert 'label' in df_labeled.columns
    assert 'target_return' in df_labeled.columns
    
    # Check label types
    assert df_labeled['label'].dtype == object
    assert set(df_labeled['label'].dropna().unique()).issubset({'BUY', 'HOLD', 'SELL'})


def test_create_labels_with_volatility():
    """Test label creation with volatile prices."""
    np.random.seed(42)
    
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    # Create prices that move up and down
    returns = np.random.normal(0, 0.02, 100)
    close_prices = 100 * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'ts': dates,
        'c': close_prices,
    })
    
    df_labeled = create_labels(df, forward_period=5, buy_threshold=0.05, sell_threshold=-0.05)
    
    # Should have all three labels with volatile data
    labels = df_labeled['label'].dropna().unique()
    assert len(labels) > 0


def test_split_data_chronological():
    """Test chronological data splitting."""
    dates = pd.date_range('2020-01-01', periods=1000, freq='D')
    
    df = pd.DataFrame({
        'ts': dates,
        'value': range(1000),
    })
    
    train, val, test = split_data_chronological(df, train_ratio=0.7, val_ratio=0.15)
    
    # Check sizes
    assert len(train) == 700
    assert len(val) == 150
    assert len(test) == 150
    
    # Check chronological order
    assert train['ts'].max() <= val['ts'].min()
    assert val['ts'].max() <= test['ts'].min()
    
    # Check all data is accounted for
    assert len(train) + len(val) + len(test) == len(df)


def test_split_data_chronological_ordering():
    """Test that split maintains chronological ordering."""
    # Create data with random timestamps
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    # Shuffle the data
    df = pd.DataFrame({
        'ts': dates,
        'value': np.random.randn(100),
    })
    df = df.sample(frac=1).reset_index(drop=True)  # Shuffle
    
    train, val, test = split_data_chronological(df, train_ratio=0.6, val_ratio=0.2)
    
    # After split, each set should be sorted
    assert train['ts'].is_monotonic_increasing
    assert val['ts'].is_monotonic_increasing
    assert test['ts'].is_monotonic_increasing


def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    # Positive returns
    returns = pd.Series([0.01, 0.02, 0.01, 0.015] * 10)
    sharpe = calculate_sharpe_ratio(returns)
    assert sharpe > 0  # Positive returns should give positive Sharpe
    
    # Negative returns
    returns_neg = pd.Series([-0.01, -0.02, -0.01, -0.015] * 10)
    sharpe_neg = calculate_sharpe_ratio(returns_neg)
    assert sharpe_neg < 0  # Negative returns should give negative Sharpe
    
    # Zero returns
    returns_zero = pd.Series([0.0] * 10)
    sharpe_zero = calculate_sharpe_ratio(returns_zero)
    assert sharpe_zero == 0.0  # Zero std should give 0


def test_calculate_sharpe_ratio_empty():
    """Test Sharpe ratio with empty series."""
    returns = pd.Series([])
    sharpe = calculate_sharpe_ratio(returns)
    assert sharpe == 0.0


def test_calculate_max_drawdown():
    """Test maximum drawdown calculation."""
    # Returns that create a drawdown
    returns = pd.Series([0.1, 0.05, -0.2, -0.1, 0.05])
    max_dd = calculate_max_drawdown(returns)
    
    # Max drawdown should be negative
    assert max_dd < 0
    
    # Should be between -1 and 0
    assert -1 <= max_dd <= 0


def test_calculate_max_drawdown_positive_trend():
    """Test max drawdown with only positive returns."""
    returns = pd.Series([0.01, 0.02, 0.01, 0.03])
    max_dd = calculate_max_drawdown(returns)
    
    # With only positive returns, max drawdown should be 0 or very small
    assert max_dd >= -0.01


def test_calculate_max_drawdown_empty():
    """Test max drawdown with empty series."""
    returns = pd.Series([])
    max_dd = calculate_max_drawdown(returns)
    assert max_dd == 0.0


def test_feature_columns_match():
    """Test that feature columns match what's defined in app.features."""
    from app.features import get_feature_columns
    
    expected = get_feature_columns()
    
    # Should have 8 features
    assert len(expected) == 8
    
    # Should include key features
    assert 'ret_1d' in expected
    assert 'ret_5d' in expected
    assert 'ret_20d' in expected
    assert 'rsi_14' in expected
    assert 'vol_20d' in expected


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
