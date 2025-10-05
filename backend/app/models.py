"""
Database models for Boursomatic.

All models use UUID as primary keys and follow snake_case naming conventions.
Includes support for soft delete and multi-profile recommendations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import JSON, TEXT, Column, Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """
    User accounts with authentication and admin capabilities.
    Supports soft delete via is_deleted flag.
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    is_admin: bool = Field(default=False)
    is_deleted: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user_settings: Optional["UserSetting"] = Relationship(back_populates="user")


class UserSetting(SQLModel, table=True):
    """
    User-specific settings including risk consent and preferences.
    One-to-one relationship with User.
    """

    __tablename__ = "user_settings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    risk_consent_accepted: bool = Field(default=False)
    risk_consent_accepted_at: datetime | None = Field(default=None)
    preferred_profile: str | None = Field(
        default="moderate", max_length=50
    )  # conservative, moderate, aggressive
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="user_settings")


class Instrument(SQLModel, table=True):
    """
    Financial instruments (stocks, ETFs) with metadata.
    Supports US & Euronext markets.
    """

    __tablename__ = "instruments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    symbol: str = Field(index=True, max_length=50)
    exchange: str = Field(index=True, max_length=50)  # NYSE, NASDAQ, EURONEXT, etc.
    name: str | None = Field(default=None, max_length=255)
    sector: str | None = Field(default=None, max_length=100)
    market_cap_bucket: str | None = Field(default=None, max_length=50)  # small, mid, large
    pe_bucket: str | None = Field(default=None, max_length=50)  # low, medium, high
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    price_bars: list["PriceBar"] = Relationship(back_populates="instrument")
    features: list["Feature"] = Relationship(back_populates="instrument")
    recommendations: list["Recommendation"] = Relationship(back_populates="instrument")


class PriceBar(SQLModel, table=True):
    """
    OHLCV price bars for instruments.
    Supports both daily and intraday (15m) intervals.
    """

    __tablename__ = "price_bars"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    instrument_id: UUID = Field(foreign_key="instruments.id", index=True)
    ts: datetime = Field(index=True)  # timestamp
    o: float = Field()  # open
    h: float = Field()  # high
    l: float = Field()  # low  # noqa: E741
    c: float = Field()  # close
    v: float = Field()  # volume
    interval: str = Field(index=True, max_length=10)  # 'daily', '15m', etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    instrument: Instrument = Relationship(back_populates="price_bars")

    __table_args__ = (
        Index(
            "idx_price_bars_instrument_ts_interval", "instrument_id", "ts", "interval", unique=True
        ),
    )


class Feature(SQLModel, table=True):
    """
    Computed features for ML model training and inference.
    Includes technical indicators and derived metrics.
    """

    __tablename__ = "features"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    instrument_id: UUID = Field(foreign_key="instruments.id", index=True)
    ts: datetime = Field(index=True)

    # Returns
    ret_1d: float | None = Field(default=None)
    ret_5d: float | None = Field(default=None)
    ret_20d: float | None = Field(default=None)

    # Technical indicators
    rsi_14: float | None = Field(default=None)
    momentum_5d: float | None = Field(default=None)
    vol_20d: float | None = Field(default=None)  # volatility
    atr_14: float | None = Field(default=None)  # average true range
    volume_zscore: float | None = Field(default=None)

    # Additional features can be added via JSON for flexibility
    additional_features: dict | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    instrument: Instrument = Relationship(back_populates="features")

    __table_args__ = (Index("idx_features_instrument_ts", "instrument_id", "ts", unique=True),)


class ModelVersion(SQLModel, table=True):
    """
    ML model version tracking with training metadata and metrics.
    """

    __tablename__ = "model_versions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    version: str = Field(unique=True, index=True, max_length=100)
    trained_at: datetime = Field(default_factory=datetime.utcnow)
    params_hash: str = Field(max_length=64)  # Hash of model parameters for reproducibility
    metrics_json: dict = Field(sa_column=Column(JSON))  # Training/validation metrics
    model_path: str | None = Field(default=None, max_length=500)  # Path to serialized model
    is_active: bool = Field(default=False, index=True)  # Current production model
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    recommendations: list["Recommendation"] = Relationship(back_populates="model_version")


class Recommendation(SQLModel, table=True):
    """
    ML-generated trading recommendations with full audit trail.
    Supports multi-profile recommendations (conservative, moderate, aggressive).
    """

    __tablename__ = "recommendations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    instrument_id: UUID = Field(foreign_key="instruments.id", index=True)
    model_version_id: UUID = Field(foreign_key="model_versions.id", index=True)

    # Recommendation details
    profile: str = Field(index=True, max_length=50)  # conservative, moderate, aggressive
    label: str = Field(index=True, max_length=10)  # BUY, HOLD, SELL
    confidence: float = Field()  # 0.0 to 1.0
    expected_return_pct: float | None = Field(default=None)
    horizon_days: int | None = Field(default=None)
    stop_loss: float | None = Field(default=None)
    take_profit: float | None = Field(default=None)

    # Audit and explainability
    justification: str | None = Field(default=None, sa_column=Column(TEXT))
    features_snapshot: dict = Field(sa_column=Column(JSON))  # Feature values at inference time

    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    is_active: bool = Field(default=True, index=True)  # For archiving old recommendations

    # Relationships
    instrument: Instrument = Relationship(back_populates="recommendations")
    model_version: ModelVersion = Relationship(back_populates="recommendations")

    __table_args__ = (
        Index("idx_recommendations_active_generated", "is_active", "generated_at"),
        Index("idx_recommendations_instrument_profile", "instrument_id", "profile", "generated_at"),
    )
