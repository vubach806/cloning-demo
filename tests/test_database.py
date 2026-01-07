"""Tests for database connections."""

import pytest
from database.connection import DatabaseManager, DatabaseSettings


def test_database_settings():
    """Test database settings loading."""
    settings = DatabaseSettings()
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.milvus_port == 19530
    assert settings.redis_port == 6379


def test_database_manager_initialization():
    """Test database manager initialization."""
    manager = DatabaseManager()
    assert manager.settings is not None
    # Note: Actual connection tests would require running services
    # manager.connect_postgres()
    # assert manager._postgres_engine is not None
