"""
Database configuration and session management.
"""

from sqlmodel import create_engine, Session
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/boursomatic")

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
