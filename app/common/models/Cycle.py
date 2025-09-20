import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, Boolean, Enum, Time, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# from app.common.models.CyclePaymentAccount import cycle_payment_account
from app.config.database import Base
from app.services.cycle_configurations.constants import FrequencyCycle, FrequencyWeek, WeekDay, Currency, CycleState
# from app.common.models.UserCycle import user_cycle
from app.common.models import Activity, Contribution, Withdrawal, RequestToJoin, ValidatorConfig, UserCycleRole, CycleConfig, LoanConfig, PenaltySanctionConfig, PaymentAccount, FinancialAccount, Refund, TypeOperator, Operator, PenaltyCategory, Guarantee, SubClientActivity, UserCycle, CyclePaymentAccount


class Cycle(Base):
    __tablename__ = "cycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_activity_id = Column(ForeignKey("sub_client_activity.id"), nullable=False)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    day_number = Column(Integer, nullable=True)
    frequency_cycle = Column(Enum(FrequencyCycle), nullable=False)
    frequency_week = Column(Enum(FrequencyWeek), nullable=True)
    week_day = Column(Enum(WeekDay), nullable=True)
    currency = Column(Enum(Currency), nullable=False)
    state = Column(Integer, nullable=False, default=CycleState.not_open)
    configured_by = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    sub_client_activity = relationship("SubClientActivity", back_populates="cycles")
    users = relationship("UserCycle", back_populates="cycle")
    payment_accounts = relationship("CyclePaymentAccount", back_populates="cycle")
    # office_roles = relationship("OfficeRole", back_populates="cycle")
    contributions = relationship("Contribution", back_populates="cycle")
    withdrawals = relationship("Withdrawal", back_populates="cycle")
    request_to_joins = relationship("RequestToJoin", back_populates="cycle")
    validator_configs = relationship("ValidatorConfig", back_populates="cycle")
    cycle_config = relationship("CycleConfig", back_populates="cycle")
    loan_configs = relationship("LoanConfig", back_populates="cycle")
    penalty_categories = relationship("PenaltyCategory", back_populates="cycle")
    penalties = relationship("PenaltySanctionConfig", back_populates="cycle")
    financial_account = relationship("FinancialAccount", back_populates="cycle")
    loan_requests = relationship("LoanRequest", back_populates="cycle")
    refunds = relationship("Refund", back_populates="cycle")
    guarantees = relationship("Guarantee", back_populates="cycle")




