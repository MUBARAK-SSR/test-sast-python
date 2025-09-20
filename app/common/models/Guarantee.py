import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, Integer, String, TIMESTAMP, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import LoanRequest, Cycle


class Guarantee(Base):
    __tablename__ = "guarantees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    configured_by = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    loan_requests = relationship("LoanRequest", back_populates="guarantee")
    cycle = relationship("Cycle", back_populates="guarantees")

    __table_args__ = (UniqueConstraint('name', 'cycle_id', name='guarantees_name_cycle_id_key'),)

