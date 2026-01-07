"""Seed the database with mock data for local development.

This script is intentionally lightweight and idempotent enough for dev:
- Creates a demo Shop named "Vieroc"
- Creates a basic SalesPipeline for that shop
- Creates a set of demo Products with stock

Run (using uv):
    uv run python seed_mock_data.py

Prereqs:
- PostgreSQL running (docker-compose up -d)
- Tables created (uv run python init_db.py)
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from database.postgres.client import get_postgres_session
from database.postgres.models import Shop, Product, SalesPipeline

from config import DEMO_SHOP_ID, DEMO_SHOP_NAME


def seed_shop(db) -> Shop:
    shop = db.query(Shop).filter(Shop.id == DEMO_SHOP_ID).first()
    if shop:
        return shop

    shop = Shop(
        id=DEMO_SHOP_ID,
        name=DEMO_SHOP_NAME,
        bot_config={
            "company_name": DEMO_SHOP_NAME,
            "currency": "VND",
            "language": "vi",
            # placeholders for later gradual wiring
            "features": {
                "use_db_catalog": False,
                "use_db_inventory": False,
            },
        },
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def seed_sales_pipeline(db, shop: Shop) -> None:
    existing = db.query(SalesPipeline).filter(SalesPipeline.shop_id == shop.id).count()
    if existing:
        return

    stages = [
        ("greeting", 1, "Chào hỏi và bắt đầu tư vấn"),
        ("need_discovery", 2, "Khai thác nhu cầu"),
        ("solution_matching", 3, "Gợi ý giải pháp / sản phẩm"),
        ("price_discussion", 4, "Trao đổi giá và ưu đãi"),
        ("objection_handling", 5, "Xử lý băn khoăn"),
        ("closing", 6, "Chốt đơn"),
    ]

    for name, order, desc in stages:
        db.add(
            SalesPipeline(
                shop_id=shop.id,
                stage_name=name,
                step_order=order,
                description=desc,
            )
        )

    db.commit()


def seed_products(db, shop: Shop) -> None:
    # Clear existing products for this shop to allow re-seeding with more
    db.query(Product).filter(Product.shop_id == shop.id).delete()
    db.commit()

    products = [
        {
            "name": "Áo thun basic Vieroc",
            "sku": "VIEROC-TSHIRT-BASIC",
            "price": Decimal("199000"),
            "stock_quantity": 42,
            "specs": {"chat_lieu": "cotton", "form": "regular"},
            "description": "Áo thun basic mềm, dễ phối đồ.",
        },
        {
            "name": "Áo sơ mi công sở Vieroc",
            "sku": "VIEROC-SHIRT-OFFICE",
            "price": Decimal("349000"),
            "stock_quantity": 18,
            "specs": {"chat_lieu": "poly-cotton", "form": "slim"},
            "description": "Sơ mi lịch sự, phù hợp đi làm.",
        },
        {
            "name": "Áo hoodie Vieroc",
            "sku": "VIEROC-HOODIE",
            "price": Decimal("499000"),
            "stock_quantity": 12,
            "specs": {"chat_lieu": "ni", "mu": True},
            "description": "Hoodie ấm, phù hợp thời tiết mát lạnh.",
        },
        {
            "name": "Quần jean slim Vieroc",
            "sku": "VIEROC-JEANS-SLIM",
            "price": Decimal("599000"),
            "stock_quantity": 25,
            "specs": {"chat_lieu": "jean", "form": "slim"},
            "description": "Quần jean ôm dáng, dễ phối với áo thun.",
        },
        {
            "name": "Áo polo Vieroc",
            "sku": "VIEROC-POLO",
            "price": Decimal("299000"),
            "stock_quantity": 30,
            "specs": {"chat_lieu": "pique", "form": "regular"},
            "description": "Áo polo thể thao, thoáng mát.",
        },
        {
            "name": "Giày sneaker Vieroc",
            "sku": "VIEROC-SNEAKER",
            "price": Decimal("799000"),
            "stock_quantity": 15,
            "specs": {"size": "39-45", "chat_lieu": "da tổng hợp"},
            "description": "Giày sneaker phong cách, phù hợp đi chơi.",
        },
        {
            "name": "Áo khoác bomber Vieroc",
            "sku": "VIEROC-BOMBER",
            "price": Decimal("699000"),
            "stock_quantity": 10,
            "specs": {"chat_lieu": "polyester", "mu": False},
            "description": "Áo khoác bomber trẻ trung, chống gió.",
        },
        {
            "name": "Quần short thể thao Vieroc",
            "sku": "VIEROC-SHORTS",
            "price": Decimal("249000"),
            "stock_quantity": 35,
            "specs": {"chat_lieu": "nylon", "form": "loose"},
            "description": "Quần short thoáng khí, lý tưởng cho thể thao.",
        },
        {
            "name": "Túi xách canvas Vieroc",
            "sku": "VIEROC-BAG",
            "price": Decimal("399000"),
            "stock_quantity": 20,
            "specs": {"kich_thuoc": "30x40cm", "chat_lieu": "canvas"},
            "description": "Túi xách tiện dụng, nhiều ngăn.",
        },
        {
            "name": "Mũ lưỡi trai Vieroc",
            "sku": "VIEROC-CAP",
            "price": Decimal("149000"),
            "stock_quantity": 50,
            "specs": {"chat_lieu": "cotton", "mau": "đen/trắng"},
            "description": "Mũ lưỡi trai basic, dễ phối đồ.",
        },
        {
            "name": "Áo len cardigan Vieroc",
            "sku": "VIEROC-CARDIGAN",
            "price": Decimal("449000"),
            "stock_quantity": 22,
            "specs": {"chat_lieu": "len", "form": "oversize"},
            "description": "Cardigan ấm áp, phù hợp mùa thu đông.",
        },
        {
            "name": "Quần jogger Vieroc",
            "sku": "VIEROC-JOGGER",
            "price": Decimal("349000"),
            "stock_quantity": 28,
            "specs": {"chat_lieu": "cotton blend", "form": "tapered"},
            "description": "Quần jogger thoải mái, phong cách streetwear.",
        },
        {
            "name": "Giày boots Vieroc",
            "sku": "VIEROC-BOOTS",
            "price": Decimal("899000"),
            "stock_quantity": 8,
            "specs": {"size": "40-46", "chat_lieu": "da thật"},
            "description": "Giày boots cổ cao, bền bỉ.",
        },
        {
            "name": "Áo blazer Vieroc",
            "sku": "VIEROC-BLAZER",
            "price": Decimal("799000"),
            "stock_quantity": 14,
            "specs": {"chat_lieu": "wool blend", "form": "fitted"},
            "description": "Blazer lịch sự, phù hợp công sở.",
        },
        {
            "name": "Vớ thể thao Vieroc",
            "sku": "VIEROC-SOCKS",
            "price": Decimal("99000"),
            "stock_quantity": 60,
            "specs": {"chat_lieu": "cotton", "size": "universal"},
            "description": "Vớ thoáng khí, chống hôi chân.",
        },
    ]

    for p in products:
        db.add(
            Product(
                shop_id=shop.id,
                name=p["name"],
                sku=p["sku"],
                price=p["price"],
                stock_quantity=p["stock_quantity"],
                specs=p.get("specs"),
                description=p.get("description"),
                image_url=None,
            )
        )

    db.commit()


def main() -> None:
    db = get_postgres_session()
    try:
        shop = seed_shop(db)
        seed_sales_pipeline(db, shop)
        seed_products(db, shop)
        print("✅ Seeded mock data for shop Vieroc")
    finally:
        db.close()


if __name__ == "__main__":
    main()
