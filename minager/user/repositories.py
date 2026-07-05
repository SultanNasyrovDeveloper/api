from uuid import UUID

from sqlalchemy import select

from minager.core.db.postgres.repositories import PostgresRepository

from . import models


class UserRepository(PostgresRepository[models.User]):
    model_class = models.User

    def get_item_id(self, item: models.User) -> str | None:
        return str(item.id)

    async def get_by_email(self, email: str) -> models.User | None:
        stmt = select(models.User).where(models.User.email == email, models.User.is_deleted.is_(False))
        return await self.select_one(stmt)

    async def get_by_username(self, username: str) -> models.User | None:
        stmt = select(models.User).where(models.User.username == username, models.User.is_deleted.is_(False))
        return await self.select_one(stmt)

    async def get_active_user(self, user_id: UUID) -> models.User | None:
        """Get active user by ID (not deleted, is active)"""
        stmt = select(models.User).where(
            models.User.id == user_id,
            models.User.is_deleted.is_(False),
            models.User.is_active.is_(True),
        )
        return await self.select_one(stmt)


class UserProfileRepository(PostgresRepository[models.UserProfile]):
    model_class = models.UserProfile

    async def get_by_user_id(self, user_id: UUID) -> models.UserProfile | None:
        stmt = select(models.UserProfile).where(models.UserProfile.user_id == user_id)
        return await self.select_one(stmt)
