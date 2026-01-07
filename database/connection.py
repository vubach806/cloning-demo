"""Database connection utilities for PostgreSQL, Milvus, and Redis."""

import os
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from pymilvus import connections, Collection
from redis import Redis
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "project_db"

    milvus_host: str = "localhost"
    milvus_port: int = 19530

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env that are not database-related


class DatabaseManager:
    """Manages connections to PostgreSQL, Milvus, and Redis."""

    def __init__(self, settings: Optional[DatabaseSettings] = None):
        """Initialize database manager.

        Args:
            settings: Database settings, defaults to loading from environment
        """
        self.settings = settings or DatabaseSettings()
        self._postgres_engine: Optional[Engine] = None
        self._postgres_session: Optional[Session] = None
        self._milvus_connected = False
        self._redis_client: Optional[Redis] = None

    def connect_postgres(self) -> Engine:
        """Connect to PostgreSQL database.

        Returns:
            SQLAlchemy engine
        """
        if self._postgres_engine is None:
            connection_string = (
                f"postgresql://{self.settings.postgres_user}:"
                f"{self.settings.postgres_password}@"
                f"{self.settings.postgres_host}:{self.settings.postgres_port}/"
                f"{self.settings.postgres_db}"
            )
            # Enable SQL query logging if DEBUG is enabled
            echo = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
            self._postgres_engine = create_engine(connection_string, echo=echo)
        return self._postgres_engine

    def get_postgres_session(self) -> Session:
        """Get PostgreSQL session.

        Returns:
            SQLAlchemy session
        """
        if self._postgres_session is None:
            engine = self.connect_postgres()
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self._postgres_session = SessionLocal()
        return self._postgres_session

    def connect_milvus(self) -> None:
        """Connect to Milvus vector database."""
        if not self._milvus_connected:
            connections.connect(
                alias="default",
                host=self.settings.milvus_host,
                port=self.settings.milvus_port,
            )
            self._milvus_connected = True

    def get_milvus_collection(self, collection_name: str) -> Collection:
        """Get Milvus collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Milvus collection
        """
        self.connect_milvus()
        return Collection(collection_name)

    def connect_redis(self) -> Redis:
        """Connect to Redis.

        Returns:
            Redis client
        """
        if self._redis_client is None:
            self._redis_client = Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                decode_responses=True,
            )
        return self._redis_client

    def close_all(self) -> None:
        """Close all database connections."""
        if self._postgres_session:
            self._postgres_session.close()
        if self._postgres_engine:
            self._postgres_engine.dispose()
        if self._milvus_connected:
            connections.disconnect("default")
        if self._redis_client:
            self._redis_client.close()


# Global database manager instance
db_manager = DatabaseManager()
