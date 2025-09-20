import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Boolean, Enum, String, UniqueConstraint, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Cycle, Ticket, User
from app.services.cycle_configurations.constants import ValidationState


class RequestToJoin(Base):
    __tablename__ = "request_to_joins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    withdrawal_date = Column(Date, nullable=False)
    state = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="request_to_joins")
    cycle = relationship("Cycle", back_populates="request_to_joins")
    ticket = relationship("Ticket", back_populates="request_to_join")

    __table_args__ = (UniqueConstraint('user_id', 'cycle_id', name='request_to_joins_user_id_cycle_id_key'),)


