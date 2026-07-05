from uuid import UUID

from minager.core.auth import dto as user_dto
from minager.core.auth.port import AbstractUserClient

from . import exceptions
from .services import UserProfileService, UserService


class UserClient(AbstractUserClient):
    def __init__(
        self,
        user_service: UserService,
        user_profile_service: UserProfileService,
    ):
        self.user_service = user_service
        self.user_profile_service = user_profile_service

    async def get_active_user(self, user_id: UUID) -> user_dto.User:
        user = await self.user_service.get_active_user(user_id)
        if not user:
            raise exceptions.UserNotFoundError
        return user_dto.User(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
        )

    async def get_user_profile(self, user_id: UUID) -> user_dto.UserProfile:
        profile = await self.user_profile_service.get_by_user_id(user_id)
        if not profile:
            raise exceptions.ProfileNotFoundError
        return user_dto.UserProfile(
            user_id=profile.user_id,
            knowledge_tree_root_id=profile.knowledge_tree_root_id,
            display_name=profile.display_name,
            bio=profile.bio,
            experience=profile.experience,
        )
