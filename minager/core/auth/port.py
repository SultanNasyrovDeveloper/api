from abc import ABCMeta, abstractmethod
from uuid import UUID

from . import dto


class AbstractUserClient(metaclass=ABCMeta):
    @abstractmethod
    async def get_active_user(self, user_id: UUID) -> dto.User:
        pass

    @abstractmethod
    async def get_user_profile(self, user_id: UUID) -> dto.UserProfile:
        pass
