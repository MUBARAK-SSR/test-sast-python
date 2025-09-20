import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Debt


class DebtHistory(Base):
    __tablename__ = "debt_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debt_id = Column(UUID(as_uuid=True), ForeignKey("debts.id"), nullable=False)
    data = Column(JSONB, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    debt = relationship("Debt", back_populates="debt_histories")

