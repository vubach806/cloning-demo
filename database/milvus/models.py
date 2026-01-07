"""Pydantic models for Milvus schema."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class SemanticMemoryRecord(BaseModel):
    """A record in the semantic memory collection."""

    id: Optional[int] = Field(None, description="Primary key (AutoID)")
    dense_vector: List[float] = Field(description="Semantic vector (dense embedding)")
    sparse_vector: Optional[List[float]] = Field(None, description="BM25 sparse vector")
    text_content: str = Field(description="Original text content")
    shop_id: int = Field(description="Partition key - shop identifier")
    doc_id: Optional[str] = Field(None, description="UUID from Postgres document ID")
    product_id: Optional[int] = Field(None, description="Product ID from Postgres")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Dynamic metadata as JSON")

    def to_milvus_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Milvus insertion.

        Returns:
            Dictionary ready for Milvus insertion
        """
        data = {
            "dense_vector": self.dense_vector,
            "text_content": self.text_content,
            "shop_id": self.shop_id,
        }

        if self.sparse_vector is not None:
            data["sparse_vector"] = self.sparse_vector

        if self.doc_id is not None:
            data["doc_id"] = self.doc_id
        else:
            data["doc_id"] = str(uuid.uuid4())

        if self.product_id is not None:
            data["product_id"] = self.product_id

        if self.metadata is not None:
            data["metadata"] = self.metadata

        return data


class SearchResult(BaseModel):
    """Search result from Milvus."""

    id: int = Field(description="Record ID")
    distance: float = Field(description="Distance/score")
    text_content: str = Field(description="Text content")
    shop_id: int = Field(description="Shop ID")
    doc_id: Optional[str] = Field(None, description="Document ID")
    product_id: Optional[int] = Field(None, description="Product ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
