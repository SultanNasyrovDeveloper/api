from uuid import uuid4

import pytest

from minager.auth.models import User


@pytest.fixture
def mock_user():
    """Create a mock regular user."""
    user = User(
        id=uuid4(),
        email='test@example.com',
        username='testuser',
        hashed_password='hashed',
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = User(
        id=uuid4(),
        email='admin@example.com',
        username='admin',
        hashed_password='hashed',
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def mock_inactive_user():
    """Create a mock inactive user."""
    user = User(
        id=uuid4(),
        email='inactive@example.com',
        username='inactive',
        hashed_password='hashed',
        is_active=False,
        is_verified=True,
        is_superuser=False,
    )
    return user


@pytest.fixture
def mock_unverified_user():
    """Create a mock unverified user."""
    user = User(
        id=uuid4(),
        email='unverified@example.com',
        username='unverified',
        hashed_password='hashed',
        is_active=True,
        is_verified=False,
        is_superuser=False,
    )
    return user
