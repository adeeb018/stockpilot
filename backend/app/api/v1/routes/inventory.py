from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_permission
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryBalanceResponse,
    InventoryMovementResponse,
)
from app.services.inventory_service import InventoryService


from app.schemas.reservations import (
    ReservationCreate,
    ReservationResponse,
)
from app.services.reservation_service import ReservationService


router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/adjustments", status_code=201)
async def adjust_inventory(
    data: InventoryAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("inventory.adjust")),
):
    return await InventoryService.adjust_stock(
        db=db,
        organization_id=context.organization.id,
        user_id=context.user.id,
        data=data,
    )


@router.get("/balances", response_model=list[InventoryBalanceResponse])
async def get_inventory_balances(
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("inventory.read")),
):
    return await InventoryService.get_balances(
        db=db,
        organization_id=context.organization.id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )


@router.get("/movements", response_model=list[InventoryMovementResponse])
async def get_inventory_movements(
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("inventory.read")),
):
    return await InventoryService.get_movements(
        db=db,
        organization_id=context.organization.id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/reservations",
    response_model=ReservationResponse,
    status_code=201,
)
async def create_reservation(
    data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("inventory.reserve")),
):
    return await ReservationService.create(
        db=db,
        organization_id=context.organization.id,
        data=data,
    )