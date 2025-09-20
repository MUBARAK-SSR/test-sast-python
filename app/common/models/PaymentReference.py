import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Contribution


class PaymentReference(Base):
    __tablename__ = "payment_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # contribution_id = Column(UUID(as_uuid=True), ForeignKey("contributions.id"), unique=True)
    source_table = Column(Integer, nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    financial_reference = Column(String, nullable=False, unique=True)
    credit_account = Column(UUID(as_uuid=True), ForeignKey("payment_accounts.id"), nullable=False)
    debit_account = Column(UUID(as_uuid=True), ForeignKey("payment_accounts.id"), nullable=False)
    state = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # contribution = relationship("Contribution", back_populates="payment_reference")
    # payment_account = relationship("PaymentAccount", back_populates="payment_references")
    # credit_payment_account = relationship("PaymentAccount", foreign_keys=[credit_account], back_populates="credit_references")
    # debit_payment_account = relationship("PaymentAccount", foreign_keys=[debit_account], back_populates="debit_references")