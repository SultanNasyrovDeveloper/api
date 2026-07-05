from uuid import uuid4

import pytest

from minager.user.repositories import UserProfileRepository, UserRepository
from minager.user.schemas import UserWithProfileSchema

pytestmark = pytest.mark.asyncio


async def test_get_by_email_success(user_repository: UserRepository, test_user: UserWithProfileSchema):
    user = await user_repository.get_by_email(test_user.email)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


async def test_get_by_email_not_found(user_repository: UserRepository):
    user = await user_repository.get_by_email('nonexistent@example.com')
    assert user is None


async def test_get_by_email_deleted_user(user_repository: UserRepository, test_user: UserWithProfileSchema):
    await user_repository.update(str(test_user.id), data={'is_deleted': True})
    user = await user_repository.get_by_email(test_user.email)
    assert user is None


async def test_get_by_username_success(user_repository: UserRepository, test_user: UserWithProfileSchema):
    user = await user_repository.get_by_username(test_user.username)

    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


async def test_get_by_username_not_found(user_repository: UserRepository):
    user = await user_repository.get_by_username('nonexistentuser')
    assert user is None


async def test_get_by_username_deleted_user(
    user_repository: UserRepository, test_user: UserWithProfileSchema
):
    await user_repository.update(str(test_user.id), data={'is_deleted': True})
    user = await user_repository.get_by_username(test_user.username)
    assert user is None


async def test_get_active_user_success(user_repository: UserRepository, test_user: UserWithProfileSchema):
    user = await user_repository.get_active_user(test_user.id)
    assert user is not None
    assert user.id == test_user.id
    assert user.is_active is True
    assert user.is_deleted is False


async def test_get_active_user_inactive(user_repository: UserRepository, test_user: UserWithProfileSchema):
    await user_repository.update(str(test_user.id), data={'is_active': False})
    user = await user_repository.get_active_user(test_user.id)
    assert user is None


async def test_get_active_user_deleted(user_repository: UserRepository, test_user: UserWithProfileSchema):
    await user_repository.update(str(test_user.id), data={'is_deleted': True})
    user = await user_repository.get_active_user(test_user.id)
    assert user is None


async def test_get_active_user_not_found(user_repository: UserRepository):
    user = await user_repository.get_active_user(uuid4())
    assert user is None


async def test_get_by_user_id_success(
    user_profile_repository: UserProfileRepository, test_user: UserWithProfileSchema
):
    profile = await user_profile_repository.get_by_user_id(test_user.id)
    assert profile is not None
    assert profile.user_id == test_user.id
    assert profile.knowledge_tree_root_id == test_user.knowledge_tree_root_id


async def test_get_by_user_id_not_found(user_profile_repository: UserProfileRepository):
    profile = await user_profile_repository.get_by_user_id(uuid4())
    assert profile is None
