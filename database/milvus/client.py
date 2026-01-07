"""Milvus client utilities."""

from typing import Optional
from pymilvus import connections, Collection
from database.connection import db_manager, DatabaseSettings


def get_milvus_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    alias: str = "default",
) -> None:
    """Connect to Milvus server.

    Args:
        host: Milvus host (defaults to settings)
        port: Milvus port (defaults to settings)
        alias: Connection alias (default: "default")

    Example:
        ```python
        # Use default connection from settings
        get_milvus_client()

        # Use custom connection
        get_milvus_client(host="localhost", port=19530)

        # Get collection
        collection = Collection("my_collection")
        ```
    """
    settings = DatabaseSettings()
    connections.connect(
        alias=alias,
        host=host or settings.milvus_host,
        port=port or settings.milvus_port,
    )


def get_default_milvus_connection() -> None:
    """Get default Milvus connection from database manager.

    Returns:
        None (connection is established)
    """
    db_manager.connect_milvus()


def get_collection(collection_name: str) -> Collection:
    """Get a Milvus collection.

    Args:
        collection_name: Name of the collection

    Returns:
        Milvus Collection object
    """
    return db_manager.get_milvus_collection(collection_name)
