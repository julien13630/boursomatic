"""
Database configuration and session management.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic"
)

# Create engine with appropriate pool settings
# For production, consider using a proper pool
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging during development
    poolclass=NullPool,  # Use NullPool for development/testing
)


def get_session():
    """Get a database session."""
    with Session(engine) as session:
        yield session
