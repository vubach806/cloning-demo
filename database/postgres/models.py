"""SQLAlchemy models for PostgreSQL schema."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Sequence,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Shop(Base):
    """Shop model - stores information about individual shops."""

    __tablename__ = "shops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Shop ID")
    name = Column(Text, nullable=False, comment="Shop name")
    bot_config = Column(JSONB, nullable=True, comment="Bot configuration")
    owner_id = Column(UUID(as_uuid=True), nullable=True, comment="Owner ID")

    # Relationships
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="shop", cascade="all, delete-orphan")
    sales_pipelines = relationship(
        "SalesPipeline", back_populates="shop", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Shop(id={self.id}, name={self.name})>"


class Product(Base):
    """Product model - stores information about products offered by shops."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Product ID")
    shop_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="Which shop's product",
    )
    name = Column(Text, nullable=False, comment="Product name")
    sku = Column(Text, nullable=True, unique=True, comment="Stock Keeping Unit")
    price = Column(Numeric(10, 2), nullable=False, comment="Product price")
    stock_quantity = Column(Integer, nullable=False, default=0, comment="Stock quantity")
    specs = Column(JSON, nullable=True, comment="Product specifications")
    description = Column(Text, nullable=True, comment="Product description")
    image_url = Column(Text, nullable=True, comment="Product image URL")

    # Relationships
    shop = relationship("Shop", back_populates="products")
    documents = relationship("Document", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, shop_id={self.shop_id})>"


class Customer(Base):
    """Customer model - stores information about customers."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Customer ID")
    shop_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="Which shop's customer",
    )
    full_name = Column(Text, nullable=False, comment="Full name")
    phone = Column(Text, nullable=True, comment="Phone number")
    email = Column(Text, nullable=True, comment="Email address")
    membership_tier = Column(Text, nullable=True, comment="Membership tier")
    preferences = Column(JSON, nullable=True, comment="Customer preferences")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last update timestamp",
    )

    # Relationships
    shop = relationship("Shop", back_populates="customers")

    def __repr__(self):
        return f"<Customer(id={self.id}, full_name={self.full_name}, shop_id={self.shop_id})>"


class Document(Base):
    """Document model - stores information about documents related to products."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Document ID")
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Related product ID",
    )
    file_name = Column(Text, nullable=False, comment="File name")
    file_path = Column(Text, nullable=False, comment="File path")
    status = Column(Text, nullable=True, default="active", comment="Document status")

    # Relationships
    product = relationship("Product", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, file_name={self.file_name}, product_id={self.product_id})>"


class SalesPipeline(Base):
    """SalesPipeline model - stores information about sales processes for shops."""

    __tablename__ = "sales_pipelines"

    id = Column(
        Integer,
        Sequence("sales_pipelines_id_seq"),
        primary_key=True,
        comment="Pipeline ID",
    )
    shop_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="Which shop's process",
    )
    stage_name = Column(Text, nullable=False, comment="Stage name")
    step_order = Column(Integer, nullable=False, comment="Step order in pipeline")
    description = Column(Text, nullable=True, comment="Stage description")

    # Relationships
    shop = relationship("Shop", back_populates="sales_pipelines")
    sessions = relationship(
        "Session", foreign_keys="Session.current_stage_id", back_populates="current_stage"
    )

    def __repr__(self):
        return (
            f"<SalesPipeline(id={self.id}, stage_name={self.stage_name}, shop_id={self.shop_id})>"
        )


class Session(Base):
    """Session model - stores information about user sessions (Episodic Memory)."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Session ID")
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="User identifier")
    title = Column(Text, nullable=True, comment="Conversation title")
    handoff_reason = Column(
        Text,
        nullable=True,
        comment="Reason for handoff (e.g., 'Khách chửi thề', 'Hỏi vấn đề phức tạp')",
    )
    current_stage_id = Column(
        Integer,
        ForeignKey("sales_pipelines.id", ondelete="SET NULL"),
        nullable=True,
        comment="Current stage ID (replaces deal_status, FK to sales_pipelines)",
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last message update timestamp (used for sorting)",
    )
    session_metadata = Column(
        JSONB,
        name="metadata",
        nullable=True,
        comment="Additional metadata (e.g., {'summary': '', 'tags': ['coding']})",
    )

    # Relationships
    current_stage = relationship("SalesPipeline", foreign_keys=[current_stage_id])
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Message(Base):
    """Message model - stores individual messages in a session."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Message ID")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Session ID (FK to sessions)",
    )
    role = Column(
        String(50), nullable=False, comment="Sender role: user, assistant, system, or tool"
    )
    content = Column(Text, nullable=False, comment="Pure text content of the message")
    tool_calls = Column(
        JSONB, nullable=True, comment="JSON representation of tool calls if role is assistant"
    )
    token_count = Column(Integer, nullable=True, comment="Number of tokens (for cost statistics)")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="Creation timestamp"
    )

    # Relationships
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role})>"
