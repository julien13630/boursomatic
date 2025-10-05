# Scripts

Scripts utilitaires pour l'ingestion, le traitement et la maintenance.

## Available Scripts

### seed_prices.py

Seed the PriceBars table with 8 years of historical daily OHLCV data for 300 US market stocks.

**Usage:**
```bash
python scripts/seed_prices.py [--batch-size 10] [--start-ticker 0] [--dry-run] [--years 8]
```

**Features:**
- 300 diversified US market tickers across sectors
- 8 years of historical daily data (~2,016 trading days per ticker)
- Progress tracking with detailed logging
- Automatic retry with exponential backoff
- Fallback provider support (Yahoo Finance → Stooq)
- Partial restart capability
- Rate limiting to respect API quotas
- Checkpoint system for monitoring
- Target: ≥98% data coverage

**Options:**
- `--batch-size N`: Process N tickers per batch (default: 10)
- `--start-ticker N`: Resume from ticker index N (default: 0)
- `--dry-run`: Test mode without database insertion
- `--years N`: Historical period in years (default: 8)

**Output:**
- `seed_prices.log`: Detailed execution log
- `seed_checkpoint.json`: Progress checkpoint for monitoring/restart

**Example:**
```bash
# Dry run test
python scripts/seed_prices.py --dry-run --batch-size 5 --years 1

# Full seeding
python scripts/seed_prices.py

# Resume from ticker 150
python scripts/seed_prices.py --start-ticker 150
```

**Tests:**
```bash
cd backend
python -m pytest tests/test_seed_prices.py -v
```

See inline documentation in the script for more details.

## Structure à venir
- Scripts de génération de features
- Scripts d'entraînement de modèles
- Utilitaires de maintenance
