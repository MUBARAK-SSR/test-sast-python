import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, TIMESTAMP, Integer, String, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import User, Operator, Cycle, PaymentReference, Ticket
from app.services.cycle_configurations.constants import ValidationState


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # to_financial_account = Column(Boolean, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=False)
    payment_mode = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    state = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=True)
    attachment_file_name = Column(String, nullable=True)
    attachment_file_url = Column(String, nullable=True)
    attachment_file_temp_url = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    operator = relationship("Operator", back_populates="contributions")
    cycle = relationship("Cycle", back_populates="contributions")
    user = relationship("User", back_populates="contributions")
    ticket = relationship("Ticket", back_populates="contribution")

    # payment_reference = relationship("PaymentReference", back_populates="contribution",  uselist=False, cascade="all, delete-orphan")
