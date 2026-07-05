import asyncio
from uuid import uuid4

import pytest
from faker import Faker

from minager.user import exceptions
from minager.user.repositories import UserRepository
from minager.user.schemas import (
    UserCreateDataSchema,
    UserProfileUpdateDataSchema,
    UserUpdateDataSchema,
    UserWithProfileSchema,
)
from minager.user.services import UserProfileService, UserService
from tests.conftest import TEST_USER_PASSWORD

pytestmark = pytest.mark.asyncio


async def test_register_success(user_service: UserService, faker: Faker):
    """Test successful user registration"""
    user_create_data = {
        'email': faker.email(),
        'username': faker.user_name(),
        'password': faker.password(),
    }
    schema = UserCreateDataSchema(**user_create_data)
    user = await user_service.register(schema)

    assert user.id is not None
    assert user.email == user_create_data['email']
    assert user.username == user_create_data['username']
    assert user.hashed_password != user_create_data['password']
    assert user.is_active is True
    assert user.is_verified is False
    assert user.is_superuser is False
    assert user.is_deleted is False
    assert user.last_login is None
    assert user.created_at is not None
    assert user.updated_at is not None


async def test_register_duplicate_email(user_service: UserService, test_user: UserWithProfileSchema):
    schema = UserCreateDataSchema(
        email=test_user.email, username='different_username', password=TEST_USER_PASSWORD
    )
    with pytest.raises(exceptions.EmailAlreadyRegisteredError):
        await user_service.register(schema)


async def test_register_duplicate_username(user_service: UserService, test_user: UserWithProfileSchema):
    schema = UserCreateDataSchema(
        email='different@example.com', username=test_user.username, password=TEST_USER_PASSWORD
    )
    with pytest.raises(exceptions.UsernameAlreadyTakenError):
        await user_service.register(schema)


async def test_authenticate_success(user_service: UserService, test_user: UserWithProfileSchema):
    user = await user_service.authenticate(email=test_user.email, password=TEST_USER_PASSWORD)
    assert user is not None
    assert user.id == test_user.id


async def test_authenticate_wrong_password(user_service: UserService, test_user: UserWithProfileSchema):
    user = await user_service.authenticate(email=test_user.email, password='WrongPassword123!')
    assert user is None


async def test_authenticate_wrong_email(user_service: UserService):
    """Test authentication with non-existent email returns None"""
    user = await user_service.authenticate(email='nonexistent@example.com', password=TEST_USER_PASSWORD)

    assert user is None


async def test_authenticate_inactive_user(
    user_service: UserService, user_repository: UserRepository, test_user: UserWithProfileSchema
):
    await user_repository.update(str(test_user.id), data={'is_active': False})
    user = await user_service.authenticate(email=test_user.email, password=TEST_USER_PASSWORD)
    assert user is None


async def test_authenticate_deleted_user(
    user_service: UserService, user_repository: UserRepository, test_user: UserWithProfileSchema
):
    await user_repository.update(str(test_user.id), data={'is_deleted': True})
    user = await user_service.authenticate(email=test_user.email, password=TEST_USER_PASSWORD)
    assert user is None


async def test_update_last_login(user_service: UserService, test_user: UserWithProfileSchema):
    original_last_login = test_user.last_login
    original_updated_at = test_user.updated_at

    await asyncio.sleep(0.01)

    updated_user = await user_service.update_last_login(test_user.id)

    assert updated_user.last_login is not None
    assert updated_user.last_login != original_last_login
    assert updated_user.updated_at > original_updated_at


async def test_update_last_login_nonexistent_user(user_service: UserService):
    with pytest.raises(exceptions.UserNotFoundError):
        await user_service.update_last_login(uuid4())


async def test_update_user_email_success(user_service: UserService, test_user: UserWithProfileSchema):
    new_email = f'updated_{uuid4().hex[:8]}@example.com'
    update_data = UserUpdateDataSchema(email=new_email)

    updated_user = await user_service.update_user(test_user.id, update_data)

    assert updated_user.email == new_email
    assert updated_user.is_verified is False
    assert updated_user.updated_at >= test_user.updated_at


async def test_update_user_password_success(user_service: UserService, test_user: UserWithProfileSchema):
    new_password = 'NewPassword123!'
    update_data = UserUpdateDataSchema(password=new_password)

    updated_user = await user_service.update_user(test_user.id, update_data)

    assert user_service.verify_password(new_password, updated_user.hashed_password) is True
    assert not user_service.verify_password(TEST_USER_PASSWORD, updated_user.hashed_password)
    assert updated_user.updated_at >= test_user.updated_at


async def test_update_profile_display_name(
    user_profile_service: UserProfileService, test_user: UserWithProfileSchema, faker: Faker
):
    new_name = faker.name()
    update_data = UserProfileUpdateDataSchema(display_name=new_name)
    updated = await user_profile_service.update_profile(test_user.id, update_data)

    assert updated.display_name == new_name
    assert updated.bio == ''


async def test_update_profile_partial_patch_preserves_other_fields(
    user_profile_service: UserProfileService, test_user: UserWithProfileSchema, faker: Faker
):
    await user_profile_service.update_profile(
        test_user.id, UserProfileUpdateDataSchema(display_name='keep_me')
    )
    updated = await user_profile_service.update_profile(
        test_user.id, UserProfileUpdateDataSchema(bio='new bio')
    )
    assert updated.display_name == 'keep_me'
    assert updated.bio == 'new bio'


async def test_update_profile_not_found(user_profile_service: UserProfileService):
    with pytest.raises(exceptions.ProfileNotFoundError):
        await user_profile_service.update_profile(uuid4(), UserProfileUpdateDataSchema(display_name='x'))


async def test_add_experience_increments(
    user_profile_service: UserProfileService, test_user: UserWithProfileSchema
):
    await user_profile_service.add_experience(test_user.id, 10)
    after_first = await user_profile_service.get_by_user_id(test_user.id)
    assert after_first.experience == 10

    await user_profile_service.add_experience(test_user.id, 10)
    after_second = await user_profile_service.get_by_user_id(test_user.id)
    assert after_second.experience == 20


async def test_add_experience_not_found(user_profile_service: UserProfileService):
    with pytest.raises(exceptions.ProfileNotFoundError):
        await user_profile_service.add_experience(uuid4(), 10)
