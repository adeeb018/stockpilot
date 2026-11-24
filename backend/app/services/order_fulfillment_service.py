from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderItem, StockReservation
from app.models.inventory import ReservationStatus


async def fulfill_order(
    session: AsyncSession,
    organization_id,
    order_id,
    user_id,
):
    try:
        # 1. Lock the order.
        result = await session.execute(
            select(Order)
            .where(
                Order.id == order_id,
                Order.organization_id == organization_id,
            )
            .with_for_update()
        )

        order = result.scalar_one_or_none()

        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != "CONFIRMED":
            raise HTTPException(
                status_code=409,
                detail="Only confirmed orders can be fulfilled",
            )

        # 2. Lock order items.
        result = await session.execute(
            select(OrderItem)
            .where(
                OrderItem.organization_id == organization_id,
                OrderItem.order_id == order_id,
            )
            .order_by(OrderItem.id)
            .with_for_update()
        )

        order_items = result.scalars().all()

        if not order_items:
            raise HTTPException(
                status_code=409,
                detail="Order has no items",
            )

        # 3. Lock active reservations.
        result = await session.execute(
            select(StockReservation)
            .where(
                StockReservation.organization_id == organization_id,
                StockReservation.order_id == order_id,
                StockReservation.status == ReservationStatus.ACTIVE,
            )
            .order_by(StockReservation.id)
            .with_for_update()
        )

        reservations = result.scalars().all()

        if not reservations:
            raise HTTPException(
                status_code=409,
                detail="Order has no active reservations",
            )

        # 4. Aggregate ordered quantities by product.
        ordered_quantities = defaultdict(int)

        for item in order_items:
            ordered_quantities[item.product_id] += item.quantity

        # 5. Aggregate reserved quantities by product.
        reserved_quantities = defaultdict(int)

        for reservation in reservations:
            reserved_quantities[reservation.product_id] += (
                reservation.quantity
            )

        # 6. Validate that reservations cover all order items.
        for product_id, ordered_quantity in ordered_quantities.items():
            if reserved_quantities[product_id] != ordered_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Reservations do not match ordered quantity "
                        f"for product {product_id}"
                    ),
                )

        # Continue with balance locking and fulfillment updates here.

    except Exception:
        await session.rollback()
        raise