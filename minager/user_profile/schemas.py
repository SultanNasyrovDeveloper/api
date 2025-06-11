from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserProfileSchema(BaseModel):
    user_id: str
    name: str
    bio: str
    experience: int

    model_config = ConfigDict()


class UserProfileEditSchema(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
