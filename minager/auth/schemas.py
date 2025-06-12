from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreateDataSchema(BaseModel):
    email: EmailStr
    password: str


class UserDetailSchema(BaseModel):
    id: UUID
    email: EmailStr
    is_email_verified: bool


class LoginData(BaseModel):
    email: EmailStr
    password: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class TokenRefreshDataSchema(BaseModel):
    refresh: str
