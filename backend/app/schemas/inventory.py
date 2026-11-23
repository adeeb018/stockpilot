from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryAdjustmentCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    quantity_delta: int = Field(
        description="Positive to add stock, negative to remove stock",
        ne=0,
    )


class InventoryBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity_on_hand: int
    quantity_reserved: int


class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    product_id: UUID
    warehouse_id: UUID
    movement_type: str
    quantity_delta: int
    reference_type: str | None
    reference_id: UUID | None
    created_by: UUID
    created_at: datetime