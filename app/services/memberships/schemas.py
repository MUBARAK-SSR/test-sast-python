from typing import Optional, List
from pydantic import BaseModel, EmailStr, UUID4, ConfigDict, Field
from datetime import date, datetime
from app.services.cycle_configurations.constants import ValidationOpinion, ValidationState


class JoinCycleRequestSchema(BaseModel):
    cycle_id: UUID4
    withdrawal_date: date
    # email: Optional[EmailStr] = None


class JoinCycleResponseSchema(JoinCycleRequestSchema):
    id: UUID4
    user_id: UUID4
    state: ValidationState
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ValidateJoinRequestSchema(BaseModel):
    opinion: ValidationOpinion
    reason: Optional[str] = None


class DirectJoinSchema(BaseModel):
    user_ids: List[UUID4]
    cycle_id: UUID4



class SanctionUsersSchema(BaseModel):
    cycle_id: UUID4
    penalty_id: UUID4
    user_ids: List[UUID4]
