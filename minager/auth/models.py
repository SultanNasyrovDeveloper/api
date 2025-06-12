import uuid

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from minager.core.db.models import Field, Model


class User(Model, table=True):
    __tablename__ = 'auth.users'
    # is_active: bool = Field(default=False)
    id: uuid.UUID = Field(  # noqa
        default_factory=uuid.uuid4, sa_column=Column(PostgresUUID(as_uuid=True), primary_key=True)
    )
    email: str = Field(nullable=False, unique=True)
    password: str = Field(nullable=True)

    is_email_verified: bool = Field(default=False)
