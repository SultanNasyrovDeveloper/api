from sqlmodel import Field


class IdentifierMixin:
    id: int = Field(primary_key=True)


class CreatedMixin:
    pass


class UpdatedMixin:
    pass
