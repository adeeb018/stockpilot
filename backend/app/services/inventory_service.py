from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InventoryBalance,
    InventoryMovement,
    Product,
    Warehouse,
)
from app.schemas.inventory import InventoryAdjustmentCreate


class InventoryService:

    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        data: InventoryAdjustmentCreate,
    ):
        try:
            # 1. Validate that product belongs to this organization.
            product_result = await db.execute(
                select(Product).where(
                    Product.id == data.product_id,
                    Product.organization_id == organization_id,
                    Product.is_active.is_(True),
                )
            )

            if product_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found or inactive",
                )

            # 2. Validate that warehouse belongs to this organization.
            warehouse_result = await db.execute(
                select(Warehouse).where(
                    Warehouse.id == data.warehouse_id,
                    Warehouse.organization_id == organization_id,
                    Warehouse.is_active.is_(True),
                )
            )

            if warehouse_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Warehouse not found or inactive",
                )

            # 3. Ensure a balance row exists.
            # Concurrent inserts are handled by the unique constraint.
            insert_balance = (
                insert(InventoryBalance)
                .values(
                    organization_id=organization_id,
                    product_id=data.product_id,
                    warehouse_id=data.warehouse_id,
                    quantity_on_hand=0,
                    quantity_reserved=0,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        InventoryBalance.warehouse_id,
                        InventoryBalance.product_id,
                    ]
                )
            )

            await db.execute(insert_balance)

            # 4. Atomically adjust stock.
            # The WHERE clause prevents stock falling below reserved quantity.
            adjustment = (
                update(InventoryBalance)
                .where(
                    InventoryBalance.organization_id == organization_id,
                    InventoryBalance.product_id == data.product_id,
                    InventoryBalance.warehouse_id == data.warehouse_id,
                    (
                        InventoryBalance.quantity_on_hand
                        + data.quantity_delta
                    ) >= InventoryBalance.quantity_reserved,
                )
                .values(
                    quantity_on_hand=(
                        InventoryBalance.quantity_on_hand
                        + data.quantity_delta
                    )
                )
                .returning(InventoryBalance)
            )

            result = await db.execute(adjustment)
            balance = result.scalar_one_or_none()

            if balance is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Insufficient available stock for this adjustment",
                )

            # 5. Record the adjustment in the append-only ledger.
            movement = InventoryMovement(
                organization_id=organization_id,
                product_id=data.product_id,
                warehouse_id=data.warehouse_id,
                movement_type="ADJUSTMENT",
                quantity_delta=data.quantity_delta,
                reference_type="MANUAL_ADJUSTMENT",
                reference_id=None,
                created_by=user_id,
            )

            db.add(movement)

            # 6. Commit balance and movement together.
            await db.commit()
            await db.refresh(balance)
            await db.refresh(movement)

            return {
                "balance": balance,
                "movement": movement,
            }

        except HTTPException:
            await db.rollback()
            raise

        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def get_balances(
        db: AsyncSession,
        organization_id: UUID,
        warehouse_id: UUID | None = None,
        product_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        query = select(InventoryBalance).where(
            InventoryBalance.organization_id == organization_id
        )

        if warehouse_id:
            query = query.where(
                InventoryBalance.warehouse_id == warehouse_id
            )

        if product_id:
            query = query.where(
                InventoryBalance.product_id == product_id
            )

        query = (
            query
            .order_by(InventoryBalance.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_movements(
        db: AsyncSession,
        organization_id: UUID,
        product_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        query = select(InventoryMovement).where(
            InventoryMovement.organization_id == organization_id
        )

        if product_id:
            query = query.where(
                InventoryMovement.product_id == product_id
            )

        if warehouse_id:
            query = query.where(
                InventoryMovement.warehouse_id == warehouse_id
            )

        query = (
            query
            .order_by(
                InventoryMovement.created_at.desc(),
                InventoryMovement.id,
            )
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return result.scalars().all()