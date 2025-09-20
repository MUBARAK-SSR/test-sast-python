import os
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, Response,HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from jwt import ExpiredSignatureError
from starlette import status

from .responses import ReplyJSON
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
SECRET_KEY_ASSOEASE = os.getenv("SECRET_KEY_ASSOEASE")



class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                return self._error_response("Invalid authentications scheme", status_code=status.HTTP_403_FORBIDDEN)
            if not self.verify_token(credentials.credentials):
                return self._error_response("Invalid token", status_code=status.HTTP_403_FORBIDDEN)

            # insertion de l utilisateur connecté dans l' objet request
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user_id = payload.get("user_id")

            return credentials.credentials
        else:
            return self._error_response("Invalid authorization credentials", status_code=status.HTTP_403_FORBIDDEN)

    def verify_token(self, token: str):
        try:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return True
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def _error_response(self, detail: str, status_code: int) -> Response:
        content = ReplyJSON(
            status=status_code,
            code="AUTH_FAILED",
            message=detail
        )
        return Response(content=content, status_code=status_code, media_type="application/json")

    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def decode_jwt(token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def decode_jwt_from_assoease(token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY_ASSOEASE, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @staticmethod
    def is_correct_token_member(token_member: str) -> bool:
        try:
            # Decode et vérifie le token
            payload = jwt.decode(token_member, SECRET_KEY_ASSOEASE, algorithms=[ALGORITHM])
            return True
        except JWTError:
            return False

