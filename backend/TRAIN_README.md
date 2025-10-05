# Training Script Documentation

## Overview

The `train.py` script implements the complete machine learning training pipeline for the Boursomatic trading recommendation system. It trains two LightGBM models:

1. **Classifier**: Multi-class model for BUY/HOLD/SELL recommendations
2. **Regressor**: Continuous model for expected return prediction

## Features

### Data Processing
- Loads features from database with configurable lookback period
- Creates target labels based on forward returns
- Chronological train/validation/test split (70/15/15)
- Handles NaN values automatically

### Model Training
- LightGBM classifier for multi-class prediction (BUY/HOLD/SELL)
- LightGBM regressor for expected return prediction
- Fixed random seed for reproducibility
- Hyperparameters optimized for financial time series

### Metrics Logged
- **Classification**: Accuracy, Precision (especially for BUY class)
- **Regression**: RMSE, MAE, R²
- **Backtest**: Sharpe Ratio, Maximum Drawdown, Total Return
- Full classification report for validation and test sets

### Artifacts Exported
- Trained classifier model (pickle)
- Trained regressor model (pickle)
- Metrics JSON file
- Feature importance CSV
- Model version saved to database

## Usage

### Basic Usage

```bash
cd backend
python train.py
```

### With Options

```bash
# Train with custom lookback period
python train.py --lookback-days 1500

# Train with custom artifacts directory
python train.py --artifacts-dir ./my_models

# Full example
python train.py --lookback-days 2000 --artifacts-dir ./models/production
```

### Command-Line Arguments

- `--lookback-days DAYS`: Number of days to look back for training data (default: 2000, ~8 years)
- `--artifacts-dir DIR`: Directory to save model artifacts (default: `artifacts`)

## Prerequisites

### Database Requirements
- PostgreSQL database with computed features
- Features table populated with technical indicators
- PriceBar table with daily OHLCV data
- Instruments table with stock metadata

To populate features, run:
```bash
# First, seed price data
python scripts/seed_prices.py

# Then compute features (assuming you have a feature computation script)
python scripts/compute_features.py
```

### Dependencies
All required packages are in `requirements.txt`:
- `lightgbm>=4.0.0`
- `scikit-learn>=1.3.0`
- `numpy>=1.26.0`
- `pandas>=2.2.0`
- `sqlmodel>=0.0.22`

## Training Pipeline Steps

1. **Load Features**: Queries database for features within lookback period
2. **Create Labels**: Generates BUY/HOLD/SELL labels based on 20-day forward returns
   - BUY: Forward return ≥ 5%
   - SELL: Forward return ≤ -2%
   - HOLD: Everything else
3. **Split Data**: Chronological split (train/val/test = 70/15/15)
4. **Train Classifier**: LightGBM multi-class model
5. **Train Regressor**: LightGBM regression model for expected returns
6. **Calculate Metrics**: Backtest on test set with Sharpe, Drawdown, Precision
7. **Export Artifacts**: Save models, metrics, and feature importance

## Output

### Console Logs
```
[1/7] Loading features from database...
[2/7] Creating target labels...
[3/7] Splitting data chronologically...
[4/7] Training classifier...
[5/7] Training regressor...
[6/7] Calculating backtest metrics...
[7/7] Exporting artifacts...

Key Metrics:
  Precision BUY (test): 0.4521
  Sharpe Ratio: 1.2345
  Max Drawdown: -0.1234
  Test Accuracy: 0.5678
  Regressor RMSE: 0.0342
```

### Artifacts Directory Structure
```
artifacts/
├── classifier_20240105_143022.pkl      # Trained classifier
├── regressor_20240105_143022.pkl       # Trained regressor
├── metrics_20240105_143022.json        # All metrics
└── feature_importance_20240105_143022.csv  # Feature rankings
```

### Database Record
A `ModelVersion` record is created with:
- Unique version timestamp
- Parameters hash for reproducibility
- All metrics in JSON format
- Path to artifacts
- `is_active=True` flag (previous models deactivated)

## Metrics Explained

### Precision BUY
The most important metric for the MVP. Measures what percentage of BUY recommendations actually resulted in profitable returns. Higher is better (>0.4 is good for stock predictions).

### Sharpe Ratio
Risk-adjusted returns of the trading strategy. Calculated from simulated returns based on model predictions:
- > 1.0: Good
- > 2.0: Excellent
- < 0: Strategy loses money

Formula: `(Mean Return - Risk Free Rate) / Std Dev of Returns` (annualized)

### Maximum Drawdown
Largest peak-to-trough decline in cumulative returns. Measures worst-case loss:
- Closer to 0 is better
- -0.20 = 20% max loss from peak
- Important for risk management

## Customization

### Label Thresholds
Edit in `create_labels()`:
```python
buy_threshold=0.05   # 5% gain for BUY
sell_threshold=-0.02  # 2% loss for SELL
```

### Model Hyperparameters
Edit in `train_classifier()` and `train_regressor()`:
```python
n_estimators=100      # Number of boosting rounds
learning_rate=0.05    # Step size
max_depth=5           # Tree depth
num_leaves=31         # Complexity
```

### Train/Val/Test Split
Edit in `split_data_chronological()`:
```python
train_ratio=0.7   # 70% train
val_ratio=0.15    # 15% validation
# test is implicit: 15%
```

## Testing

Run unit tests:
```bash
pytest tests/test_train.py -v
```

Tests cover:
- Label creation
- Data splitting
- Sharpe ratio calculation
- Maximum drawdown calculation
- Feature consistency

## Reproducibility

The script ensures reproducibility through:
- Fixed random seed (`RANDOM_SEED = 42`)
- Deterministic LightGBM training
- Parameters hash stored in database
- Chronological (not random) data splits

## Troubleshooting

### "No features found in database"
- Run feature computation first
- Check database connection in `.env`
- Verify lookback period includes data

### Out of Memory
- Reduce `--lookback-days`
- Train on smaller instrument subset
- Increase system memory

### Poor Metrics
- Check label distribution (need balanced classes)
- Verify features have low NaN count
- Consider longer lookback period
- Tune hyperparameters

## Next Steps

After training:
1. Review metrics in artifacts directory
2. Check `model_versions` table in database
3. Use trained models for inference
4. Monitor model performance over time
5. Retrain periodically as new data arrives

## Related Files

- `app/models.py`: Database models (ModelVersion, Feature)
- `app/features.py`: Feature engineering functions
- `tests/test_train.py`: Unit tests for training functions
- `requirements.txt`: Python dependencies
