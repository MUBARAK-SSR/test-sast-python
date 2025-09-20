import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Role, UserCycle


class UserCycleRole(Base):
    __tablename__ = "user_cycle_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_cycle_id = Column(ForeignKey("user_cycle.id"), nullable=False)
    role_id = Column(ForeignKey("roles.id"), nullable=False)
    configured_by = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # is_active = Column(Boolean, default=True)

    user_cycle = relationship("UserCycle", back_populates="roles")
    role = relationship("Role", back_populates="user_cycles")

    __table_args__ = (UniqueConstraint('role_id', 'user_cycle_id', name='user_cycle_roles_role_id_user_cycle_id_key'),)

