#!/usr/bin/env python3
"""
Integration test for train.py using in-memory database with synthetic data.

This test validates the full training pipeline without requiring a real PostgreSQL database.
"""

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session, SQLModel, create_engine

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features import get_feature_columns
from app.models import Feature, Instrument, PriceBar
from train import (
    calculate_backtest_metrics,
    create_labels,
    export_artifacts,
    split_data_chronological,
    train_classifier,
    train_regressor,
)


def create_test_database():
    """Create an in-memory database with synthetic data."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    np.random.seed(42)
    
    with Session(engine) as session:
        # Create instruments
        instruments = []
        for i in range(3):
            instrument = Instrument(
                symbol=f"TEST{i:03d}",
                exchange="TEST",
                name=f"Test Stock {i}",
                is_active=True,
            )
            session.add(instrument)
            instruments.append(instrument)
        
        session.commit()
        
        # Generate data for each instrument
        n_days = 300
        start_date = datetime.now(UTC) - timedelta(days=n_days)
        
        for instrument in instruments:
            # Generate price data
            initial_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = initial_price * (1 + returns).cumprod()
            
            for day in range(n_days):
                ts = start_date + timedelta(days=day)
                price = prices[day]
                
                # Create price bar
                price_bar = PriceBar(
                    instrument_id=instrument.id,
                    ts=ts,
                    o=price,
                    h=price * 1.01,
                    l=price * 0.99,
                    c=price,
                    v=1e6,
                    interval="daily",
                )
                session.add(price_bar)
                
                # Create features (after warm-up period)
                if day >= 20:
                    ret_1d = (prices[day] / prices[day - 1] - 1) if day > 0 else 0
                    ret_5d = (prices[day] / prices[day - 5] - 1) if day >= 5 else 0
                    ret_20d = (prices[day] / prices[day - 20] - 1) if day >= 20 else 0
                    
                    feature = Feature(
                        instrument_id=instrument.id,
                        ts=ts,
                        ret_1d=ret_1d,
                        ret_5d=ret_5d,
                        ret_20d=ret_20d,
                        rsi_14=50 + np.random.uniform(-20, 20),
                        momentum_5d=ret_5d,
                        vol_20d=0.02 + np.random.uniform(-0.005, 0.005),
                        atr_14=2.0 + np.random.uniform(-0.5, 0.5),
                        volume_zscore=np.random.normal(0, 1),
                    )
                    session.add(feature)
        
        session.commit()
    
    return engine


def test_full_training_pipeline():
    """Test the complete training pipeline with synthetic data."""
    print("\n" + "=" * 80)
    print("Integration Test: Full Training Pipeline")
    print("=" * 80)
    
    # Create test database
    print("\n[1/6] Creating test database with synthetic data...")
    engine = create_test_database()
    
    # Load data from database
    print("[2/6] Loading features from database...")
    from sqlmodel import select
    
    with Session(engine) as session:
        query = (
            select(Feature, PriceBar, Instrument)
            .join(
                PriceBar,
                (Feature.instrument_id == PriceBar.instrument_id) & (Feature.ts == PriceBar.ts),
            )
            .join(Instrument, Feature.instrument_id == Instrument.id)
            .order_by(Feature.ts)
        )
        
        results = session.exec(query).all()
        
        data = []
        for feature, price_bar, _instrument in results:
            row = {
                'ts': feature.ts,
                'c': price_bar.c,
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
    
    print(f"Loaded {len(df)} feature records")
    
    # Create labels
    print("[3/6] Creating target labels...")
    df = create_labels(df, forward_period=20)
    df = df.dropna(subset=['target_return', 'label'])
    print(f"Dataset size after labels: {len(df)}")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    
    # Split data
    print("[4/6] Splitting data chronologically...")
    train_df, val_df, test_df = split_data_chronological(df, train_ratio=0.6, val_ratio=0.2)
    
    # Prepare features
    feature_cols = get_feature_columns()
    x_train = train_df[feature_cols]
    y_train_clf = train_df['label']
    y_train_reg = train_df['target_return']
    
    x_val = val_df[feature_cols]
    y_val_clf = val_df['label']
    y_val_reg = val_df['target_return']
    
    # Train classifier
    print("[5/6] Training models...")
    clf, clf_metrics = train_classifier(x_train, y_train_clf, x_val, y_val_clf)
    print(f"✓ Classifier trained: accuracy={clf_metrics['val_accuracy']:.4f}")
    
    # Train regressor
    reg, reg_metrics = train_regressor(x_train, y_train_reg, x_val, y_val_reg)
    print(f"✓ Regressor trained: RMSE={reg_metrics['val_rmse']:.4f}")
    
    # Calculate backtest metrics
    backtest_metrics = calculate_backtest_metrics(test_df, clf, feature_cols)
    print(f"✓ Backtest completed: Sharpe={backtest_metrics['sharpe_ratio']:.4f}")
    
    # Export artifacts
    print("[6/6] Exporting artifacts...")
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "test_artifacts"
        all_metrics = {**clf_metrics, **reg_metrics, **backtest_metrics}
        artifact_paths = export_artifacts(clf, reg, all_metrics, artifacts_dir)
        
        # Verify artifacts exist
        assert Path(artifact_paths['classifier_path']).exists()
        assert Path(artifact_paths['regressor_path']).exists()
        assert Path(artifact_paths['metrics_path']).exists()
        assert Path(artifact_paths['importance_path']).exists()
        
        print(f"✓ Artifacts exported to {artifacts_dir}")
        print(f"  - Classifier: {Path(artifact_paths['classifier_path']).name}")
        print(f"  - Regressor: {Path(artifact_paths['regressor_path']).name}")
        print(f"  - Metrics: {Path(artifact_paths['metrics_path']).name}")
        print(f"  - Importance: {Path(artifact_paths['importance_path']).name}")
    
    # Verify metrics
    print("\n" + "=" * 80)
    print("INTEGRATION TEST PASSED")
    print("=" * 80)
    print("\nKey Metrics:")
    print(f"  Validation Accuracy: {clf_metrics['val_accuracy']:.4f}")
    print(f"  Precision BUY: {clf_metrics['precision_buy_val']:.4f}")
    print(f"  Regressor RMSE: {reg_metrics['val_rmse']:.4f}")
    print(f"  Sharpe Ratio: {backtest_metrics['sharpe_ratio']:.4f}")
    print(f"  Max Drawdown: {backtest_metrics['max_drawdown']:.4f}")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        test_full_training_pipeline()
        print("\n✓ Integration test completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
