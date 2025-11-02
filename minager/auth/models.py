import uuid

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from minager.core.db.models import Field, Model


class User(Model, table=True):
    __tablename__ = 'auth.users'

    id: uuid.UUID = Field(  # noqa
        primary_key=True,
        default_factory=uuid.uuid4,
        sa_column=Column(PostgresUUID(as_uuid=True), primary_key=True),
    )
    username: str = Field()
    email: str = Field(nullable=False, unique=True)
    password: str = Field(nullable=True)

    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    is_email_verified: bool = Field(default=False)
