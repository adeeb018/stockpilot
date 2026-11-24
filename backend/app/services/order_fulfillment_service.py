# app/services/order_fulfillment_service.py

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InventoryBalance,
    InventoryMovement,
    Order,
    OrderItem,
    StockReservation,
)
from app.models.inventory import MovementType, ReservationStatus


async def fulfill_order(
    session: AsyncSession,
    organization_id: UUID,
    order_id: UUID,
    user_id: UUID,
) -> Order:
    """
    Fully fulfill a confirmed order.

    All inventory, reservation, movement, and order updates
    are committed in one transaction.
    """

    now = datetime.now(timezone.utc)

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

        # 3. Lock active reservations for this order.
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

        # 4. Aggregate order quantities by product.
        ordered_quantities = defaultdict(int)

        for item in order_items:
            ordered_quantities[item.product_id] += item.quantity

        # 5. Aggregate reservation quantities by product.
        reserved_quantities = defaultdict(int)

        for reservation in reservations:
            # Do not fulfill reservations whose expiry has passed,
            # even if the expiration worker has not processed them yet.
            if (
                reservation.expires_at is not None
                and reservation.expires_at <= now
            ):
                raise HTTPException(
                    status_code=409,
                    detail="One or more reservations have expired",
                )

            reserved_quantities[reservation.product_id] += (
                reservation.quantity
            )

        # 6. Ensure reservations exactly cover the order.
        all_product_ids = (
            set(ordered_quantities) | set(reserved_quantities)
        )

        for product_id in all_product_ids:
            if ordered_quantities[product_id] != reserved_quantities[product_id]:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Reservation quantity does not match "
                        f"order quantity for product {product_id}"
                    ),
                )

        # 7. Aggregate reservations by inventory balance.
        # A product may be reserved from multiple warehouses.
        balance_quantities = defaultdict(int)

        for reservation in reservations:
            key = (
                reservation.organization_id,
                reservation.warehouse_id,
                reservation.product_id,
            )
            balance_quantities[key] += reservation.quantity

        # 8. Lock inventory balances in deterministic order.
        balances = {}

        for key in sorted(
            balance_quantities,
            key=lambda value: tuple(str(part) for part in value),
        ):
            org_id, warehouse_id, product_id = key

            result = await session.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.organization_id == org_id,
                    InventoryBalance.warehouse_id == warehouse_id,
                    InventoryBalance.product_id == product_id,
                )
                .with_for_update()
            )
            balance = result.scalar_one_or_none()

            if balance is None:
                raise HTTPException(
                    status_code=409,
                    detail="Inventory balance not found",
                )

            required_quantity = balance_quantities[key]

            if balance.quantity_reserved < required_quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient reserved inventory",
                )

            if balance.quantity_on_hand < required_quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient on-hand inventory",
                )

            balances[key] = balance

        # 9. Consume inventory and create movement records.
        for key, quantity in balance_quantities.items():
            balance = balances[key]

            balance.quantity_on_hand -= quantity
            balance.quantity_reserved -= quantity

            session.add(
                InventoryMovement(
                    organization_id=key[0],
                    warehouse_id=key[1],
                    product_id=key[2],
                    movement_type=MovementType.OUTBOUND,
                    quantity_delta=-quantity,
                    reference_type="ORDER",
                    reference_id=order.id,
                    created_by=user_id,
                )
            )

        # 10. Mark all reservations as fulfilled.
        for reservation in reservations:
            reservation.status = ReservationStatus.FULFILLED

        # 11. Update order status.
        order.status = "FULFILLED"

        # 12. Commit everything atomically.
        await session.commit()
        await session.refresh(order)

        return order

    except Exception:
        await session.rollback()
        raise