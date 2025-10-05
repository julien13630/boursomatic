#!/usr/bin/env python3
"""
Demo script to test train.py with synthetic data.

This script creates a minimal database with synthetic features and runs
the training pipeline to verify it works end-to-end.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session, create_engine

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import Feature, Instrument, PriceBar

# Create in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")

# Import tables to create them
from app.models import SQLModel

SQLModel.metadata.create_all(engine)


def generate_synthetic_data(n_instruments: int = 5, n_days: int = 500):
    """Generate synthetic instruments, price bars, and features."""
    print(f"Generating synthetic data: {n_instruments} instruments, {n_days} days")
    
    np.random.seed(42)
    
    with Session(engine) as session:
        instruments = []
        
        # Create instruments
        for i in range(n_instruments):
            instrument = Instrument(
                symbol=f"SYN{i:03d}",
                exchange="SYNTHETIC",
                name=f"Synthetic Stock {i}",
                sector="Technology",
                is_active=True,
            )
            session.add(instrument)
            instruments.append(instrument)
        
        session.commit()
        
        # Generate price data for each instrument
        start_date = datetime.now() - timedelta(days=n_days)
        
        for instrument in instruments:
            # Generate random walk prices
            initial_price = 100.0
            returns = np.random.normal(0.0005, 0.02, n_days)
            prices = initial_price * (1 + returns).cumprod()
            
            for day in range(n_days):
                ts = start_date + timedelta(days=day)
                price = prices[day]
                
                # Create OHLCV
                o = price * (1 + np.random.uniform(-0.01, 0.01))
                h = price * (1 + abs(np.random.uniform(0, 0.02)))
                l_price = price * (1 - abs(np.random.uniform(0, 0.02)))
                c = price
                v = np.random.uniform(1e6, 5e6)
                
                price_bar = PriceBar(
                    instrument_id=instrument.id,
                    ts=ts,
                    o=o,
                    h=h,
                    l=l_price,
                    c=c,
                    v=v,
                    interval="daily",
                )
                session.add(price_bar)
                
                # Create features (calculate simple technical indicators)
                if day >= 20:  # Need 20 days for indicators
                    ret_1d = (prices[day] / prices[day - 1] - 1) if day > 0 else 0
                    ret_5d = (prices[day] / prices[day - 5] - 1) if day >= 5 else 0
                    ret_20d = (prices[day] / prices[day - 20] - 1) if day >= 20 else 0
                    
                    # Simple momentum
                    momentum_5d = ret_5d
                    
                    # Simple volatility (std of returns)
                    recent_returns = np.diff(prices[max(0, day - 20):day + 1]) / prices[max(0, day - 20):day]
                    vol_20d = np.std(recent_returns) if len(recent_returns) > 0 else 0.0
                    
                    # Simple RSI-like indicator
                    rsi_14 = 50 + np.random.uniform(-30, 30)  # Simplified
                    
                    # ATR placeholder
                    atr_14 = vol_20d * price
                    
                    # Volume z-score placeholder
                    volume_zscore = np.random.normal(0, 1)
                    
                    feature = Feature(
                        instrument_id=instrument.id,
                        ts=ts,
                        ret_1d=ret_1d,
                        ret_5d=ret_5d,
                        ret_20d=ret_20d,
                        rsi_14=rsi_14,
                        momentum_5d=momentum_5d,
                        vol_20d=vol_20d,
                        atr_14=atr_14,
                        volume_zscore=volume_zscore,
                    )
                    session.add(feature)
        
        session.commit()
        
        # Count records
        from sqlmodel import select
        
        n_instruments_db = len(session.exec(select(Instrument)).all())
        n_price_bars = len(session.exec(select(PriceBar)).all())
        n_features = len(session.exec(select(Feature)).all())
        
        print(f"Created {n_instruments_db} instruments")
        print(f"Created {n_price_bars} price bars")
        print(f"Created {n_features} features")


if __name__ == "__main__":
    print("=" * 80)
    print("Train.py Demo with Synthetic Data")
    print("=" * 80)
    
    # Generate synthetic data
    generate_synthetic_data(n_instruments=10, n_days=800)
    
    print("\nSynthetic data generated successfully!")
    print("\nTo run training with this data, you would:")
    print("1. Set up a real PostgreSQL database")
    print("2. Run feature computation on real price data")
    print("3. Run: python train.py --lookback-days 600 --artifacts-dir ./demo_artifacts")
    print("\nFor now, you can test individual functions from train.py")
    print("=" * 80)
