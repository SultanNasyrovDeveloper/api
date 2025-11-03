from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserProfileSchema(BaseModel):
    user_id: str
    name: str
    bio: str
    experience: int
    palace_root_id: str

    model_config = ConfigDict()


class UserProfileEditSchema(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
