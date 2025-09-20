from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import JWTBearer
from app.common.pagination import PaginatedResponse
from app.config.database import get_db_instance
from app.services.cycle_configurations.constants import ValidationState, PaymentMode
from app.services.permissions.middleware.middleware import verify_permission_factory
from app.services.withdrawals.handlers import request_withdrawal, reject_withdrawal, process_withdrawal, \
    validate_withdrawal, list_withdrawals, confirm_withdrawal, return_ticket_to_initiator
from app.services.withdrawals.schemas import WithdrawalRequestSchema, \
    WithdrawalPaymentSchema, RejectWithdrawalSchema, WithdrawalOutSchema, ConfirmWithdrawal

router = APIRouter(prefix="/v1/api/withdrawals", tags=["Withdrawals"])


@router.post("/request", dependencies=[Depends(JWTBearer())])
async def submit_withdrawal(
        data: WithdrawalRequestSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await request_withdrawal(data, db, token)


@router.get("", response_model=PaginatedResponse[WithdrawalOutSchema], dependencies=[Depends(JWTBearer())])
async def list_withdrawal_route(
        request: Request,
        page: int = Query(1, ge=1),
        size: int = Query(10, gt=0, le=30),
        state: Optional[ValidationState] = Query(None),
        id: Optional[UUID] = Query(None),
        payment_mode: Optional[PaymentMode] = Query(None),
        db: AsyncSession = Depends(get_db_instance),
): return await list_withdrawals(db, page, size, str(request.url_for("list_withdrawal_route")), state, id, payment_mode)


@router.post("/reject/{ticket_id}", dependencies=[Depends(JWTBearer())])
async def reject_withdrawal_route(
        ticket_id: UUID,
        data: RejectWithdrawalSchema,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer())
): return await reject_withdrawal(ticket_id, data, db, token)


@router.post("/validate/{ticket_id}", dependencies=[Depends(JWTBearer())])
async def validate_withdrawal_route(
        ticket_id: UUID,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await validate_withdrawal(ticket_id, db, token)


@router.post("/process/{ticket_id}", dependencies=[Depends(JWTBearer())])
async def process_withdrawal_route(
        ticket_id: UUID,
        data: WithdrawalPaymentSchema = Depends(WithdrawalPaymentSchema.as_form),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
        autorize: bool = Depends(verify_permission_factory('DCS'))
): return await process_withdrawal(ticket_id, data, db, token)


@router.post("/confirm/{ticket_id}", dependencies=[Depends(JWTBearer())])
async def confirm_withdrawal_route(
        request: Request,
        ticket_id: UUID,
        data: ConfirmWithdrawal = Body(...),
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await confirm_withdrawal(ticket_id, data, db, token)


@router.get("/return_for_confirmation/{ticket_id}", dependencies=[Depends(JWTBearer())])
async def return_ticket_to_initiator_route(
        ticket_id: UUID,
        db: AsyncSession = Depends(get_db_instance),
        token: str = Depends(JWTBearer()),
): return await return_ticket_to_initiator(ticket_id, db, token)
