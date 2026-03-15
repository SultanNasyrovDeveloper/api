from uuid import uuid4

import pytest
from faker import Faker

from minager.auth.managers import UserManager
from minager.auth.models import User
from minager.auth.schemas import UserCreateDataSchema, UserUpdateDataSchema

pytestmark = pytest.mark.asyncio


async def test_create_user_success(user_manager: UserManager, faker: Faker):
    """Test successful user creation"""
    user_create_data = {
        'email': faker.email(),
        'username': faker.user_name(),
        'password': faker.password(),
    }
    schema = UserCreateDataSchema(**user_create_data)
    user = await user_manager.create_user(schema)

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


async def test_create_user_duplicate_email(user_manager: UserManager, test_user: User):
    schema = UserCreateDataSchema(
        email=test_user.email, username='different_username', password='TestPassword123!'
    )
    with pytest.raises(ValueError, match='Email already registered'):
        await user_manager.create_user(schema)


async def test_create_user_duplicate_username(user_manager: UserManager, test_user: User):
    schema = UserCreateDataSchema(
        email='different@example.com', username=test_user.username, password='TestPassword123!'
    )
    with pytest.raises(ValueError, match='Username already taken'):
        await user_manager.create_user(schema)


async def test_get_by_email_success(user_manager: UserManager, test_user: User):
    user = await user_manager.get_by_email(test_user.email)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


async def test_get_by_email_not_found(user_manager: UserManager):
    user = await user_manager.get_by_email('nonexistent@example.com')
    assert user is None


async def test_get_by_email_deleted_user(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_deleted': True})
    user = await user_manager.get_by_email(test_user.email)
    assert user is None


async def test_get_by_username_success(user_manager: UserManager, test_user: User):
    user = await user_manager.get_by_username(test_user.username)

    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username


async def test_get_by_username_not_found(user_manager: UserManager):
    user = await user_manager.get_by_username('nonexistentuser')
    assert user is None


async def test_get_by_username_deleted_user(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_deleted': True})
    user = await user_manager.get_by_username(test_user.username)
    assert user is None


async def test_get_active_user_success(user_manager: UserManager, test_user: User):
    user = await user_manager.get_active_user(test_user.id)
    assert user is not None
    assert user.id == test_user.id
    assert user.is_active is True
    assert user.is_deleted is False


async def test_get_active_user_inactive(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_active': False})
    user = await user_manager.get_active_user(test_user.id)
    assert user is None


async def test_get_active_user_deleted(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_deleted': True})
    user = await user_manager.get_active_user(test_user.id)
    assert user is None


async def test_get_active_user_not_found(user_manager: UserManager):
    user = await user_manager.get_active_user(uuid4())
    assert user is None


async def test_authenticate_success(user_manager: UserManager, test_user: User):
    user = await user_manager.authenticate(
        email=test_user.email, password='TestPassword123!'  # TODO: Refactor - do not use raw value
    )
    assert user is not None
    assert user.id == test_user.id


async def test_authenticate_wrong_password(user_manager: UserManager, test_user: User):
    user = await user_manager.authenticate(email=test_user.email, password='WrongPassword123!')
    assert user is None


async def test_authenticate_wrong_email(user_manager: UserManager):
    """Test authentication with non-existent email returns None"""
    user = await user_manager.authenticate(
        email='nonexistent@example.com', password='TestPassword123!'
    )

    assert user is None


async def test_authenticate_inactive_user(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_active': False})
    user = await user_manager.authenticate(
        email=test_user.email, password='TestPassword123!'  # TODO: Refactor - do not use raw value
    )
    assert user is None


#


async def test_authenticate_deleted_user(user_manager: UserManager, test_user: User):
    await user_manager.update(str(test_user.id), data={'is_deleted': True})
    user = await user_manager.authenticate(
        email=test_user.email, password='TestPassword123!'  # TODO: Refactor - do not use raw value
    )
    assert user is None


async def test_update_last_login(user_manager: UserManager, test_user: User):
    original_last_login = test_user.last_login
    original_updated_at = test_user.updated_at

    import asyncio

    await asyncio.sleep(0.01)

    updated_user = await user_manager.update_last_login(test_user.id)

    assert updated_user.last_login is not None
    assert updated_user.last_login != original_last_login
    assert updated_user.updated_at > original_updated_at


@pytest.mark.xfail()
async def test_update_last_login_nonexistent_user(user_manager: UserManager):
    with pytest.raises(Exception):  # SQLAlchemy will raise an error
        await user_manager.update_last_login(uuid4())


@pytest.mark.xfail()
async def test_update_user_email_success(user_manager: UserManager, test_user: User):
    new_email = f'updated_{uuid4().hex[:8]}@example.com'
    update_data = UserUpdateDataSchema(email=new_email)

    updated_user = await user_manager.update_user(test_user.id, update_data)

    assert updated_user.email == new_email
    assert updated_user.is_verified is False
    assert updated_user.updated_at > test_user.updated_at


@pytest.mark.xfail()
async def test_update_user_password_success(user_manager: UserManager, test_user: User):
    new_password = 'NewPassword123!'
    update_data = UserUpdateDataSchema(password=new_password)

    updated_user = await user_manager.update_user(test_user.id, update_data)

    assert user_manager.verify_password(new_password, updated_user.hashed_password) is True
    is_old_pass_verified = user_manager.verify_password(
        'TestPassword123!', updated_user.hashed_password  # TODO: Refactor - do not use raw value,
    )
    assert not is_old_pass_verified
    assert updated_user.updated_at > test_user.updated_at
