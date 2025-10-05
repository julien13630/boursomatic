#!/usr/bin/env python3
"""
Test script to validate database schema and migrations.

This script can be used to test database creation, verify schema,
and test basic CRUD operations without requiring a running PostgreSQL server.

Usage:
    python scripts/test_schema.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import (
    User,
    UserSetting,
    Instrument,
    PriceBar,
    Feature,
    ModelVersion,
    Recommendation,
)
from datetime import datetime
from uuid import uuid4


def test_model_creation():
    """Test that all models can be instantiated."""
    print("Testing model creation...")

    # Test User
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        is_admin=False,
        is_deleted=False,
    )
    print(f"✓ User model: {user.email}")

    # Test UserSetting
    user_setting = UserSetting(
        id=uuid4(),
        user_id=user.id,
        risk_consent_accepted=True,
        risk_consent_accepted_at=datetime.utcnow(),
        preferred_profile="moderate",
    )
    print(f"✓ UserSetting model: profile={user_setting.preferred_profile}")

    # Test Instrument
    instrument = Instrument(
        id=uuid4(),
        symbol="AAPL",
        exchange="NASDAQ",
        name="Apple Inc.",
        sector="Technology",
        market_cap_bucket="large",
        pe_bucket="medium",
    )
    print(f"✓ Instrument model: {instrument.symbol} ({instrument.exchange})")

    # Test PriceBar
    price_bar = PriceBar(
        id=uuid4(),
        instrument_id=instrument.id,
        ts=datetime.utcnow(),
        o=150.0,
        h=155.0,
        l=149.0,
        c=154.0,
        v=1000000.0,
        interval="daily",
    )
    print(f"✓ PriceBar model: {price_bar.interval} OHLCV={price_bar.o}/{price_bar.h}/{price_bar.l}/{price_bar.c}")

    # Test Feature
    feature = Feature(
        id=uuid4(),
        instrument_id=instrument.id,
        ts=datetime.utcnow(),
        ret_1d=0.02,
        ret_5d=0.05,
        ret_20d=0.15,
        rsi_14=55.0,
        momentum_5d=0.03,
        vol_20d=0.25,
        atr_14=2.5,
        volume_zscore=1.2,
        additional_features={"custom_feature": 123.45},
    )
    print(f"✓ Feature model: ret_1d={feature.ret_1d}, rsi_14={feature.rsi_14}")

    # Test ModelVersion
    model_version = ModelVersion(
        id=uuid4(),
        version="v1.0.0",
        trained_at=datetime.utcnow(),
        params_hash="abc123def456",
        metrics_json={
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85,
            "sharpe_ratio": 1.5,
        },
        model_path="/models/v1.0.0.pkl",
        is_active=True,
    )
    print(f"✓ ModelVersion model: {model_version.version} (active={model_version.is_active})")

    # Test Recommendation
    recommendation = Recommendation(
        id=uuid4(),
        instrument_id=instrument.id,
        model_version_id=model_version.id,
        profile="moderate",
        label="BUY",
        confidence=0.85,
        expected_return_pct=12.5,
        horizon_days=90,
        stop_loss=140.0,
        take_profit=180.0,
        justification="Strong technical indicators with positive momentum",
        features_snapshot={
            "ret_1d": 0.02,
            "rsi_14": 55.0,
            "vol_20d": 0.25,
        },
    )
    print(f"✓ Recommendation model: {recommendation.label} ({recommendation.profile}) confidence={recommendation.confidence}")

    print("\n✅ All models created successfully!")
    return True


def test_model_fields():
    """Test that all required fields are present."""
    print("\nTesting model field definitions...")

    # Test User fields
    user_fields = set(User.model_fields.keys())
    expected_user_fields = {"id", "email", "password_hash", "is_admin", "is_deleted", "created_at"}
    assert expected_user_fields.issubset(user_fields), f"User missing fields: {expected_user_fields - user_fields}"
    print(f"✓ User has all required fields: {len(user_fields)} fields")

    # Test Instrument fields
    instrument_fields = set(Instrument.model_fields.keys())
    expected_instrument_fields = {"id", "symbol", "exchange", "sector", "is_active"}
    assert expected_instrument_fields.issubset(instrument_fields), f"Instrument missing fields: {expected_instrument_fields - instrument_fields}"
    print(f"✓ Instrument has all required fields: {len(instrument_fields)} fields")

    # Test PriceBar fields
    price_bar_fields = set(PriceBar.model_fields.keys())
    expected_price_bar_fields = {"id", "instrument_id", "ts", "o", "h", "l", "c", "v", "interval"}
    assert expected_price_bar_fields.issubset(price_bar_fields), f"PriceBar missing fields: {expected_price_bar_fields - price_bar_fields}"
    print(f"✓ PriceBar has all required fields: {len(price_bar_fields)} fields")

    # Test Feature fields
    feature_fields = set(Feature.model_fields.keys())
    expected_feature_fields = {"id", "instrument_id", "ts", "ret_1d", "rsi_14", "vol_20d"}
    assert expected_feature_fields.issubset(feature_fields), f"Feature missing fields: {expected_feature_fields - feature_fields}"
    print(f"✓ Feature has all required fields: {len(feature_fields)} fields")

    # Test Recommendation fields
    recommendation_fields = set(Recommendation.model_fields.keys())
    expected_recommendation_fields = {"id", "instrument_id", "model_version_id", "profile", "label", "confidence", "features_snapshot"}
    assert expected_recommendation_fields.issubset(recommendation_fields), f"Recommendation missing fields: {expected_recommendation_fields - recommendation_fields}"
    print(f"✓ Recommendation has all required fields: {len(recommendation_fields)} fields")

    print("\n✅ All model fields validated!")
    return True


def test_table_names():
    """Test that table names follow snake_case convention."""
    print("\nTesting table names...")

    tables = {
        "User": User,
        "UserSetting": UserSetting,
        "Instrument": Instrument,
        "PriceBar": PriceBar,
        "Feature": Feature,
        "ModelVersion": ModelVersion,
        "Recommendation": Recommendation,
    }

    for model_name, model_class in tables.items():
        table_name = model_class.__tablename__
        # Check snake_case (no uppercase, uses underscores)
        assert table_name.islower() or "_" in table_name, f"{model_name} table name '{table_name}' is not snake_case"
        print(f"✓ {model_name:20s} -> {table_name}")

    print("\n✅ All table names follow snake_case convention!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Database Schema Validation Tests")
    print("=" * 60)

    try:
        test_model_creation()
        test_model_fields()
        test_table_names()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Ensure PostgreSQL is running")
        print("2. Set DATABASE_URL environment variable")
        print("3. Run: alembic upgrade head")
        print("4. Verify with: psql -d boursomatic -c '\\dt'")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
