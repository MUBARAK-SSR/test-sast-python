from app.services.permissions.middleware.database_provider import DatabaseProvider
from app.config.database import get_db_instance
from fastapi import HTTPException , status , Request , Depends
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

load_dotenv()

def verify_permission_factory(permission_necessaire: str):
    async def verify_permission(
        request: Request,
        db: AsyncSession = Depends(get_db_instance),
        #user_id: UUID = "acc58d60-d703-4cb2-92b6-dfccc7fc441f",
    ):

        # recupération de l utilisateur connecté
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            raise HTTPException(status_code=401, detail="l'identifiant de l utilisateur est abscent")

        print('identifiant de l utilisateur connecté : ', user_id)
        #recupération du client concerné par l action
        sub_client_id = request.headers.get("customer-id")
        if sub_client_id is None:
            raise HTTPException(status_code=400, detail="l'identifiant du client est abscent dans la requete")
        sub_client_id = UUID (sub_client_id)

        db_provider = DatabaseProvider()

        # recupération de la liste des permissions de l utilisateur connecté
        user_permissions_list = await db_provider.get_permissions(user_id, sub_client_id, db)

        # controlle de la permission
        if not db_provider.check_permission(permission_necessaire, user_permissions_list):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non autorisé"
            )
        return True

    return verify_permission


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.getenv("PERMISSION_SECRET_KEY"), algorithms=[os.getenv("PERMISSION_ALGORITHM")])
        client_id: str = payload.get("client_id")
        if client_id is None:
            raise HTTPException(status_code=401, detail="Invalid token backend to backend")
        return client_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token backend to backend")