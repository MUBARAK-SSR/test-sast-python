from datetime import datetime, time, date

from fastapi import HTTPException
from pydantic import BaseModel, UUID4, Field, ConfigDict, model_validator
from typing import Optional, List, Dict
from app.services.cycle_configurations.constants import FrequencyCycle, FrequencyWeek, WeekDay, Currency, ValidatorFlag, \
    PenalityFlag, PriorityEnum, CycleState


class EnumItem(BaseModel):
    name: str
    value: int
    description: str


class CycleBase(BaseModel):
    name: str
    description: str
    start_date: date
    end_date: date
    start_time: time
    end_time: time
    day_number: Optional[int] = None
    frequency_cycle: FrequencyCycle
    frequency_week: Optional[FrequencyWeek] = None
    week_day: Optional[WeekDay] = None
    currency: Currency
    configured_by: Optional[str] = None


class CycleCreateBase(CycleBase):
    activity_id: UUID4
    sub_client_id: UUID4


class CycleCreateSchema(CycleCreateBase):
    payment_account_ids: List[UUID4]

    @model_validator(mode="after")
    def validate_frequency_fields(self):
        frequency_cycle = self.frequency_cycle
        day_number = self.day_number
        frequency_week = self.frequency_week
        week_day = self.week_day

        if frequency_cycle == FrequencyCycle.monthly:
            # Case 1: day_number is provided alone
            if day_number is not None and (frequency_week is not None or week_day is not None):
                raise HTTPException(422,
                    "When frequency_cycle is 'monthly' and day_number is provided, "
                    "frequency_week and week_day must not be provided."
                )
            # Case 2: frequency_week and week_day are provided together
            if (frequency_week is not None) != (week_day is not None):
                raise HTTPException(422,
                    "When frequency_cycle is 'monthly', frequency_week and week_day "
                    "must both be provided or both be absent."
                )
            # Case 3: At least one of day_number or (frequency_week, week_day) must be provided
            if day_number is None and frequency_week is None and week_day is None:
                raise HTTPException(422,
                    "When frequency_cycle is 'monthly', either day_number or both "
                    "frequency_week and week_day must be provided."
                )
        elif frequency_cycle == FrequencyCycle.weekly:
            # For weekly, only week_day is required; frequency_week and day_number must be absent
            if week_day is None:
                raise HTTPException(422, "When frequency_cycle is 'weekly', week_day must be provided.")
            if frequency_week is not None:
                raise HTTPException(422, "When frequency_cycle is 'weekly', frequency_week must not be provided.")
            if day_number is not None:
                raise HTTPException(422, "When frequency_cycle is 'weekly', day_number must not be provided.")

        if day_number is not None:
            if not (1 <= day_number <= 31):
                raise HTTPException(422, "day_number must be between 1 and 31.")

        if self.start_date >= self.end_date:
            raise HTTPException(422, "start_date must be less than end_date.")

        if self.start_time >= self.end_time:
            raise HTTPException(422, "start_time must be less than end_time.")

        return self

    class Config:
        json_encoders = {date: lambda v: v.isoformat(), time: lambda v: v.isoformat(), }


class CycleResponseSchema(CycleBase):
    id: UUID4
    sub_client_activity_id: UUID4
    state: CycleState
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CycleConfigCreateSchema(BaseModel):
    cycle_id: UUID4
    minimum_contribution_amount: float = Field(..., gt=0)
    maximum_loan: float = Field(..., gt=0)
    contribution_mandatory: Optional[bool] = None
    can_user_provide_withdrawal_date: bool
    withdrawal_dates: Optional[List[date]] = None

    @model_validator(mode="after")
    def validate_withdrawal_dates(self):
        can_user_provide_withdrawal_date = self.can_user_provide_withdrawal_date
        withdrawal_dates = self.withdrawal_dates

        # Validation: withdrawal_dates required when can_user_provide_withdrawal_date is False
        if can_user_provide_withdrawal_date is False and withdrawal_dates is None:
            raise HTTPException(422, "withdrawal_dates is required when can_user_provide_withdrawal_date is False.")
        # Validation: withdrawal_dates must not be provided when can_user_provide_withdrawal_date is True
        if can_user_provide_withdrawal_date is True and withdrawal_dates is not None:
            raise HTTPException(422, "withdrawal_dates must not be provided when can_user_provide_withdrawal_date is True.")

        # Extra validation: all withdrawal_dates must be greater than today
        if withdrawal_dates:
            today = date.today()
            for d in withdrawal_dates:
                if d < today:
                    raise HTTPException(422, f"withdrawal_dates must be greater than or equal to today. Invalid value: {d}")

        return self


class CycleConfigResponseSchema(CycleConfigCreateSchema):
    id: UUID4
    is_active: bool
    configured_by: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleCreateSchema(BaseModel):
    sub_client_id: Optional[UUID4]
    name: str
    level: int


class RoleResponseSchema(RoleCreateSchema):
    id: UUID4
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CreateOfficeSchema(BaseModel):
    cycle_id: UUID4
    role_ids: List[UUID4]
    user_id: UUID4


class OfficeResponseSchema(BaseModel):
    id: UUID4
    user_cycle_id: UUID4
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ValidatorConfigCreateSchema(BaseModel):
    cycle_id: UUID4
    operation_name: str
    validators_id: Dict[int, UUID4]
    flag: ValidatorFlag


class ValidatorConfigResponseSchema(ValidatorConfigCreateSchema):
    id: UUID4
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PenaltyCategoryCreateSchema(BaseModel):
    cycle_id: UUID4
    title: str
    description: Optional[str] = None
    default: bool


class PenaltyCategoryResponseSchema(PenaltyCategoryCreateSchema):
    id: UUID4
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PenaltySanctionConfigCreateBase(BaseModel):
    cycle_id: UUID4
    name: str
    percentage_levy: Optional[float] = Field(None, gt=0)
    value: Optional[float] = Field(None, gt=0)
    category_id: Optional[UUID4] = None
    priority: PriorityEnum

    @model_validator(mode="after")
    def validate_percentage_levy_and_value(self):
        percentage_levy = self.percentage_levy
        value = self.value

        # Ensure exactly one of percentage_levy or value is provided
        if percentage_levy is not None and value is not None:
            raise HTTPException(422, "Only one of percentage_levy or value can be provided, not both.")
        if percentage_levy is None and value is None:
            raise HTTPException(422, "One of percentage_levy or value must be provided.")

        return self


class PenaltySanctionConfigCreateSchema(PenaltySanctionConfigCreateBase):
    flag: PenalityFlag


class PenaltySanctionConfigUpdateSchema(BaseModel):
    cycle_id: UUID4
    flag: PenalityFlag
    percentage_levy: Optional[float] = Field(None, gt=0)
    value: Optional[float] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_percentage_levy_and_value(self):
        percentage_levy = self.percentage_levy
        value = self.value

        # Ensure exactly one of percentage_levy or value is provided
        if percentage_levy is not None and value is not None:
            raise HTTPException(422, "Only one of percentage_levy or value can be provided, not both.")
        if percentage_levy is None and value is None:
            raise HTTPException(422, "One of percentage_levy or value must be provided.")

        return self


class PenaltySanctionConfigResponseSchema(PenaltySanctionConfigCreateBase):
    id: UUID4
    flag: Optional[PenalityFlag] = None
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LoanConfigCreateSchema(BaseModel):
    cycle_id: UUID4
    duration_in_day: int = Field(..., gt=0)
    interest_percentage: float = Field(..., ge=0)
    # is_paid_once: Optional[bool] = None
    payment_tranche: Optional[int] = Field(None, gt=0)

    # @model_validator(mode="after")
    # def validate_refund_and_tranche(self):
    #     refund_at_end = self.is_paid_once
    #     payment_tranche = self.payment_tranche
    #
    #     # Validation: payment_tranche required when is_paid_once is False
    #     if is_paid_once is False and payment_tranche is None:
    #         raise HTTPException(422, "payment_tranche is required when is_paid_once is False.")
    #     # Validation: payment_tranche must not be provided when is_paid_once is True
    #     if is_paid_once is True and payment_tranche is not None:
    #         raise HTTPException(422, "payment_tranche must not be provided when is_paid_once is True.")
    #
    #     return self


class LoanConfigResponseSchema(LoanConfigCreateSchema):
    id: UUID4
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GuaranteeCreateSchema(BaseModel):
    cycle_id: UUID4
    name: str = Field(..., min_length=2)
    description: Optional[str] = None


class GuaranteeResponseSchema(GuaranteeCreateSchema):
    id: UUID4
    configured_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)





