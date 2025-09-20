import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import Operator, Cycle


class TypeOperator(Base):
    __tablename__ = "type_operators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    common_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # operators = relationship("Operator", back_populates="type_operator")



