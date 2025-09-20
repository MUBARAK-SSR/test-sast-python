import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.common.models import SubClient


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(UUID(as_uuid=True) , ForeignKey("sub_clients.id"), nullable=True)
    name = Column(String, nullable=True)
    level = Column(Integer, nullable=True)
    configured_by = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    '''
        champs et relations ajouté
    '''
    label = Column (String , nullable = False)
    code = Column (String , nullable = False, unique=True)
    #customer_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = True)
    state = Column (Integer , nullable = False , default= 1)

    # relation pour la lecture des differents éléments associés à un role (permissions , polices)
    role_relations = relationship("RoleRelation", back_populates= "role")
    '''
        end
    '''

    sub_client = relationship("SubClient", back_populates="roles")
    user_cycles = relationship("UserCycleRole", back_populates="role")

    __table_args__ = (UniqueConstraint('name', 'sub_client_id', name='roles_name_sub_client_id_key'),)
