import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_table = Column(String, nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    object = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)

