from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Order,
    OrderItem,
    InventoryBalance,
    StockReservation,
)
from app.models.inventory import ReservationStatus
from app.schemas.reservations import ReservationCreate


class ReservationService:

    @staticmethod
    async def create(
        db: AsyncSession,
        organization_id: UUID,
        data: ReservationCreate,
        expires_in_minutes: int = 30,
    ) -> StockReservation:

        try:
            # 1. Lock and validate the order.
            order_result = await db.execute(
                select(Order)
                .where(
                    Order.id == data.order_id,
                    Order.organization_id == organization_id,
                )
                .with_for_update()
            )

            order = order_result.scalar_one_or_none()

            if order is None:
                raise HTTPException(
                    status_code=404,
                    detail="Order not found",
                )

            if order.status != "CONFIRMED":
                raise HTTPException(
                    status_code=409,
                    detail="Only confirmed orders can reserve stock",
                )

            # 2. Lock the matching order item.
            item_result = await db.execute(
                select(OrderItem)
                .where(
                    OrderItem.organization_id == organization_id,
                    OrderItem.order_id == data.order_id,
                    OrderItem.product_id == data.product_id,
                )
                .with_for_update()
            )

            order_item = item_result.scalar_one_or_none()

            if order_item is None:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found in this order",
                )

            # 3. Calculate how much has already been reserved
            # for this order item.
            reserved_result = await db.execute(
                select(
                    func.coalesce(
                        func.sum(StockReservation.quantity), 0
                    )
                ).where(
                    StockReservation.organization_id == organization_id,
                    StockReservation.order_id == data.order_id,
                    StockReservation.product_id == data.product_id,
                    StockReservation.status == ReservationStatus.ACTIVE,
                )
            )

            already_reserved = reserved_result.scalar_one()

            if already_reserved + data.quantity > order_item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Reservation exceeds the remaining order quantity",
                )

            # 4. Lock inventory balance.
            balance_result = await db.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.organization_id == organization_id,
                    InventoryBalance.product_id == data.product_id,
                    InventoryBalance.warehouse_id == data.warehouse_id,
                )
                .with_for_update()
            )

            balance = balance_result.scalar_one_or_none()

            if balance is None:
                raise HTTPException(
                    status_code=409,
                    detail="No inventory balance exists for this product and warehouse",
                )

            # 5. Check available stock.
            available = (
                balance.quantity_on_hand
                - balance.quantity_reserved
            )

            if data.quantity > available:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient available stock",
                )

            # 6. Update reserved quantity.
            balance.quantity_reserved += data.quantity

            # 7. Create reservation.
            reservation = StockReservation(
                organization_id=organization_id,
                order_id=data.order_id,
                product_id=data.product_id,
                warehouse_id=data.warehouse_id,
                quantity=data.quantity,
                status=ReservationStatus.ACTIVE,
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=expires_in_minutes),
            )

            db.add(reservation)

            # 8. Commit both operations together.
            await db.commit()
            await db.refresh(reservation)

            return reservation

        except HTTPException:
            await db.rollback()
            raise

        except Exception:
            await db.rollback()
            raise