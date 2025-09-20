from datetime import datetime
from uuid import UUID
from fastapi import Form, UploadFile, File, HTTPException
from pydantic import BaseModel, UUID4, Field, ConfigDict, EmailStr
from typing import List, Optional

from starlette import status

from app.services.cycle_configurations.constants import PaymentType, PaymentAccountType


class ClientSchema(BaseModel):
    common_id: UUID4
    name: str
    code: str


class SubClientCreateSchema(ClientSchema):
    client_id: UUID4


class ClientCreateSchema(ClientSchema):
    sub_clients: List[ClientSchema] = Field(default_factory=list)


class SubClientResponse(SubClientCreateSchema):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


class ClientResponseOut(ClientSchema):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


class ClientResponseSchema(ClientSchema):
    id: UUID4
    sub_clients: List[SubClientResponse]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientResponseSchemaOut(ClientSchema):
    id: UUID4
    sub_clients: List[SubClientResponse]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CreateUserSchema(BaseModel):
    name: str
    member_niu: str
    email: EmailStr
    phone_number: str = Field(..., min_length=9, max_length=9)


class CreateUserOutSchema(BaseModel):
    id: UUID4
    email: EmailStr
    phone_number: str = Field(..., min_length=9, max_length=9)
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TypeOperatorCreateSchema(BaseModel):
    common_id: UUID4
    name: str = Field(..., min_length=2)
    description: Optional[str] = None


class TypeOperatorResponseSchema(TypeOperatorCreateSchema):
    id: UUID4
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OperatorCreateSchema(BaseModel):
    common_id: UUID4
    type_operator: PaymentType
    country_code: str
    name: str
    description: Optional[str] = None
    has_api: bool


class OperatorResponseSchema(OperatorCreateSchema):
    id: UUID4
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class PaymentAccountBaseSchema(BaseModel):
    bank_account_number: Optional[str] = None
    mobile_number: Optional[str] = None
    agency_number: Optional[str] = None
    payment_counter: Optional[str] = None
    key: Optional[str] = None
    operator_id: UUID4
    rib: Optional[UploadFile] = None


class MerchantPaymentAccountSchema(BaseModel):
    mobile_number: str = None
    merchant_code: str
    operator_id: UUID4
    sub_client_id: UUID4


class SubClientPaymentAccountSchema(PaymentAccountBaseSchema):
    sub_client_id: UUID4

    @classmethod
    def as_form(
            cls,
            bank_account_number: Optional[str] = Form(None),
            mobile_number: Optional[str] = Form(None),
            agency_number: Optional[str] = Form(None),
            payment_counter: Optional[str] = Form(None),
            key: Optional[str] = Form(None),
            operator_id: str = Form(...),
            sub_client_id: str = Form(...),
            rib: Optional[UploadFile] = File(None)
    ):
        """
        Class method to convert form parameters to a PaymentAccountBaseSchema instance.
        """
        try:
            return cls(
                bank_account_number=bank_account_number,
                mobile_number=mobile_number,
                agency_number=agency_number,
                payment_counter=payment_counter,
                key=key,
                operator_id=UUID(operator_id),
                sub_client_id=UUID(sub_client_id),
                rib=rib,
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,f"Validation error: {e}")


class UserPaymentAccountSchema(PaymentAccountBaseSchema):
    user_id: UUID4

    @classmethod
    def as_form(
            cls,
            bank_account_number: Optional[str] = Form(None),
            mobile_number: Optional[str] = Form(None),
            agency_number: Optional[str] = Form(None),
            payment_counter: Optional[str] = Form(None),
            key: Optional[str] = Form(None),
            operator_id: str = Form(...),
            user_id: str = Form(...),
            rib: Optional[UploadFile] = File(None)
    ):
        """
        Class method to convert form parameters to a PaymentAccountBaseSchema instance.
        """
        try:
            return cls(
                bank_account_number=bank_account_number,
                mobile_number=mobile_number,
                agency_number=agency_number,
                payment_counter=payment_counter,
                key=key,
                operator_id=UUID(operator_id),
                user_id=UUID(user_id),
                rib=rib,
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,f"Validation error: {e}")


class PaymentAccountResponseSchema(PaymentAccountBaseSchema):
    id: UUID4
    account_type: PaymentAccountType
    user_id: Optional[UUID4]
    sub_client_id: Optional[UUID4]
    configured_by: str
    rib_file_name: Optional[str] = None
    rib_file_url: Optional[str] = None
    rib_file_temp_url: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ActivityOut(BaseModel):
    id: UUID4
    title: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class SubClientActivitiesSchema(BaseModel):
    activities_id: List[UUID]
