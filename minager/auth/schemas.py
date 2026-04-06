from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from . import models


class TokenPayloadSchema(BaseModel):
    """Decoded JWT token payload"""

    sub: UUID  # Subject (user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # Token type: 'access' or 'refresh'


class AccessTokenSchema(BaseModel):
    """Access token response"""

    access_token: str
    token_type: str = 'bearer'


class TokenPairSchema(BaseModel):
    """Access + Refresh token pair response"""

    token_type: str = 'bearer'
    access_token: str
    refresh_token: str


class RefreshTokenRequestSchema(BaseModel):
    """Request to refresh access token"""

    refresh_token: str


class UserCreateDataSchema(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    username: str = Field(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')


class UserDetailSchema(BaseModel):
    """User response (public fields)"""

    id: UUID
    username: str
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UserUpdateDataSchema(BaseModel):
    """User update request (auth fields only)"""

    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=100)


class UserProfileDetailSchema(BaseModel):
    """User profile response"""

    user_id: UUID
    display_name: str
    bio: str
    knowledge_tree_root_id: str | None
    experience: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateDataSchema(BaseModel):
    """User profile update request"""

    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserProfileCreateSchema(BaseModel):
    """Internal schema for profile creation"""

    user_id: UUID
    knowledge_tree_root_id: str | None = None


class UserWithProfileSchema(BaseModel):
    """User with profile data (for /me endpoint)"""

    id: UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None

    display_name: str
    bio: str
    knowledge_tree_root_id: str | None
    experience: int

    @classmethod
    def build(cls, user: models.User, profile: models.UserProfile) -> Self:
        return cls(
            id=user.id,
            **user.model_dump(exclude={'id'}),
            **profile.model_dump(exclude={'id', 'user_id', 'created_at', 'updated_at'})
        )


class LoginCredentialsSchema(BaseModel):
    """Login credentials"""

    username: str  # always email for now
    password: str
