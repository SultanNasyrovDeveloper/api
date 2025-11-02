from uuid import UUID

from pydantic import BaseModel


class UserCreateDataSchema(BaseModel):
    email: str
    password: str


class UserDetailSchema(BaseModel):
    id: UUID
    email: str
    is_email_verified: bool


class LoginData(BaseModel):
    email: str
    password: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class TokenRefreshDataSchema(BaseModel):
    refresh: str
