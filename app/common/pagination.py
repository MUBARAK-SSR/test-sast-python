from typing import TypeVar, Generic, Type, List, Optional, Callable, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T", bound=BaseModel)


class PaginationMeta(BaseModel):
    current_page: int
    last_page: int
    per_page: int
    from_: int
    to: int
    total: int
    first_page_url: str
    last_page_url: str
    prev_page_url: Optional[str]
    next_page_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


async def paginate(
        db: AsyncSession,
        query: Select,
        schema: Type[T],
        page: int,
        size: int,
        base_url: str,
        mapper: Optional[Callable[[Any], BaseModel]] = None,
) -> PaginatedResponse[T]:
    # Count total items
    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar_one()

    # Calculate pagination values
    offset = (page - 1) * size
    last_page = (total + size - 1) // size
    from_ = offset + 1 if total > 0 else 0
    to = min(offset + size, total)

    # Fetch paginated items
    result = await db.execute(query.offset(offset).limit(size))
    items = result.unique().scalars().all()

    # Convert to Pydantic
    if mapper:
        pydantic_items = [mapper(item) for item in items]
    else:
        pydantic_items = [schema.model_validate(item) for item in items]

    # Build meta
    meta = PaginationMeta(
        current_page=page,
        last_page=last_page,
        per_page=size,
        total=total,
        from_=from_,
        to=to,
        first_page_url=f"{base_url}?page=1&size={size}",
        last_page_url=f"{base_url}?page={last_page}&size={size}",
        prev_page_url=(f"{base_url}?page={page - 1}&size={size}" if page > 1 else None),
        next_page_url=(f"{base_url}?page={page + 1}&size={size}" if page < last_page else None),
    )

    return PaginatedResponse[T](
        data=pydantic_items,
        meta=meta,
    )
