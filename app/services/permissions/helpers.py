# Placeholder content for handlers.py
from uuid import UUID
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert , select , and_ , or_
from sqlalchemy.orm import selectinload , with_loader_criteria
from app.services.permissions.constants import SourceTypeConstant
from app.common.models.model_permission import ( 
    Permission, RolePermission, Policy, 
    PolicyPermission , RolePolicy
    )
from app.common.models.Role import Role
from app.common.models.User import User
from app.common.models.SubClient import SubClient as Customer
from app.common.models.SubClientUser import SubClientUser as CustomerUser

async def read_one_user_helper( user_id: int ,sub_client_id: int, db: AsyncSession):

    try:
        
        #recherche de l'utilisateur appartenant au client spécifié
        print('*******************************end of helper for read user')

        try:
            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

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
        except Exception as exception:
            raise HTTPException(
                status_code=500,
                detail=f"{str(exception)}"
            )
        
        roles = []
        policies = []
        permissions = []

        #search of roles , policies and permissions of user in customer
        for item in customer_user.user_relations:
            
            #filter roles
            if item.source_type == SourceTypeConstant.role_source_type() :

                result = await db.execute(select(Role).where(Role.id == item.source_id))
                role = result.scalar_one()
                roles.append(role)

            #filter policies
            if item.source_type == SourceTypeConstant.policy_source_type() :
                result = await db.execute(select(Policy).where(Policy.id == item.source_id))
                policy = result.scalar_one()
                policies.append(policy)

            #filter permissions
            if item.source_type == SourceTypeConstant.permission_source_type() :
                result = await db.execute(select(Permission).where(Permission.id == item.source_id))
                permission = result.scalar_one()
                permissions.append(permission)

        #serialize detail of user, including roles, polices, permissions
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
            "is_active": customer_user.user.is_active,
            "created_at": customer_user.user.created_at,
            "updated_at": customer_user.user.updated_at,
            "roles": roles,
            "policies": policies,
            "permissions":permissions
        }

        print('*******************************end of helper for read user')

        return dict(user_detail)
    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite : {str(exception)}"
        )
    

async def read_one_policy_permissions_helper( policy_id: int,  sub_client_id : int , db: AsyncSession):
    try:

        print ('azzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzazazazzzzzzzzzzzzzzzzzzzz : ', policy_id , sub_client_id, db)
        #reseach of the policy of user that we have specify
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

        #extraction of all permissions of policy found
        Permissions = [
            policy_permission.permission.code for policy_permission in policy.policies_permissions
        ]

        print('****************************end of helper for read policies permissions')

        return Permissions

    except Exception as exception:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"une erreur s'est produite : {str(exception)}"
        )
  


async def read_one_role_permissions_helper( role_id: UUID , sub_client_id : UUID, db: AsyncSession ) :
    try:

        #research of roles 
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

        role = result.scalar_one()

        policy_permissions = []
        permissions = []

        #extration of policies and permissions associate at this role
        for item in role.role_relations :

            #extration of permissions associate at one policy of role and meige result to old permissions policies
            if item.source_type == SourceTypeConstant.policy_source_type():

                policy_permissions = policy_permissions + await read_one_policy_permissions_helper (item.policy.id ,sub_client_id, db )
            
            #extration of permissions of role
            elif item.source_type == SourceTypeConstant.permission_source_type():
                permissions.append(item.permission.code)

        #meige of of permissions and return result
        permissions = permissions + policy_permissions

        print('*************************end of helper for read roles permissions')

        return permissions

    except Exception as exception:
        raise HTTPException(
            status_code=500,
            detail= f"une erreur s'est produite : {str(exception)}"
        )