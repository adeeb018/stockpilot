from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import ReservationStatus


class ReservationCreate(BaseModel):
    order_id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: int = Field(gt=0)


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    order_id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity: int
    status: ReservationStatus
    expires_at: datetime | None