# Placeholder content for handlers.py
import json
import os
from uuid import UUID
from typing import List
from dotenv import load_dotenv
from fastapi import Header, Request
from datetime import datetime, timedelta , timezone
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi_cache import FastAPICache
import jwt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert , select , delete , and_ , or_
from sqlalchemy.orm import selectinload , with_loader_criteria
from app.services.permissions.constants import SourceTypeConstant , PERMISSION_ACCESS_TOKEN_EXPIRE_SECOND , PERMISSION_ALGORITHM
from app.services.permissions.schemas import (
    CustomerCreate , CustomerRead, PermissionCreate , PermissionRead, PermissionListRead, PermissionUpdate, PolicyCreate, PolicyUpdate, RoleCreate,
    RoleListRead , RoleRead, RoleUpdate, UserRead , ListUserRead , PolicyRead , ListPolicyRead,
    PolicyReadForCreation , PolicyPermissionCreate , PolicyPermissionRead , 
    RoleReadForCreation , RoleRelationRequest , UserRelationRequest, CustomerUserReadFromCustomerUser
    )
from app.common.models.model_permission import ( 
    Permission, RolePermission  , Policy, 
    PolicyPermission , RolePolicy , UserPolicy, UserPermission, UserRole,
    RoleRelation
    )



load_dotenv()

from app.common.models.User import User
from app.common.models.Role import Role
from app.common.models.SubClient import SubClient as Customer
from app.common.models.SubClientUser import SubClientUser as CustomerUser




'''
    fucntions for create data in database
'''


async def create_permissions (permission_object: PermissionCreate  ,  db: AsyncSession)->PermissionRead:
    
    try:
        new_permission = Permission(
            label =permission_object.label,
            code  =permission_object.code
        )

        # Ajout à la session
        db.add(new_permission)
        await db.commit()
        await db.refresh(new_permission)

        permission_object_response = {
            "id": new_permission.id,
            "label": new_permission.label,
            "code": new_permission.code,
            "state": new_permission.state,
            "created_at": new_permission.created_at,
            "updated_at": new_permission.updated_at,
            "policies_permissions": [] 
        }
        # Conversion en Pydantic
        return PermissionRead.model_validate(permission_object_response , from_attributes= True)
    except Exception as exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

# fonction permettant aux administrateurs de creer un role dans le service
async def create_role (role_object: RoleCreate  ,  db: AsyncSession , request : Request)->RoleReadForCreation:
    
    try:

        new_role = Role(
            name =role_object.label,
            label =role_object.label,
            code  =role_object.code,
            level =role_object.level,
            configured_by =role_object.configured_by,
        )

        # Ajout à la session
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        role_object_response = {
            "id": new_role.id,
            "name": new_role.name,  
            "level": new_role.level,  
            "configured_by": new_role.configured_by,
            "label": new_role.label,
            "code": new_role.code,
            "state": new_role.state,
            "created_at": new_role.created_at,
            "updated_at": new_role.updated_at,
            "role_relations": [] 
        }
        # Conversion en Pydantic
        return RoleReadForCreation(**role_object_response)
    except Exception as exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        ) 

#fonction permettant à un client de creer son role
async def create_role_by_customer (
        role_object: RoleCreate  ,
        db: AsyncSession ,
        request : Request,
        customer_id: UUID
)->RoleReadForCreation:
    
    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        

        new_role = Role(
            #name =role_object.name,
            label =role_object.label,
            code  =role_object.code,
            # level =role_object.level,
            # configured_by =role_object.configured_by,
            sub_client_id = sub_client_id
        )

        # Ajout à la session
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        role_object_response = {
            "id": new_role.id,
            "name": new_role.name,  
            "level": new_role.level,  
            "configured_by": new_role.configured_by,
            "label": new_role.label,
            "code": new_role.code,
            "state": new_role.state,
            "created_at": new_role.created_at,
            "updated_at": new_role.updated_at,
            "role_relations": [] 
        }
        # Conversion en Pydantic
        return RoleReadForCreation(**role_object_response)
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        ) 

# fonction permettant aux administrateurs de creer une politique dans le service
async def create_policy (policy_object: PolicyCreate  ,  db: AsyncSession)->PolicyReadForCreation:
    
    try:
        new_policy = Policy(
            label =policy_object.label,
            code  =policy_object.code
        )

        # Ajout à la session
        db.add(new_policy)
        await db.commit()
        await db.refresh(new_policy)

        policy_object_response = {
            "id": new_policy.id,
            "label": new_policy.label,
            "code": new_policy.code,
            "state": new_policy.state,
            "created_at": new_policy.created_at,
            "updated_at": new_policy.updated_at,
            "policies_permissions": [] 
        }
        # Conversion en Pydantic
        return PolicyReadForCreation(**policy_object_response)
    except Exception as exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        ) 

# fonction permettant aux administrateurs de creer sa role dans le service
async def create_policy_by_customer (policy_object: PolicyCreate  ,  db: AsyncSession , request : Request, customer_id: UUID)->PolicyReadForCreation:
    
    
    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        
        new_policy = Policy(
            label =policy_object.label,
            code  =policy_object.code,
            sub_client_id = sub_client_id
        )

        # Ajout à la session
        db.add(new_policy)
        await db.commit()
        await db.refresh(new_policy)

        policy_object_response = {
            "id": new_policy.id,
            "label": new_policy.label,
            "code": new_policy.code,
            "state": new_policy.state,
            "created_at": new_policy.created_at,
            "updated_at": new_policy.updated_at,
            "policies_permissions": [] 
        }
        # Conversion en Pydantic
        return PolicyReadForCreation(**policy_object_response)
    except Exception as exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        ) 


'''
    fucntions for update data in database
'''
async def update_permissions (
    permission_id: int , 
    permission_object: PermissionUpdate  , 
    db: AsyncSession, 
    request : Request
)->PermissionRead:
    
    try:
        result = await db.execute(select(Permission).where(Permission.id == permission_id))
        new_permission = result.scalar_one_or_none()
        
        if not new_permission:
            raise HTTPException(status_code=404, detail="Permission non trouvée")

        # Mise à jour des champs
        new_permission.label = permission_object.label
        new_permission.code = permission_object.code

        await db.commit()
        await db.refresh(new_permission)

        permission_object_response = {
            "id": new_permission.id,
            "label": new_permission.label,
            "code": new_permission.code,
            "state": new_permission.state,
            "created_at": new_permission.created_at,
            "updated_at": new_permission.updated_at,
            "policies_permissions": []
        }

        return PermissionRead.model_validate(permission_object_response)

    except HTTPException:
        # On laisse passer les erreurs HTTP telles quelles
        raise
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

# fonction permettant aux administrateurs de modifier un role dans le service
async def update_roles (
    role_id: UUID , 
    role_object: RoleUpdate  ,  
    db: AsyncSession , 
    request : Request
)->RoleReadForCreation:
    
    try:
        result = await db.execute(select(Role).where(Role.id == role_id))
        new_role = result.scalar_one_or_none()
        
        if not new_role:
            raise HTTPException(status_code=404, detail="Role non trouvée")

        # Mise à jour des champs
        new_role.name = role_object.name or new_role.name
        new_role.level = role_object.level or new_role.level
        new_role.configured_by = role_object.label or new_role.configured_by
        new_role.code = role_object.code or new_role.code
        new_role.label = role_object.label or new_role.label

        await db.commit()
        await db.refresh(new_role)

        role_object_response = {
            "id": new_role.id,
            "label": new_role.label,
            "code": new_role.code,
            "name": new_role.name,  
            "level": new_role.level,  
            "configured_by": new_role.configured_by,
            "state": new_role.state,
            "created_at": new_role.created_at,
            "updated_at": new_role.updated_at,
            "role_relations": []

        }

        return RoleReadForCreation(**role_object_response)

    except HTTPException:
        raise
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

# fonction permettant à un client de modifier le role qu'il a créé dans le service
async def update_roles_by_customer (
    role_id: UUID , 
    role_object: RoleUpdate  ,  
    db: AsyncSession , 
    request : Request, 
    customer_id: UUID
)->RoleReadForCreation:
    
    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        result = await db.execute(select(Role).where(and_(Role.id == role_id , Role.sub_client_id == sub_client_id)))
        new_role = result.scalar_one_or_none()
        
        if not new_role:
            raise HTTPException(status_code=404, detail="Role non trouvée")

        # Mise à jour des champs
        new_role.name = role_object.name or new_role.name
        new_role.level = role_object.level or new_role.level
        new_role.configured_by = role_object.label or new_role.configured_by
        new_role.code = role_object.code or new_role.code
        new_role.label = role_object.label or new_role.label

        await db.commit()
        await db.refresh(new_role)

        role_object_response = {
            "id": new_role.id,
            "label": new_role.label,
            "code": new_role.code,
            "name": new_role.name,  
            "level": new_role.level,  
            "configured_by": new_role.configured_by,
            "state": new_role.state,
            "created_at": new_role.created_at,
            "updated_at": new_role.updated_at,
            "role_relations": []

        }

        return RoleReadForCreation(**role_object_response)

    except HTTPException:
        # On laisse passer les erreurs HTTP telles quelles
        raise
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )
    
# fonction permettant aux administrateurs de modifier une politique dans le service
async def update_policies (
    policy_id: int , 
    policy_object: PolicyUpdate  ,  
    db: AsyncSession , 
    request : Request, 
)->PolicyReadForCreation:
    
    try:
        result = await db.execute(select(Policy).where(Policy.id == policy_id))
        new_policy = result.scalar_one_or_none()
        
        if not new_policy:
            raise HTTPException(status_code=404, detail="Politique non trouvée")

        # Mise à jour des champs
        new_policy.label = policy_object.label
        new_policy.code = policy_object.code

        await db.commit()
        await db.refresh(new_policy)

        policy_object_response = {

            "id": new_policy.id,
            "label": new_policy.label,
            "code": new_policy.code,
            "state": new_policy.state,
            "created_at": new_policy.created_at,
            "updated_at": new_policy.updated_at,
            "role_relations": []
        }

        return PolicyReadForCreation(**policy_object_response)

    except HTTPException:
        # On laisse passer les erreurs HTTP telles quelles
        raise
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

# fonction permettant à un client de modifier la politique qu'il a créé dans le service
async def update_policies_by_customer (
    policy_id: UUID , 
    policy_object: PolicyUpdate  ,  
    db: AsyncSession , 
    request : Request, 
    customer_id: UUID
)->PolicyReadForCreation:
    
    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        
        result = await db.execute(select(Policy).where(and_(Policy.id == policy_id , Policy.sub_client_id == sub_client_id)))
        new_policy = result.scalar_one_or_none()
        
        if not new_policy:
            raise HTTPException(status_code=404, detail="Politique non trouvée")

        # Mise à jour des champs
        new_policy.label = policy_object.label
        new_policy.code = policy_object.code

        await db.commit()
        await db.refresh(new_policy)

        policy_object_response = {

            "id": new_policy.id,
            "label": new_policy.label,
            "code": new_policy.code,
            "state": new_policy.state,
            "created_at": new_policy.created_at,
            "updated_at": new_policy.updated_at,
            "role_relations": []
        }

        return PolicyReadForCreation(**policy_object_response)

    except HTTPException:
        # On laisse passer les erreurs HTTP telles quelles
        raise
    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )
  
'''
    fucntions for read data in database
'''
async def read_permissions(db: AsyncSession) -> List[PermissionListRead]:
    try:
        results = await db.execute(select(Permission))
        permissions = results.scalars().all()

        return [
            PermissionListRead.model_validate(one_permission, from_attributes=True).model_dump(exclude={"policies_permissions"})
            for one_permission in permissions
        ]

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

#fonction permettant de lire les roles
async def read_roles(db: AsyncSession , request : Request, customer_id: UUID) -> List[RoleListRead]:
    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        
        results = await db.execute(
            select(Role)
            .where(or_ (Role.sub_client_id == None , Role.sub_client_id == sub_client_id)))  
       
        roles = results.scalars().all()
        
        return [
            RoleListRead.model_validate(one_role, from_attributes=True)
            for one_role in roles
        ]

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

#fonction permettant de lire un role
async def read_one_role( role_id: UUID , db: AsyncSession , request : Request, customer_id: UUID) -> RoleRead:
    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.role_relations.of_type(RolePermission)).selectinload(RolePermission.permission),
                selectinload(Role.role_relations.of_type(RolePolicy)).selectinload(RolePolicy.policy),
                with_loader_criteria(RolePermission, RolePermission.sub_client_id == sub_client_id),
                with_loader_criteria(RolePolicy, RolePolicy.sub_client_id == sub_client_id)
            )
            .where(and_((Role.id == role_id) , or_(Role.sub_client_id.is_(None) , Role.sub_client_id == sub_client_id)))
        )

        role = result.scalar_one_or_none()

        policies = []
        permissions = []

        for item in role.role_relations :
            if item.source_type == SourceTypeConstant.policy_source_type():
                policies.append(item.policy)
            elif item.source_type == SourceTypeConstant.permission_source_type():
                permissions.append(item.permission)

        detail_role = {
            "code": role.code,
            "id": role.id,
            "label": role.label,
            "name": role.name,
            "level": role.level,
            "configured_by": role.configured_by,
            "state": role.state,
            "updated_at": role.updated_at,
            "sub_client_id": role.sub_client_id ,
            "created_at": role.created_at,
            "role_relations" : {
                "policies" : policies,
                "permissions" : permissions,
            }
        }

        return RoleRead.model_validate(detail_role , from_attributes = True)

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail= f"une erreur s'est produite : {str(exception)}"
        )
    
#fonction permettant de lire les utilisateurs
async def read_users(db: AsyncSession , request : Request, customer_id: UUID) -> List[CustomerUserReadFromCustomerUser]:
    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        results = await db.execute(select(CustomerUser).options(
            selectinload(CustomerUser.user)
            ).where(CustomerUser.sub_client_id == sub_client_id)
        )

        users = results.scalars().all()

        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        return [
            CustomerUserReadFromCustomerUser.model_validate(one_user, from_attributes=True)
            for one_user in users
        ]

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

#fonction permettant de lire un utilisateur
async def read_one_user( user_id: int , db: AsyncSession,  request : Request, customer_id: UUID) -> UserRead:

    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        result = await db.execute(
            select(CustomerUser)
            .options(selectinload(CustomerUser.user))
            .options(selectinload(CustomerUser.user_relations))
            .where(
                CustomerUser.user_id == user_id,
                CustomerUser.sub_client_id == sub_client_id
            )
        )
        customer_user = result.scalar_one()

        roles = []
        policies = []
        permissions = []

        for item in customer_user.user_relations:

            if item.source_type == SourceTypeConstant.role_source_type() :

                result = await db.execute(select(Role).where(Role.id == item.source_id))
                role = result.scalar_one()
                roles.append(role)

            if item.source_type == SourceTypeConstant.policy_source_type() :
                result = await db.execute(select(Policy).where(Policy.id == item.source_id))
                policy = result.scalar_one()
                policies.append(policy)
            if item.source_type == SourceTypeConstant.permission_source_type() :
                result = await db.execute(select(Permission).where(Permission.id == item.source_id))
                permission = result.scalar_one()
                permissions.append(permission)

        print("************************************** : {sub_client_id}")

        user_detail = {
            "id": customer_user.user.id,
            "name": customer_user.user.name,
            "email": customer_user.user.email,
            "phone": customer_user.user.phone,
            "login": customer_user.user.login,
            "surname": customer_user.user.surname,
            "birth_date": customer_user.user.birth_date,
            "phone_number_code": customer_user.user.phone_number_code,
            "gender": customer_user.user.gender,
            "state": customer_user.user.is_active,
            "created_at": customer_user.user.created_at,
            "updated_at": customer_user.user.updated_at,
            "roles": roles,
            "policies": policies,
            "permissions":permissions
        }

        return UserRead.model_validate(user_detail, from_attributes=True)
        #return user_detail
    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite : {str(exception)}"
        )
    
#fonction permettant de lire les politiques
async def read_policies(db: AsyncSession ,  request : Request, customer_id: UUID) -> List[ListPolicyRead]:
    try:
        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        results = await db.execute(select(Policy) 
            .where(or_ (Policy.sub_client_id.is_(None) , Policy.sub_client_id == sub_client_id ))             
        )
        policies = results.scalars().all()

        return [
            ListPolicyRead.model_validate(one_policy, from_attributes=True)
            for one_policy in policies
        ]

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=[f"une erreur s'est produite : {str(exception)}"]
        )

#fonction permettant de lire une poilitique
async def read_one_policy( policy_id: UUID , db: AsyncSession,  request : Request, customer_id: UUID) -> PolicyRead:
    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        
        result = await db.execute(
            select(Policy)
            .options(
                selectinload(Policy.policies_permissions)
                .selectinload(PolicyPermission.permission),
                with_loader_criteria(
                    PolicyPermission,
                    lambda cls: cls.sub_client_id == sub_client_id,
                    include_aliases=True
                )
            )
            .where(or_(Policy.sub_client_id.is_(None), Policy.sub_client_id == sub_client_id))
            .where(Policy.id == policy_id)
        )
        policy = result.scalar_one()

        return PolicyRead.model_validate(policy, from_attributes=True)

    except Exception as exception:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite : {str(exception)}"
        )
    
#fonction permettant configurer les politiques de permissions  par un client
async def make_policy_config( 
        policy_id: UUID ,
        policy_permission_object:PolicyPermissionCreate, 
        db: AsyncSession,  
        request : Request,
        customer_id: UUID
):
    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        result = await db.execute(select(Policy).where(Policy.id == policy_id))
        policy = result.scalar_one_or_none()

        if policy is None:
            raise HTTPException(
                status_code=400,
                detail="Politique inexistante"
            )

        print (" policy ok")

        await db.execute(delete(PolicyPermission).where(and_(PolicyPermission.policy_id == policy_id , PolicyPermission.sub_client_id == sub_client_id)))
        await db.commit()

        for permission_id in policy_permission_object.permission_ids:
            
            result = await db.execute(select(Permission).where(Permission.id == permission_id))
            permission = result.scalar_one_or_none()

            if permission == None:
                raise HTTPException(
                    status_code=400,
                    detail=f" la Permission avec l'id {permission_id} est inexistante"
                )

            result = await db.execute(
                select(PolicyPermission).where(
                    PolicyPermission.sub_client_id == sub_client_id,
                    PolicyPermission.policy_id == policy_id,
                    PolicyPermission.permission_id == permission_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                print (" policy_permission ok 2")
                
                policy_permission = PolicyPermission(
                    sub_client_id = sub_client_id,
                    policy_id=policy_id,
                    permission_id=permission_id
                )
                
                db.add(policy_permission) 
                await db.commit()
                await db.refresh(policy_permission)

        #rebuilt_header = {"customer-id": str(sub_client_id)}

        return await read_one_policy(policy_id, db , request , customer_id)
        #return {'status_code' : 200, 'status' : 'success' , 'message' : 'success', 'data': []}
    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite : {str(exception)}"
        )

#fonction permettant configurer les roles par un client
async def make_role_config(
    role_id: UUID ,
    role_relation_object:RoleRelationRequest, 
    db: AsyncSession,  
    request : Request, 
    customer_id: UUID
):
    sub_client_id = customer_id
    if sub_client_id is None:
        raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

    if len(role_relation_object.policy_ids) == 0 and len(role_relation_object.permission_ids) == 0 :
        raise HTTPException(
            status_code= 500,
            detail= "aucune configuration renseigné pour ce role"
        )

    try:
        # we verify if role that we want to configure exist in database
        result = await db.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()

        if role is None:
            raise HTTPException(
                status_code=400,
                detail="role inexistant"
            )

        
        # if we have policies within request , we execute this function
        if len(role_relation_object.policy_ids) > 0 :

            #deleting of all recording those are present  in database for current role_id and current source_type = policy_class
            await db.execute(delete(RolePolicy).where(and_(RolePolicy.role_id == role_id , RolePolicy.sub_client_id == sub_client_id)))
            await db.commit()

            # stating registration of configuration process
            for policy_id in role_relation_object.policy_ids:

                result = await db.execute(
                    select(Policy).where(
                        Policy.id == policy_id,
                    )
                )
                policy_existing = result.scalar_one_or_none()

                # 1 st control : we verify if policy is present in own table
                if policy_existing is None:
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f" la politique avec l'id {policy_id} est inexistante"
                    )
                
                result = await db.execute(
                    select(RolePolicy).where(
                        and_(
                            RolePolicy.source_id == policy_id,
                            RolePolicy.sub_client_id == sub_client_id
                        )
                    )
                )
                policy_role_relation_existing = result.scalar_one_or_none()

                # 2 nd control : we verify if policy is present in roles_relations table
                if policy_role_relation_existing is None:
                    
                    role_relation_for_policy = RolePolicy(
                        role_id= role_id,
                        source_id= policy_id,
                        sub_client_id = sub_client_id
                    )
                    
                    db.add(role_relation_for_policy) 
                    await db.commit()
                    await db.refresh(role_relation_for_policy)

        if len(role_relation_object.permission_ids) > 0 :

            await db.execute(delete(RolePermission).where(and_(RolePermission.role_id == role_id,  RolePermission.sub_client_id == sub_client_id)))
            await db.commit()

            for permission_id in role_relation_object.permission_ids:
                
                result = await db.execute(
                    select(Permission).where(
                        Permission.id == permission_id,
                    )
                )
                permission_existing = result.scalar_one_or_none()

                if permission_existing is None:
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f" la permissiont avec l'id {permission_id} est inexistante"
                    )
                

                result = await db.execute(
                    select(RolePermission).where(
                        RolePermission.source_id == permission_id,
                        RolePermission.sub_client_id == sub_client_id
                    )
                )
                permission_role_relation_existing = result.scalar_one_or_none()

                if permission_role_relation_existing is None:
                    
                    role_relation_for_permission = RolePermission(
                        role_id= role_id,
                        source_id= permission_id,
                        sub_client_id = sub_client_id
                    )
                    
                    db.add(role_relation_for_permission) 
                    await db.commit()
                    await db.refresh(role_relation_for_permission)

        #rebuilt_header = {"customer-id": str(sub_client_id)}
        return await read_one_role(role_id, db , request, customer_id)

    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite. {str(exception)}"
        )

#fonction permettant configurer les roles et les permissions d'un utilisateur par un client
async def make_user_config(
    user_id: UUID,
    user_relation_object: UserRelationRequest,
    db: AsyncSession,
    request : Request,
    customer_id: UUID
):
    
    if len(user_relation_object.role_ids) == 0 and len(user_relation_object.policy_ids) == 0 and len(user_relation_object.permission_ids) == 0 :
        raise HTTPException(
            status_code= 500,
            detail= "aucune configuration renseigné pour cet utilisateur"
        )

    try:

        sub_client_id = customer_id
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")

        # we verify if user that we want to configure exist in database
        result = await db.execute(select(CustomerUser).where(and_(CustomerUser.user_id == user_id , CustomerUser.sub_client_id == sub_client_id )))

        customer_user = result.scalar_one_or_none()

        if customer_user is None:
            raise HTTPException(
                status_code=400,
                detail="utilisateur inexistant"
            )

        
        # if we have policies within request , we execute this part function
        if len(user_relation_object.policy_ids) > 0 :

            #deleting of all recording those are present  in database for current role_id and current source_type = policy_class
            await db.execute(delete(UserPolicy).where(UserPolicy.customer_user_id == customer_user.id , UserPolicy.sub_client_id == sub_client_id))
            await db.commit()

            # stating registration of configuration process
            for policy_id in user_relation_object.policy_ids:

                result = await db.execute(
                    select(Policy).where(
                        Policy.id == policy_id,
                    )
                )
                policy_existing = result.scalar_one_or_none()

                # 1 st control : we verify if policy is present in own table
                if policy_existing is None:
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f" la politique avec l'id {policy_id} est inexistante"
                    )
                

                result = await db.execute(
                    select(UserPolicy).where(
                        UserPolicy.source_id == policy_id,
                        UserPolicy.sub_client_id == sub_client_id
                    )
                )
                policy_user_relation_existing = result.scalar_one_or_none()

                # 2 nd control : we verify if policy is present in roles_relations table
                if policy_user_relation_existing is None:
                    
                    user_relation_for_policy = UserPolicy(
                        customer_user_id= customer_user.id,
                        source_id= policy_id,
                        sub_client_id = sub_client_id
                    )
                    
                    db.add(user_relation_for_policy) 
                    await db.commit()
                    await db.refresh(user_relation_for_policy)

        if len(user_relation_object.permission_ids) > 0 :

            await db.execute(delete(UserPermission).where(UserPermission.customer_user_id == customer_user.id , UserPermission.sub_client_id == sub_client_id))
            await db.commit()

            for permission_id in user_relation_object.permission_ids:
                
                result = await db.execute(
                    select(Permission).where(
                        Permission.id == permission_id,
                    )
                )
                permission_existing = result.scalar_one_or_none()

                if permission_existing is None:
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f" la permissiont avec l'id {permission_id} est inexistante"
                    )
                

                result = await db.execute(
                    select(UserPermission).where(
                        UserPermission.source_id == permission_id,
                        UserPermission.sub_client_id == sub_client_id
                    )
                )
                permission_user_relation_existing = result.scalar_one_or_none()

                if permission_user_relation_existing is None:
                    
                    user_relation_for_permission = UserPermission(
                        customer_user_id= customer_user.id,
                        source_id= permission_id,
                        sub_client_id = sub_client_id
                    )
                    
                    db.add(user_relation_for_permission) 
                    await db.commit()
                    await db.refresh(user_relation_for_permission)
        
        if len(user_relation_object.role_ids) > 0 :

            await db.execute(delete(UserRole).where(UserRole.customer_user_id == customer_user.id , UserRole.sub_client_id == sub_client_id))
            await db.commit()

            for role_id in user_relation_object.role_ids:
                
                result = await db.execute(
                    select(Role).where(
                        Role.id == role_id,
                    )
                )

                role_existing = result.scalar_one_or_none()

                if role_existing is None:
                    
                    raise HTTPException(
                        status_code=400,
                        detail=f" e role avec l'id {permission_id} est inexistante"
                    )
                

                result = await db.execute(
                    select(UserRole).where(
                        UserRole.source_id == role_id,
                        UserRole.sub_client_id == sub_client_id
                    )
                )
                role_user_relation_existing = result.scalar_one_or_none()

                if role_user_relation_existing is None:
                    
                    user_relation_for_role = UserRole(
                        customer_user_id     = customer_user.id,
                        source_id   = role_id,
                        sub_client_id = sub_client_id
                    )
                    
                    db.add(user_relation_for_role) 
                    await db.commit()
                    await db.refresh(user_relation_for_role)
        
        #rebuilt_header = {"customer-id": str(sub_client_id)}
        return await read_one_user(user_id, db, request, customer_id)

    except Exception as exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite. {str(exception)}"
        )


# function for generate token authentificator
async def generate_token(request:Request , client_id: str):

    try:

        if (client_id != os.getenv('CLIENT_ID_IAM')):
            return {
                "status_code"   : 404,
                "status"        : "error",
                "message"       : "Le client_id renseigné est invalide"
            }

        data = {"client_id": client_id}

        secret_key = os.getenv("PERMISSION_SECRET_KEY", "default_secret")
        algorithm = PERMISSION_ALGORITHM or 'HS256'
        expire_seconds = PERMISSION_ACCESS_TOKEN_EXPIRE_SECOND

        expire = datetime.utcnow() + timedelta(seconds= expire_seconds)

        to_encode = data.copy()
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)

        # cache_permissions_key = f"cache du token pour la gestion des permissions"+"client_id:"+{client_id}+"number_key:"+{client_id}

        # await FastAPICache.get_backend().set(cache_permissions_key , encoded_jwt)
        return {
            "status_code" : 200,
            "status" : "success",
            "message" : "success",
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expire_at" : expire_seconds
        }

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du token : {str(exception)}"
        )


async def create_customer (
        customer_object: CustomerCreate , 
        db: AsyncSession
)->CustomerRead:

    new_customer = Customer(
        name=customer_object.name,
        slug=customer_object.slug,
        domain=customer_object.domain,
        subscription_tier=customer_object.subscription_tier,
        subscription_expires_at=customer_object.subscription_expires_at,
        state=customer_object.state or 1
    )

    # Ajout à la session
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)

    customer_object_response = {
        "id": new_customer.id,
        "name": new_customer.name,
        "slug": new_customer.slug,
        "domain": new_customer.domain,
        "subscription_tier": new_customer.subscription_tier,
        "subscription_expires_at": new_customer.subscription_expires_at,
        "state": new_customer.state,
        "created_at": new_customer.created_at,
        "updated_at": new_customer.updated_at,
        "users": []  # vide si pas encore créé
    }
    # Conversion en Pydantic
    return CustomerRead.model_validate(customer_object_response)
