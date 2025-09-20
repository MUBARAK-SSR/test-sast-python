from datetime import datetime

from psycopg2.extensions import JSONB
from pydantic import BaseModel, Field, UUID4, model_validator
from uuid import UUID
from typing import Optional, List, Self


from app.services.cycle_configurations.constants import ValidationOpinion, PaymentMode, PaymentType, ValidationState


class TicketResponseModel(BaseModel):
    id: UUID
    User_id: UUID
    state: str
    updated_at: datetime
class LoanSimulationRequest(BaseModel):
    loan_config_id: UUID
    cycle_id: UUID
    amount_claimed: float
    include_cycle_end_date: Optional[bool] = False

class DeadlineDetail(BaseModel):
    refund_deadline: str
    capital: float
    interest: float
    total: float

class LoanSimulationResponse(BaseModel):
    total_amount_to_refund: float
    deadlines: List[DeadlineDetail]

class GuaranteeSchema(BaseModel):
    guarantor_id: UUID
    guarantee_id: Optional[UUID] = None
    guarantee_file_names: Optional[List[str]] = None
    guarantee_file_urls: Optional[List[str]] = None
    guarantee_file_temp_urls: Optional[List[str]] = None

class LoanRequestCreate(BaseModel):
    cycle_id: UUID
    loan_config_id: UUID
    amount_claimed: float
    desired_payment_method: Optional[UUID] = None
    loan_duration_day: int
    guarantee: GuaranteeSchema
    include_cycle_end_date: Optional[bool] = False
    cut_interest_before: bool

class LoanRequestResponse(BaseModel):
    message: str
    status: int
    #data: TicketResponseModel
class LoanDisbursementResponse(BaseModel):
    message: str
    status: int
    total_to_refund: float


class ReceiptPaymentResponse(BaseModel):
    message: str
    status: int

class LoanRequestOut(BaseModel):
    id: UUID
    user_id: UUID
    cycle_id: UUID
    amount_claimed: float
    loan_duration_day: int
    interest_percentage: float
    state: ValidationState
    created_at: datetime
    #
    # class Config:
    #     orm_mode = True
class PaginatedLoanRequests(BaseModel):
    message: str
    status: int
    items: List[LoanRequestOut]
class ListLoanSchema(BaseModel):
    state: Optional[ValidationState] = None
    user_id: Optional[UUID] = None
    loan_request_id: Optional[UUID] = None
    refunded: Optional[bool] = None
    sort_by: Optional[str] = "created_at",
    limit: int = 10
    offset: int = 0
    order: str = "desc"

class DebtCreate(BaseModel):
    cycle_id: UUID
    loan_request_id: UUID
    subscriber_id: UUID
    refund_amount: float
    refund_interest: float
    total_refund_amount: float
    penalty_id: Optional[bool] = False
    tranche_number: Optional[str]
    state: Optional[bool] = False

class RejectLoanRequestSchema(BaseModel):
    cycle_id: UUID
    reason: str

class ValidationGuarantorSchema(BaseModel):
    cycle_id: UUID
    opinion: ValidationOpinion
    reason: Optional[str] = None

class ReceiptPaymentRequest(BaseModel):
    payment_received: bool



class LoanDisbursementRequest(BaseModel):
    cycle_id: UUID
    operator_id: UUID
    #amount_given: float
    reason: Optional[str] = None
    financial_reference: Optional[str] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    attachment_url: Optional[str] = None
    payment_method_code: PaymentType
    payment_mode_code: PaymentMode

class LoanAutorisationRequest(BaseModel):
    cycle_id: UUID
    reason: Optional[str] = None
    opinion: ValidationOpinion

# class LoanDisbursementRequest(BaseModel):
#     cycle_id: UUID
#     reason: Optional[str] = None
#     opinion: ValidationOpinion


    @model_validator(mode='after')
    def validate_payment_details(self) -> Self:
        if self.payment_mode_code == PaymentMode.manual:
            if not self.financial_reference:
                raise ValueError("Une référence financière est requise pour le mode paiement MANUEL.")
            if not self.debit_account or not self.credit_account:
                raise ValueError("Des comptes de débit et de crédit sont requis pour le mode  paiement MANUEL.")
        return self
