from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from minager.core.db.postgres.models import Model

from .utils import utc_now_naive


class User(Model, table=True):
    """
    User model for authentication and authorization.
    Contains only auth-related fields. Additional user info stored in UserProfile.
    """

    __tablename__ = 'auth__users'

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False, max_length=50)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    last_login: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now_naive, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now_naive, nullable=False)

    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    is_deleted: bool = Field(default=False)


class UserProfile(Model, table=True):
    __tablename__ = 'auth__user_profiles'

    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key='auth__users.id')
    knowledge_tree_root_id: str | None = Field(default=None, max_length=50)
    display_name: str = Field(default='', max_length=100)
    bio: str = Field(default='', max_length=500)
    created_at: datetime = Field(default_factory=utc_now_naive, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now_naive, nullable=False)

    experience: int = Field(default=0)
