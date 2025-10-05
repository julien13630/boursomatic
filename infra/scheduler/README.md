# Scheduler Configuration

This directory contains configuration files for scheduled data ingestion jobs.

## Intraday 15m Data Ingestion

### Overview

The intraday ingestion job runs daily to maintain a rolling 30-day window of 15-minute OHLCV data for up to 300 tickers. This enables intraday analysis and feature generation for the ML model.

### Configuration

- **Schedule**: Daily at 8:00 PM EST (4 hours after market close)
- **Max Tickers**: 300 (limited to respect API quotas)
- **Data Window**: Rolling 30 days (J-30)
- **Interval**: 15 minutes
- **Expected Coverage**: ≥95% of tickers

### Deployment Options

#### Option 1: GCP Cloud Scheduler (Recommended for Production)

Cloud Scheduler provides managed cron jobs with built-in monitoring and retries.

```bash
# Create the Cloud Scheduler job
gcloud scheduler jobs create http intraday-ingestion-job \
  --schedule="0 20 * * *" \
  --uri="https://YOUR_BACKEND_URL/api/v1/jobs/ingest-intraday" \
  --http-method=POST \
  --headers="Content-Type=application/json,Authorization=Bearer YOUR_SERVICE_TOKEN" \
  --message-body='{"max_tickers":300,"days":30,"batch_size":10,"delay":1.0,"batch_delay":10}' \
  --location=us-central1 \
  --time-zone="America/New_York" \
  --attempt-deadline=7200s

# List all scheduler jobs
gcloud scheduler jobs list

# Trigger manually for testing
gcloud scheduler jobs run intraday-ingestion-job

# View logs
gcloud scheduler jobs describe intraday-ingestion-job
```

#### Option 2: Local Cron (Development/Self-Hosted)

For local or self-hosted deployments, use the provided cron script.

```bash
# Make script executable
chmod +x scripts/cron_intraday.sh

# Edit crontab
crontab -e

# Add this line (runs daily at 8:00 PM):
0 20 * * * /path/to/boursomatic/scripts/cron_intraday.sh

# Verify crontab
crontab -l

# Monitor logs
tail -f logs/intraday_cron_*.log
```

#### Option 3: Direct Script Execution

For manual or custom scheduling:

```bash
cd /path/to/boursomatic
python3 scripts/seed_prices_intraday.py --max-tickers 300 --days 30
```

### Job Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_tickers` | 300 | Maximum number of tickers to process |
| `days` | 30 | Number of days of historical intraday data |
| `batch_size` | 10 | Number of tickers per batch before pause |
| `delay` | 1.0 | Delay in seconds between tickers |
| `batch_delay` | 10 | Delay in seconds between batches |
| `start_ticker` | 0 | Index to start from (for partial restarts) |
| `dry_run` | false | Test mode without actual data fetch/insert |

### Quota Management

The job includes built-in quota management:

- **Rate Limiting**: Configurable delays between API calls
- **Batching**: Processes tickers in batches with longer pauses
- **Retry Logic**: Exponential backoff on failures (3 attempts)
- **Quota Tracking**: Logs quota warnings for monitoring

### Monitoring

#### Logs

All execution logs are written to:
- File: `seed_prices_intraday.log`
- Checkpoint: `seed_intraday_checkpoint.json`
- Cron logs: `logs/intraday_cron_YYYYMMDD_HHMMSS.log`

#### Metrics Tracked

- Total tickers processed
- Successful vs failed tickers
- Coverage percentage (target: ≥95%)
- Bars inserted vs skipped
- Quota warnings
- Error details

#### Success Criteria

The job is considered successful if:
1. Coverage ≥95% of target tickers
2. Exit code 0
3. No critical quota violations

### Troubleshooting

#### Low Coverage (<95%)

Check the checkpoint file for failed tickers:
```bash
cat seed_intraday_checkpoint.json | jq '.errors'
```

Restart from last successful ticker:
```bash
python3 scripts/seed_prices_intraday.py --start-ticker 150
```

#### Quota Exceeded

Increase delays between requests:
```bash
python3 scripts/seed_prices_intraday.py --delay 2.0 --batch-delay 20
```

#### Network Errors

The script includes automatic retry with exponential backoff. For persistent issues, check:
1. Network connectivity
2. API service status
3. Firewall rules

### Alerting

Configure alerts for:
- Job failures (exit code ≠ 0)
- Coverage below 95%
- Quota warnings exceeding threshold
- Job duration exceeding 2 hours

Example email alert (using sendmail):
```bash
echo "Intraday job failed" | mail -s "Alert: Intraday Ingestion Failed" admin@boursomatic.com
```

### Maintenance

- **Log Rotation**: Old logs are automatically cleaned (30-day retention)
- **Checkpoint Files**: Saved after each batch for restart capability
- **Database**: Duplicate detection prevents data corruption
- **Monitoring**: Review coverage and errors daily

### Future Enhancements

- [ ] Parallel processing with worker pools
- [ ] Advanced quota prediction
- [ ] Real-time alerting via webhooks
- [ ] Integration with Cloud Monitoring dashboards
- [ ] Adaptive retry strategies based on error types
