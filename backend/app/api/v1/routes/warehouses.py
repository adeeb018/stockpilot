from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_permission
from app.schemas.warehouses import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services.warehouse_service import WarehouseService

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.post("", response_model=WarehouseResponse, status_code=201)
async def create_warehouse(
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("warehouse.create")),
):
    return await WarehouseService.create(
        db=db,
        organization_id=context.organization.id,
        data=data,
    )


@router.get("")
async def list_warehouses(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("warehouse.read")),
):
    return await WarehouseService.list(
        db=db,
        organization_id=context.organization.id,
        limit=limit,
        offset=offset,
        search=search,
        is_active=is_active,
    )


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: UUID,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("warehouse.read")),
):
    return await WarehouseService.get(
        db=db,
        organization_id=context.organization.id,
        warehouse_id=warehouse_id,
    )


@router.patch("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: UUID,
    data: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    context=Depends(require_permission("warehouse.update")),
):
    return await WarehouseService.update(
        db=db,
        organization_id=context.organization.id,
        warehouse_id=warehouse_id,
        data=data,
    )