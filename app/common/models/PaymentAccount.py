import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# from app.common.models.CyclePaymentAccount import cycle_payment_account
from app.config.database import Base
from app.common.models import User, Operator, Cycle, CyclePaymentAccount
from app.services.cycle_configurations.constants import PaymentAccountType


class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(Integer, nullable=False)
    merchant_code = Column(String, nullable=True, unique=True)
    bank_account_number = Column(String, nullable=True)
    mobile_number = Column(String, nullable=True)
    agency_number = Column(String, nullable=True)
    payment_counter = Column(String, nullable=True)
    key = Column(String, nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("operators.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id"), nullable=True)
    configured_by = Column(String, nullable=False)
    rib_file_name = Column(String, nullable=True)
    rib_file_url = Column(String, nullable=True)
    rib_file_temp_url = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    cycles = relationship("CyclePaymentAccount", back_populates="payment_account")
    user = relationship("User", back_populates="payment_accounts")
    operator = relationship("Operator", back_populates="payment_accounts")
    sub_client = relationship("SubClient", back_populates="payment_accounts")
    withdrawals = relationship("Withdrawal", back_populates="payment_account")

    # payment_references = relationship("PaymentReference", back_populates="payment_account")
    # credit_references = relationship("PaymentReference", foreign_keys=[PaymentReference.credit_account], back_populates="credit_payment_account")
    # debit_references = relationship("PaymentReference", foreign_keys=[PaymentReference.debit_account], back_populates="debit_payment_account")