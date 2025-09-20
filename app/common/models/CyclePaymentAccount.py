import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


# cycle_payment_account = Table(
#     'cycle_payment_account',
#     Base.metadata,
#
#     Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
#     Column('cycle_id', UUID(as_uuid=True), ForeignKey('cycles.id'), nullable=False),
#     Column('payment_account_id', UUID(as_uuid=True), ForeignKey('payment_accounts.id'), nullable=False),
#     Column('created_at', TIMESTAMP(timezone=True), default=datetime.now(timezone.utc)),
#     Column('updated_at', TIMESTAMP(timezone=True), nullable=True),
#     Column('deleted_at', TIMESTAMP(timezone=True), nullable=True),
# )


class CyclePaymentAccount(Base):
    __tablename__ = "cycle_payment_account"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_account_id = Column(ForeignKey("payment_accounts.id"), nullable=False)
    cycle_id = Column(ForeignKey("cycles.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    cycle = relationship("Cycle", back_populates="payment_accounts")
    payment_account = relationship("PaymentAccount", back_populates="cycles")
