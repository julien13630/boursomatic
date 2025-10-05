-- Generated SQL for initial database schema
-- This file shows the complete SQL that will be executed by the initial migration
-- Run via Alembic: alembic upgrade head

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE users (
    id UUID NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_is_deleted ON users (is_deleted);

COMMENT ON TABLE users IS 'User accounts with authentication and admin capabilities. Supports soft delete.';
COMMENT ON COLUMN users.id IS 'Unique user identifier (UUID)';
COMMENT ON COLUMN users.email IS 'User email address (unique)';
COMMENT ON COLUMN users.password_hash IS 'Hashed password using Argon2id';
COMMENT ON COLUMN users.is_admin IS 'Admin privileges flag';
COMMENT ON COLUMN users.is_deleted IS 'Soft delete flag - true if user is deleted';
COMMENT ON COLUMN users.created_at IS 'Account creation timestamp';

-- ============================================================================
-- USER_SETTINGS TABLE
-- ============================================================================
CREATE TABLE user_settings (
    id UUID NOT NULL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    risk_consent_accepted BOOLEAN NOT NULL DEFAULT false,
    risk_consent_accepted_at TIMESTAMP,
    preferred_profile VARCHAR(50) DEFAULT 'moderate',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_user_settings_user_id ON user_settings (user_id);

COMMENT ON TABLE user_settings IS 'User-specific settings and preferences. One-to-one with users.';
COMMENT ON COLUMN user_settings.risk_consent_accepted IS 'Whether user accepted risk disclosure';
COMMENT ON COLUMN user_settings.risk_consent_accepted_at IS 'When risk consent was accepted';
COMMENT ON COLUMN user_settings.preferred_profile IS 'Preferred risk profile: conservative, moderate, aggressive';

-- ============================================================================
-- INSTRUMENTS TABLE
-- ============================================================================
CREATE TABLE instruments (
    id UUID NOT NULL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    sector VARCHAR(100),
    market_cap_bucket VARCHAR(50),
    pe_bucket VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_instruments_symbol ON instruments (symbol);
CREATE INDEX ix_instruments_exchange ON instruments (exchange);
CREATE INDEX ix_instruments_is_active ON instruments (is_active);

COMMENT ON TABLE instruments IS 'Financial instruments (stocks, ETFs) tracked by the system';
COMMENT ON COLUMN instruments.symbol IS 'Stock ticker symbol (e.g., AAPL)';
COMMENT ON COLUMN instruments.exchange IS 'Exchange code (NYSE, NASDAQ, EURONEXT, etc.)';
COMMENT ON COLUMN instruments.market_cap_bucket IS 'Market cap category: small, mid, large';
COMMENT ON COLUMN instruments.pe_bucket IS 'P/E ratio category: low, medium, high';

-- ============================================================================
-- MODEL_VERSIONS TABLE
-- ============================================================================
CREATE TABLE model_versions (
    id UUID NOT NULL PRIMARY KEY,
    version VARCHAR(100) NOT NULL UNIQUE,
    trained_at TIMESTAMP NOT NULL DEFAULT NOW(),
    params_hash VARCHAR(64) NOT NULL,
    metrics_json JSON NOT NULL,
    model_path VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_model_versions_version ON model_versions (version);
CREATE INDEX ix_model_versions_is_active ON model_versions (is_active);

COMMENT ON TABLE model_versions IS 'ML model version tracking and metadata';
COMMENT ON COLUMN model_versions.version IS 'Version string (e.g., v1.0.0)';
COMMENT ON COLUMN model_versions.params_hash IS 'Hash of model parameters for reproducibility';
COMMENT ON COLUMN model_versions.metrics_json IS 'Training/validation metrics (JSON)';
COMMENT ON COLUMN model_versions.is_active IS 'Current production model flag (only one should be true)';

-- ============================================================================
-- PRICE_BARS TABLE
-- ============================================================================
CREATE TABLE price_bars (
    id UUID NOT NULL PRIMARY KEY,
    instrument_id UUID NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    o DOUBLE PRECISION NOT NULL,
    h DOUBLE PRECISION NOT NULL,
    l DOUBLE PRECISION NOT NULL,
    c DOUBLE PRECISION NOT NULL,
    v DOUBLE PRECISION NOT NULL,
    interval VARCHAR(10) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_price_bars_instrument_id ON price_bars (instrument_id);
CREATE INDEX ix_price_bars_ts ON price_bars (ts);
CREATE INDEX ix_price_bars_interval ON price_bars (interval);
CREATE UNIQUE INDEX idx_price_bars_instrument_ts_interval ON price_bars (instrument_id, ts, interval);

COMMENT ON TABLE price_bars IS 'OHLCV price bars for instruments. Supports daily and intraday (15m).';
COMMENT ON COLUMN price_bars.ts IS 'Bar timestamp';
COMMENT ON COLUMN price_bars.o IS 'Open price';
COMMENT ON COLUMN price_bars.h IS 'High price';
COMMENT ON COLUMN price_bars.l IS 'Low price';
COMMENT ON COLUMN price_bars.c IS 'Close price';
COMMENT ON COLUMN price_bars.v IS 'Volume';
COMMENT ON COLUMN price_bars.interval IS 'Time interval: daily, 15m, etc.';

-- ============================================================================
-- FEATURES TABLE
-- ============================================================================
CREATE TABLE features (
    id UUID NOT NULL PRIMARY KEY,
    instrument_id UUID NOT NULL REFERENCES instruments(id),
    ts TIMESTAMP NOT NULL,
    ret_1d DOUBLE PRECISION,
    ret_5d DOUBLE PRECISION,
    ret_20d DOUBLE PRECISION,
    rsi_14 DOUBLE PRECISION,
    momentum_5d DOUBLE PRECISION,
    vol_20d DOUBLE PRECISION,
    atr_14 DOUBLE PRECISION,
    volume_zscore DOUBLE PRECISION,
    additional_features JSON,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_features_instrument_id ON features (instrument_id);
CREATE INDEX ix_features_ts ON features (ts);
CREATE UNIQUE INDEX idx_features_instrument_ts ON features (instrument_id, ts);

COMMENT ON TABLE features IS 'Computed technical indicators and features for ML models';
COMMENT ON COLUMN features.ret_1d IS '1-day return';
COMMENT ON COLUMN features.ret_5d IS '5-day return';
COMMENT ON COLUMN features.ret_20d IS '20-day return';
COMMENT ON COLUMN features.rsi_14 IS '14-period RSI';
COMMENT ON COLUMN features.momentum_5d IS '5-day momentum';
COMMENT ON COLUMN features.vol_20d IS '20-day volatility';
COMMENT ON COLUMN features.atr_14 IS '14-period Average True Range';
COMMENT ON COLUMN features.volume_zscore IS 'Volume z-score';
COMMENT ON COLUMN features.additional_features IS 'Flexible JSON storage for additional features';

-- ============================================================================
-- RECOMMENDATIONS TABLE
-- ============================================================================
CREATE TABLE recommendations (
    id UUID NOT NULL PRIMARY KEY,
    instrument_id UUID NOT NULL REFERENCES instruments(id),
    model_version_id UUID NOT NULL REFERENCES model_versions(id),
    profile VARCHAR(50) NOT NULL,
    label VARCHAR(10) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    expected_return_pct DOUBLE PRECISION,
    horizon_days INTEGER,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    justification TEXT,
    features_snapshot JSON NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX ix_recommendations_instrument_id ON recommendations (instrument_id);
CREATE INDEX ix_recommendations_model_version_id ON recommendations (model_version_id);
CREATE INDEX ix_recommendations_profile ON recommendations (profile);
CREATE INDEX ix_recommendations_label ON recommendations (label);
CREATE INDEX ix_recommendations_generated_at ON recommendations (generated_at);
CREATE INDEX ix_recommendations_is_active ON recommendations (is_active);
CREATE INDEX idx_recommendations_active_generated ON recommendations (is_active, generated_at);
CREATE INDEX idx_recommendations_instrument_profile ON recommendations (instrument_id, profile, generated_at);

COMMENT ON TABLE recommendations IS 'ML-generated trading recommendations with full audit trail';
COMMENT ON COLUMN recommendations.profile IS 'Risk profile: conservative, moderate, aggressive';
COMMENT ON COLUMN recommendations.label IS 'Recommendation signal: BUY, HOLD, SELL';
COMMENT ON COLUMN recommendations.confidence IS 'Model confidence (0.0 to 1.0)';
COMMENT ON COLUMN recommendations.expected_return_pct IS 'Expected return percentage';
COMMENT ON COLUMN recommendations.horizon_days IS 'Investment horizon in days';
COMMENT ON COLUMN recommendations.stop_loss IS 'Suggested stop loss price';
COMMENT ON COLUMN recommendations.take_profit IS 'Suggested take profit price';
COMMENT ON COLUMN recommendations.justification IS 'Human-readable explanation';
COMMENT ON COLUMN recommendations.features_snapshot IS 'Feature values at inference time (JSON) - for audit trail';
COMMENT ON COLUMN recommendations.is_active IS 'Active recommendation flag - allows archiving without deletion';

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Sample user
-- INSERT INTO users (id, email, password_hash, is_admin, is_deleted)
-- VALUES (
--     gen_random_uuid(),
--     'demo@boursomatic.com',
--     '$argon2id$v=19$m=65536,t=3,p=4$...',  -- Replace with actual hash
--     false,
--     false
-- );

-- Sample instruments
-- INSERT INTO instruments (id, symbol, exchange, name, sector, is_active)
-- VALUES
--     (gen_random_uuid(), 'AAPL', 'NASDAQ', 'Apple Inc.', 'Technology', true),
--     (gen_random_uuid(), 'MSFT', 'NASDAQ', 'Microsoft Corporation', 'Technology', true),
--     (gen_random_uuid(), 'BNP', 'EURONEXT', 'BNP Paribas', 'Finance', true);
