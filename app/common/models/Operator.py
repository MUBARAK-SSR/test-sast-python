import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Boolean, UniqueConstraint, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import TypeOperator, PaymentAccount, Contribution, Withdrawal, Refund, Debt, Cycle


class Operator(Base):
    __tablename__ = "operators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    common_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    has_api = Column(Boolean, nullable=False)
    country_code = Column(String, nullable=False)
    # type_operator_id = Column(UUID(as_uuid=True), ForeignKey("type_operators.common_id"), nullable=False)
    type_operator = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    # type_operator = relationship("TypeOperator", back_populates="operators")
    payment_accounts = relationship("PaymentAccount", back_populates="operator")
    contributions = relationship("Contribution", back_populates="operator")
    refunds = relationship("Refund", back_populates="operator")
    debts = relationship("Debt", back_populates="operator")
    # countries = relationship("Country", secondary=operator_country, back_populates="operators")



