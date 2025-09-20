from typing import Optional

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, UUID4, Field, model_validator, ConfigDict
from datetime import date, datetime

from sqlalchemy import UUID
from starlette import status

from app.services.cycle_configurations.constants import PaymentMode, ValidationState


class WithdrawalRequestSchema(BaseModel):
    cycle_id: UUID4
    amount_claimed: float = Field(..., gt=0)
    desired_payment_account: UUID4
    desired_payment_mode: int
    withdrawal_request_date: date


class WithdrawalPaymentSchema(BaseModel):
    payment_mode: PaymentMode
    cycle_id: UUID4
    operator_id: UUID4
    amount_withdraw: float = Field(..., gt=0)
    financial_reference: Optional[str] = None
    credit_account: Optional[UUID4] = None
    debit_account: Optional[UUID4] = None
    attachment: Optional[UploadFile] = None
    payment_date: Optional[date] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields(self):
        payment_mode = self.payment_mode
        financial_reference = self.financial_reference
        credit_account = self.credit_account
        debit_account = self.debit_account
        attachment = self.attachment
        payment_date = self.payment_date

        if payment_mode == PaymentMode.auto and payment_date is not None:
            raise HTTPException(422, "payment_date must not be provided when payment_mode is automatic.")
        if (payment_mode == PaymentMode.manual or payment_mode == PaymentMode.cash) and payment_date is None:
            raise HTTPException(422, "payment_date is required when payment_mode is manual or cash.")
        if payment_date > date.today():
            raise HTTPException(422, "payment_date must be less than or equal to today .")
        if payment_mode == PaymentMode.cash and attachment is not None:
            raise HTTPException(422,"attachment must not be provided when payment_mode is cash.")
        if (payment_mode == PaymentMode.manual or payment_mode == PaymentMode.auto) and (
                financial_reference is None or credit_account is None or debit_account is None):
            raise HTTPException(422, 
                "financial_reference, credit_account and debit_account are required when payment_mode is manual or automatic.")
        if payment_mode == PaymentMode.cash and (
                financial_reference is not None or credit_account is not None or debit_account is not None):
            raise HTTPException(422, 
                "Niether financial_reference nor credit_account nor debit_account must not be provided when payment_mode is cash.")
        return self

    @classmethod
    def as_form(
            cls,
            payment_mode: str = Form(...),
            cycle_id: str = Form(...),
            operator_id: str = Form(...),
            amount_withdraw: float = Form(...),
            financial_reference: Optional[str] = Form(None),
            credit_account: Optional[str] = Form(None),
            debit_account: Optional[str] = Form(None),
            attachment: Optional[UploadFile] = File(None),
            payment_date: Optional[date] = Form(None),
            reason: Optional[str] = Form(None)

    ):
        """
        Class method to convert form parameters to a ContributionPaymentSchema instance.
        """
        try:
            return cls(
                payment_mode=payment_mode,
                cycle_id=cycle_id,
                operator_id=operator_id,
                amount_withdraw=amount_withdraw,
                financial_reference=financial_reference,
                credit_account=credit_account,
                debit_account=debit_account,
                attachment=attachment,
                payment_date=payment_date,
                reason = reason
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,f"Validation error: {e}")


class RejectWithdrawalSchema(BaseModel):
    reason: Optional[str] = None


class ConfirmWithdrawal(BaseModel):
    status: bool
    financial_reference: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_financial_reference(self):
        status = self.status
        amount = self.amount
        financial_reference = self.financial_reference

        if status is True and amount is None:
            raise HTTPException(422, "amount is required when status is True.")
        if status is False and (financial_reference is not None or amount is not None):
            raise HTTPException(422, "financial_reference and amount must not be provided when status is False.")
        return self

class WithdrawalOutSchema(BaseModel):
    id: UUID4
    initiator_id: UUID4
    cycle_id: UUID4
    amount_claimed: float = Field(..., gt=0)
    amount_withdraw: Optional[float] = Field(default=None, gt=0)
    desired_payment_account: UUID4
    payment_account_id: Optional[UUID4] = None
    desired_payment_mode: PaymentMode
    payment_mode: Optional[PaymentMode] = None
    withdrawal_request_date: Optional[date] = None
    payment_date: Optional[date] = None
    state: ValidationState
    open_at: datetime
    model_config = ConfigDict(from_attributes=True)
