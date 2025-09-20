import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, Date, String, TIMESTAMP, Integer, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Cycle, Debt, Ticket, Guarantee, User
from app.services.cycle_configurations.constants import PaymentMode


class LoanRequest(Base):
    __tablename__ = "loan_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guarantor_id = Column(JSONB, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    guarantee_id = Column(UUID(as_uuid=True), ForeignKey("guarantees.id"), nullable=True)
    desired_operator_id = Column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=True)
    amount_claimed = Column(Float, nullable=False)
    desired_payment_method = Column(UUID(as_uuid=True))
    loan_config_id = Column(UUID(as_uuid=True), nullable=False)
    loan_duration_day = Column(Integer, nullable=False)
    interest_percentage = Column(Float, nullable=False)
    guarantor_opinion = Column(Boolean, nullable=True)
    refund_at_end_of_cycle = Column(Boolean, nullable=True)
    cut_interest_before = Column(Boolean, nullable=False)
    payment_tranche = Column(Integer, nullable=True)
    file_names = Column(JSONB, nullable=True)
    file_urls = Column(JSONB, nullable=True)
    file_temp_urls = Column(JSONB, nullable=True)
    state = Column(Integer, nullable=True)
    state_refund = Column(Boolean, nullable=False, default=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)


    cycle = relationship("Cycle", back_populates="loan_requests")
    debts = relationship("Debt", back_populates="loan_request")
    ticket = relationship("Ticket", back_populates="loan_request")
    guarantee = relationship("Guarantee", back_populates="loan_requests")
    user = relationship("User", back_populates="loan_requests", foreign_keys=[user_id])
    #guarantor = relationship("User", back_populates="guarantor_loan_requests", foreign_keys=[guarantor_id])