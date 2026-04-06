from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from minager.core.db.managers import PostgresDatabaseManager
from minager.settings import crypt_context

from . import models, schemas, utils


class UserManager(PostgresDatabaseManager[models.User]):
    """Manager for User model with authentication logic"""

    model_class = models.User

    def get_item_id(self, item: models.User) -> str | None:
        return str(item.id)

    async def get_by_email(
        self, email: str, session: AsyncSession | None = None
    ) -> models.User | None:
        """Get user by email address"""
        stmt = select(models.User).where(
            models.User.email == email, models.User.is_deleted == False
        )
        return await self.select_one(stmt, session=session)

    async def get_by_username(
        self,
        username: str,
        session: AsyncSession | None = None,
    ) -> models.User | None:
        """Get user by username"""
        stmt = select(models.User).where(
            models.User.username == username, models.User.is_deleted == False
        )
        return await self.select_one(stmt, session=session)

    async def get_active_user(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> models.User | None:
        """Get active user by ID (not deleted, is active)"""
        stmt = select(models.User).where(
            models.User.id == user_id,
            models.User.is_deleted == False,
            models.User.is_active == True,
        )
        return await self.select_one(stmt, session=session)

    async def create_user(
        self, user_data: schemas.UserCreateDataSchema, session: AsyncSession | None = None
    ) -> models.User:
        """
        Create new user with hashed password.
        Raises ValueError if email or username already exists.
        """
        existing_user = await self.get_by_email(str(user_data.email), session=session)
        if existing_user:
            raise ValueError('Email already registered')

        existing_username = await self.get_by_username(user_data.username, session=session)
        if existing_username:
            raise ValueError('Username already taken')

        hashed_password = crypt_context.hash(user_data.password)
        create_data = {
            'email': str(user_data.email),
            'username': user_data.username,
            'hashed_password': hashed_password,
        }
        return await self.create(create_data, session=session)

    async def authenticate(
        self, email: str, password: str, session: AsyncSession | None = None
    ) -> models.User | None:
        """
        Authenticate user by email and password.
        Returns User if credentials valid, None otherwise.
        """
        user = await self.get_by_email(email, session=session)

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        if not user.is_active or user.is_deleted:
            return None

        return user

    async def update_last_login(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> models.User:
        now = datetime.now(UTC).replace(tzinfo=None)
        return await self.update(
            str(user_id), data={'last_login': now, 'updated_at': now}, session=session
        )

    async def update_user(
        self,
        user_id: UUID,
        user_data: schemas.UserUpdateDataSchema,
        session: AsyncSession | None = None,
    ) -> models.User:
        """Update user auth fields (email, password)"""
        user = await self.get(str(user_id), session=session)
        if not user:
            raise ValueError('User not found')

        update_data = {}
        if user_data.email is not None:
            existing = await self.get_by_email(str(user_data.email), session=session)
            if existing and existing.id != user_id:
                raise ValueError('Email already registered')
            update_data['email'] = user_data.email
            update_data['is_verified'] = False  # Re-verify email after change
        if user_data.password is not None:
            update_data['hashed_password'] = crypt_context.hash(user_data.password)
        update_data['updated_at'] = datetime.now(UTC).replace(tzinfo=None)

        return await self.update(str(user_id), data=update_data, session=session)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return crypt_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password"""
        return crypt_context.hash(password)


class UserProfileManager(PostgresDatabaseManager[models.UserProfile]):
    """Manager for UserProfile model"""

    model_class = models.UserProfile

    async def create_profile(
        self,
        profile_data: schemas.UserProfileCreateSchema,
        session: AsyncSession | None = None,
    ) -> models.UserProfile:
        profile = models.UserProfile(
            user_id=profile_data.user_id,
            knowledge_tree_root_id=profile_data.knowledge_tree_root_id,
        )
        new_profile = await self.create(profile, session=session)
        return new_profile

    async def get_by_user_id(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> models.UserProfile | None:
        """Get profile by user ID"""
        stmt = select(models.UserProfile).where(models.UserProfile.user_id == user_id)
        return await self.select_one(stmt, session=session)

    async def update_profile(
        self,
        user_id: UUID,
        profile_data: schemas.UserProfileUpdateDataSchema,
        session: AsyncSession | None = None,
    ) -> models.UserProfile:
        """Update user profile"""
        profile = await self.get_by_user_id(user_id, session=session)
        if not profile:
            raise ValueError('Profile not found')
        return await self.update(profile.id, data=profile_data.model_dump(), session=session)

    async def add_experience(
        self, user_id: UUID, amount: int, session: AsyncSession | None = None
    ) -> models.UserProfile:
        """Add experience points to user profile"""
        profile = await self.get_by_user_id(user_id, session=session)
        if not profile:
            raise ValueError('Profile not found')
        return await self.update(
            profile.id,
            data={'experience': amount, 'updated_at': utils.utc_now_naive()},
            session=session,
        )
