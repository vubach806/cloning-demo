"""Redis client utilities."""

from typing import Optional
from redis import Redis
from database.connection import db_manager, DatabaseSettings


def get_redis_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: Optional[int] = None,
    decode_responses: bool = True,
) -> Redis:
    """Get a Redis client instance.

    Args:
        host: Redis host (defaults to settings)
        port: Redis port (defaults to settings)
        db: Redis database number (defaults to settings)
        decode_responses: Whether to decode responses as strings (default: True)

    Returns:
        Redis client instance

    Example:
        ```python
        # Use default connection from settings
        redis_client = get_redis_client()

        # Use custom connection
        redis_client = get_redis_client(host="localhost", port=6379, db=0)

        # Test connection
        redis_client.ping()
        ```
    """
    if host is None and port is None and db is None:
        # Use the global database manager
        return db_manager.connect_redis()

    # Use custom connection
    settings = DatabaseSettings()
    return Redis(
        host=host or settings.redis_host,
        port=port or settings.redis_port,
        db=db if db is not None else settings.redis_db,
        decode_responses=decode_responses,
    )


# Convenience: Export a default client instance
def get_default_redis_client() -> Redis:
    """Get the default Redis client from database manager.

    Returns:
        Default Redis client instance
    """
    return db_manager.connect_redis()
