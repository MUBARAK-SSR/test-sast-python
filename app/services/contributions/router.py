from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import JWTBearer
from app.common.pagination import PaginatedResponse
from app.config.database import get_db_instance
from app.services.contributions.handlers import process_contribution_payment, validate_contribution_payment, \
    list_contributions, reject_contribution_payment
from app.services.contributions.schemas import ContributionPaymentSchema, ValidateContributionPaymentSchema, \
    ContributionPaymentOutSchema
from app.services.cycle_configurations.constants import ValidationState, PaymentMode

router = APIRouter(prefix="/v1/api/contributions", tags=["Contributions"])


@router.post("/payment", dependencies=[Depends(JWTBearer())])
async def pay_contribution(
        data: ContributionPaymentSchema = Depends(ContributionPaymentSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await process_contribution_payment(data, db, token)


@router.get("", response_model=PaginatedResponse[ContributionPaymentOutSchema], dependencies=[Depends(JWTBearer())])
async def list_contribution_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        state: Optional[ValidationState] = Query(None),
        id: Optional[UUID] = Query(None),
        payment_mode: Optional[PaymentMode] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_contributions(db, page, size, str(request.url_for("list_contribution_route")), state, id, payment_mode)


@router.post("/{ticket_id}/payment-validation", dependencies=[Depends(JWTBearer())])
async def validate_payment(
    ticket_id: UUID,
    data: ValidateContributionPaymentSchema,
    db: AsyncSession = Depends(get_db_instance),
    token: str = Depends(JWTBearer())
): return await validate_contribution_payment(ticket_id, data, db, token)


@router.post("/{ticket_id}/payment-rejection", dependencies=[Depends(JWTBearer())])
async def reject_payment_route(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db_instance),
    token: str = Depends(JWTBearer())
): return await reject_contribution_payment(ticket_id, db, token)