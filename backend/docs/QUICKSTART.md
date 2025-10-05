# Quick Start Guide - Database Setup

This guide will help you set up the Boursomatic database from scratch.

## Prerequisites

- PostgreSQL 14+ installed and running
- Python 3.12+
- Git repository cloned

## Step 1: Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Create PostgreSQL Database

```bash
# Option 1: Using psql command line
psql -U postgres -c "CREATE DATABASE boursomatic;"

# Option 2: Using createdb utility
createdb -U postgres boursomatic

# Verify database was created
psql -U postgres -l | grep boursomatic
```

## Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your database connection
# DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/boursomatic
nano .env  # or use your preferred editor
```

## Step 4: Run Migrations

```bash
# Method 1: Using alembic directly
alembic upgrade head

# Method 2: Using the helper script
./scripts/db_migration.sh migrate
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 168e12fdbaea, Initial schema: users, user_settings, instruments, price_bars, features, model_versions, recommendations
```

## Step 5: Verify Schema

```bash
# Check tables were created
psql -d boursomatic -c "\dt"

# Should show:
# Schema | Name                 | Type  | Owner
# --------+----------------------+-------+--------
# public | users                | table | postgres
# public | user_settings        | table | postgres
# public | instruments          | table | postgres
# public | price_bars           | table | postgres
# public | features             | table | postgres
# public | model_versions       | table | postgres
# public | recommendations      | table | postgres
```

## Step 6: Check Migration Status

```bash
alembic current

# Should show:
# 168e12fdbaea (head)
```

## Common Issues & Troubleshooting

### Issue: "psycopg.OperationalError: connection failed"

**Solution**: Check if PostgreSQL is running
```bash
# Linux/macOS
sudo systemctl status postgresql
# or
pg_isready

# Windows
# Check Services app or run:
pg_ctl status
```

### Issue: "FATAL: database does not exist"

**Solution**: Create the database first (see Step 2)

### Issue: "FATAL: password authentication failed"

**Solution**: Update DATABASE_URL in .env file with correct password

### Issue: "relation already exists"

**Solution**: Database already has tables. To reset:
```bash
# Rollback migrations
alembic downgrade base

# Re-apply
alembic upgrade head

# Or drop and recreate database
psql -U postgres -c "DROP DATABASE boursomatic;"
psql -U postgres -c "CREATE DATABASE boursomatic;"
alembic upgrade head
```

## Testing the Schema

Run the validation script:
```bash
python scripts/test_schema.py
```

This will verify:
- All models can be instantiated
- Required fields are present
- Table names follow conventions

## Next Steps

After setting up the database:

1. **Implement data ingestion** (Phase 1)
   - Price bars from yfinance/Stooq
   - Historical + intraday data

2. **Feature engineering** (Phase 2)
   - Calculate technical indicators
   - Populate features table

3. **Model training** (Phase 2)
   - Train LightGBM model
   - Store in model_versions

4. **API development** (Phase 3-4)
   - FastAPI endpoints
   - Authentication

5. **Frontend** (Phase 4)
   - Recommendations UI
   - User dashboard

## Useful Commands Reference

```bash
# Check migration history
alembic history

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current

# Generate SQL for migration (without executing)
alembic upgrade head --sql

# Create new migration (autogenerate)
alembic revision --autogenerate -m "Add new column"

# Create new migration (manual)
alembic revision -m "Custom migration"
```

## Database Connection Strings

### Local Development
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic
```

### Docker
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/boursomatic
```

### GCP Cloud SQL (Production)
```
DATABASE_URL=postgresql+psycopg://user:pass@/boursomatic?host=/cloudsql/project:region:instance
```

## Backup & Restore

### Backup
```bash
# Full database backup
pg_dump -U postgres boursomatic > backup_$(date +%Y%m%d).sql

# Schema only
pg_dump -U postgres --schema-only boursomatic > schema_backup.sql

# Data only
pg_dump -U postgres --data-only boursomatic > data_backup.sql
```

### Restore
```bash
# Restore full backup
psql -U postgres boursomatic < backup_20241005.sql

# Restore to new database
createdb boursomatic_restore
psql -U postgres boursomatic_restore < backup_20241005.sql
```

## Performance Tips

1. **Monitor query performance**
   ```sql
   -- Enable query logging in postgresql.conf
   log_statement = 'all'
   log_duration = on
   
   -- Or use EXPLAIN ANALYZE
   EXPLAIN ANALYZE SELECT * FROM recommendations WHERE is_active = true;
   ```

2. **Check index usage**
   ```sql
   SELECT schemaname, tablename, indexname, idx_scan
   FROM pg_stat_user_indexes
   ORDER BY idx_scan;
   ```

3. **Vacuum regularly** (automated by default, but can be manual)
   ```sql
   VACUUM ANALYZE recommendations;
   ```

## Security Checklist

- [ ] Use strong passwords for database users
- [ ] Restrict network access (pg_hba.conf)
- [ ] Use SSL connections in production
- [ ] Regularly backup database
- [ ] Keep PostgreSQL updated
- [ ] Use environment variables for secrets (never commit)
- [ ] Enable query logging for audit trail
- [ ] Implement row-level security if needed

## Documentation

- Full schema documentation: [docs/database_schema.md](docs/database_schema.md)
- Schema diagram: [docs/schema_diagram.txt](docs/schema_diagram.txt)
- SQL reference: [docs/schema.sql](docs/schema.sql)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review migration logs: `alembic.log` (if configured)
3. Check PostgreSQL logs
4. Consult the main README.md
