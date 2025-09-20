import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, Integer, ForeignKey, String, TIMESTAMP, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Cycle

class LoanConfig(Base):
    __tablename__ = "loan_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    duration_in_day = Column(Integer, nullable=False)
    interest_percentage = Column(Float, nullable=False)
    is_paid_once = Column(Boolean, nullable=True)
    payment_tranche = Column(Integer, nullable=True)
    configured_by = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    cycle = relationship("Cycle", back_populates="loan_configs")

    # __table_args__ = (UniqueConstraint('duration_in_day', 'interest_percentage', 'payment_tranche', name='loan_configs_duration_interest_tranche_key'),)
