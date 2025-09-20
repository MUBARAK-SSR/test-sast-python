# Placeholder content for schemas.py
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Literal , Union
from pydantic import BaseModel, ConfigDict, EmailStr


# -----------------------------
# Customer
# -----------------------------
class CustomerBase(BaseModel):
    name: str
    slug: str
    domain: str
    subscription_tier: str
    subscription_expires_at: datetime
    state: int

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    domain: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    state: Optional[int] = None

class CustomerRead(CustomerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    customer_users: Optional[List["CustomerUserRead"]] = None  

    model_config = ConfigDict(from_attributes=True)

class CustomerOut(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# -----------------------------
# UserRelation (polymorphique)
# -----------------------------
class UserRelationBase(BaseModel):
    customer_id: UUID
    source_id: UUID
    source_type: Literal["role_class", "policy_class", "permission_class"]
    state: int

class UserRelationRequest(BaseModel):
    role_ids: List[UUID] 
    policy_ids: List[UUID] 
    permission_ids: List[UUID] 

class UserRelationCreate(UserRelationBase):
    pass

class UserRelationUpdate(BaseModel):
    source_id: Optional[UUID] = None
    source_type: Optional[str] = None
    state: Optional[int] = None

class UserRelationRead(UserRelationBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



# -----------------------------
# User
# -----------------------------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: int
    login: Optional[str] = None
    surname: Optional[str] = None
    birth_date: Optional[str] = None
    phone_number_code: Optional[str] = None
    gender: str
    is_active: bool = True

class UserCreate(UserBase):
    name: str
    email: str
    login: str
    surname: Optional[str] = None
    birth_date: Optional[str] = None
    phone_number_code: Optional[str] = None
    gender: str
    state: int = 1

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[int] = None
    login: Optional[str] = None
    surname: Optional[str] = None
    birth_date: Optional[str] = None
    phone_number_code: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[int] = None

class UserRoleRead(BaseModel):
    label: str
    #customer_id: Optional[int]
    created_at: Optional[datetime]
    id: UUID
    code: str
    state: int = 1
    updated_at: Optional[datetime]

class UserPolicyRead(BaseModel):
    label: str
    #customer_id: Optional[int]
    created_at: Optional[datetime]
    id: UUID
    code: str
    state: int = 1
    updated_at: Optional[datetime]

class UserPermissionRead(BaseModel):
    label: str
    #customer_id: Optional[int]
    created_at: Optional[datetime]
    id: UUID
    code: str
    state: int = 1
    updated_at: Optional[datetime]

class UserRead(UserBase):
    id: UUID
    name: str
    email: str
    login: str
    phone: int
    surname: Optional[str] = None
    birth_date: Optional[str] = None
    phone_number_code: Optional[str] = None
    gender: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    roles: Optional[List[UserRoleRead]] = None 
    policies: Optional[List[UserPolicyRead]] = None 
    permissions: Optional[List[UserPermissionRead]] = None

    model_config = ConfigDict(from_attributes=True)

class ListUserRead(UserBase):
    id: UUID
    name: str
    email: str
    login: str
    phone: int
    surname: Optional[str] = None
    birth_date: Optional[str] = None
    phone_number_code: Optional[str] = None
    gender: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)




class CustomerUserBase(BaseModel):
    sub_client_id: UUID
    user_id: UUID
    is_active: bool = True


class CustomerUserCreate(CustomerUserBase):
    pass


class CustomerUserUpdate(BaseModel):
    customer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    state: Optional[int] = None


class CustomerUserRead(CustomerUserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    # relations
    customer: Optional[CustomerRead] = None
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)

class CustomerUserReadFromCustomerUser(CustomerUserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    user: Optional[UserRead] = None
    #user_relations: Optional[UserRelationRead] = None
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Role
# -----------------------------

class RolePolicyRead (BaseModel):
    id: UUID
    label: str
    code: str
    state: int

class PermissionRead (BaseModel):
    id: UUID
    label: str
    code: str
    state: int

class RoleBase(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    label: str
    configured_by: Optional[str] = None
    code: str
    state: int = 1

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    configured_by: Optional[str] = None
    code: Optional[str] = None
    label: Optional[str] = None
    state: Optional[int] = None

class RoleReadForCreation(RoleBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    role_relations: Optional[List] = None

    model_config = ConfigDict(from_attributes=True)

class RoleRead(RoleBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    role_relations: Optional[dict[str, list[Union[RolePolicyRead, PermissionRead]]]] = None

    model_config = ConfigDict(from_attributes=True)

class RoleListRead(BaseModel):
    id: UUID
    label: str
    code: str
    state: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
# -----------------------------
# RoleRelation (polymorphique)
# -----------------------------
class RoleRelationBase(BaseModel):
    role_id: UUID 
    source_id: UUID
    source_type: Literal["policy_class", "permission_class"]
    state: int

class RoleRelationRequest(BaseModel):
    policy_ids: List[UUID] 
    permission_ids: List[UUID] 

    # source_id: int
    # source_type: Literal["policy_class", "permission_class"]
    # state: int

class RoleRelationCreate(RoleRelationBase):
    pass

class RoleRelationUpdate(BaseModel):
    source_id: Optional[UUID] = None
    source_type: Optional[str] = None
    state: Optional[int] = None

class RoleRelationRead(RoleRelationBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Permission
# -----------------------------
class PermissionBase(BaseModel):
    label: str
    code: str
    state: int = 1

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    label: Optional[str] = None
    code: Optional[str] = None
    state: Optional[int] = None

class PermissionRead(PermissionBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    policies_permissions: Optional[List["PolicyPermissionRead"]] = None

    model_config = ConfigDict(from_attributes=True)

class PermissionReadForRelation(PermissionBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #policies_permissions: Optional[List["PolicyPermissionRead"]] = None

    model_config = ConfigDict(from_attributes=True)

class PermissionListRead(BaseModel):
    id: UUID
    label: str
    code: str
    state: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
# -----------------------------
# Policy
# -----------------------------
class PolicyBase(BaseModel):
    label: str
    code: str
    state: int = 1

class PolicyCreate(PolicyBase):
    pass

class PolicyUpdate(BaseModel):
    label: Optional[str] = None
    code: Optional[str] = None
    state: Optional[int] = None

class PolicyReadForCreation(PolicyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    policies_permissions: Optional[List] = None

    model_config = ConfigDict(from_attributes=True)

class PolicyRead(PolicyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    policies_permissions: Optional[List["PolicyPermissionReadForRelation"]] = None

    model_config = ConfigDict(from_attributes=True)

class ListPolicyRead(PolicyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# -----------------------------
# PolicyPermission
# -----------------------------
class PolicyPermissionBase(BaseModel):
    policy_id: Optional[UUID] = None
    permission_id: Optional[UUID] = None 
    state: int

class PolicyPermissionCreate(BaseModel):
    permission_ids: List[UUID]
    state: int = 1

class PolicyPermissionUpdate(BaseModel):
    policy_id: Optional[UUID] = None
    permission_id: Optional[UUID] = None
    state: Optional[int] = None


class PolicyPermissionRead(PolicyPermissionBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    policy: Optional[PolicyRead] = None
    permission: Optional[PermissionRead] = None

    model_config = ConfigDict(from_attributes=True)

class PolicyPermissionReadForRelation(PolicyPermissionBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #policy: Optional[PolicyRead] = None
    permission: Optional[PermissionReadForRelation] = None

    model_config = ConfigDict(from_attributes=True)
# -----------------------------
# Résolution des références circulaires
# -----------------------------
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    CustomerRead.model_rebuild()
    UserRead.model_rebuild()
    UserRelationRead.model_rebuild()
    RoleRead.model_rebuild()
    RoleRelationRead.model_rebuild()
    PermissionRead.model_rebuild()
    PolicyRead.model_rebuild()
    PolicyPermissionRead.model_rebuild()
