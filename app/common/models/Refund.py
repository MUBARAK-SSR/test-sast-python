import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Float, Boolean, TIMESTAMP, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Operator, Cycle, Debt, Ticket
from app.services.cycle_configurations.constants import PaymentMode


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    debt_id = Column(UUID(as_uuid=True), ForeignKey("debts.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=False)
    payment_mode = Column(Integer, nullable=False)
    amount_refunded = Column(Float, nullable=False)
    amount_left = Column(Float, nullable=False)
    is_delayed = Column(Boolean, default=False)
    state = Column(Boolean, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    operator = relationship("Operator", back_populates="refunds")
    cycle = relationship("Cycle", back_populates="refunds")
    debt = relationship("Debt", back_populates="refund")
    user = relationship("User", back_populates="refunds")
    ticket = relationship("Ticket", back_populates="refund")
