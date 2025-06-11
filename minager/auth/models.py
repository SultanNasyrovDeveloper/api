from minager.core.db.models import Field, Model


class User(Model, table=True):
    __tablename__ = 'auth.users'

    id: int = Field(primary_key=True)
    email: str = Field(nullable=False)
    password: str = Field(nullable=True)
