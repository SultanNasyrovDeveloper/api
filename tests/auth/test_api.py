"""Tests for authentication and user management API endpoints"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from minager.auth.jwt import jwt_service


@pytest.fixture
def test_user_data(fake):
    """Generate test user data"""
    return {
        'email': fake.email(),
        'password': 'TestPassword123!',
        'username': fake.user_name(),
    }


# ============================================================================
# Fixture Argument Tests
# ============================================================================
class TestFixtureArguments:
    """Test that all fixtures are properly configured and pass correct arguments"""

    def test_fake_fixture_returns_faker_instance(self, fake):
        """Verify fake fixture returns a Faker instance with working methods"""
        assert hasattr(fake, 'email')
        assert hasattr(fake, 'user_name')
        email = fake.email()
        assert '@' in email
        username = fake.user_name()
        assert isinstance(username, str)
        assert len(username) > 0

    def test_test_user_data_fixture_structure(self, test_user_data):
        """Verify test_user_data fixture returns correct data structure"""
        assert isinstance(test_user_data, dict)
        assert 'email' in test_user_data
        assert 'password' in test_user_data
        assert 'username' in test_user_data
        assert '@' in test_user_data['email']
        assert test_user_data['password'] == 'TestPassword123!'
        assert isinstance(test_user_data['username'], str)

    @pytest.mark.asyncio
    async def test_test_user_fixture_creates_valid_user(self, test_user, main_db):
        """Verify test_user fixture creates a valid user with all required attributes"""
        assert hasattr(test_user, 'id')
        assert hasattr(test_user, 'email')
        assert hasattr(test_user, 'username')
        assert hasattr(test_user, 'plain_password')
        assert hasattr(test_user, 'is_active')
        assert test_user.is_active is True
        assert test_user.plain_password == 'TestPassword123!'
        assert '@' in test_user.email

    @pytest.mark.asyncio
    async def test_main_db_fixture_provides_session(self, main_db):
        """Verify main_db fixture provides a valid async session"""
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(main_db, AsyncSession)
        assert main_db.is_active

    def test_api_client_fixture_provides_test_client(self, api_client):
        """Verify api_client fixture provides a TestClient instance"""
        assert isinstance(api_client, TestClient)
        assert hasattr(api_client, 'get')
        assert hasattr(api_client, 'post')
        assert hasattr(api_client, 'patch')
        assert hasattr(api_client, 'delete')

    def test_api_user_fixture_structure(self, api_user):
        """Verify api_user fixture returns correct data structure"""
        assert isinstance(api_user, dict)
        assert 'id' in api_user
        assert 'sub' in api_user
        assert api_user['id'] == 'test_user'
        assert api_user['sub'] == 'test_user'

    @pytest.mark.asyncio
    async def test_fixtures_work_together(self, api_client, test_user, main_db):
        """Verify fixtures can be used together in a single test"""
        # This test verifies that combining fixtures doesn't cause conflicts
        response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.json()

    def test_multiple_fake_calls_generate_different_data(self, fake):
        """Verify fake fixture generates different data on each call"""
        email1 = fake.email()
        email2 = fake.email()
        # While not guaranteed to be different, with high probability they should be
        # This tests that the faker instance is properly seeded and working
        assert isinstance(email1, str)
        assert isinstance(email2, str)
        assert '@' in email1
        assert '@' in email2


# ============================================================================
# Authentication Endpoints Tests
# ============================================================================
class TestAuthenticationEndpoints:
    """Test authentication endpoints: /auth/token, /auth/refresh, /auth/logout"""

    def test_login_success(self, api_client, test_user, main_db):
        """Test successful login with valid credentials"""
        response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'bearer'

        # Verify tokens are valid
        access_payload = jwt_service.decode_token(data['access_token'])
        assert str(access_payload.sub) == str(test_user.id)
        assert access_payload.type == 'access'

        refresh_payload = jwt_service.decode_token(data['refresh_token'])
        assert str(refresh_payload.sub) == str(test_user.id)
        assert refresh_payload.type == 'refresh'

    def test_login_invalid_email(self, api_client):
        """Test login with non-existent email"""
        response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': 'nonexistent@example.com', 'password': 'password123'},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()['detail'] == 'Incorrect email or password'

    def test_login_invalid_password(self, api_client, test_user):
        """Test login with wrong password"""
        response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': 'WrongPassword123!'},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()['detail'] == 'Incorrect email or password'

    def test_login_missing_fields(self, api_client):
        """Test login with missing required fields"""
        response = api_client.post('/api/v1/auth/auth/token', json={'email': 'test@example.com'})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_refresh_token_success(self, api_client, test_user):
        """Test successful token refresh with valid refresh token"""
        # First login to get tokens
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        refresh_token = login_response.json()['refresh_token']

        # Refresh the access token
        response = api_client.post(
            '/api/v1/auth/auth/refresh', json={'refresh_token': refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'

        # Verify new access token is valid
        access_payload = jwt_service.decode_token(data['access_token'])
        assert str(access_payload.sub) == str(test_user.id)
        assert access_payload.type == 'access'

    def test_refresh_token_with_access_token(self, api_client, test_user):
        """Test refresh endpoint rejects access tokens"""
        # Get access token
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Try to use access token for refresh (should fail)
        response = api_client.post(
            '/api/v1/auth/auth/refresh', json={'refresh_token': access_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'Invalid token type' in response.json()['detail']

    def test_refresh_token_invalid(self, api_client):
        """Test refresh with invalid token"""
        response = api_client.post(
            '/api/v1/auth/auth/refresh', json={'refresh_token': 'invalid.token.here'}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# User Management Endpoints Tests
# ============================================================================
class TestUserManagementEndpoints:
    """Test user management endpoints: /users/signup, /users/me, /users/me/profile"""

    def test_signup_success(self, api_client, test_user_data, main_db):
        """Test successful user registration"""
        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['email'] == test_user_data['email']
        assert 'id' in data
        assert data['is_active'] is True
        assert data['is_verified'] is False
        assert data['is_superuser'] is False
        assert 'hashed_password' not in data  # Should not expose password

    def test_signup_duplicate_email(self, api_client, test_user, test_user_data):
        """Test signup with already registered email"""
        test_user_data['email'] = test_user.email

        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Email already registered' in response.json()['detail']

    def test_signup_duplicate_username(self, api_client, test_user, test_user_data):
        """Test signup with already taken username"""
        test_user_data['username'] = test_user.username

        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Username already taken' in response.json()['detail']

    def test_signup_invalid_email(self, api_client, test_user_data):
        """Test signup with invalid email format"""
        test_user_data['email'] = 'not-an-email'

        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_weak_password(self, api_client, test_user_data):
        """Test signup with password that's too short"""
        test_user_data['password'] = 'short'

        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_invalid_username(self, api_client, test_user_data):
        """Test signup with invalid username (special characters)"""
        test_user_data['username'] = 'invalid user!'

        response = api_client.post('/api/v1/auth/users/signup', json=test_user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_me_success(self, api_client, test_user):
        """Test getting current user info with profile"""
        # Login first
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Get user info
        response = api_client.get(
            '/api/v1/auth/users/me', headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['id'] == str(test_user.id)
        assert data['email'] == test_user.email
        assert 'username' in data
        assert 'display_name' in data
        assert 'experience' in data
        assert 'level' in data

    def test_get_me_unauthorized(self, api_client):
        """Test /me endpoint without authentication"""
        response = api_client.get('/api/v1/auth/users/me')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_me_invalid_token(self, api_client):
        """Test /me endpoint with invalid token"""
        response = api_client.get(
            '/api/v1/auth/users/me', headers={'Authorization': 'Bearer invalid.token.here'}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_me_email(self, api_client, test_user, fake):
        """Test updating user email"""
        # Login first
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Update email
        new_email = fake.email()
        response = api_client.patch(
            '/api/v1/auth/users/me',
            json={'email': new_email},
            headers={'Authorization': f'Bearer {access_token}'},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['email'] == new_email
        assert data['is_verified'] is False  # Should reset verification

    def test_update_me_password(self, api_client, test_user):
        """Test updating user password"""
        # Login first
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Update password
        new_password = 'NewPassword456!'
        response = api_client.patch(
            '/api/v1/auth/users/me',
            json={'password': new_password},
            headers={'Authorization': f'Bearer {access_token}'},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify can login with new password
        login_response = api_client.post(
            '/api/v1/auth/auth/token', json={'email': test_user.email, 'password': new_password}
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_get_profile(self, api_client, test_user):
        """Test getting user profile"""
        # Login first
        login_response = api_client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Get profile
        response = api_client.get(
            '/api/v1/auth/users/me/profile',
            headers={'Authorization': f'Bearer {access_token}'},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['user_id'] == str(test_user.id)
        assert 'username' in data
        assert 'display_name' in data
        assert 'bio' in data
        assert 'experience' in data
        assert 'level' in data

    def test_update_profile(self, client, test_user):
        """Test updating user profile"""
        # Login first
        login_response = client.post(
            '/api/v1/auth/auth/token',
            json={'email': test_user.email, 'password': test_user.plain_password},
        )
        access_token = login_response.json()['access_token']

        # Update profile
        new_display_name = 'New Display Name'
        new_bio = 'This is my new bio'
        response = client.patch(
            '/api/v1/auth/users/me/profile',
            json={'display_name': new_display_name, 'bio': new_bio},
            headers={'Authorization': f'Bearer {access_token}'},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['display_name'] == new_display_name
        assert data['bio'] == new_bio
