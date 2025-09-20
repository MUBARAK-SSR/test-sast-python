from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.auth import JWTBearer
from app.common.pagination import PaginatedResponse
from app.config.database import get_db_instance
from app.services.cycle_configurations.constants import ValidationState
from app.services.memberships.handlers import request_to_join, validate_join_request, list_request_to_joins, direct_join
from app.services.memberships.schemas import JoinCycleRequestSchema, JoinCycleResponseSchema, ValidateJoinRequestSchema, \
    DirectJoinSchema

router = APIRouter(prefix="/v1/api/memberships", tags=["Memberships"])


@router.post("/join", response_model=JoinCycleResponseSchema, dependencies=[Depends(JWTBearer())])
async def join_cycle_route(
        payload: JoinCycleRequestSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await request_to_join(payload, db, token)


@router.get("/join", response_model=PaginatedResponse[JoinCycleResponseSchema])
async def list_request_to_joins_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        state: ValidationState = Query(None),
        id: Optional[UUID] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_request_to_joins(db, page, size, str(request.url_for("list_request_to_joins_route")), state, id)


@router.post("/{ticket_id}/validation", dependencies=[Depends(JWTBearer())])
async def validate_join(
        ticket_id: UUID,
        payload: ValidateJoinRequestSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await validate_join_request(ticket_id, payload, db, token)


@router.post("/direct_join", dependencies=[Depends(JWTBearer())])
async def direct_join_route(
        payload: DirectJoinSchema,
        db: AsyncSession = Depends(get_db_instance),
): return await direct_join(payload, db)