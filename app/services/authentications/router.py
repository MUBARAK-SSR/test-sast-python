from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
from app.services.authentications.handlers import authenticate_user
from app.services.authentications.schemas import AuthenticationBase

router = APIRouter(prefix="/v1/api/auth", tags=["Authentication"])

@router.post("/generate_token")
async def generate_token(request: AuthenticationBase, db: AsyncSession = Depends(get_db_instance)):
    return await authenticate_user(request, db)
