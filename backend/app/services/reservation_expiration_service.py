from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InventoryBalance, StockReservation
from app.models.inventory import ReservationStatus


async def expire_reservations(
    session: AsyncSession,
    batch_size: int = 100,
) -> int:
    """
    Expire a batch of active reservations whose expiry time has passed.

    Returns the number of reservations expired.
    """

    now = datetime.now(timezone.utc)

    try:
        # 1. Lock expired reservations.
        # SKIP LOCKED allows multiple workers to process different batches.
        result = await session.execute(
            select(StockReservation)
            .where(
                StockReservation.status == ReservationStatus.ACTIVE,
                StockReservation.expires_at <= now,
            )
            .order_by(
                StockReservation.expires_at,
                StockReservation.id,
            )
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        reservations = result.scalars().all()

        if not reservations:
            return 0

        # 2. Aggregate reserved quantities by inventory balance.
        quantities = defaultdict(int)

        for reservation in reservations:
            key = (
                reservation.organization_id,
                reservation.warehouse_id,
                reservation.product_id,
            )
            quantities[key] += reservation.quantity

        # 3. Lock balances in deterministic order.
        balances = {}

        for key in sorted(quantities, key=lambda item: tuple(map(str, item))):
            organization_id, warehouse_id, product_id = key

            result = await session.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.organization_id == organization_id,
                    InventoryBalance.warehouse_id == warehouse_id,
                    InventoryBalance.product_id == product_id,
                )
                .with_for_update()
            )

            balance = result.scalar_one_or_none()

            if balance is None:
                raise RuntimeError(
                    f"Inventory balance missing for reservation group: {key}"
                )

            if balance.quantity_reserved < quantities[key]:
                raise RuntimeError(
                    f"Reserved quantity inconsistency for inventory balance: {key}"
                )

            balances[key] = balance

        # 4. Release reserved quantities.
        for key, quantity in quantities.items():
            balances[key].quantity_reserved -= quantity

        # 5. Mark reservations as expired.
        for reservation in reservations:
            reservation.status = ReservationStatus.EXPIRED

        # 6. Commit everything atomically.
        await session.commit()

        return len(reservations)

    except Exception:
        await session.rollback()
        raise