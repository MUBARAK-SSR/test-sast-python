import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Float, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount_invested = Column(Float, nullable=False)
    sold_to = Column(UUID(as_uuid=True), ForeignKey("subscribers.id"), nullable=False)
    amount_received = Column(Float, nullable=False)
    repayment_duration = Column(Integer, nullable=False)
    amount_to_repay = Column(Float, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    buyer = relationship("User")
