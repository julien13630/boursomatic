# Data Provider Implementation

This module implements a flexible data provider abstraction for fetching market data from multiple sources.

## Architecture

### Abstract Base Class: `DataProvider`

The `DataProvider` class defines the interface that all data providers must implement:

- `fetch_ohlcv(tickers, start_date, end_date, interval)` - Fetch OHLCV price data
- `fetch_fundamentals(ticker)` - Fetch fundamental company data
- `normalize_symbol(symbol, exchange)` - Normalize ticker symbols for the provider

### Implementations

#### 1. YahooDataProvider (Primary)

Uses the `yfinance` library to fetch data from Yahoo Finance:

**Features:**
- Daily OHLCV data with automatic adjustment for splits/dividends
- Fundamental data (sector, market cap, P/E ratio, etc.)
- Symbol normalization for Euronext markets (.PA, .AS, .BR suffixes)
- Retry logic with exponential backoff (3 attempts)
- Structured logging with context

**Usage:**
```python
from app.data_provider import YahooDataProvider
from datetime import datetime, timezone

provider = YahooDataProvider()

# Fetch OHLCV data
data = provider.fetch_ohlcv(
    tickers=["AAPL", "MSFT"],
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
    interval="1d"
)

# Fetch fundamentals
fundamentals = provider.fetch_fundamentals("AAPL")
```

#### 2. StooqDataProvider (Fallback)

Uses Stooq's CSV download API:

**Features:**
- Daily OHLCV data for US and European markets
- Retry logic with exponential backoff (3 attempts)
- Symbol normalization for US markets (.US suffix)
- Limited fundamental data support

**Usage:**
```python
from app.data_provider import StooqDataProvider

provider = StooqDataProvider()

# Fetch OHLCV data
data = provider.fetch_ohlcv(
    tickers=["AAPL"],
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 12, 31, tzinfo=timezone.utc)
)
```

### Factory Function

The `create_data_provider_with_fallback()` function creates both primary and fallback providers:

```python
from app.data_provider import create_data_provider_with_fallback

primary, fallback = create_data_provider_with_fallback()

# Try primary, fallback to secondary if needed
try:
    data = primary.fetch_ohlcv(tickers, start, end)
except Exception as e:
    logger.warning(f"Primary provider failed: {e}, using fallback")
    data = fallback.fetch_ohlcv(tickers, start, end)
```

## Dependencies

Required packages (added to `requirements.txt`):
- `yfinance>=0.2.40` - Yahoo Finance API client
- `pandas>=2.2.0` - Data manipulation
- `requests>=2.31.0` - HTTP client for Stooq
- `tenacity>=9.0.0` - Retry logic with exponential backoff

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Testing

The module includes comprehensive unit tests with mocked API responses:

```bash
# Run all tests
pytest tests/test_data_provider.py -v

# Run specific test class
pytest tests/test_data_provider.py::TestYahooDataProvider -v

# Run with coverage
pytest tests/test_data_provider.py --cov=app.data_provider --cov-report=term-missing
```

### Test Coverage

- **Abstract Interface**: Tests that enforce implementation of required methods
- **Yahoo Provider**: 
  - Symbol normalization (US, Euronext)
  - OHLCV fetching (single/multiple tickers)
  - Empty data handling
  - Fundamental data fetching
  - Error handling
  - Retry logic
- **Stooq Provider**:
  - Symbol normalization (US markets)
  - OHLCV fetching
  - HTTP error handling
  - Limited fundamental support
- **Factory Function**: Provider creation with fallback

## Logging

All providers use structured logging with contextual information:

```python
logger.info(
    "Fetching OHLCV data",
    extra={
        "source": self.source_name,
        "tickers": tickers,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "interval": interval,
    },
)
```

Log levels:
- **INFO**: Successful operations, initialization
- **WARNING**: Empty data, fallback usage, limited support
- **ERROR**: Failed requests, API errors

## Error Handling

The providers implement graceful error handling:

1. **Validation Errors**: Raise `ValueError` for invalid inputs (empty tickers, invalid dates)
2. **Network Errors**: Retry with exponential backoff, log failures
3. **Partial Failures**: Continue processing remaining tickers if one fails
4. **API Errors**: Raise `RuntimeError` after exhausting retries

## Future Enhancements

Potential additions for future phases:

1. **Additional Providers**:
   - AlphaVantage (free tier: 25 requests/day)
   - IEX Cloud (sandbox mode for testing)
   - Finnhub (free tier available)

2. **Caching Layer**:
   - Redis integration for recently fetched data
   - TTL-based cache invalidation
   - Cache warming strategies

3. **Rate Limiting**:
   - Per-provider rate limits
   - Token bucket or sliding window algorithms
   - Backoff strategies

4. **Intraday Support**:
   - 15-minute interval data
   - Real-time streaming data
   - WebSocket connections

5. **Data Validation**:
   - Schema validation for fetched data
   - Outlier detection
   - Missing data interpolation

## Code Quality

- **Linting**: Passes `ruff` checks with strict settings
- **Type Hints**: Full type coverage with Python 3.12+ syntax
- **Documentation**: Comprehensive docstrings in Google/NumPy style
- **Testing**: High coverage with mocked external dependencies

## Notes

- The Yahoo provider automatically adjusts prices for splits and dividends (`auto_adjust=True`)
- Stooq primarily supports daily data; intraday intervals may not be available
- Both providers handle timezone-aware datetime objects
- Symbol normalization varies by provider and exchange
- Retry logic uses exponential backoff (2s, 4s, 8s) with max 3 attempts
