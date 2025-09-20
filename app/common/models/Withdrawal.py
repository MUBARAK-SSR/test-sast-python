import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Float, Date, String, TIMESTAMP, Integer, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Operator, Cycle, User, Ticket
from app.services.cycle_configurations.constants import ValidationState, PaymentMode


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # from_financial_account = Column(Boolean, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    desired_payment_account = Column(UUID(as_uuid=True), nullable=False)
    payment_account_id = Column(UUID(as_uuid=True), ForeignKey("payment_accounts.id"), nullable=True)
    desired_payment_mode = Column(Integer, nullable=False)
    payment_mode = Column(Integer, nullable=True)
    amount_claimed = Column(Float, nullable=False)
    amount_withdraw = Column(Float, nullable=True)
    penalty_amount = Column(Float, default=0.0)
    reason = Column(String, nullable=True)
    withdrawal_request_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    # confirmed = Column(Boolean,nullable=True)
    state = Column(Integer, nullable=False)
    attachment_file_name = Column(String, nullable=True)
    attachment_file_url = Column(String, nullable=True)
    attachment_file_temp_url = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    payment_account = relationship("PaymentAccount", back_populates="withdrawals")
    cycle = relationship("Cycle", back_populates="withdrawals")
    user = relationship("User", back_populates="withdrawals")
    ticket = relationship("Ticket", back_populates="withdrawal")

