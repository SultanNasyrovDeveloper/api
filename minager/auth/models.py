import uuid

from pydantic import UUID4
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

from minager.core.db.models import Field, Model


class User(Model, table=True):
    __tablename__ = 'auth.users'

    id: uuid.UUID = Field(  # noqa
        primary_key=True,
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
    username: str = Field(max_length=32, unique=True, index=True)
    email: str = Field(unique=True)
    password: str = Field(nullable=True)

    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    is_email_verified: bool = Field(default=False)


class UserProfile(Model, table=True):
    user_id: UUID4 = Field(max_length=50, primary_key=True)
    username: str = Field(max_length=30, unique=True, index=True)
    name: str = Field(max_length=250, default='')
    bio: str = Field(max_length=500, default='')

    experience: int = 0

    palace_root_id: str = Field(max_length=50, nullable=False)
