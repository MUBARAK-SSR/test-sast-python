from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.services.loan_debts.schemas import (
    LoanSimulationRequest,
    LoanSimulationResponse,
    LoanRequestCreate,
    LoanRequestResponse, RejectLoanRequestSchema, LoanDisbursementRequest, LoanDisbursementResponse,
    ReceiptPaymentResponse, ReceiptPaymentRequest, PaginatedLoanRequests, ValidationGuarantorSchema,
    LoanAutorisationRequest, ListLoanSchema
)
from app.config.database import get_db_instance
from app.common.auth import JWTBearer

from app.services.loan_debts.handlers import simulate_loan, submit_loan_request, reject_loan_request, \
    disburse_loan_amount, validation_receipt_payment, get_loans_by_state, get_loans_by_user, get_debts_by_loan_request, \
    validation_guarantor_loan, authorize_loan_request

router = APIRouter(prefix="/v1/api/loan", tags=["Loans"])

@router.post("/simulation", response_model=LoanSimulationResponse,  dependencies=[Depends(JWTBearer())])
async def simulate_loan_endpoint(payload: LoanSimulationRequest, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
    return await simulate_loan(db, payload, token)


@router.post("/submit", response_model=LoanRequestResponse,  dependencies=[Depends(JWTBearer())])
async def submit_loan(payload: LoanRequestCreate, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
    return await submit_loan_request(db, payload, token)

@router.post("/{loan_id}/guarantor/opinion", response_model=LoanRequestResponse,  dependencies=[Depends(JWTBearer())])
async def validation_guarantor(loan_id: UUID, payload: ValidationGuarantorSchema, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
    return await validation_guarantor_loan(db, loan_id, payload, token)

@router.post("/{loan_id}/reject", response_model=LoanRequestResponse, dependencies=[Depends(JWTBearer())])
async def reject_loan(loan_id: UUID, data: RejectLoanRequestSchema, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
   return await reject_loan_request(db, loan_id, data, token)

@router.post("/{loan_id}/validation", response_model=LoanRequestResponse, dependencies=[Depends(JWTBearer())])
async def validation_loan(loan_id: UUID, payload: LoanAutorisationRequest, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
   return await authorize_loan_request(db, loan_id, payload, token)
@router.post("/{loan_id}/payment", dependencies=[Depends(JWTBearer())])
async def disburse_loan(loan_id: UUID, payload: LoanDisbursementRequest, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
    return await disburse_loan_amount(db, loan_id, payload, token)

@router.post("/{loan_id}/collection/validation", response_model=ReceiptPaymentResponse, dependencies=[Depends(JWTBearer())])
async def receipt_payment(loan_id: UUID, payload: ReceiptPaymentRequest, db: AsyncSession = Depends(get_db_instance), token: str = Depends(JWTBearer())):
    return await validation_receipt_payment(db, loan_id, payload, token)


@router.get("/loan-requests", response_model=PaginatedLoanRequests)
async def list_loan_requests(
    # state: Optional[str] = Query(
    #     None, description="Filtrer par état: encours | valide | rejete"
    # ),
    # limit: int = Query(10, ge=1, le=100, description="Nombre max de résultats"),
    # offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    # order: str = Query("desc", description="Ordre du tri par created_at: asc | desc"),

    # state, limit, offset, order
    payload: ListLoanSchema,
    db: AsyncSession = Depends(get_db_instance)
):
    return await get_loans_by_state(db, payload)


@router.get("/user/{user_id}", response_model=PaginatedLoanRequests)
async def list_loan_requests_by_user(
    # user_id: UUID,
    # state: Optional[str] = Query(
    #     None, description="Filtrer par état: encours | valide | rejete"
    # ),
    # limit: int = Query(10, ge=1, le=100, description="Nombre max de résultats"),
    # offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    # order: str = Query("desc", description="Ordre du tri par created_at: asc | desc"),
    payload: ListLoanSchema,
    db: AsyncSession = Depends(get_db_instance)
):
    return await get_loans_by_user(db, payload)


@router.get("/loan-request/{loan_request_id}", response_model=PaginatedLoanRequests)
async def list_debts_by_loan_request(
    # loan_request_id: UUID,
    # refunded: Optional[bool] = Query(None, description="Filtrer par remboursement (true/false)"),
    # skip: int = Query(0, ge=0, description="Nombre d'enregistrements à ignorer (offset)"),
    # limit: int = Query(10, ge=1, le=100, description="Nombre max de résultats par page"),
    # sort_by: str = Query("created_at", description="Champ de tri (ex: created_at, amount_given, tranche_number)"),
    # order: str = Query("desc", description="Ordre de tri (asc ou desc)"),
    payload: ListLoanSchema,
    db: AsyncSession = Depends(get_db_instance)
):
    return await get_debts_by_loan_request(db, payload)