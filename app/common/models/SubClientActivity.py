import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class SubClientActivity(Base):
    __tablename__ = "sub_client_activity"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(ForeignKey("sub_clients.id"), nullable=False)
    activity_id = Column(ForeignKey("activities.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    sub_client = relationship("SubClient", back_populates="activities")
    activity = relationship("Activity", back_populates="sub_clients")
    cycles = relationship("Cycle", back_populates="sub_client_activity")

