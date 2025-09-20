import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, TIMESTAMP, UniqueConstraint, Integer, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Debt, PenaltyCategory, Cycle
from app.services.cycle_configurations.constants import PenalityFlag, PriorityEnum


class PenaltySanctionConfig(Base):
    __tablename__ = "penalty_sanction_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    name = Column(String, nullable=False, unique=True)
    percentage_levy = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("penalty_categories.id"), nullable=True)
    flag = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=False)
    configured_by = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    debts = relationship("Debt", back_populates="penalty")
    penalty_category = relationship("PenaltyCategory", back_populates="penalties")
    cycle = relationship("Cycle", back_populates="penalties")

    __table_args__ = (UniqueConstraint('flag', 'cycle_id', name='penalties_flag_cycle_id_key'),)

