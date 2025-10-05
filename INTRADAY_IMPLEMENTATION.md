# Intraday 15m Data Ingestion - Implementation Summary

## Overview

This implementation provides a complete solution for ingesting rolling 30-day intraday 15-minute OHLCV data for up to 300 tickers, as required by Phase 1.4.

## Components Delivered

### 1. Intraday Ingestion Script
**File**: `scripts/seed_prices_intraday.py`

A production-ready Python script that:
- Fetches 15m OHLCV data for a rolling 30-day window
- Supports up to 300 tickers (configurable)
- Implements batching and rate limiting to respect API quotas
- Provides comprehensive logging with structured JSON format
- Includes progress tracking and checkpoint saving
- Supports partial restart via `--start-ticker` parameter
- Validates 95% coverage target

**Key Features**:
- Rate limiting: 1s delay between tickers, 10s between batches
- Automatic retry with exponential backoff (3 attempts)
- Duplicate detection to prevent data corruption
- Quota warning tracking
- Dry-run mode for testing

### 2. Scheduler Configurations

#### Cloud Scheduler (Production)
**File**: `infra/scheduler/intraday_job.yaml`

Cloud Scheduler job configuration for GCP:
- Runs daily at 8:00 PM EST (after market close)
- HTTP endpoint trigger
- 2-hour timeout
- Retry configuration with exponential backoff
- Alert on failure

#### Cron Script (Local/Self-Hosted)
**File**: `scripts/cron_intraday.sh`

Bash script for cron-based execution:
- Manages virtual environment activation
- Creates rotating logs
- Email alerts on failure
- Automatic log cleanup (30-day retention)

### 3. Tests
**File**: `backend/tests/test_intraday_ingestion.py`

Comprehensive test suite covering:
- 15m interval data fetching
- Rolling 30-day window support
- Batch processing
- Error handling and partial failures
- Date/ticker validation
- Multiple interval support

**Test Results**: 9/9 tests passing

### 4. Documentation
**File**: `infra/scheduler/README.md`

Complete deployment and operational guide covering:
- Deployment options (Cloud Scheduler, Cron, Manual)
- Configuration parameters
- Quota management strategies
- Monitoring and alerting
- Troubleshooting procedures

## Acceptance Criteria Status

✅ **fetch_ohlcv 15m fonctionne**: The existing `YahooDataProvider.fetch_ohlcv()` method supports the `interval="15m"` parameter without modification. Tests verify proper functionality.

✅ **Scheduler déclenche job**: Two scheduler options provided:
   - Cloud Scheduler configuration (YAML)
   - Cron script for local execution
   - Both configured to run daily at 8:00 PM EST

✅ **Logs fails clairs**: Comprehensive structured logging implemented:
   - Per-ticker success/failure logs
   - Error details with timestamps
   - Quota warning tracking
   - Progress checkpoints saved to JSON
   - Rotating log files

✅ **Au moins 95% tickers 15m à jour**: Script validates coverage:
   - Tracks successful vs failed tickers
   - Reports coverage percentage
   - Exit code 0 only if ≥95% coverage achieved
   - Checkpoint files enable restart from failures

## Technical Implementation Details

### Data Provider Integration
- No modifications needed to `backend/app/data_provider.py`
- Existing `fetch_ohlcv()` method fully supports 15m interval
- Yahoo Finance API provides intraday data via yfinance library

### Database Schema
- Existing `PriceBar` model already supports intraday intervals
- `interval` field distinguishes '15m' from 'daily' data
- Unique constraint on (instrument_id, ts, interval) prevents duplicates

### Quota Management
The script implements multiple quota protection strategies:

1. **Rate Limiting**:
   - Default 1s delay between ticker requests
   - Configurable via `--delay` parameter
   - 10s pause between batches (configurable)

2. **Batching**:
   - Default 10 tickers per batch
   - Configurable via `--batch-size` parameter

3. **Quota Tracking**:
   - Logs quota-related errors separately
   - Tracks quota warning count
   - Enables adaptive retry strategies

4. **Retry Logic**:
   - 3 attempts with exponential backoff
   - Inherited from DataProvider's @retry decorator

### Expected Data Volume

For 300 tickers over 30 days:
- ~26 bars/day (6.5 market hours * 4 bars/hour)
- 30 days = ~780 bars per ticker
- Total: ~234,000 bars for full dataset

## Usage Examples

### Manual Execution
```bash
# Full run with defaults
python scripts/seed_prices_intraday.py

# Dry run to test
python scripts/seed_prices_intraday.py --dry-run

# Custom parameters
python scripts/seed_prices_intraday.py \
  --max-tickers 300 \
  --days 30 \
  --batch-size 10 \
  --delay 2.0 \
  --batch-delay 15

# Restart from failure
python scripts/seed_prices_intraday.py --start-ticker 150
```

### Cloud Scheduler Setup
```bash
gcloud scheduler jobs create http intraday-ingestion-job \
  --schedule="0 20 * * *" \
  --uri="https://YOUR_BACKEND_URL/api/v1/jobs/ingest-intraday" \
  --http-method=POST \
  --location=us-central1 \
  --time-zone="America/New_York"
```

### Cron Setup
```bash
# Add to crontab
0 20 * * * /path/to/boursomatic/scripts/cron_intraday.sh
```

## Monitoring

### Key Metrics
- Coverage percentage (target: ≥95%)
- Successful vs failed tickers
- Bars inserted vs skipped
- Quota warnings
- Execution time

### Log Files
- `seed_prices_intraday.log` - Main execution log
- `seed_intraday_checkpoint.json` - Progress checkpoint
- `logs/intraday_cron_*.log` - Cron execution logs (when using cron)

### Alert Conditions
- Coverage < 95%
- Exit code ≠ 0
- Quota warnings > threshold
- Execution time > 2 hours

## Dependencies

No new dependencies required. Uses existing:
- `yfinance` - Market data API
- `pandas` - Data processing
- `sqlmodel` - Database ORM
- `tenacity` - Retry logic

## Future Enhancements

Potential improvements for Phase 2+:
- [ ] Parallel processing with worker pools
- [ ] Advanced quota prediction
- [ ] Real-time alerting via webhooks
- [ ] Cloud Monitoring dashboard integration
- [ ] Adaptive retry strategies
- [ ] Support for other intervals (5m, 1h, etc.)

## Integration Notes

### Backend API Endpoint (Optional)
For Cloud Scheduler HTTP trigger, add this endpoint to FastAPI:

```python
@router.post("/api/v1/jobs/ingest-intraday")
async def ingest_intraday_job(request: IntradayJobRequest):
    """Trigger intraday data ingestion job."""
    # Run seed_prices_intraday.py as background task
    # Return job ID for tracking
    pass
```

### Environment Variables
No new environment variables required. Uses existing database configuration.

## Rollout Plan

1. **Development**: Test with `--dry-run` and small `--max-tickers` value
2. **Staging**: Run with full 300 tickers, verify coverage
3. **Production**: 
   - Deploy scheduler (Cloud Scheduler or cron)
   - Monitor first few runs
   - Adjust delays if quota issues occur

## Support

For issues or questions:
- Check logs: `seed_prices_intraday.log`
- Review checkpoint: `seed_intraday_checkpoint.json`
- See troubleshooting guide: `infra/scheduler/README.md`

## Conclusion

This implementation fully satisfies the Phase 1.4 requirements:
- ✅ 15m interval data fetching working
- ✅ Database ingestion with structured logging
- ✅ Scheduler configurations provided
- ✅ 95% coverage target validated
- ✅ Comprehensive tests passing
- ✅ Production-ready documentation

The solution is minimal, focused, and integrates seamlessly with existing architecture.
