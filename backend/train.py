#!/usr/bin/env python3
"""
Training script for LightGBM classifier and regressor models.

This script:
1. Loads features from the database
2. Creates target labels (BUY/HOLD/SELL) based on future returns
3. Splits data chronologically (train/val/test)
4. Trains LightGBM classifier (multi-class) and regressor
5. Logs key metrics (Precision BUY, Sharpe ratio, Max Drawdown)
6. Exports model artifacts and saves to database

Usage:
    python train.py [--lookback-days DAYS] [--artifacts-dir DIR]
"""

import argparse
import hashlib
import json
import logging
import pickle
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, precision_score
from sqlmodel import Session, select

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.features import get_feature_columns
from app.models import Feature, Instrument, ModelVersion, PriceBar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set random seed for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from returns.
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default 0.0)
    
    Returns:
        Sharpe ratio (annualized)
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    # Annualize assuming daily returns
    mean_return = returns.mean() * 252
    std_return = returns.std() * np.sqrt(252)
    
    return (mean_return - risk_free_rate) / std_return


def calculate_max_drawdown(returns: pd.Series) -> float:
    """
    Calculate maximum drawdown from returns.
    
    Args:
        returns: Series of returns
    
    Returns:
        Maximum drawdown as a percentage (negative value)
    """
    if len(returns) == 0:
        return 0.0
    
    # Calculate cumulative returns
    cumulative = (1 + returns).cumprod()
    
    # Calculate running maximum
    running_max = cumulative.expanding().max()
    
    # Calculate drawdown
    drawdown = (cumulative - running_max) / running_max
    
    return drawdown.min()


def create_labels(
    df: pd.DataFrame,
    forward_period: int = 20,
    buy_threshold: float = 0.05,
    sell_threshold: float = -0.02,
) -> pd.DataFrame:
    """
    Create target labels (BUY/HOLD/SELL) based on forward returns.
    
    Args:
        df: DataFrame with price data and features
        forward_period: Days to look forward (default 20)
        buy_threshold: Minimum return for BUY label (default 5%)
        sell_threshold: Maximum return for SELL label (default -2%)
    
    Returns:
        DataFrame with 'label' and 'target_return' columns added
    """
    # Calculate forward return
    df = df.copy()
    df['target_return'] = df['c'].pct_change(periods=forward_period).shift(-forward_period)
    
    # Create labels
    conditions = [
        df['target_return'] >= buy_threshold,
        df['target_return'] <= sell_threshold,
    ]
    choices = ['BUY', 'SELL']
    df['label'] = np.select(conditions, choices, default='HOLD')
    
    return df


def load_features_from_db(
    lookback_days: int = 2000,
) -> pd.DataFrame:
    """
    Load features from database.
    
    Args:
        lookback_days: Number of days to look back (default 2000 for ~8 years)
    
    Returns:
        DataFrame with features and price data
    """
    logger.info(f"Loading features from database (lookback: {lookback_days} days)")
    
    cutoff_date = datetime.now(UTC) - timedelta(days=lookback_days)
    
    with Session(engine) as session:
        # Load features with instrument and price data
        query = (
            select(Feature, PriceBar, Instrument)
            .join(
                PriceBar,
                (Feature.instrument_id == PriceBar.instrument_id) & (Feature.ts == PriceBar.ts),
            )
            .join(Instrument, Feature.instrument_id == Instrument.id)
            .where(Feature.ts >= cutoff_date)
            .where(PriceBar.interval == "daily")
            .order_by(Feature.ts)
        )
        
        results = session.exec(query).all()
        
        if not results:
            raise ValueError("No features found in database. Please run feature computation first.")
        
        logger.info(f"Loaded {len(results)} feature records")
        
        # Convert to DataFrame
        data = []
        for feature, price_bar, instrument in results:
            row = {
                'ts': feature.ts,
                'instrument_id': str(feature.instrument_id),
                'symbol': instrument.symbol,
                'c': price_bar.c,  # close price for label calculation
                'ret_1d': feature.ret_1d,
                'ret_5d': feature.ret_5d,
                'ret_20d': feature.ret_20d,
                'rsi_14': feature.rsi_14,
                'momentum_5d': feature.momentum_5d,
                'vol_20d': feature.vol_20d,
                'atr_14': feature.atr_14,
                'volume_zscore': feature.volume_zscore,
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Remove any remaining NaN values
        initial_rows = len(df)
        df = df.dropna()
        logger.info(f"Dropped {initial_rows - len(df)} rows with NaN values")
        
        return df


def split_data_chronological(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data chronologically into train/val/test sets.
    
    Args:
        df: DataFrame with features
        train_ratio: Ratio for training set (default 0.7)
        val_ratio: Ratio for validation set (default 0.15)
    
    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    # Sort by timestamp
    df = df.sort_values('ts').reset_index(drop=True)
    
    # Calculate split indices
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    logger.info(f"Split data: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
    logger.info(f"Train period: {train_df['ts'].min()} to {train_df['ts'].max()}")
    logger.info(f"Val period: {val_df['ts'].min()} to {val_df['ts'].max()}")
    logger.info(f"Test period: {test_df['ts'].min()} to {test_df['ts'].max()}")
    
    return train_df, val_df, test_df


def train_classifier(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_val: pd.DataFrame,
    y_val: pd.Series,
) -> tuple[lgb.LGBMClassifier, dict[str, Any]]:
    """
    Train LightGBM classifier for BUY/HOLD/SELL prediction.
    
    Args:
        x_train: Training features
        y_train: Training labels
        x_val: Validation features
        y_val: Validation labels
    
    Returns:
        Tuple of (trained model, metrics dict)
    """
    logger.info("Training LightGBM classifier...")
    
    # Create and train classifier
    clf = lgb.LGBMClassifier(
        objective='multiclass',
        num_class=3,
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        verbose=-1,
    )
    
    clf.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        eval_metric='multi_logloss',
    )
    
    # Calculate metrics
    y_pred_train = clf.predict(x_train)
    y_pred_val = clf.predict(x_val)
    
    train_acc = accuracy_score(y_train, y_pred_train)
    val_acc = accuracy_score(y_val, y_pred_val)
    
    # Calculate precision for BUY class
    try:
        precision_buy_val = precision_score(y_val, y_pred_val, labels=['BUY'], average=None)[0]
    except Exception:
        precision_buy_val = 0.0
    
    metrics = {
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'precision_buy_val': float(precision_buy_val),
    }
    
    logger.info(f"Classifier metrics: {metrics}")
    logger.info("\nValidation Classification Report:")
    logger.info("\n" + classification_report(y_val, y_pred_val, zero_division=0))
    
    return clf, metrics


def train_regressor(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_val: pd.DataFrame,
    y_val: pd.Series,
) -> tuple[lgb.LGBMRegressor, dict[str, Any]]:
    """
    Train LightGBM regressor for expected return prediction.
    
    Args:
        x_train: Training features
        y_train: Training target returns
        x_val: Validation features
        y_val: Validation target returns
    
    Returns:
        Tuple of (trained model, metrics dict)
    """
    logger.info("Training LightGBM regressor...")
    
    # Create and train regressor
    reg = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        verbose=-1,
    )
    
    reg.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        eval_metric='rmse',
    )
    
    # Calculate metrics
    y_pred_val = reg.predict(x_val)
    
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    
    mae = mean_absolute_error(y_val, y_pred_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
    r2 = r2_score(y_val, y_pred_val)
    
    metrics = {
        'val_mae': float(mae),
        'val_rmse': float(rmse),
        'val_r2': float(r2),
    }
    
    logger.info(f"Regressor metrics: {metrics}")
    
    return reg, metrics


def calculate_backtest_metrics(
    test_df: pd.DataFrame,
    clf: lgb.LGBMClassifier,
    feature_cols: list[str],
) -> dict[str, Any]:
    """
    Calculate backtest metrics on test set.
    
    Args:
        test_df: Test DataFrame with features and labels
        clf: Trained classifier
        feature_cols: List of feature column names
    
    Returns:
        Dictionary with backtest metrics
    """
    logger.info("Calculating backtest metrics on test set...")
    
    x_test = test_df[feature_cols]
    y_test = test_df['label']
    
    # Get predictions
    y_pred = clf.predict(x_test)
    
    # Test accuracy
    test_acc = accuracy_score(y_test, y_pred)
    
    # Precision for BUY
    try:
        precision_buy_test = precision_score(y_test, y_pred, labels=['BUY'], average=None)[0]
    except Exception:
        precision_buy_test = 0.0
    
    # Simulate strategy returns
    # BUY: hold for forward_period, SELL: short for forward_period, HOLD: no position
    strategy_returns = []
    for pred, actual_return in zip(y_pred, test_df['target_return'], strict=False):
        if pred == 'BUY':
            strategy_returns.append(actual_return)
        elif pred == 'SELL':
            strategy_returns.append(-actual_return)  # Short position
        else:  # HOLD
            strategy_returns.append(0.0)
    
    strategy_returns = pd.Series(strategy_returns)
    
    # Remove NaN values (from end of series)
    strategy_returns = strategy_returns.dropna()
    
    # Calculate Sharpe ratio and Max Drawdown
    sharpe = calculate_sharpe_ratio(strategy_returns)
    max_dd = calculate_max_drawdown(strategy_returns)
    
    metrics = {
        'test_accuracy': float(test_acc),
        'precision_buy_test': float(precision_buy_test),
        'sharpe_ratio': float(sharpe),
        'max_drawdown': float(max_dd),
        'mean_return': float(strategy_returns.mean()),
        'total_return': float((1 + strategy_returns).prod() - 1),
    }
    
    logger.info(f"Backtest metrics: {metrics}")
    logger.info(f"  Precision BUY: {precision_buy_test:.4f}")
    logger.info(f"  Sharpe Ratio: {sharpe:.4f}")
    logger.info(f"  Max Drawdown: {max_dd:.4f}")
    
    return metrics


def export_artifacts(
    clf: lgb.LGBMClassifier,
    reg: lgb.LGBMRegressor,
    metrics: dict[str, Any],
    artifacts_dir: Path,
) -> dict[str, str]:
    """
    Export model artifacts to disk.
    
    Args:
        clf: Trained classifier
        reg: Trained regressor
        metrics: Combined metrics dictionary
        artifacts_dir: Directory to save artifacts
    
    Returns:
        Dictionary with artifact paths
    """
    logger.info(f"Exporting artifacts to {artifacts_dir}")
    
    # Create artifacts directory
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate version timestamp
    version = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    
    # Save classifier
    clf_path = artifacts_dir / f"classifier_{version}.pkl"
    with open(clf_path, 'wb') as f:
        pickle.dump(clf, f)
    logger.info(f"Saved classifier to {clf_path}")
    
    # Save regressor
    reg_path = artifacts_dir / f"regressor_{version}.pkl"
    with open(reg_path, 'wb') as f:
        pickle.dump(reg, f)
    logger.info(f"Saved regressor to {reg_path}")
    
    # Save metrics
    metrics_path = artifacts_dir / f"metrics_{version}.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics to {metrics_path}")
    
    # Save feature importance
    feature_importance = pd.DataFrame({
        'feature': get_feature_columns(),
        'importance': clf.feature_importances_,
    }).sort_values('importance', ascending=False)
    
    importance_path = artifacts_dir / f"feature_importance_{version}.csv"
    feature_importance.to_csv(importance_path, index=False)
    logger.info(f"Saved feature importance to {importance_path}")
    
    return {
        'classifier_path': str(clf_path),
        'regressor_path': str(reg_path),
        'metrics_path': str(metrics_path),
        'importance_path': str(importance_path),
        'version': version,
    }


def save_model_version_to_db(
    version: str,
    metrics: dict[str, Any],
    model_path: str,
) -> None:
    """
    Save model version to database.
    
    Args:
        version: Model version string
        metrics: Metrics dictionary
        model_path: Path to model artifacts
    """
    logger.info("Saving model version to database...")
    
    # Calculate params hash for reproducibility
    params = {
        'random_seed': RANDOM_SEED,
        'n_estimators': 100,
        'learning_rate': 0.05,
        'max_depth': 5,
    }
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()
    
    with Session(engine) as session:
        # Deactivate all existing models
        existing_models = session.exec(
            select(ModelVersion).where(ModelVersion.is_active)
        ).all()
        for model in existing_models:
            model.is_active = False
            session.add(model)
        
        # Create new model version
        model_version = ModelVersion(
            version=version,
            params_hash=params_hash,
            metrics_json=metrics,
            model_path=model_path,
            is_active=True,
        )
        
        session.add(model_version)
        session.commit()
        
        logger.info(f"Saved model version {version} to database (id: {model_version.id})")


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(
        description="Train LightGBM models for trading recommendations"
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=2000,
        help='Number of days to look back for training data (default: 2000)',
    )
    parser.add_argument(
        '--artifacts-dir',
        type=str,
        default='artifacts',
        help='Directory to save model artifacts (default: artifacts)',
    )
    
    args = parser.parse_args()
    
    artifacts_dir = Path(args.artifacts_dir)
    
    logger.info("=" * 80)
    logger.info("Starting LightGBM Training Pipeline")
    logger.info("=" * 80)
    logger.info(f"Random seed: {RANDOM_SEED}")
    logger.info(f"Lookback days: {args.lookback_days}")
    logger.info(f"Artifacts directory: {artifacts_dir}")
    
    try:
        # Step 1: Load features from database
        logger.info("\n[1/7] Loading features from database...")
        df = load_features_from_db(lookback_days=args.lookback_days)
        
        # Step 2: Create target labels
        logger.info("\n[2/7] Creating target labels...")
        df = create_labels(df)
        
        # Remove rows without target (end of series)
        df = df.dropna(subset=['target_return', 'label'])
        logger.info(f"Dataset size after label creation: {len(df)} rows")
        
        # Log label distribution
        label_dist = df['label'].value_counts()
        logger.info(f"Label distribution:\n{label_dist}")
        
        # Step 3: Split data chronologically
        logger.info("\n[3/7] Splitting data chronologically...")
        train_df, val_df, test_df = split_data_chronological(df)
        
        # Prepare features and labels
        feature_cols = get_feature_columns()
        
        x_train = train_df[feature_cols]
        y_train_clf = train_df['label']
        y_train_reg = train_df['target_return']
        
        x_val = val_df[feature_cols]
        y_val_clf = val_df['label']
        y_val_reg = val_df['target_return']
        
        # Step 4: Train classifier
        logger.info("\n[4/7] Training classifier...")
        clf, clf_metrics = train_classifier(x_train, y_train_clf, x_val, y_val_clf)
        
        # Step 5: Train regressor
        logger.info("\n[5/7] Training regressor...")
        reg, reg_metrics = train_regressor(x_train, y_train_reg, x_val, y_val_reg)
        
        # Step 6: Calculate backtest metrics
        logger.info("\n[6/7] Calculating backtest metrics...")
        backtest_metrics = calculate_backtest_metrics(test_df, clf, feature_cols)
        
        # Combine all metrics
        all_metrics = {
            **clf_metrics,
            **reg_metrics,
            **backtest_metrics,
        }
        
        # Step 7: Export artifacts
        logger.info("\n[7/7] Exporting artifacts...")
        artifact_paths = export_artifacts(clf, reg, all_metrics, artifacts_dir)
        
        # Save to database
        save_model_version_to_db(
            version=artifact_paths['version'],
            metrics=all_metrics,
            model_path=str(artifacts_dir),
        )
        
        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Version: {artifact_paths['version']}")
        logger.info(f"Artifacts saved to: {artifacts_dir}")
        logger.info("\nKey Metrics:")
        logger.info(f"  Precision BUY (test): {all_metrics['precision_buy_test']:.4f}")
        logger.info(f"  Sharpe Ratio: {all_metrics['sharpe_ratio']:.4f}")
        logger.info(f"  Max Drawdown: {all_metrics['max_drawdown']:.4f}")
        logger.info(f"  Test Accuracy: {all_metrics['test_accuracy']:.4f}")
        logger.info(f"  Regressor RMSE: {all_metrics['val_rmse']:.4f}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
