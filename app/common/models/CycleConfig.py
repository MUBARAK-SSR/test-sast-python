import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, Integer, ForeignKey, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Cycle


class CycleConfig(Base):
    __tablename__ = "cycle_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    minimum_contribution_amount = Column(Float, nullable=False)
    maximum_loan = Column(Float, nullable=False)
    contribution_mandatory = Column(Boolean, nullable=True)
    configured_by = Column(String, nullable=False)
    can_user_provide_withdrawal_date = Column(Boolean, nullable=False)
    withdrawal_dates = Column(JSONB, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    cycle = relationship("Cycle", back_populates="cycle_config")
