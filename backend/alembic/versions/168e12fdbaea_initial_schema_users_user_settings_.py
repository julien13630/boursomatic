"""Initial schema: users, user_settings, instruments, price_bars, features, model_versions, recommendations

Revision ID: 168e12fdbaea
Revises: 
Create Date: 2025-10-05 18:00:39.335314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '168e12fdbaea'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_is_deleted'), 'users', ['is_deleted'], unique=False)

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_consent_accepted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('risk_consent_accepted_at', sa.DateTime(), nullable=True),
        sa.Column('preferred_profile', sa.String(length=50), nullable=True, server_default='moderate'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=False)

    # Create instruments table
    op.create_table(
        'instruments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('market_cap_bucket', sa.String(length=50), nullable=True),
        sa.Column('pe_bucket', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_instruments_symbol'), 'instruments', ['symbol'], unique=False)
    op.create_index(op.f('ix_instruments_exchange'), 'instruments', ['exchange'], unique=False)
    op.create_index(op.f('ix_instruments_is_active'), 'instruments', ['is_active'], unique=False)

    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('params_hash', sa.String(length=64), nullable=False),
        sa.Column('metrics_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('model_path', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )
    op.create_index(op.f('ix_model_versions_version'), 'model_versions', ['version'], unique=False)
    op.create_index(op.f('ix_model_versions_is_active'), 'model_versions', ['is_active'], unique=False)

    # Create price_bars table
    op.create_table(
        'price_bars',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('o', sa.Float(), nullable=False),
        sa.Column('h', sa.Float(), nullable=False),
        sa.Column('l', sa.Float(), nullable=False),
        sa.Column('c', sa.Float(), nullable=False),
        sa.Column('v', sa.Float(), nullable=False),
        sa.Column('interval', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'])
    )
    op.create_index(op.f('ix_price_bars_instrument_id'), 'price_bars', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_price_bars_ts'), 'price_bars', ['ts'], unique=False)
    op.create_index(op.f('ix_price_bars_interval'), 'price_bars', ['interval'], unique=False)
    op.create_index('idx_price_bars_instrument_ts_interval', 'price_bars', ['instrument_id', 'ts', 'interval'], unique=True)

    # Create features table
    op.create_table(
        'features',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('ret_1d', sa.Float(), nullable=True),
        sa.Column('ret_5d', sa.Float(), nullable=True),
        sa.Column('ret_20d', sa.Float(), nullable=True),
        sa.Column('rsi_14', sa.Float(), nullable=True),
        sa.Column('momentum_5d', sa.Float(), nullable=True),
        sa.Column('vol_20d', sa.Float(), nullable=True),
        sa.Column('atr_14', sa.Float(), nullable=True),
        sa.Column('volume_zscore', sa.Float(), nullable=True),
        sa.Column('additional_features', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'])
    )
    op.create_index(op.f('ix_features_instrument_id'), 'features', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_features_ts'), 'features', ['ts'], unique=False)
    op.create_index('idx_features_instrument_ts', 'features', ['instrument_id', 'ts'], unique=True)

    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=10), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('expected_return_pct', sa.Float(), nullable=True),
        sa.Column('horizon_days', sa.Integer(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit', sa.Float(), nullable=True),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('features_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id']),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'])
    )
    op.create_index(op.f('ix_recommendations_instrument_id'), 'recommendations', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_recommendations_model_version_id'), 'recommendations', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_recommendations_profile'), 'recommendations', ['profile'], unique=False)
    op.create_index(op.f('ix_recommendations_label'), 'recommendations', ['label'], unique=False)
    op.create_index(op.f('ix_recommendations_generated_at'), 'recommendations', ['generated_at'], unique=False)
    op.create_index(op.f('ix_recommendations_is_active'), 'recommendations', ['is_active'], unique=False)
    op.create_index('idx_recommendations_active_generated', 'recommendations', ['is_active', 'generated_at'], unique=False)
    op.create_index('idx_recommendations_instrument_profile', 'recommendations', ['instrument_id', 'profile', 'generated_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table('recommendations')
    op.drop_table('features')
    op.drop_table('price_bars')
    op.drop_table('model_versions')
    op.drop_table('instruments')
    op.drop_table('user_settings')
    op.drop_table('users')

