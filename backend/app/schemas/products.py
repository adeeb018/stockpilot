from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: UUID | None = None
    unit_price: Decimal = Field(
        ge=0,
        max_digits=14,
        decimal_places=2
    )


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID | None
    unit_price: Decimal
    is_active: bool