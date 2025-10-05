#!/bin/bash
# Cron setup for intraday data ingestion
# This script can be added to crontab for daily execution
#
# Usage:
#   1. Make this script executable: chmod +x scripts/cron_intraday.sh
#   2. Add to crontab: crontab -e
#   3. Add line: 0 20 * * * /path/to/boursomatic/scripts/cron_intraday.sh
#
# This runs daily at 8:00 PM (after market close with buffer)

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_ROOT}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log file
LOG_FILE="${LOG_DIR}/intraday_cron_${TIMESTAMP}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Intraday ingestion started at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Activate virtual environment if it exists
if [ -d "${PROJECT_ROOT}/venv" ]; then
    echo "Activating virtual environment..." | tee -a "$LOG_FILE"
    source "${PROJECT_ROOT}/venv/bin/activate"
fi

# Change to project root
cd "$PROJECT_ROOT"

# Run the intraday seeding script
echo "Running intraday data ingestion..." | tee -a "$LOG_FILE"
python3 scripts/seed_prices_intraday.py \
    --max-tickers 300 \
    --days 30 \
    --batch-size 10 \
    --delay 1.0 \
    --batch-delay 10 \
    2>&1 | tee -a "$LOG_FILE"

# Capture exit code
EXIT_CODE=${PIPESTATUS[0]}

echo "========================================" | tee -a "$LOG_FILE"
echo "Intraday ingestion completed at $(date)" | tee -a "$LOG_FILE"
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Optional: Send email notification on failure
if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Intraday ingestion failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
    # Uncomment to send email on failure:
    # echo "Intraday ingestion failed. Check log: $LOG_FILE" | \
    #   mail -s "Boursomatic: Intraday Ingestion Failed" admin@boursomatic.com
fi

# Cleanup old logs (keep last 30 days)
find "$LOG_DIR" -name "intraday_cron_*.log" -type f -mtime +30 -delete

exit $EXIT_CODE
