import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, ForeignKey, TIMESTAMP, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.services.cycle_configurations.constants import FinancialAccountType, FinancialAccountType
from app.common.models import User, AccountMovement, Cycle


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    debt_amount = Column(Float, nullable=True, default=0.0)
    amount_to_endorse = Column(Float, nullable=True, default=0.0)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=True)
    amount_loaned_by_cycle = Column(Float, nullable=True, default=0.0)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="financial_account")
    cycle = relationship("Cycle", back_populates="financial_account")
    account_movements = relationship("AccountMovement", back_populates="financial_account")
