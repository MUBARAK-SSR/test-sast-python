import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, String, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import FinancialAccount


class AccountMovement(Base):
    __tablename__ = "account_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    financial_account_id = Column(UUID(as_uuid=True), ForeignKey("financial_accounts.id"), nullable=False)
    source_table = Column(Integer, nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    old_balance = Column(Float, nullable=True)
    new_balance = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    debt_amount = Column(Float, nullable=True)
    #new_debt_amount = Column(Float, nullable=True)
    amount_to_endorse = Column(Float, nullable=True)
    #new_amount_to_endorse = Column(Float, nullable=True)
    amount_loaned_by_cycle = Column(Float, nullable=True)
    #new_amount_loaned_by_cycle = Column(Float, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    financial_account = relationship("FinancialAccount", back_populates="account_movements")
