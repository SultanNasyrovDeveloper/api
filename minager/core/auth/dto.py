from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    id: UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    is_superuser: bool


class UserProfile(BaseModel):
    user_id: UUID
    knowledge_tree_root_id: str | None
    display_name: str
    bio: str
    experience: int
