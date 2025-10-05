# Database Schema Documentation

## Overview

The Boursomatic database schema is designed for a financial recommendation platform that provides ML-generated trading signals. The schema supports:

- User authentication and preferences
- Multi-market instrument tracking (US & Euronext)
- Historical and intraday price data
- Feature engineering for ML models
- Model versioning and tracking
- Multi-profile recommendations (conservative, moderate, aggressive)
- Full audit trail for compliance

## Design Principles

1. **UUID Primary Keys**: All tables use UUID as primary keys for better distribution and security
2. **snake_case Naming**: Consistent use of snake_case for table and column names
3. **Soft Delete**: Users table includes `is_deleted` flag for soft deletion
4. **Timestamps**: All tables include creation timestamps; updated_at where appropriate
5. **Audit Trail**: Recommendations include `features_snapshot` for reproducibility
6. **Multi-Profile Support**: Recommendations can be generated for different risk profiles

## Tables

### users

User accounts with authentication capabilities.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password (Argon2id) |
| is_admin | BOOLEAN | NOT NULL, DEFAULT false | Admin privileges flag |
| is_deleted | BOOLEAN | NOT NULL, DEFAULT false | Soft delete flag |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation timestamp |

**Indexes:**
- `ix_users_email` on (email)
- `ix_users_is_deleted` on (is_deleted)

**Notes:**
- Soft delete ensures historical data integrity
- Passwords should be hashed using Argon2id via passlib

### user_settings

User-specific settings and preferences (one-to-one with users).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique setting identifier |
| user_id | UUID | FK(users.id), UNIQUE, NOT NULL | Associated user |
| risk_consent_accepted | BOOLEAN | NOT NULL, DEFAULT false | Risk disclosure acceptance |
| risk_consent_accepted_at | TIMESTAMP | NULL | When consent was accepted |
| preferred_profile | VARCHAR(50) | DEFAULT 'moderate' | Preferred risk profile |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Settings creation |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `ix_user_settings_user_id` on (user_id)

**Valid Values:**
- `preferred_profile`: 'conservative', 'moderate', 'aggressive'

### instruments

Financial instruments (stocks, ETFs) tracked by the system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique instrument identifier |
| symbol | VARCHAR(50) | NOT NULL | Stock ticker symbol |
| exchange | VARCHAR(50) | NOT NULL | Exchange code (NYSE, NASDAQ, EURONEXT, etc.) |
| name | VARCHAR(255) | NULL | Company/instrument name |
| sector | VARCHAR(100) | NULL | Business sector |
| market_cap_bucket | VARCHAR(50) | NULL | Market cap category |
| pe_bucket | VARCHAR(50) | NULL | P/E ratio category |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Whether instrument is actively tracked |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes:**
- `ix_instruments_symbol` on (symbol)
- `ix_instruments_exchange` on (exchange)
- `ix_instruments_is_active` on (is_active)

**Valid Values:**
- `market_cap_bucket`: 'small', 'mid', 'large'
- `pe_bucket`: 'low', 'medium', 'high'

### price_bars

OHLCV (Open, High, Low, Close, Volume) price bars for instruments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique bar identifier |
| instrument_id | UUID | FK(instruments.id), NOT NULL | Associated instrument |
| ts | TIMESTAMP | NOT NULL | Bar timestamp |
| o | FLOAT | NOT NULL | Open price |
| h | FLOAT | NOT NULL | High price |
| l | FLOAT | NOT NULL | Low price |
| c | FLOAT | NOT NULL | Close price |
| v | FLOAT | NOT NULL | Volume |
| interval | VARCHAR(10) | NOT NULL | Time interval ('daily', '15m', etc.) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation |

**Indexes:**
- `ix_price_bars_instrument_id` on (instrument_id)
- `ix_price_bars_ts` on (ts)
- `ix_price_bars_interval` on (interval)
- `idx_price_bars_instrument_ts_interval` on (instrument_id, ts, interval) UNIQUE

**Notes:**
- The composite unique index ensures no duplicate bars for the same instrument/time/interval
- Supports both daily (8 years historical) and intraday (15m, 30-day rolling) data

### features

Computed technical indicators and derived features for ML models.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique feature record identifier |
| instrument_id | UUID | FK(instruments.id), NOT NULL | Associated instrument |
| ts | TIMESTAMP | NOT NULL | Feature timestamp |
| ret_1d | FLOAT | NULL | 1-day return |
| ret_5d | FLOAT | NULL | 5-day return |
| ret_20d | FLOAT | NULL | 20-day return |
| rsi_14 | FLOAT | NULL | 14-period RSI |
| momentum_5d | FLOAT | NULL | 5-day momentum |
| vol_20d | FLOAT | NULL | 20-day volatility |
| atr_14 | FLOAT | NULL | 14-period Average True Range |
| volume_zscore | FLOAT | NULL | Volume z-score |
| additional_features | JSON | NULL | Flexible storage for additional features |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation |

**Indexes:**
- `ix_features_instrument_id` on (instrument_id)
- `ix_features_ts` on (ts)
- `idx_features_instrument_ts` on (instrument_id, ts) UNIQUE

**Notes:**
- `additional_features` JSON column allows flexible feature expansion without schema changes
- Unique constraint ensures one feature record per instrument per timestamp

### model_versions

ML model version tracking and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique version identifier |
| version | VARCHAR(100) | UNIQUE, NOT NULL | Version string (e.g., 'v1.0.0') |
| trained_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Training completion time |
| params_hash | VARCHAR(64) | NOT NULL | Hash of model parameters |
| metrics_json | JSON | NOT NULL | Training/validation metrics |
| model_path | VARCHAR(500) | NULL | Path to serialized model file |
| is_active | BOOLEAN | NOT NULL, DEFAULT false | Current production model flag |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation |

**Indexes:**
- `ix_model_versions_version` on (version)
- `ix_model_versions_is_active` on (is_active)

**Notes:**
- Only one model should have `is_active = true` at a time
- `metrics_json` should include: accuracy, precision, recall, F1, Sharpe ratio, max drawdown, etc.
- `params_hash` enables reproducibility and parameter drift detection

### recommendations

ML-generated trading recommendations with full audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique recommendation identifier |
| instrument_id | UUID | FK(instruments.id), NOT NULL | Target instrument |
| model_version_id | UUID | FK(model_versions.id), NOT NULL | Model used for generation |
| profile | VARCHAR(50) | NOT NULL | Risk profile |
| label | VARCHAR(10) | NOT NULL | Recommendation signal |
| confidence | FLOAT | NOT NULL | Model confidence (0.0-1.0) |
| expected_return_pct | FLOAT | NULL | Expected return percentage |
| horizon_days | INTEGER | NULL | Investment horizon in days |
| stop_loss | FLOAT | NULL | Suggested stop loss price |
| take_profit | FLOAT | NULL | Suggested take profit price |
| justification | TEXT | NULL | Human-readable explanation |
| features_snapshot | JSON | NOT NULL | Feature values at inference time |
| generated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Generation timestamp |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Active recommendation flag |

**Indexes:**
- `ix_recommendations_instrument_id` on (instrument_id)
- `ix_recommendations_model_version_id` on (model_version_id)
- `ix_recommendations_profile` on (profile)
- `ix_recommendations_label` on (label)
- `ix_recommendations_generated_at` on (generated_at)
- `ix_recommendations_is_active` on (is_active)
- `idx_recommendations_active_generated` on (is_active, generated_at)
- `idx_recommendations_instrument_profile` on (instrument_id, profile, generated_at)

**Valid Values:**
- `profile`: 'conservative', 'moderate', 'aggressive'
- `label`: 'BUY', 'HOLD', 'SELL'

**Notes:**
- `features_snapshot` provides full audit trail for compliance and debugging
- Multi-profile support allows different recommendations for different risk appetites
- `is_active` flag allows archiving old recommendations without deletion

## Relationships

```
users (1) ←→ (1) user_settings
users (1) → (0..*) [recommendations via user preferences]

instruments (1) → (0..*) price_bars
instruments (1) → (0..*) features
instruments (1) → (0..*) recommendations

model_versions (1) → (0..*) recommendations
```

## Entity Relationship Diagram (Text)

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │
│ email           │
│ password_hash   │
│ is_admin        │
│ is_deleted      │
│ created_at      │
└────────┬────────┘
         │
         │ 1:1
         ▼
┌─────────────────────────┐
│    user_settings        │
├─────────────────────────┤
│ id (PK)                 │
│ user_id (FK)            │
│ risk_consent_accepted   │
│ preferred_profile       │
│ created_at, updated_at  │
└─────────────────────────┘

┌──────────────────────┐
│    instruments       │
├──────────────────────┤
│ id (PK)              │
│ symbol               │
│ exchange             │
│ sector               │
│ market_cap_bucket    │
│ is_active            │
│ created_at           │
└──────┬───────────────┘
       │
       │ 1:N
       ├──────────────────────┐
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────────┐
│ price_bars   │      │    features      │
├──────────────┤      ├──────────────────┤
│ id (PK)      │      │ id (PK)          │
│ instrument_id│      │ instrument_id    │
│ ts           │      │ ts               │
│ o,h,l,c,v    │      │ ret_1d, ret_5d   │
│ interval     │      │ rsi_14, vol_20d  │
└──────────────┘      │ additional_feats │
                      └──────────────────┘
       │
       │ 1:N
       ▼
┌────────────────────────┐      ┌──────────────────┐
│   recommendations      │◄─────│ model_versions   │
├────────────────────────┤ N:1  ├──────────────────┤
│ id (PK)                │      │ id (PK)          │
│ instrument_id (FK)     │      │ version          │
│ model_version_id (FK)  │      │ trained_at       │
│ profile                │      │ params_hash      │
│ label                  │      │ metrics_json     │
│ confidence             │      │ is_active        │
│ expected_return_pct    │      └──────────────────┘
│ features_snapshot      │
│ justification          │
│ generated_at           │
└────────────────────────┘
```

## Migration Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set database URL
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/boursomatic"
```

### Running Migrations
```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to base (empty database)
alembic downgrade base

# Generate new migration (autogenerate)
alembic revision --autogenerate -m "Description of changes"

# Generate new migration (manual)
alembic revision -m "Description of changes"
```

### Using the Helper Script
```bash
# Run migrations
./backend/scripts/db_migration.sh migrate

# Show status
./backend/scripts/db_migration.sh status

# Rollback all migrations
./backend/scripts/db_migration.sh rollback

# Recreate (rollback + migrate)
./backend/scripts/db_migration.sh recreate
```

## Testing Database Creation

### Prerequisites
1. PostgreSQL server running
2. Database created: `CREATE DATABASE boursomatic;`
3. Python virtual environment with dependencies installed

### Test Procedure
```bash
# 1. Set environment
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic"

# 2. Run migrations
cd backend
source venv/bin/activate
alembic upgrade head

# 3. Verify tables created
psql -d boursomatic -c "\dt"

# 4. Test rollback
alembic downgrade base

# 5. Verify tables dropped
psql -d boursomatic -c "\dt"

# 6. Re-apply migrations
alembic upgrade head
```

## Sample Data Queries

### Insert Sample User
```sql
INSERT INTO users (id, email, password_hash, is_admin, is_deleted)
VALUES (
    gen_random_uuid(),
    'test@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$...',  -- hashed password
    false,
    false
);
```

### Insert Sample Instrument
```sql
INSERT INTO instruments (id, symbol, exchange, name, sector, is_active)
VALUES (
    gen_random_uuid(),
    'AAPL',
    'NASDAQ',
    'Apple Inc.',
    'Technology',
    true
);
```

### Query Active Recommendations
```sql
SELECT 
    r.id,
    i.symbol,
    i.exchange,
    r.profile,
    r.label,
    r.confidence,
    r.expected_return_pct,
    r.generated_at
FROM recommendations r
JOIN instruments i ON r.instrument_id = i.id
WHERE r.is_active = true
AND r.generated_at > NOW() - INTERVAL '7 days'
ORDER BY r.generated_at DESC;
```

## Performance Considerations

1. **Indexes**: All foreign keys and frequently queried columns are indexed
2. **Composite Indexes**: Used for common query patterns (e.g., instrument + timestamp)
3. **JSON Columns**: Used sparingly for flexibility; consider extracting frequently queried fields
4. **Partitioning**: Consider partitioning `price_bars` by time for large datasets
5. **Archiving**: Use `is_active` flags for soft archiving instead of deletion

## Security Notes

1. **Password Storage**: Always use Argon2id hashing via passlib
2. **SQL Injection**: Use parameterized queries via SQLModel/SQLAlchemy
3. **Access Control**: Implement row-level security for multi-tenant scenarios if needed
4. **Audit Trail**: `features_snapshot` in recommendations provides full audit capability
5. **Soft Delete**: Use `is_deleted` instead of hard deletion for compliance

## Future Enhancements

1. **Partitioning**: Time-based partitioning for price_bars and features
2. **Materialized Views**: For common aggregations and reporting
3. **Full-Text Search**: On instrument names and recommendation justifications
4. **Archival**: Automated archiving of old price bars to cold storage
5. **Replication**: Read replicas for analytics workloads
