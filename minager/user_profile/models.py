from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    user_id: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=250, default='')
    bio: str = Field(max_length=500, default='')
    palace_root_id: str = Field(max_length=50, nullable=False)

    experience: int = 0
