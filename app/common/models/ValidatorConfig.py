import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, String, TIMESTAMP, Integer, UniqueConstraint, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Cycle
from app.services.cycle_configurations.constants import ValidatorFlag


class ValidatorConfig(Base):
    __tablename__ = "validator_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    validators_id = Column(JSONB, nullable=False)
    flag = Column(Integer, nullable=False)
    operation_name = Column(String, nullable=False)
    configured_by = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    cycle = relationship("Cycle", back_populates="validator_configs")

    __table_args__ = (UniqueConstraint('flag', 'cycle_id', name='validator_configs_flag_cycle_id_key'),)

