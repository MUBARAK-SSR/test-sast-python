# Placeholder content for router.py
from uuid import UUID
from fastapi import APIRouter , Depends,HTTPException ,  Header, Query, Request
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.auth import JWTBearer
from app.config.database import get_db_instance
from app.services.permissions.middleware.middleware import verify_permission_factory, verify_token

from app.services.permissions.schemas import ( 
    CustomerRead, PermissionRead, PermissionListRead, PolicyCreate, PolicyUpdate, RoleCreate,
    RoleListRead , RoleRead, RoleUpdate , UserRead , ListPolicyRead , PolicyRead , PermissionUpdate , 
    PolicyPermissionCreate, RoleRelationRequest , UserRelationRequest,CustomerUserReadFromCustomerUser,
    PermissionCreate,RoleReadForCreation, PolicyReadForCreation
    )


from app.services.permissions.handlers import (
    create_customer, create_policy, create_role_by_customer, generate_token , read_permissions , read_roles , read_one_role, read_users , read_one_user,
    read_policies , read_one_policy, make_policy_config , make_role_config, make_user_config,
    create_permissions, create_role, update_policies_by_customer,update_roles, update_policies,
    update_permissions , create_policy_by_customer, update_roles_by_customer
    )

from app.services.permissions.seeders.database_seeder import updat_all_database , update_system_permissions, update_system_roles

router = APIRouter(prefix="/api/v1", tags=["Permissions"])

'''
    road for seeders execution
'''

@router.get('/system/')
async def update_system__path (db: AsyncSession = Depends(get_db_instance)):
    return await updat_all_database(db)

'''
    roads for create data in database
'''
@router.post('/permissions/', response_model= PermissionRead )
async def ceate_permissions_path (
    permission_object: PermissionCreate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await create_permissions(permission_object, db)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])
    

@router.post('/roles/', response_model= RoleReadForCreation )
async def ceate_role__path (
    request: Request , 
    role_object: RoleCreate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await create_role(role_object, db, request)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])
    

@router.post('/roles/customer', response_model= RoleReadForCreation )
async def ceate_role_by_customer_path (
    request: Request , 
    role_object: RoleCreate , 
    db : AsyncSession = Depends(get_db_instance),
    customer_id: UUID= Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await create_role_by_customer(role_object, db, request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])
    

@router.post('/policies/', response_model= PolicyReadForCreation )
async def ceate_policy_path (
    policy_object: PolicyCreate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await create_policy(policy_object, db)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])

@router.post('/policies/customer', response_model= PolicyReadForCreation )
async def ceate_policy_by_customer_path (
    request : Request , 
    policy_object: PolicyCreate , 
    db : AsyncSession = Depends(get_db_instance), 
    customer_id: UUID= Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await create_policy_by_customer(policy_object, db , request , customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])    

'''
    roads for update data in database
'''
@router.put('/permissions/{permission_id}', response_model= PermissionRead )
async def update_permissions_path (
    request: Request , 
    permission_id : UUID , 
    permission_object: PermissionUpdate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await update_permissions(permission_id, permission_object, db , request)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])
    
@router.put('/roles/{role_id}', response_model= RoleReadForCreation )
async def update_roles_path (
    request : Request , 
    role_id : UUID , 
    role_object: RoleUpdate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await update_roles(role_id, role_object, db, request)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])

@router.put('/roles/customer/{role_id}', response_model= RoleReadForCreation )
async def update_roles_by_customer_path (
    request : Request ,
    role_id : UUID , 
    role_object: RoleUpdate , 
    db : AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await update_roles_by_customer(role_id, role_object, db, request ,customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])

@router.put('/policies/{policy_id}', response_model= PolicyReadForCreation)
async def update_policies_path (
    request : Request, 
    policy_id : UUID , 
    policy_object: PolicyUpdate , 
    db : AsyncSession = Depends(get_db_instance),
    client_id : str = Depends(verify_token)
):
    try:
        return await update_policies(policy_id, policy_object, db, request)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])

@router.put('/policies/customer/{policy_id}', response_model= PolicyReadForCreation)
async def update_policies_path (
    request : Request,
    policy_id : UUID , 
    policy_object: PolicyUpdate , 
    db : AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await update_policies_by_customer(policy_id, policy_object, db, request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])

'''
    roads for read data in database
'''
@router.get('/permissions/', response_model= List[PermissionListRead])
async def get_permission__path (
    db: AsyncSession = Depends(get_db_instance), 
    #autorize : bool = Depends(verify_permission_factory('P3')),
    client_id : str = Depends(verify_token)
):
    try:
        
        return await read_permissions(db)
    
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.get('/roles/', response_model= List[RoleListRead])
async def get_roles__path (
    request:Request , 
    db: AsyncSession = Depends(get_db_instance), 
    customer_id : UUID = Header(...),
    #autorize : bool = Depends(verify_permission_factory('P3')),
    client_id : str = Depends(verify_token)
):
    try:
        return await read_roles(db  , request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.get('/roles/{role_id}', response_model = RoleRead)
async def get_one_role__path (
    request:Request, 
    role_id : UUID ,
    db: AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:

        return await read_one_role( role_id, db, request,customer_id)
    
    except HTTPException as exception:
        raise HTTPException(
            status_code=500,
            detail=f"erreur dans la requete : {str(exception)}"
        )
    except Exception as exception:
        return JSONResponse(
            status_code=500,
            content={"message": f"erreur dans la requete : {str(exception)}"}
        )


@router.get('/users/', response_model= List[CustomerUserReadFromCustomerUser])
async def get_users__path (
    request : Request, 
    db: AsyncSession = Depends(get_db_instance) ,
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await read_users(db , request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.get('/users/{user_id}', response_model= UserRead)
async def get_one_user__path (
    request : Request, 
    user_id : UUID ,
    db: AsyncSession = Depends(get_db_instance), 
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        
        return await read_one_user( user_id,db, request, customer_id)
    
    except HTTPException as exception:
        raise HTTPException(
            status_code=500,
            detail=f"erreur dans la requete : {str(exception)}"
        )
    except Exception as exception:
        return JSONResponse(
            status_code=500,
            content={"message": f"erreur dans la requete : {str(exception)}"}
        )


@router.get('/policies/', response_model= List[ListPolicyRead])
async def get_users__path (
    request: Request , 
    db: AsyncSession = Depends(get_db_instance), 
    customer_id : UUID = Header(...) , 
    client_id : str = Depends(verify_token)
):
    try:
        return await read_policies(db , request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.get('/policies/{policy_id}', response_model= PolicyRead)
async def get_one_policy__path (
    request: Request ,
    policy_id : UUID ,
    db: AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:

        return await read_one_policy( policy_id ,db , request, customer_id)
    
    except HTTPException as exception:
        raise HTTPException(
            status_code=500,
            detail=f"erreur dans la requete : {str(exception)}"
        )
    except Exception as exception:
        return JSONResponse(
            status_code=500,
            content={"message": f"erreur dans la requete : {str(exception)}"}
        )


'''
    road for make configurations of the entities within database
'''
@router.put('/policies-permission/{policy_id}', response_model= PolicyRead)
async def make_policy_config__path (
    request: Request ,
    policy_id : UUID, 
    policy_permission_object: PolicyPermissionCreate ,
    db: AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:

        return await make_policy_config( policy_id,policy_permission_object ,db , request , customer_id)
    
    except HTTPException as exception:
        raise HTTPException(
            status_code=500,
            detail=f"erreur dans la requete : {str(exception)}"
        )
    except Exception as exception:
        return JSONResponse(
            status_code=500,
            content={"message": f"erreur dans la requete : {str(exception)}"}
        )
    

@router.put('/roles-policies-permissions/{role_id}', response_model= RoleRead)
async def make_role_config__path (
    request: Request ,
    role_id: UUID, 
    role_relation_object: RoleRelationRequest ,
    db: AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await make_role_config(role_id ,role_relation_object , db, request , customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.put('/users-roles-permissions/{user_id}', response_model= UserRead)
async def make_user_config__path (
    request: Request ,
    user_id: UUID ,
    role_relation_object: UserRelationRequest ,
    db: AsyncSession = Depends(get_db_instance),
    customer_id : UUID = Header(...),
    client_id : str = Depends(verify_token)
):
    try:
        return await make_user_config(user_id ,role_relation_object , db , request, customer_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content= [f"erreur dans la requete : {str(exception)}"])


@router.get('/generate-token')
async def generate_token_path(request: Request , client_id : str = Header(...)):
    try:
        return await generate_token (request , client_id)
    except Exception as exception:
        return JSONResponse(status_code=500 , content=f"une erreur s'est produite")


@router.post('/customer')
async def create_customer_path (
    customer_object: CustomerRead , 
    db: AsyncSession = Depends(get_db_instance)
):
    return await create_customer(customer_object , db)
