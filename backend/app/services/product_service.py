from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category, Product
from app.schemas.products import ProductCreate, ProductUpdate


class ProductService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: UUID,
        data: ProductCreate
    ) -> Product:

        if data.category_id:
            result = await self.db.execute(
                select(Category.id).where(
                    Category.id == data.category_id,
                    Category.organization_id == organization_id
                )
            )

            if result.scalar_one_or_none() is None:
                raise HTTPException(404, "Category not found")

        product = Product(
            organization_id=organization_id,
            **data.model_dump()
        )

        self.db.add(product)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                409,
                "Product SKU already exists"
            )

        await self.db.refresh(product)

        return product

    async def get(
        self,
        organization_id: UUID,
        product_id: UUID
    ) -> Product:

        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.organization_id == organization_id
            )
        )

        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(404, "Product not found")

        return product

    async def list(
        self,
        organization_id: UUID,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        is_active: bool | None = None
    ):

        filters = [
            Product.organization_id == organization_id
        ]

        if search:
            term = f"%{search}%"

            filters.append(
                or_(
                    Product.name.ilike(term),
                    Product.sku.ilike(term)
                )
            )

        if is_active is not None:
            filters.append(
                Product.is_active.is_(is_active)
            )

        count_result = await self.db.execute(
            select(func.count())
            .select_from(Product)
            .where(*filters)
        )

        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Product)
            .where(*filters)
            .order_by(Product.created_at.desc(), Product.id)
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    async def update(
        self,
        organization_id: UUID,
        product_id: UUID,
        data: ProductUpdate
    ) -> Product:

        product = await self.get(
            organization_id,
            product_id
        )

        changes = data.model_dump(exclude_unset=True)

        for field, value in changes.items():
            setattr(product, field, value)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, "Product update conflict")

        await self.db.refresh(product)

        return product