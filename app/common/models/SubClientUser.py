import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Table, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base

class SubClientUser(Base):
    __tablename__ = "sub_client_user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(UUID(as_uuid=True) , ForeignKey("sub_clients.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True) , ForeignKey("users.id"), nullable=False)
    member_nui = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)


    # ralations ajouté
    user_relations = relationship('UserRelation', back_populates = 'customer_user')
    customer = relationship('SubClient', back_populates = 'customer_users')
    #user = relationship('User', back_populates = 'customer_users')

    sub_client = relationship("SubClient", back_populates="users")
    user = relationship("User", back_populates="sub_clients")
