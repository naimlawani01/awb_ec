"""
Database connection and session management.
Handles both AWB Editor database (read-only) and internal database.
"""
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import settings

# AWB Editor Database (read-only) - Sync engine
awb_sync_engine = create_engine(
    settings.awb_database_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Internal Database for platform-specific data
internal_engine = create_engine(
    settings.internal_db_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Session factories
AWBSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=awb_sync_engine
)

InternalSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=internal_engine
)

# Base classes for models
InternalBase = declarative_base()

# Metadata for AWB database reflection
awb_metadata = MetaData()


def get_awb_db() -> Generator[Session, None, None]:
    """Get session for AWB database."""
    db = AWBSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_internal_db() -> Generator[Session, None, None]:
    """Get session for internal database."""
    db = InternalSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_internal_db():
    """Initialize internal database tables."""
    InternalBase.metadata.create_all(bind=internal_engine)


def reflect_awb_tables():
    """Reflect AWB database tables for dynamic exploration."""
    awb_metadata.reflect(bind=awb_sync_engine)
    return awb_metadata.tables

