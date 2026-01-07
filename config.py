"""Centralized config for demo + gradual wiring.

We keep the project multi-shop capable at the data model level, but for local demo
it's convenient to fix one default shop.

Environment variables (optional):
- DEMO_SHOP_ID: UUID string for the default demo shop
- DEMO_SHOP_NAME: display name (default: Vieroc)
- USE_DB_CATALOG: enable DB-backed product catalog for upsell candidate list

Note: For now we read environment variables directly (no new deps).
"""

from __future__ import annotations

import os
import uuid


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


DEMO_SHOP_ID = uuid.UUID(
    os.getenv("DEMO_SHOP_ID", "11111111-1111-1111-1111-111111111111")
)
DEMO_SHOP_NAME = os.getenv("DEMO_SHOP_NAME", "Vieroc")

USE_DB_CATALOG = True #_env_bool("USE_DB_CATALOG", default=True)
