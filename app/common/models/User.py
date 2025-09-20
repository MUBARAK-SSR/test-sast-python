import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Column, BigInteger, Integer, String, DateTime, func ,UniqueConstraint, CheckConstraint


# from app.common.models.SubClientUser import sub_client_user
# from app.common.models.UserCycle import user_cycle
from app.config.database import Base
from app.common.models import Contribution, Withdrawal, FinancialAccount, PaymentAccount, RequestToJoin, LoanRequest, SubClientUser, UserCycle


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.common_id"), nullable=False)
    # member_niu = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    phone_number = Column(String, nullable=False, unique=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    '''
        champs et relations ajoutées
    '''
    name = Column(String, nullable=False)
    phone = Column(Integer, nullable=True)
    login = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    birth_date = Column(String, nullable=True)
    phone_number_code = Column(String, nullable=True)
    gender = Column(String, nullable=True)

    #customer_users = relationship('SubClientUser', back_populates = 'user')
    '''
        end
    '''

    cycles = relationship("UserCycle", back_populates="user")
    sub_clients = relationship("SubClientUser", back_populates="user")
    # office_roles = relationship("OfficeRole", back_populates="user")
    contributions = relationship("Contribution", back_populates="user")
    refunds = relationship("Refund", back_populates="user")
    withdrawals = relationship("Withdrawal", back_populates="user")
    financial_account = relationship("FinancialAccount", back_populates="user")
    payment_accounts = relationship("PaymentAccount", back_populates="user")
    request_to_joins = relationship("RequestToJoin", back_populates="user")
    loan_requests = relationship("LoanRequest", back_populates="user", foreign_keys="[LoanRequest.user_id]")
    # guarantor_loan_requests = relationship("LoanRequest", back_populates="guarantor", foreign_keys="[LoanRequest.guarantor_id]")




