import uuid
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import Column, String, TIMESTAMP, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.common.uuid_json_model import UUIDJsonModel
from app.config.database import Base
from app.services.cycle_configurations.constants import ValidationState, ValidationOpinion


class TicketLog(Base, UUIDJsonModel):
    __tablename__ = "ticket_logs"

    id = Column(Integer, autoincrement=True, primary_key=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    opinion = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    infos = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    ticket = relationship("Ticket", back_populates="logs")

