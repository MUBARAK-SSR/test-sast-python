import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import SubClient


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    common_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, unique=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    sub_clients = relationship("SubClient", back_populates="client")





