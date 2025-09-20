import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, UniqueConstraint, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import PenaltySanctionConfig, Cycle


class PenaltyCategory(Base):
    __tablename__ = "penalty_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    configured_by = Column(String, nullable=False)
    default = Column(Boolean, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    penalties = relationship("PenaltySanctionConfig", back_populates="penalty_category")
    cycle = relationship("Cycle", back_populates="penalty_categories")

    __table_args__ = (UniqueConstraint('title', 'cycle_id', name='penalty_categories_title_cycle_id_key'),)
