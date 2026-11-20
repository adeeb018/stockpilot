from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin

class MovementType(str, Enum):
    RECEIPT = "RECEIPT"
    ADJUSTMENT = "ADJUSTMENT"
    FULFILLMENT = "FULFILLMENT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    REVERSAL = "REVERSAL"

class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    FULFILLED = "FULFILLED"
    EXPIRED = "EXPIRED"

class InventoryBalance(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_wh_product"),
        UniqueConstraint("organization_id", "id", name="uq_inventory_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"],
            ["warehouses.organization_id", "warehouses.id"],
            name="fk_inventory_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name="fk_inventory_product_same_org",
        ),
        CheckConstraint("quantity_on_hand >= 0", name="on_hand_nonnegative"),
        CheckConstraint("quantity_reserved >= 0", name="reserved_nonnegative"),
        CheckConstraint("quantity_reserved <= quantity_on_hand", name="reserved_lte_on_hand"),
        Index("ix_inventory_org_warehouse", "organization_id", "warehouse_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"), nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"), nullable=False)

class InventoryMovement(UUIDPrimaryKey, Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"],
            ["warehouses.organization_id", "warehouses.id"],
            name="fk_movements_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name="fk_movements_product_same_org",
        ),
        Index("ix_movements_org_product_created", "organization_id", "product_id", "created_at"),
        Index("ix_movements_reference", "reference_type", "reference_id"),
        CheckConstraint("quantity_delta <> 0", name="movement_delta_nonzero"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(String(30), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

class StockReservation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "warehouse_id"],
            ["warehouses.organization_id", "warehouses.id"],
            name="fk_reservations_warehouse_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name="fk_reservations_product_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
            name="fk_reservations_order_same_org",
        ),
        CheckConstraint("quantity > 0", name="reservation_quantity_positive"),
        Index("ix_reservations_status_expiry", "status", "expires_at"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(String(20), default=ReservationStatus.ACTIVE, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
