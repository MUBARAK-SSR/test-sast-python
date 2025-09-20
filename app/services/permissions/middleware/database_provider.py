import json
from fastapi_cache import FastAPICache
from app.services.permissions.helpers import read_one_user_helper, read_one_policy_permissions_helper, read_one_role_permissions_helper
from app.services.permissions.constants import expire_cache_time as constant_expire_cache_time

from app.services.permissions.middleware.permission_provider_contract import PermProvider
from typing import Dict, List
from app.config.database import get_db_instance
from fastapi import Depends , HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class DatabaseProvider(PermProvider):

    # fonction pour lister les permissions d un utilisateur afin de voir s'il 
    # détient la permission qui donne accès à la route désiré
    async def get_permissions(self, user_id: int, sub_client_id: int, db) -> List[str]:
        
        try:
            cache_key = f"user_permissions:{sub_client_id}:{user_id}"

            # verifier si la cache n'est pas vide pour utiliser 
            # ses données directement et ne plus aller faire des sélestion dans la bd
            cached_permissions = await FastAPICache.get_backend().get(cache_key)
            if cached_permissions:
                return  json.loads(cached_permissions)
            
            # rechercher les informations sur l utilisateur souhaitant acceder à une route
            user = await read_one_user_helper(user_id, sub_client_id, db)

            print(type(user['permissions']))
            # stocker dans un tableau les permissions directement attachées à l utilisateur
            user_permissions_permission_tab = [
                permission.code for permission in user['permissions']
            ]

            print(user_permissions_permission_tab)
 
            user_policy_permissions_tab = []
            user_role_permissions_tab = []

            #chercher les permissions attaché aux police de l'utilisateur
            for policy in user['policies']:
                user_policy_permissions_tab = user_policy_permissions_tab + await read_one_policy_permissions_helper(policy.id , sub_client_id , db)
            
            #chercher les permissions attaché aux roles de l'utilisateur
            for role in user['roles'] :
                user_role_permissions_tab = user_role_permissions_tab + await read_one_role_permissions_helper(role.id , sub_client_id , db)
            
            # fusionner toutes les permissions de l utilisateur
            user_permissions = [*user_permissions_permission_tab, *user_policy_permissions_tab, *user_role_permissions_tab]
            
            #éliminer les doublons de permissions
            final_user_permissions = list(set([
                *user_permissions_permission_tab,
                *user_policy_permissions_tab,
                *user_role_permissions_tab
            ]))

            #la liste des permissions en cache
            await FastAPICache.get_backend().set(cache_key, json.dumps(final_user_permissions), expire=constant_expire_cache_time)
            
            #retourner les permissions de l utilisateur au middleware pour la verification
            return final_user_permissions
           
        except Exception as exception:
            raise HTTPException(
                status_code= 500,
                detail= f"erreur lors de la lecture des permissions de l'utiliateur {str(exception)}"
            )
        
    #fonction qui verifie si la permission qui donne accès à la route
    #  est présente dans l'ensemble des permissions de l utilisateur
    def check_permission(self, permission_to_access: str, user_permissions) -> bool:
        if permission_to_access in user_permissions :
            return True
        return False
