"""Debug utilities for database operations."""

import os
from typing import Optional
from sqlalchemy import text
from database.connection import db_manager
from database.postgres.client import get_postgres_session, get_postgres_engine
from database.redis.client import get_redis_client
from database.milvus.client import get_milvus_client


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if DEBUG environment variable is set to 'true' or '1'
    """
    debug = os.getenv("DEBUG", "false").lower()
    return debug in ("true", "1", "yes")


def test_postgres_connection() -> bool:
    """Test PostgreSQL connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_postgres_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        if is_debug_enabled():
            print("✅ PostgreSQL connection: OK")
        return True
    except Exception as e:
        if is_debug_enabled():
            print(f"❌ PostgreSQL connection failed: {e}")
        return False


def test_redis_connection() -> bool:
    """Test Redis connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        if is_debug_enabled():
            print("✅ Redis connection: OK")
        return True
    except Exception as e:
        if is_debug_enabled():
            print(f"❌ Redis connection failed: {e}")
        return False


def test_milvus_connection() -> bool:
    """Test Milvus connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        get_milvus_client()
        if is_debug_enabled():
            print("✅ Milvus connection: OK")
        return True
    except Exception as e:
        if is_debug_enabled():
            print(f"❌ Milvus connection failed: {e}")
        return False


def print_database_status() -> None:
    """Print status of all database connections."""
    if not is_debug_enabled():
        return

    print("\n" + "=" * 80)
    print("🗄️  DATABASE CONNECTION STATUS")
    print("=" * 80)

    postgres_ok = test_postgres_connection()
    redis_ok = test_redis_connection()
    milvus_ok = test_milvus_connection()

    print("=" * 80 + "\n")


def print_postgres_tables() -> None:
    """Print list of all PostgreSQL tables."""
    if not is_debug_enabled():
        return

    try:
        engine = get_postgres_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
                )
            )
            tables = [row[0] for row in result]

        print("\n" + "=" * 80)
        print("📊 POSTGRESQL TABLES")
        print("=" * 80)
        if tables:
            for table in tables:
                print(f"  ✓ {table}")
        else:
            print("  (no tables found)")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"❌ Error listing tables: {e}")


def print_session_info(session_id: str) -> None:
    """Print information about a session.

    Args:
        session_id: Session UUID identifier
    """
    if not is_debug_enabled():
        return

    try:
        from database.postgres.session_service import get_session
        from database.postgres.models import Session as SessionModel

        session = get_session(session_id)
        if session:
            print("\n" + "=" * 80)
            print(f"📝 SESSION INFO: {session_id}")
            print("=" * 80)
            print(f"ID:              {session.id}")
            print(f"User ID:         {session.user_id}")
            print(f"Title:           {session.title or '(empty)'}")
            print(f"Handoff Reason:  {session.handoff_reason or '(none)'}")
            print(f"Current Stage:   {session.current_stage_id or '(none)'}")
            print(f"Created At:      {session.created_at}")
            print(f"Updated At:      {session.updated_at}")
            if session.session_metadata:
                print(f"Metadata:        {session.session_metadata}")
            print("=" * 80 + "\n")
        else:
            print(f"⚠️  Session not found: {session_id}")
    except Exception as e:
        print(f"❌ Error getting session info: {e}")


def print_redis_keys(pattern: str = "agent:*") -> None:
    """Print Redis keys matching pattern.

    Args:
        pattern: Key pattern to search (default: "agent:*")
    """
    if not is_debug_enabled():
        return

    try:
        redis_client = get_redis_client()
        keys = redis_client.keys(pattern)
        print("\n" + "=" * 80)
        print(f"🔑 REDIS KEYS: {pattern}")
        print("=" * 80)
        if keys:
            for key in sorted(keys):
                key_type = redis_client.type(key)
                ttl = redis_client.ttl(key)
                ttl_str = f"TTL: {ttl}s" if ttl > 0 else "No TTL"
                print(f"  {key} ({key_type}, {ttl_str})")
        else:
            print("  (no keys found)")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"❌ Error listing Redis keys: {e}")


def test_all_connections() -> dict:
    """Test all database connections and return status.

    Returns:
        Dictionary with connection status for each database
    """
    status = {
        "postgres": test_postgres_connection(),
        "redis": test_redis_connection(),
        "milvus": test_milvus_connection(),
    }
    return status
