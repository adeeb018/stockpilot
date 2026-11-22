from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Warehouse
from app.schemas.warehouses import WarehouseCreate, WarehouseUpdate


class WarehouseService:

    @staticmethod
    async def create(
        db: AsyncSession,
        organization_id: UUID,
        data: WarehouseCreate,
    ) -> Warehouse:
        warehouse = Warehouse(
            organization_id=organization_id,
            name=data.name,
            code=data.code,
            address=data.address,
        )

        db.add(warehouse)

        try:
            await db.commit()
            await db.refresh(warehouse)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse code already exists in this organization",
            )

        return warehouse

    @staticmethod
    async def get(
        db: AsyncSession,
        organization_id: UUID,
        warehouse_id: UUID,
    ) -> Warehouse:
        result = await db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
        )

        warehouse = result.scalar_one_or_none()

        if warehouse is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found",
            )

        return warehouse

    @staticmethod
    async def list(
        db: AsyncSession,
        organization_id: UUID,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        filters = [
            Warehouse.organization_id == organization_id
        ]

        if search:
            search_term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Warehouse.name.ilike(search_term),
                    Warehouse.code.ilike(search_term),
                )
            )

        if is_active is not None:
            filters.append(Warehouse.is_active == is_active)

        count_result = await db.execute(
            select(func.count())
            .select_from(Warehouse)
            .where(*filters)
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(Warehouse)
            .where(*filters)
            .order_by(Warehouse.created_at.desc(), Warehouse.id)
            .limit(limit)
            .offset(offset)
        )

        return {
            "items": result.scalars().all(),
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    async def update(
        db: AsyncSession,
        organization_id: UUID,
        warehouse_id: UUID,
        data: WarehouseUpdate,
    ) -> Warehouse:
        warehouse = await WarehouseService.get(
            db,
            organization_id,
            warehouse_id,
        )

        updates = data.model_dump(exclude_unset=True)

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update",
            )

        for field, value in updates.items():
            setattr(warehouse, field, value)

        try:
            await db.commit()
            await db.refresh(warehouse)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update warehouse due to a database constraint",
            )

        return warehouse