from datetime import UTC, datetime
from uuid import UUID

from minager.core.auth.password import PasswordService

from . import exceptions, models, schemas, utils
from .repositories import UserProfileRepository, UserRepository


class UserService:
    def __init__(self, repository: UserRepository, password_service: PasswordService):
        self.repository = repository
        self.password_service = password_service

    async def register(self, user_data: schemas.UserCreateDataSchema) -> models.User:
        existing_user = await self.repository.get_by_email(str(user_data.email))
        if existing_user:
            raise exceptions.EmailAlreadyRegisteredError

        existing_username = await self.repository.get_by_username(user_data.username)
        if existing_username:
            raise exceptions.UsernameAlreadyTakenError

        hashed_password = self.password_service.hash_password(user_data.password)
        create_data = {
            'email': str(user_data.email),
            'username': user_data.username,
            'hashed_password': hashed_password,
        }
        return await self.repository.create(create_data)

    async def authenticate(self, email: str, password: str) -> models.User | None:
        user = await self.repository.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not self.password_service.verify_password(password, user.hashed_password):
            return None
        return user

    async def get_active_user(self, user_id: UUID) -> models.User | None:
        return await self.repository.get_active_user(user_id)

    async def update_last_login(self, user_id: UUID) -> models.User:
        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            return await self.repository.update(str(user_id), data={'last_login': now, 'updated_at': now})
        except ValueError:
            raise exceptions.UserNotFoundError from None

    async def update_user(
        self,
        user_id: UUID,
        user_data: schemas.UserUpdateDataSchema,
    ) -> models.User:
        """Update user auth fields (email, password)"""
        user = await self.repository.get(str(user_id))
        if not user:
            raise exceptions.UserNotFoundError

        update_data = {}
        if user_data.email is not None:
            existing = await self.repository.get_by_email(str(user_data.email))
            if existing and existing.id != user_id:
                raise exceptions.EmailAlreadyRegisteredError
            update_data['email'] = user_data.email
            update_data['is_verified'] = False  # Re-verify email after change
        if user_data.password is not None:
            update_data['hashed_password'] = self.password_service.hash_password(user_data.password)
        update_data['updated_at'] = datetime.now(UTC).replace(tzinfo=None)

        return await self.repository.update(str(user_id), data=update_data)

    async def delete(self, user_id: UUID) -> None:
        await self.repository.delete(str(user_id))


class UserProfileService:
    def __init__(self, repository: UserProfileRepository):
        self.repository = repository

    async def create_profile(self, profile_data: schemas.UserProfileCreateSchema) -> models.UserProfile:
        profile = models.UserProfile(
            user_id=profile_data.user_id,
            knowledge_tree_root_id=profile_data.knowledge_tree_root_id,
        )
        return await self.repository.create(profile)

    async def get_by_user_id(self, user_id: UUID) -> models.UserProfile | None:
        return await self.repository.get_by_user_id(user_id)

    async def update_profile(
        self,
        user_id: UUID,
        profile_data: schemas.UserProfileUpdateDataSchema,
    ) -> models.UserProfile:
        profile = await self.repository.get_by_user_id(user_id)
        if not profile:
            raise exceptions.ProfileNotFoundError
        assert profile.id
        update_data = profile_data.model_dump(exclude_none=True)
        update_data['updated_at'] = utils.utc_now_naive()
        return await self.repository.update(profile.id, data=update_data)

    async def add_experience(self, user_id: UUID, amount: int) -> models.UserProfile:
        profile = await self.repository.get_by_user_id(user_id)
        if not profile:
            raise exceptions.ProfileNotFoundError
        assert profile.id
        return await self.repository.update(
            profile.id,
            data={'experience': profile.experience + amount, 'updated_at': utils.utc_now_naive()},
        )
