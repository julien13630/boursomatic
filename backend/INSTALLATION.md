# Installation and Testing Guide

## Prerequisites

Python 3.12+ is required for this project.

## Installing Dependencies

Due to the data provider implementation, the following new dependencies are required:

```bash
cd backend
pip install -r requirements.txt
```

### New Dependencies Added

- `yfinance>=0.2.40` - Yahoo Finance API wrapper
- `pandas>=2.2.0` - Data manipulation and analysis
- `requests>=2.31.0` - HTTP library (Stooq API)
- `tenacity>=9.0.0` - Retry/exponential backoff library

## Running Tests

Once dependencies are installed, run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run only data provider tests
pytest tests/test_data_provider.py -v

# Run with coverage
pytest tests/test_data_provider.py --cov=app.data_provider --cov-report=html

# Run specific test class
pytest tests/test_data_provider.py::TestYahooDataProvider -v
```

## Linting

The code passes all ruff checks:

```bash
ruff check app/ tests/
```

All code follows:
- PEP 8 style guidelines
- Type hints for all functions/methods
- Google-style docstrings
- Maximum line length: 100 characters

## Example Usage

See `examples/data_provider_example.py` for a complete usage example:

```bash
cd backend
PYTHONPATH=. python examples/data_provider_example.py
```

## Troubleshooting

### Module Not Found Errors

If you encounter `ModuleNotFoundError` for pandas, yfinance, etc.:

```bash
pip install --user pandas yfinance requests tenacity
```

### Network/PyPI Timeout Issues

If pip times out connecting to PyPI, try:

```bash
pip install --default-timeout=300 --retries=10 -r requirements.txt
```

Or use a different mirror:

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### Import Errors in Tests

Ensure PYTHONPATH includes the backend directory:

```bash
cd backend
PYTHONPATH=. pytest tests/
```

## Implementation Status

✅ **Completed:**
- Abstract DataProvider base class with fetch_ohlcv and fetch_fundamentals
- YahooDataProvider implementation with retry logic
- StooqDataProvider fallback implementation
- Symbol normalization for US and Euronext markets
- Comprehensive unit tests with mocked API responses (33+ test cases)
- Structured logging with contextual information
- Error handling with graceful degradation
- Factory function for primary/fallback provider creation
- Documentation and usage examples

## Next Steps

After dependencies are installed, the implementation is ready for:

1. Integration with database ingestion pipeline
2. Scheduled data fetching (cron/Cloud Scheduler)
3. Historical data backfill (8 years daily)
4. Instrument catalog population
5. Feature engineering pipeline integration

See `app/DATA_PROVIDER_README.md` for detailed documentation on the implementation.
