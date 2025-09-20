from sqlalchemy import ForeignKey, Column, BigInteger, Integer, String, DateTime, func ,UniqueConstraint, CheckConstraint

from sqlalchemy.orm import relationship 
from app.config.database import Base
from app.common.models.SubClient import SubClient

import uuid
from sqlalchemy.dialects.postgresql import UUID

# class Customer (Base): 
    
#     id = Column(BigInteger,autoincrement=True) 
#     name = Column(String, nullable=False) 
#     slug = Column(String, nullable=False) 
#     domain = Column(String, nullable=False) 
#     subscription_tier = Column(String, nullable=False) 
#     subscription_expires_at = Column(DateTime(timezone=True), nullable=False) 
#     state = Column(Integer, nullable=False ,  default=1) 
#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) 
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False) 
    
#     customer_users = relationship('CustomerUser', back_populates = 'customer')
#     #roles = relationship('Role', back_populates = 'customer')


# class User (Base): 
#     __tablename__ = "users" 

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String, nullable=False) 
#     email = Column(String, nullable=False) 
#     phone = Column(Integer, nullable=False) 
#     login = Column(String, nullable=True) 
#     surname = Column(String, nullable=True) 
#     birth_date = Column(String, nullable=True) 
#     phone_number_code = Column(String, nullable=True) 
#     gender = Column(String, nullable=False)
#     state = Column (Integer , nullable = False , default= 1) 
    
#     created_at = Column(DateTime(timezone=True), server_default=func.now()) 
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 
    
     

# class CustomerUser (Base): 
#     __tablename__ = 'customers_users' 

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = False)  
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE") , nullable = False) 
#     state = Column (Integer , nullable = False , default= 1) 
#     created_at = Column(DateTime(timezone=True), server_default=func.now()) 
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 
    
#     user_relations = relationship('UserRelation', back_populates = 'customer_user')
#     customer = relationship('SubClient', back_populates = 'customer_users')
#     user = relationship('User', back_populates = 'customer_users')





class UserRelation (Base): 
    __tablename__ = 'user_relations' 

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = False)  
    customer_user_id = Column(UUID(as_uuid=True) , ForeignKey('sub_client_user.id', ondelete = "CASCADE") , nullable = False) 
    source_id = Column (UUID(as_uuid=True) , nullable = False) 
    source_type = Column (String , nullable = False) 
    state = Column (Integer , nullable = False , default= 1) 
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 

    customer_user = relationship('SubClientUser', back_populates = 'user_relations')

    __table_args__ = (
        UniqueConstraint("customer_user_id", "source_type", "source_id", name="unique_user_resource"),
        CheckConstraint("source_type IN ('role_class','policy_class','permission_class')", name="ck_source_type"),
    )     
    
    __mapper_args__ = {
        "polymorphic_on": source_type,
        "polymorphic_identity": "user_relation"
    }

class UserPermission (UserRelation):
    __mapper_args__ = {
        "polymorphic_identity": "permission_class"
    }
    permission = relationship(
        "Permission",
        primaryjoin="UserPermission.source_id == Permission.id",
        foreign_keys=[UserRelation.source_id],
        viewonly=True,
        lazy="joined"
    )

class UserPolicy (UserRelation):
    __mapper_args__ = {
        "polymorphic_identity": "policy_class"
    }

    policy = relationship(
        "Policy",
        primaryjoin="UserPolicy.source_id == Policy.id",
        foreign_keys=[UserRelation.source_id],
        viewonly=True,
        lazy="joined"
    )

    

class UserRole (UserRelation):
    __mapper_args__ = {
        "polymorphic_identity": "role_class"
    }

    role = relationship(
        "Role",
        primaryjoin="UserRole.source_id == Role.id",
        foreign_keys=[UserRelation.source_id],
        viewonly=True,
        lazy="joined"
    )


class RoleRelation (Base): 
    __tablename__ = 'roles_relations' 

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = True)  
    role_id = Column(UUID(as_uuid=True) , ForeignKey('roles.id', ondelete = "CASCADE") , nullable = False) 
    source_id = Column (UUID(as_uuid=True) , nullable = False) 
    source_type = Column (String , nullable = False)     
    state = Column (Integer , nullable = False , default= 1) 
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 

    role = relationship("Role", back_populates= "role_relations")

    __table_args__ = (
        UniqueConstraint("role_id", "source_type", "source_id", name="unique_role_resource"),
        CheckConstraint("source_type IN ('policy_class','permission_class')", name="ck_source_type"),
    )
    
    __mapper_args__ = {
        "polymorphic_on": source_type,
        "polymorphic_identity": "role_relation"
    }


class RolePermission (RoleRelation):
    __mapper_args__ = {
        "polymorphic_identity": "permission_class"
    }

    permission = relationship(
        "Permission",
        primaryjoin="RolePermission.source_id == Permission.id",
        foreign_keys=[RoleRelation.source_id],
        viewonly=True,
        lazy="joined"
    )


class RolePolicy (RoleRelation):
    __mapper_args__ = {
        "polymorphic_identity": "policy_class"
    }

    policy = relationship(
        "Policy",
        primaryjoin="RolePolicy.source_id == Policy.id",
        foreign_keys=[RoleRelation.source_id],
        viewonly=True,
        lazy="joined"
    )


# class Role (Base): 
#     __tablename__ = "roles"
     
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     label = Column (String , nullable = False) 
#     code = Column (String , nullable = False, unique=True) 
#     sub_client_id = Column(BigInteger, ForeignKey("customers.id", ondelete="CASCADE") , nullable = True)         
#     state = Column (Integer , nullable = False , default= 1) 
#     created_at = Column(DateTime(timezone=True), server_default=func.now()) 
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 

#     role_relations = relationship("RoleRelation", back_populates= "role")
#     # customer = relationship("Customer", back_populates= "roles")


class Permission (Base): 
    __tablename__ = 'permissions' 
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column (String , nullable = False) 
    code = Column (String , nullable = False , unique=True) 
    state = Column (Integer , nullable = False , default= 1) 
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 
    
    policies_permissions = relationship('PolicyPermission', back_populates = 'permission')


class Policy (Base): 
    __tablename__ = 'policies' 

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column (String , nullable = False) 
    code = Column (String , nullable = False , unique=True) 
    sub_client_id = Column(UUID(as_uuid=True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = True)  
    state = Column (Integer , nullable = False , default= 1) 
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 
    
    policies_permissions = relationship('PolicyPermission', back_populates = 'policy')


class PolicyPermission (Base): 
    __tablename__ = 'policies_permissions' 

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sub_client_id = Column(UUID(as_uuid = True), ForeignKey("sub_clients.id", ondelete="CASCADE") , nullable = True)  
    policy_id = Column(UUID(as_uuid = True) , ForeignKey('policies.id', ondelete = "CASCADE") , nullable = False) 
    permission_id = Column (UUID(as_uuid = True) , ForeignKey('permissions.id', ondelete = "CASCADE") , nullable = False) 
    state = Column (Integer , nullable = False , default= 1) 
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) 
    
    policy = relationship('Policy', back_populates = 'policies_permissions')
    permission = relationship('Permission', back_populates = 'policies_permissions')
