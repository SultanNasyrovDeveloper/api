from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    user_id: str = Field(max_length=50, primary_key=True)
    username: str = Field(max_length=30, unique=True, index=True)
    name: str = Field(max_length=250, default='')
    bio: str = Field(max_length=500, default='')

    experience: int = 0

    palace_root_id: str = Field(max_length=50, nullable=False)
