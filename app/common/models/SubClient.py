import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# from app.common.models.SubClientUser import sub_client_user
# from app.common.models.UserCycle import user_cycle
from app.config.database import Base
from app.common.models import Contribution, Withdrawal, FinancialAccount, PaymentAccount, RequestToJoin, LoanRequest, SubClientActivity, SubClientUser, Role
from sqlalchemy import ForeignKey, Column, BigInteger, Integer, String, DateTime, func ,UniqueConstraint, CheckConstraint


class SubClient(Base):
    __tablename__ = "sub_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    common_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, unique=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    slug = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    subscription_tier = Column(String, nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    #relation pour recuperer l'ensemble des utilisateurs d'un client
    customer_users = relationship('SubClientUser', back_populates = 'customer')

    users = relationship("SubClientUser", back_populates="sub_client")
    activities = relationship("SubClientActivity", back_populates="sub_client")
    client = relationship("Client", back_populates="sub_clients")
    payment_accounts = relationship("PaymentAccount", back_populates="sub_client")
    roles = relationship("Role", back_populates="sub_client")
    # cycles = relationship("Cycle", back_populates="sub_client")





