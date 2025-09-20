# Placeholder content for schemas.py
from pydantic import BaseModel, UUID4, ConfigDict


class AuthenticationBase(BaseModel):
    member_token: str


class AuthenticationOut(AuthenticationBase):
    token: str
    model_config = ConfigDict(from_attributes=True)






