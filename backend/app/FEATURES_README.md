# Features Engineering Module

This module provides a comprehensive feature engineering pipeline for technical analysis and machine learning on financial time series data.

## Overview

The `features.py` module calculates various technical indicators and derived metrics from OHLCV (Open, High, Low, Close, Volume) price data. It includes robust NaN handling, logging, and validation capabilities.

## Features Computed

### Returns
- **ret_1d**: 1-day percentage return
- **ret_5d**: 5-day percentage return
- **ret_20d**: 20-day percentage return

### Technical Indicators
- **rsi_14**: Relative Strength Index (14-period)
- **momentum_5d**: 5-day momentum (rate of change)
- **vol_20d**: 20-day rolling volatility (standard deviation of returns)
- **atr_14**: Average True Range (14-period)

### Volume Metrics
- **volume_zscore**: Standardized volume (z-score over 20-day window)

## Usage

### Basic Usage

```python
import pandas as pd
from app.features import compute_features_for_instrument

# Load OHLCV data
price_df = pd.DataFrame({
    'o': [...],  # open prices
    'h': [...],  # high prices
    'l': [...],  # low prices
    'c': [...],  # close prices
    'v': [...],  # volume
}, index=pd.DatetimeIndex([...]))

# Compute all features
features_df = compute_features_for_instrument(price_df, nan_strategy='drop')

# Result contains all OHLCV columns plus computed features
print(features_df.columns)
# ['o', 'h', 'l', 'c', 'v', 'ret_1d', 'ret_5d', 'ret_20d', 
#  'rsi_14', 'momentum_5d', 'vol_20d', 'atr_14', 'volume_zscore']
```

### Individual Feature Functions

You can also compute features individually:

```python
from app.features import (
    calculate_returns,
    calculate_rsi,
    calculate_momentum,
    calculate_volatility,
    calculate_atr,
    calculate_volume_zscore,
)

# Calculate just returns
df = calculate_returns(price_df, periods=[1, 5, 20])

# Calculate just RSI
df = calculate_rsi(price_df, period=14)

# And so on...
```

### NaN Handling Strategies

The pipeline supports multiple strategies for handling NaN values that appear at the beginning of the time series (due to rolling windows):

```python
# Drop rows with any NaN values (default, recommended)
features_df = compute_features_for_instrument(price_df, nan_strategy='drop')

# Fill NaN values with zeros
features_df = compute_features_for_instrument(price_df, nan_strategy='zero')

# Forward fill NaN values
features_df = compute_features_for_instrument(price_df, nan_strategy='ffill')

# Backward fill NaN values
features_df = compute_features_for_instrument(price_df, nan_strategy='bfill')
```

**Note**: The `'drop'` strategy is recommended for ML training as it ensures clean data without artificial fill values.

### Validation

Validate computed features and get statistics:

```python
from app.features import validate_features

stats = validate_features(features_df)

print(f"Total rows: {stats['total_rows']}")
print(f"Valid rows: {stats['valid_rows']}")
print(f"Coverage: {stats['coverage_pct']:.1f}%")
print(f"NaN counts: {stats['nan_counts']}")
print(f"Feature statistics: {stats['summary']}")
```

## Technical Details

### Returns Calculation
Returns are calculated as percentage changes:
```
ret_N = (close_t - close_{t-N}) / close_{t-N}
```

### RSI Calculation
Relative Strength Index uses exponential moving averages:
```
RSI = 100 - (100 / (1 + RS))
where RS = EMA(gains) / EMA(losses)
```

### Volatility Calculation
Volatility is the rolling standard deviation of daily returns:
```
vol_N = std(returns) over N-day window
```

### ATR Calculation
Average True Range uses exponential moving average of true range:
```
True Range = max(high - low, |high - prev_close|, |low - prev_close|)
ATR = EMA(True Range)
```

### Volume Z-Score
Standardized volume over rolling window:
```
volume_zscore = (volume - mean(volume)) / std(volume)
```

## Expected Data Shape

### Input Requirements
- **Minimum rows**: At least 20 rows recommended (for 20-day indicators)
- **Columns**: Must have `o`, `h`, `l`, `c`, `v` (OHLCV)
- **Index**: Should be DatetimeIndex (sorted chronologically)

### Output Shape
- With `'drop'` strategy: Approximately **input_rows - 20** (depends on longest window)
- With other strategies: Same as input_rows

### NaN Patterns
The number of initial NaN values depends on the indicator window:
- 1-day indicators: 1 NaN
- 5-day indicators: 5 NaN
- 14-day indicators: ~14 NaN
- 20-day indicators: 20 NaN

Using the `'drop'` strategy removes all rows with any NaN, resulting in approximately 20 fewer rows than the input.

## Logging

The module uses Python's standard logging framework. Configure logging in your application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now feature computation will log:
# - Initial data shape
# - NaN counts before/after handling
# - Final data shape
# - Validation results
```

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/test_features.py -v
```

All 19 tests should pass, covering:
- Returns calculation
- RSI computation
- Momentum calculation
- Volatility measurement
- ATR calculation
- Volume z-score
- Complete pipeline
- NaN handling strategies
- Feature validation

### Run Demonstration

```bash
python scripts/demo_features.py
```

This demonstrates:
1. Basic feature computation
2. Realistic 8-year stock data
3. Multiple stock processing
4. NaN handling strategies

### Test on Database Tickers

```bash
python scripts/test_features.py
```

This tests feature computation on actual ticker data from the database.

## Performance

### Computational Complexity
- **Returns**: O(n) - single pass
- **RSI**: O(n) - exponential moving average
- **Momentum**: O(n) - single pass
- **Volatility**: O(n × window) - rolling calculation
- **ATR**: O(n) - exponential moving average
- **Volume Z-score**: O(n × window) - rolling calculation

**Overall**: O(n × window) where window = 20 for most indicators

### Typical Performance
- **100 rows**: < 0.01 seconds
- **1,000 rows**: < 0.05 seconds
- **10,000 rows**: < 0.5 seconds

## Examples

See:
- `scripts/demo_features.py` - Comprehensive demonstrations
- `backend/tests/test_features.py` - Unit test examples
- `scripts/test_features.py` - Database integration example

## Dependencies

- **pandas**: DataFrame operations and rolling calculations
- **numpy**: (indirectly via pandas) numerical operations

Both are already included in `backend/requirements.txt`.

## Best Practices

1. **Always use 'drop' strategy for ML training** - Ensures clean data without artificial values
2. **Validate features before use** - Use `validate_features()` to check for NaN values
3. **Log transformations** - Enable INFO logging to track data transformations
4. **Check coverage** - Ensure sufficient valid rows after feature computation
5. **Monitor edge cases** - Very short time series (< 20 rows) may have limited features

## Troubleshooting

### "All features are NaN"
- Check that input DataFrame has enough rows (minimum 20-30 recommended)
- Verify OHLCV columns are named correctly (`o`, `h`, `l`, `c`, `v`)
- Ensure data is sorted chronologically

### "Too many rows dropped"
- This is expected for short time series
- 20-day indicators require 20 initial rows before they can be computed
- Consider using longer historical data

### "Features don't match model schema"
- Use `get_feature_columns()` to get the list of computed features
- Ensure database schema matches computed features
- Check that additional_features JSON field is used for custom features

## Integration with Database

To store features in the database:

```python
from app.database import engine
from app.models import Feature
from sqlmodel import Session

# Compute features
features_df = compute_features_for_instrument(price_df, nan_strategy='drop')

# Store in database
with Session(engine) as session:
    for timestamp, row in features_df.iterrows():
        feature = Feature(
            instrument_id=instrument_id,
            ts=timestamp,
            ret_1d=row['ret_1d'],
            ret_5d=row['ret_5d'],
            ret_20d=row['ret_20d'],
            rsi_14=row['rsi_14'],
            momentum_5d=row['momentum_5d'],
            vol_20d=row['vol_20d'],
            atr_14=row['atr_14'],
            volume_zscore=row['volume_zscore'],
        )
        session.add(feature)
    
    session.commit()
```

## Future Enhancements

Potential additions:
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Stochastic Oscillator
- On-Balance Volume
- Additional momentum indicators
- Sector/market relative features
- Correlation features
