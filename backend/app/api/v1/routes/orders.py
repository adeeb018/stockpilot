from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_context
from app.db.session import get_db
from app.schemas.order import OrderFulfillmentResponse
from app.services.order_fulfillment_service import fulfill_order
from app.api.dependencies import require_permission

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/{order_id}/fulfill",
    response_model=OrderFulfillmentResponse,
)
async def fulfill_order_endpoint(
    order_id: UUID,
    context=Depends(require_permission("order.fulfill")),
    session: AsyncSession = Depends(get_db),
):
    order = await fulfill_order(
        session=session,
        organization_id=context.organization.id,
        order_id=order_id,
        user_id=context.user.id,
    )

    return order