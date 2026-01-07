"""Catalog/Inventory adapter layer.

This keeps DB access out of the orchestrator and lets us enable DB-backed
catalog/inventory gradually.

Today we only implement a minimal read path for products.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence
import uuid

from database.postgres.client import get_postgres_session
from database.postgres.models import Product


@dataclass(frozen=True)
class CatalogProduct:
    id: str
    name: str
    sku: Optional[str]
    price: Decimal
    stock_quantity: int


def list_products_for_shop(shop_id: str | uuid.UUID, limit: int = 50) -> Sequence[CatalogProduct]:
    """Return products for a shop.

    Args:
        shop_id: UUID string
        limit: max number of products
    """
    # Be flexible: callers may pass UUID or string.
    shop_uuid = shop_id if isinstance(shop_id, uuid.UUID) else uuid.UUID(str(shop_id))

    db = get_postgres_session()
    try:
        rows = (
            db.query(Product)
            .filter(Product.shop_id == shop_uuid)
            .order_by(Product.name.asc())
            .limit(limit)
            .all()
        )
        return [
            CatalogProduct(
                id=str(p.id),
                name=p.name,
                sku=p.sku,
                price=p.price,
                stock_quantity=p.stock_quantity,
            )
            for p in rows
        ]
    finally:
        db.close()
