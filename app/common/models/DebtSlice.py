import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, Integer, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base


class DebtSlice(Base):
    __tablename__ = "debts_slice"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debts_id = Column(UUID(as_uuid=True), ForeignKey("debts.id"), nullable=False)
    refund_amount = Column(Float, nullable=False)
    refund_interest = Column(Float, nullable=False)
    total_refund_amount = Column(Float, nullable=False)
    tranche_number = Column(Integer, nullable=False)
    state = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    debt = relationship("Debt", back_populates="debt_slices")
