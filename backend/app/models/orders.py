from uuid import UUID
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin

class Order(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "order_number", name="uq_orders_org_number"),
        UniqueConstraint("organization_id", "id", name="uq_orders_org_id"),
        Index("ix_orders_org_status_created", "organization_id", "status", "created_at"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

class OrderItem(UUIDPrimaryKey, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
            ondelete="CASCADE",
            name="fk_order_items_order_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name="fk_order_items_product_same_org",
        ),
        CheckConstraint("quantity > 0", name="order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="order_item_price_nonnegative"),
        CheckConstraint("line_total >= 0", name="order_item_total_nonnegative"),
    )

    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
