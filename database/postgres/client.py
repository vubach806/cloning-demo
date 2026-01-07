"""PostgreSQL client utilities."""

from typing import Optional
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.connection import db_manager, DatabaseSettings


def get_postgres_engine(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> Engine:
    """Get a PostgreSQL engine instance.

    Args:
        host: PostgreSQL host (defaults to settings)
        port: PostgreSQL port (defaults to settings)
        user: PostgreSQL user (defaults to settings)
        password: PostgreSQL password (defaults to settings)
        database: Database name (defaults to settings)

    Returns:
        SQLAlchemy Engine instance

    Example:
        ```python
        # Use default connection from settings
        engine = get_postgres_engine()

        # Use custom connection
        engine = get_postgres_engine(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="my_db"
        )
        ```
    """
    settings = DatabaseSettings()
    connection_string = (
        f"postgresql://{user or settings.postgres_user}:"
        f"{password or settings.postgres_password}@"
        f"{host or settings.postgres_host}:{port or settings.postgres_port}/"
        f"{database or settings.postgres_db}"
    )
    return create_engine(connection_string)


def get_postgres_session(
    engine: Optional[Engine] = None,
) -> Session:
    """Get a PostgreSQL session.

    Args:
        engine: SQLAlchemy engine (uses default if not provided)

    Returns:
        SQLAlchemy Session instance

    Example:
        ```python
        # Use default session from database manager
        session = get_postgres_session()

        # Use custom engine
        engine = get_postgres_engine()
        session = get_postgres_session(engine=engine)

        # Use session
        shops = session.query(Shop).all()
        ```
    """
    if engine is None:
        return db_manager.get_postgres_session()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_default_postgres_engine() -> Engine:
    """Get the default PostgreSQL engine from database manager.

    Returns:
        Default PostgreSQL engine
    """
    return db_manager.connect_postgres()
