from pydantic import BaseModel, EmailStr


class UserCreateDataSchema(BaseModel):
    email: EmailStr
    password: str


class UserDetailSchema(BaseModel):
    email: EmailStr
