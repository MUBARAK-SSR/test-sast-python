import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class UserCycle(Base):
    __tablename__ = "user_cycle"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    cycle_id = Column(ForeignKey("cycles.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="cycles")
    cycle = relationship("Cycle", back_populates="users")
    roles = relationship("UserCycleRole", back_populates="user_cycle")

    # office_roles = relationship("OfficeRole", back_populates="user_cycle")
