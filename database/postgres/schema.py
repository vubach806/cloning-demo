"""PostgreSQL schema initialization and utilities."""

from typing import Optional
from sqlalchemy import Engine
from database.postgres.models import Base
from database.postgres.client import get_postgres_engine, get_default_postgres_engine


def create_all_tables(engine: Optional[Engine] = None) -> None:
    """Create all tables in the database.

    Args:
        engine: SQLAlchemy engine (uses default if not provided)

    Example:
        ```python
        from database.postgres import create_all_tables

        # Create all tables
        create_all_tables()
        ```
    """
    if engine is None:
        engine = get_default_postgres_engine()
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine: Optional[Engine] = None) -> None:
    """Drop all tables from the database.

    Warning: This will delete all data!

    Args:
        engine: SQLAlchemy engine (uses default if not provided)

    Example:
        ```python
        from database.postgres import drop_all_tables

        # Drop all tables (WARNING: deletes all data!)
        drop_all_tables()
        ```
    """
    if engine is None:
        engine = get_default_postgres_engine()
    Base.metadata.drop_all(bind=engine)


def recreate_all_tables(engine: Optional[Engine] = None) -> None:
    """Drop and recreate all tables.

    Warning: This will delete all data!

    Args:
        engine: SQLAlchemy engine (uses default if not provided)

    Example:
        ```python
        from database.postgres import recreate_all_tables

        # Recreate all tables (WARNING: deletes all data!)
        recreate_all_tables()
        ```
    """
    if engine is None:
        engine = get_default_postgres_engine()
    drop_all_tables(engine)
    create_all_tables(engine)
