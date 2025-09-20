import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, Integer, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Operator, LoanRequest, PenaltySanctionConfig, DebtHistory, Refund


class Debt(Base):
    __tablename__ = "debts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_request_id = Column(UUID(as_uuid=True), ForeignKey("loan_requests.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=False)
    amount_given = Column(Float, nullable=False)
    refund_amount = Column(Float, nullable=False)
    refund_interest = Column(Float, nullable=False)
    total_refund_amount = Column(Float, nullable=False)
    penalty_id = Column(UUID(as_uuid=True), ForeignKey("penalty_sanction_configs.id"), nullable=True)
    tranche_number = Column(Integer, nullable=False)
    type = Column(Integer, nullable=False) #enum à créer pour catégoriser les types
    refund_preview_day = Column(TIMESTAMP(timezone=True), nullable=True)
    #refund_preview_day = Column(Date, nullable=True)
    date_he_repaid = Column(TIMESTAMP(timezone=True), nullable=True)
    state = Column(Boolean, default=False)


    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    operator = relationship("Operator", back_populates="debts")
    loan_request = relationship("LoanRequest", back_populates="debts")
    penalty = relationship("PenaltySanctionConfig", back_populates="debts")
    debt_histories = relationship("DebtHistory", back_populates="debt")
    debt_slices = relationship("DebtSlice", back_populates="debt")
    refund = relationship("Refund", back_populates="debt")
