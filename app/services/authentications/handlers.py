# Placeholder content for handlers.py
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.common.models.Cycle import Cycle
from app.common.models.SubClientUser import SubClientUser
from app.common.models.User import User
from app.services.authentications.schemas import AuthenticationBase
from app.common.auth import JWTBearer
import os

def insecure_example():
    password = "super_secret_password"  # hardcoded secret
    os.system("ls -la")  # command injection risk
    return password


async def authenticate_user(data: AuthenticationBase, db: AsyncSession):

    # decoder et verifier que le token du membre est celui attendu
    if not JWTBearer.is_correct_token_member(data.member_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token du membre invalide"
        )
    #Générer le token d’accès au service
    decoded = JWTBearer.decode_jwt_from_assoease(data.member_token)
    member_nui = decoded.get("MNIU")
    u_key = decoded.get("U-KEY")
    a_key = decoded.get("A-KEY")
    voting = decoded.get("VOTING")
    print(a_key, member_nui)

    if not member_nui:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token payload: member_nui missing"
        )

    # Récupéré l'utilisateur associé au MNIU
    result = await db.execute(select(User).join(SubClientUser, SubClientUser.user_id == User.id).where(User.is_active == True, SubClientUser.member_nui == member_nui,))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found or inactive")

    # Générer un nouveau token
    token = JWTBearer.create_access_token({
        "user_id": str(user.id),
        "member_nui": member_nui,
        "a_key": a_key,
        "u_key": u_key,
        "voting": voting
    })
    print(f"identifiant de l'utilisateur: {user.id}")

    return {"message": "Access granted", "token": token}
