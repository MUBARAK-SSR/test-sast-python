from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class RefundCreate(BaseModel):
    cycle_id: UUID
    debt_id: UUID
    subscriber_id: UUID
    amount_refunded: float
    amount_left: float
    is_delayed: Optional[bool] = False
    status: Optional[str]
