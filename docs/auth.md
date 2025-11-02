# Authentication Application

## Overview

The Authentication application is a core component of Minager that handles user registration, authentication, and authorization. It implements JWT-based token authentication with access and refresh tokens, password hashing using bcrypt, and integrates with the User Profile and Palace Node services during user registration.

The application uses PostgreSQL for user storage and follows the monoservices architectural pattern, where it operates independently without direct database foreign keys to other services.

## Architecture

### Database
- **Database Type**: PostgreSQL
- **Schema**: `auth`
- **Table**: `auth.users`
- **Connection**: Async SQLAlchemy via `PostgresDatabaseManager`
- **Configuration**: Via core database settings

### Key Components

```
minager/auth/
├── api.py                    # FastAPI routers and endpoints
├── managers.py               # UserManager for database operations
├── models.py                 # SQLAlchemy User model
├── schemas.py                # Pydantic models for data validation
├── exceptions.py             # Custom exception classes
├── utils.py                  # Utility functions (timestamp conversion)
└── migrations/               # Alembic database migrations
    └── 1749725817_add_auth_user_model.py
```

## Core Concepts

### User Model

The User model represents an authenticated user in the system:

**Fields:**
- `id` (UUID): Primary key, auto-generated UUID
- `email` (str): Unique email address, used for authentication
- `password` (str): Bcrypt-hashed password
- `is_email_verified` (bool): Email verification status (default: False)

**Location:** `minager/auth/models.py:9`

### Authentication Flow

#### 1. User Registration

**Endpoint:** `POST /users/`

**Flow:**
1. Client sends email and password
2. Password is hashed using bcrypt via `crypt_context`
3. User record is created in PostgreSQL
4. Mind Palace root node is created in SurrealDB via `palace_manager`
5. User profile is created with reference to palace root node
6. User details are returned (excluding password)

**Code:** `minager/auth/api.py:13`

**Integration Points:**
- User creation: `UserManager.add_user()`
- Palace creation: `palace_manager.create()`
- Profile creation: `user_profile_manager.create()`

#### 2. Token Generation (Login)

**Endpoint:** `POST /token`

**Flow:**
1. Client sends credentials via OAuth2PasswordRequestForm
2. User is authenticated via email lookup and password verification
3. If valid, both access and refresh tokens are generated
4. Tokens are returned to client

**Code:** `minager/auth/api.py:31`

**Token Details:**
- **Access Token**: Contains full user data (except password), expires in minutes
- **Refresh Token**: Contains minimal user data (id only), expires in days
- Both tokens are signed with HS256 algorithm using the application secret key

#### 3. Token Refresh

**Endpoint:** `POST /refresh`

**Flow:**
1. Client sends refresh token
2. Token is validated and decoded
3. User is fetched from database
4. New access and refresh tokens are generated
5. New tokens are returned to client

**Code:** `minager/auth/api.py:41`

#### 4. Current User Retrieval

**Endpoint:** `GET /users/me`

**Flow:**
1. Client sends request with access token in Authorization header
2. Token is validated via `RequestDBUser` dependency
3. User object is fetched from database
4. User details are returned

**Code:** `minager/auth/api.py:26`

### Authentication Dependencies

The application provides three FastAPI dependencies for authentication:

#### RequestUser
Returns the decoded JWT payload as a dictionary without database lookup.

**Usage:** When you need basic user info (id, email) without database query
**Code:** `minager/core/api/dependencies.py:17`

#### RequestDBUser
Returns the full User model instance from the database.

**Usage:** When you need complete user information with database state
**Code:** `minager/core/api/dependencies.py:25`

#### App
Provides access to the FastAPI application instance and its state managers.

**Usage:** To access `app.state.users`, `app.state.nodes`, etc.
**Code:** `minager/core/api/dependencies.py:14`

### UserManager

The `UserManager` class extends `PostgresDatabaseManager` and provides authentication-specific operations.

**Key Methods:**

#### `add_user(create_user_data, session=None)`
Creates a new user with hashed password.
- Accepts dict or `UserCreateDataSchema`
- Hashes password using bcrypt before storage
- Returns created User model

**Code:** `minager/auth/managers.py:17`

#### `authenticate(data, session=None)`
Authenticates user with email and password.
- Accepts `OAuth2PasswordRequestForm`
- Looks up user by email
- Verifies password hash
- Returns User or None

**Code:** `minager/auth/managers.py:25`

#### `verify_password(user, password)`
Verifies a plain password against a user's hashed password.
- Uses `crypt_context.verify()` from passlib
- Returns boolean

**Code:** `minager/auth/managers.py:36`

#### `validate_token(token)`
Validates and decodes a JWT token.
- Decodes using secret key and algorithm
- Raises `HTTPException` for expired or invalid tokens
- Returns decoded payload dict

**Code:** `minager/auth/managers.py:39`

#### `make_user_tokens(user)`
Generates access and refresh tokens for a user.
- Access token: Full user data, short expiration
- Refresh token: Minimal data (id only), long expiration
- Returns `Tokens` schema with both tokens

**Code:** `minager/auth/managers.py:52`

### Schemas

#### UserCreateDataSchema
Input schema for user registration.
```python
{
    "email": "user@example.com",
    "password": "securepassword"
}
```

#### UserDetailSchema
Output schema for user information.
```python
{
    "id": "uuid-string",
    "email": "user@example.com",
    "is_email_verified": false
}
```

#### Tokens
Output schema for authentication tokens.
```python
{
    "access_token": "jwt-string",
    "refresh_token": "jwt-string",
    "token_type": "bearer"
}
```

#### TokenRefreshDataSchema
Input schema for token refresh.
```python
{
    "refresh": "refresh-jwt-string"
}
```

**Location:** `minager/auth/schemas.py`

### Exceptions

#### UserNotFoundException
Raised when a user cannot be found by identifier.

**Location:** `minager/auth/exceptions.py:4`

#### UserAlreadyExistsException
Raised when attempting to create a user with an email that already exists.

**Location:** `minager/auth/exceptions.py:8`

**Note:** These exceptions are defined but not currently used in the codebase.

## Security Features

### Password Hashing
- Uses bcrypt via passlib's `CryptContext`
- Configured in `minager/settings.py`
- Passwords are never stored in plain text
- Hashing occurs in `UserManager.add_user()`

### JWT Tokens
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Secret Key**: Configurable via environment variable
- **Access Token Expiration**: Configurable in minutes (default from config)
- **Refresh Token Expiration**: Configurable in days (default from config)

### Token Payload
- **Access Token**: Contains id, email, is_email_verified, exp
- **Refresh Token**: Contains id, is_email_verified, exp (email excluded for security)

### OAuth2 Bearer Token
- Uses FastAPI's `OAuth2PasswordBearer` security scheme
- Token extracted from `Authorization: Bearer <token>` header
- Configured in `minager/settings.py` as `AuthBearerToken`

## Configuration

Configuration is managed through `minager/settings.py`:

- `secret_key`: Secret key for JWT signing (SecretStr)
- `jwt_hashing_algorithm`: Algorithm for JWT (default: HS256)
- `access_token_expire`: Access token lifetime in minutes
- `refresh_token_expire`: Refresh token lifetime in days
- `crypt_context`: Passlib CryptContext for password hashing

## Database Schema

### auth.users Table

```sql
CREATE TABLE auth.users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password VARCHAR,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE
);
```

**Migration:** `minager/auth/migrations/1749725817_add_auth_user_model.py`

## API Endpoints

### User Router (`/users`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/users/` | Register new user | No |
| GET | `/users/me` | Get current user details | Yes |

### Auth Router

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/token` | Login and get tokens | No |
| POST | `/refresh` | Refresh access token | Yes (Refresh Token) |

## Integration with Other Services

### User Profile Service
During registration, the auth service creates a user profile via `user_profile_manager.create()` with:
- `user_id`: The created user's UUID
- `palace_root_id`: The root node ID of the user's Mind Palace

### Palace Node Service
During registration, the auth service creates a Mind Palace root node via `palace_manager.create()` with:
- `owner_id`: The created user's UUID
- `title`: "Mind Palace"

## Usage Examples

### Register a New User
```python
POST /users/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword123"
}

Response:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "is_email_verified": false
}
```

### Login (Get Tokens)
```python
POST /token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Get Current User
```python
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "is_email_verified": false
}
```

### Refresh Tokens
```python
POST /refresh
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response:
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

## Testing Considerations

### Unit Testing
- Mock `UserManager` database operations
- Test password hashing and verification
- Test token generation and validation
- Test authentication logic

### Integration Testing
- Test full registration flow with database
- Test login with valid/invalid credentials
- Test token refresh with valid/expired tokens
- Test protected endpoint access

### Security Testing
- Test password strength requirements
- Test token expiration handling
- Test invalid token rejection
- Test SQL injection prevention
- Test email uniqueness constraint

## Common Patterns

### Protecting Endpoints
```python
from minager.core.api.dependencies import RequestDBUser

@router.get('/protected')
async def protected_route(user: RequestDBUser):
    # user is automatically validated and fetched from DB
    return {'message': f'Hello {user.email}'}
```

### Accessing Managers
```python
from minager.core.api.dependencies import App

@router.post('/custom')
async def custom_route(app: App):
    user_manager = app.state.users
    async with user_manager:
        # Perform database operations
        user = await user_manager.get(user_id)
    return user
```

## Monitoring and Logging

The authentication system should be monitored for:
- Failed login attempts
- Token expiration rates
- User registration patterns
- Password reset requests (when implemented)

## Future Enhancements

Potential improvements for the auth application:
- Email verification workflow
- Password reset functionality
- Account lockout after failed attempts
- Two-factor authentication (2FA)
- OAuth2 provider integration (Google, GitHub, etc.)
- Session management and revocation
- Audit logging for security events
- Rate limiting on authentication endpoints
