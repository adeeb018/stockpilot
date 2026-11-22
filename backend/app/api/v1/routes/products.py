from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AuthContext,
    require_permission
)
from app.db.session import get_db

from app.schemas.products import (
    ProductCreate,
    ProductUpdate,
    ProductResponse
)

from app.services.product_service import ProductService


router = APIRouter(
    prefix="/products",
    tags=["products"]
)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreate,
    context: AuthContext = Depends(
        require_permission("product.create")
    ),
    db: AsyncSession = Depends(get_db)
):
    return await ProductService(db).create(
        context.organization.id,
        payload
    )


@router.get("")
async def list_products(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    is_active: bool | None = None,
    context: AuthContext = Depends(
        require_permission("product.read")
    ),
    db: AsyncSession = Depends(get_db)
):

    items, total = await ProductService(db).list(
        context.organization.id,
        limit,
        offset,
        search,
        is_active
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    context: AuthContext = Depends(
        require_permission("product.read")
    ),
    db: AsyncSession = Depends(get_db)
):
    return await ProductService(db).get(
        context.organization.id,
        product_id
    )


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    context: AuthContext = Depends(
        require_permission("product.update")
    ),
    db: AsyncSession = Depends(get_db)
):
    return await ProductService(db).update(
        context.organization.id,
        product_id,
        payload
    )