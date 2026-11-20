from uuid import UUID
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin

class Category(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_categories_org_id"),
        UniqueConstraint("organization_id", "name", name="uq_categories_org_name"),
        ForeignKeyConstraint(
            ["organization_id", "parent_id"],
            ["categories.organization_id", "categories.id"],
            name="fk_categories_parent_same_org",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    name: Mapped[str] = mapped_column(String(100), nullable=False)

class Product(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_products_org_sku"),
        UniqueConstraint("organization_id", "id", name="uq_products_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "category_id"],
            ["categories.organization_id", "categories.id"],
            name="fk_products_category_same_org",
        ),
        CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Warehouse(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_warehouses_org_code"),
        UniqueConstraint("organization_id", "id", name="uq_warehouses_org_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class WarehouseLocation(UUIDPrimaryKey, Base):
    __tablename__ = "warehouse_locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_locations_wh_code"),
    )

    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
