"""Milvus schema implementation for semantic memory."""

from typing import List, Optional, Dict, Any
from pymilvus import (
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    connections,
    utility,
)
from database.connection import db_manager
from database.milvus.models import SemanticMemoryRecord, SearchResult


def create_semantic_memory_collection(
    collection_name: str,
    dense_vector_dim: int = 768,
    sparse_vector_dim: Optional[int] = None,
    description: str = "Semantic memory collection for vector search",
) -> Collection:
    """Create a semantic memory collection with the specified schema.

    Args:
        collection_name: Name of the collection
        dense_vector_dim: Dimension of dense vector (default: 768)
        sparse_vector_dim: Dimension of sparse vector (optional, for BM25)
        description: Collection description

    Returns:
        Created Milvus Collection

    Schema fields:
        - id: Int64 (Primary Key, AutoID)
        - dense_vector: FloatVector (semantic vector)
        - sparse_vector: FloatVector (BM25 sparse vector, optional)
        - text_content: VarChar (original content)
        - shop_id: Int64 (Partition Key)
        - doc_id: VarChar (UUID from Postgres)
        - product_id: Int64 (ID from Postgres)
        - metadata: JSON (Dynamic metadata)
    """
    # Ensure connection
    db_manager.connect_milvus()

    # Check if collection exists
    if utility.has_collection(collection_name):
        return Collection(collection_name)

    # Define fields
    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.INT64,
            is_primary=True,
            auto_id=True,
            description="Primary key (AutoID)",
        ),
        FieldSchema(
            name="dense_vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=dense_vector_dim,
            description="Semantic vector (dense embedding)",
        ),
        FieldSchema(
            name="text_content",
            dtype=DataType.VARCHAR,
            max_length=65535,
            description="Original text content",
        ),
        FieldSchema(
            name="shop_id",
            dtype=DataType.INT64,
            description="Partition key - shop identifier",
        ),
        FieldSchema(
            name="doc_id",
            dtype=DataType.VARCHAR,
            max_length=255,
            description="UUID from Postgres document ID",
        ),
        FieldSchema(
            name="product_id",
            dtype=DataType.INT64,
            description="Product ID from Postgres",
        ),
        FieldSchema(
            name="metadata",
            dtype=DataType.JSON,
            description="Dynamic metadata as JSON",
        ),
    ]

    # Add sparse vector if dimension is provided
    if sparse_vector_dim is not None:
        fields.insert(
            2,
            FieldSchema(
                name="sparse_vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=sparse_vector_dim,
                description="BM25 sparse vector",
            ),
        )

    # Create schema
    schema = CollectionSchema(
        fields=fields,
        description=description,
        enable_dynamic_field=True,
    )

    # Create collection
    collection = Collection(
        name=collection_name,
        schema=schema,
        using="default",
    )

    # Create index for dense_vector
    index_params = {
        "metric_type": "L2",  # or "IP" for inner product
        "index_type": "IVF_FLAT",  # or "HNSW" for better performance
        "params": {"nlist": 1024},
    }
    collection.create_index(
        field_name="dense_vector",
        index_params=index_params,
    )

    # Create index for sparse_vector if exists
    if sparse_vector_dim is not None:
        sparse_index_params = {
            "metric_type": "IP",  # Inner product for sparse vectors
            "index_type": "SPARSE_INVERTED_INDEX",
        }
        collection.create_index(
            field_name="sparse_vector",
            index_params=sparse_index_params,
        )

    # Load collection
    collection.load()

    return collection


class SemanticMemoryCollection:
    """Manages semantic memory collection operations."""

    def __init__(
        self,
        collection_name: str,
        dense_vector_dim: int = 768,
        sparse_vector_dim: Optional[int] = None,
    ):
        """Initialize semantic memory collection manager.

        Args:
            collection_name: Name of the collection
            dense_vector_dim: Dimension of dense vector
            sparse_vector_dim: Dimension of sparse vector (optional)
        """
        self.collection_name = collection_name
        self.dense_vector_dim = dense_vector_dim
        self.sparse_vector_dim = sparse_vector_dim

        # Ensure connection
        db_manager.connect_milvus()

        # Create or get collection
        if not utility.has_collection(collection_name):
            self.collection = create_semantic_memory_collection(
                collection_name=collection_name,
                dense_vector_dim=dense_vector_dim,
                sparse_vector_dim=sparse_vector_dim,
            )
        else:
            self.collection = Collection(collection_name)
            if not self.collection.has_index():
                # Create index if not exists
                index_params = {
                    "metric_type": "L2",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024},
                }
                self.collection.create_index(
                    field_name="dense_vector",
                    index_params=index_params,
                )
            if not self.collection.is_empty:
                self.collection.load()

    def insert(self, records: List[SemanticMemoryRecord]) -> List[int]:
        """Insert records into the collection.

        Args:
            records: List of SemanticMemoryRecord to insert

        Returns:
            List of inserted IDs
        """
        if not records:
            return []

        # Convert records to Milvus format
        data = [record.to_milvus_dict() for record in records]

        # Prepare data for insertion
        insert_data = {
            "dense_vector": [r["dense_vector"] for r in data],
            "text_content": [r["text_content"] for r in data],
            "shop_id": [r["shop_id"] for r in data],
            "doc_id": [r.get("doc_id", "") for r in data],
            "product_id": [r.get("product_id", 0) for r in data],
            "metadata": [r.get("metadata", {}) for r in data],
        }

        # Add sparse_vector if provided
        if self.sparse_vector_dim is not None:
            insert_data["sparse_vector"] = [
                r.get("sparse_vector", [0.0] * self.sparse_vector_dim) for r in data
            ]

        # Insert data
        result = self.collection.insert(insert_data)
        self.collection.flush()

        return result.primary_keys

    def search(
        self,
        query_vector: List[float],
        shop_id: Optional[int] = None,
        limit: int = 10,
        search_params: Optional[Dict[str, Any]] = None,
        output_fields: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Query dense vector
            shop_id: Filter by shop_id (optional)
            limit: Number of results to return
            search_params: Additional search parameters
            output_fields: Fields to return in results

        Returns:
            List of SearchResult objects
        """
        if output_fields is None:
            output_fields = [
                "id",
                "text_content",
                "shop_id",
                "doc_id",
                "product_id",
                "metadata",
            ]

        # Build expression for filtering
        expr = None
        if shop_id is not None:
            expr = f"shop_id == {shop_id}"

        # Default search params
        if search_params is None:
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        # Perform search
        results = self.collection.search(
            data=[query_vector],
            anns_field="dense_vector",
            param=search_params,
            limit=limit,
            expr=expr,
            output_fields=output_fields,
        )

        # Parse results
        search_results = []
        for hit in results[0]:
            result = SearchResult(
                id=hit.id,
                distance=hit.distance,
                text_content=hit.entity.get("text_content", ""),
                shop_id=hit.entity.get("shop_id", 0),
                doc_id=hit.entity.get("doc_id"),
                product_id=hit.entity.get("product_id"),
                metadata=hit.entity.get("metadata"),
            )
            search_results.append(result)

        return search_results

    def search_by_sparse_vector(
        self,
        query_sparse_vector: List[float],
        shop_id: Optional[int] = None,
        limit: int = 10,
        search_params: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search using sparse vector (BM25).

        Args:
            query_sparse_vector: Query sparse vector
            shop_id: Filter by shop_id (optional)
            limit: Number of results to return
            search_params: Additional search parameters

        Returns:
            List of SearchResult objects
        """
        if self.sparse_vector_dim is None:
            raise ValueError("Sparse vector dimension not configured")

        expr = None
        if shop_id is not None:
            expr = f"shop_id == {shop_id}"

        if search_params is None:
            search_params = {"metric_type": "IP", "params": {}}

        results = self.collection.search(
            data=[query_sparse_vector],
            anns_field="sparse_vector",
            param=search_params,
            limit=limit,
            expr=expr,
            output_fields=["id", "text_content", "shop_id", "doc_id", "product_id", "metadata"],
        )

        search_results = []
        for hit in results[0]:
            result = SearchResult(
                id=hit.id,
                distance=hit.distance,
                text_content=hit.entity.get("text_content", ""),
                shop_id=hit.entity.get("shop_id", 0),
                doc_id=hit.entity.get("doc_id"),
                product_id=hit.entity.get("product_id"),
                metadata=hit.entity.get("metadata"),
            )
            search_results.append(result)

        return search_results

    def delete_by_shop_id(self, shop_id: int) -> None:
        """Delete all records for a specific shop.

        Args:
            shop_id: Shop ID to delete records for
        """
        expr = f"shop_id == {shop_id}"
        self.collection.delete(expr)
        self.collection.flush()

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete record by document ID.

        Args:
            doc_id: Document ID to delete
        """
        expr = f'doc_id == "{doc_id}"'
        self.collection.delete(expr)
        self.collection.flush()

    def delete_by_product_id(self, product_id: int, shop_id: Optional[int] = None) -> None:
        """Delete record by product ID.

        Args:
            product_id: Product ID to delete
            shop_id: Optional shop_id filter
        """
        if shop_id is not None:
            expr = f"product_id == {product_id} && shop_id == {shop_id}"
        else:
            expr = f"product_id == {product_id}"
        self.collection.delete(expr)
        self.collection.flush()

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dictionary with collection stats
        """
        stats = self.collection.num_entities
        return {
            "num_entities": stats,
            "collection_name": self.collection_name,
        }
