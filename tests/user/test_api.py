from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from minager.app import app
from minager.core.auth.dependencies import jwt_service
from minager.user.dependencies import get_knowledge_tree_client
from minager.user.repositories import UserRepository
from minager.user.schemas import UserCreateDataSchema, UserWithProfileSchema
from minager.user.services import UserService
from tests.conftest import TEST_USER_PASSWORD

pytestmark = pytest.mark.asyncio

AUTH_BASE = '/api/v1/auth'
USERS_BASE = '/api/v1/auth/users'


# ---------------------------------------------------------------------------
# POST /users/signup
# ---------------------------------------------------------------------------


async def test_signup_creates_user(app_client: AsyncClient):
    suffix = uuid4().hex[:8]
    payload = {
        'email': f'new_{suffix}@example.com',
        'username': f'newuser_{suffix}',
        'password': 'StrongPass123!',
    }
    response = await app_client.post(f'{USERS_BASE}/signup', json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == payload['email']
    assert data['username'] == payload['username']
    assert 'hashed_password' not in data


async def test_signup_duplicate_email_returns_400(app_client: AsyncClient, test_user: UserWithProfileSchema):
    payload = {
        'email': test_user.email,
        'username': f'other_{uuid4().hex[:8]}',
        'password': 'StrongPass123!',
    }
    response = await app_client.post(f'{USERS_BASE}/signup', json=payload)
    assert response.status_code == 400


async def test_signup_duplicate_username_returns_400(
    app_client: AsyncClient, test_user: UserWithProfileSchema
):
    payload = {
        'email': f'other_{uuid4().hex[:8]}@example.com',
        'username': test_user.username,
        'password': 'StrongPass123!',
    }
    response = await app_client.post(f'{USERS_BASE}/signup', json=payload)
    assert response.status_code == 400


async def test_signup_missing_fields_returns_422(app_client: AsyncClient):
    response = await app_client.post(f'{USERS_BASE}/signup', json={})
    assert response.status_code == 422


async def test_signup_atomicity_cleans_up_user_on_tree_failure(
    app_client: AsyncClient,
    user_repository: UserRepository,
):
    suffix = uuid4().hex[:8]
    payload = {
        'email': f'atomic_{suffix}@example.com',
        'username': f'atomicuser_{suffix}',
        'password': 'StrongPass123!',
    }
    mock_client = AsyncMock()
    mock_client.create = AsyncMock(return_value=None)
    app.dependency_overrides[get_knowledge_tree_client] = lambda: mock_client
    try:
        response = await app_client.post(f'{USERS_BASE}/signup', json=payload)
    finally:
        app.dependency_overrides.pop(get_knowledge_tree_client)

    assert response.status_code == 400

    user = await user_repository.get_by_email(payload['email'])
    assert user is None


# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------


async def test_get_token_success(app_client: AsyncClient, test_user: UserWithProfileSchema):
    payload = {'username': test_user.email, 'password': TEST_USER_PASSWORD}
    response = await app_client.post(f'{AUTH_BASE}/token', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['token_type'] == 'bearer'


async def test_get_token_wrong_password_returns_401(
    app_client: AsyncClient, test_user: UserWithProfileSchema
):
    payload = {'username': test_user.email, 'password': 'WrongPassword!'}
    response = await app_client.post(f'{AUTH_BASE}/token', json=payload)
    assert response.status_code == 401


async def test_get_token_unknown_email_returns_401(app_client: AsyncClient):
    payload = {'username': 'nobody@example.com', 'password': 'SomePass123!'}
    response = await app_client.post(f'{AUTH_BASE}/token', json=payload)
    assert response.status_code == 401


async def test_get_token_missing_fields_returns_422(app_client: AsyncClient):
    response = await app_client.post(f'{AUTH_BASE}/token', json={})
    assert response.status_code == 422


async def test_get_token_updates_last_login(
    app_client: AsyncClient,
    test_user: UserWithProfileSchema,
    user_repository: UserRepository,
):
    payload = {'username': test_user.email, 'password': TEST_USER_PASSWORD}
    await app_client.post(f'{AUTH_BASE}/token', json=payload)

    user = await user_repository.get_by_email(test_user.email)
    assert user.last_login is not None


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


async def test_refresh_token_success(app_client: AsyncClient, test_user: UserWithProfileSchema):
    refresh_token = jwt_service.create_refresh_token(test_user.id)
    response = await app_client.post(f'{AUTH_BASE}/refresh', json={'refresh_token': refresh_token})
    assert response.status_code == 200
    assert 'access_token' in response.json()


async def test_refresh_token_with_access_token_returns_401(
    app_client: AsyncClient, test_user: UserWithProfileSchema
):
    access_token = jwt_service.create_access_token(test_user.id)
    response = await app_client.post(f'{AUTH_BASE}/refresh', json={'refresh_token': access_token})
    assert response.status_code == 401
    # Verify the error message does NOT leak token type details (C3)
    assert 'Invalid token type' not in response.json()['detail']
    assert 'Expected' not in response.json()['detail']


async def test_refresh_token_invalid_token_returns_401(app_client: AsyncClient):
    response = await app_client.post(f'{AUTH_BASE}/refresh', json={'refresh_token': 'not.a.token'})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


async def test_get_me_success(
    app_client: AsyncClient,
    test_user: UserWithProfileSchema,
    auth_headers: dict,
):
    response = await app_client.get(f'{USERS_BASE}/me', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == str(test_user.id)
    assert data['email'] == test_user.email


async def test_get_me_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f'{USERS_BASE}/me')
    assert response.status_code in (401, 403)


async def test_get_me_knowledge_tree_root_id_nullable(
    app_client: AsyncClient, test_user: UserWithProfileSchema, auth_headers: dict
):
    response = await app_client.get(f'{USERS_BASE}/me', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Field must be present; value may be null (H4)
    assert 'knowledge_tree_root_id' in data


# ---------------------------------------------------------------------------
# PATCH /users/me
# ---------------------------------------------------------------------------


async def test_update_me_email_success(
    app_client: AsyncClient, test_user: UserWithProfileSchema, auth_headers: dict
):
    new_email = f'updated_{uuid4().hex[:8]}@example.com'
    response = await app_client.patch(f'{USERS_BASE}/me', json={'email': new_email}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['email'] == new_email
    assert response.json()['is_verified'] is False


async def test_update_me_duplicate_email_returns_400(
    app_client: AsyncClient,
    test_user: UserWithProfileSchema,
    auth_headers: dict,
    user_service: UserService,
):
    suffix = uuid4().hex[:8]
    other = await user_service.register(
        UserCreateDataSchema(
            email=f'other_{suffix}@example.com',
            username=f'other_{suffix}',
            password='OtherPass123!',
        )
    )
    response = await app_client.patch(f'{USERS_BASE}/me', json={'email': other.email}, headers=auth_headers)
    assert response.status_code == 400
    # No cleanup needed — pg_connection rollback undoes everything after the test


async def test_update_me_requires_auth(app_client: AsyncClient):
    response = await app_client.patch(f'{USERS_BASE}/me', json={'email': 'x@example.com'})
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /users/me/profile
# ---------------------------------------------------------------------------


async def test_get_my_profile_success(
    app_client: AsyncClient, test_user: UserWithProfileSchema, auth_headers: dict
):
    response = await app_client.get(f'{USERS_BASE}/me/profile', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['user_id'] == str(test_user.id)


async def test_get_my_profile_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f'{USERS_BASE}/me/profile')
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /users/me/profile
# ---------------------------------------------------------------------------


async def test_update_my_profile_success(
    app_client: AsyncClient, test_user: UserWithProfileSchema, auth_headers: dict
):
    response = await app_client.patch(
        f'{USERS_BASE}/me/profile',
        json={'display_name': 'New Name', 'bio': 'Hello world'},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data['display_name'] == 'New Name'
    assert data['bio'] == 'Hello world'


async def test_update_my_profile_caller_cannot_set_updated_at(
    app_client: AsyncClient, test_user: UserWithProfileSchema, auth_headers: dict
):
    # Sending a backdated updated_at should be ignored (H3)
    response = await app_client.patch(
        f'{USERS_BASE}/me/profile',
        json={'display_name': 'x', 'updated_at': '2020-01-01T00:00:00Z'},
        headers=auth_headers,
    )
    assert response.status_code == 200
    from datetime import datetime

    updated_at = datetime.fromisoformat(response.json()['updated_at'])
    assert updated_at.year >= 2024


async def test_update_my_profile_requires_auth(app_client: AsyncClient):
    response = await app_client.patch(f'{USERS_BASE}/me/profile', json={'display_name': 'x'})
    assert response.status_code in (401, 403)
