# Authentication Application - Technical Debt

This document outlines technical debt, security concerns, and recommendations for improving the authentication module.

## Critical Issues

### 1. Missing Exception Handling

**Location:** `minager/auth/exceptions.py`, `minager/auth/managers.py:17`

**Problem:**
- Custom exceptions `UserAlreadyExistsException` and `UserNotFoundException` are defined but never used
- `add_user()` doesn't check for existing email before creation
- Duplicate email attempts will result in database constraint errors instead of proper exceptions
- Authentication failures return `None` or generic `HTTPException` instead of specific exceptions

**Impact:** Poor error handling, unclear error messages, harder debugging

**Recommendation:**
```python
# In UserManager.add_user()
async def add_user(
    self, create_user_data: dict | schemas.UserCreateDataSchema, session: AsyncSession = None
) -> models.User:
    if isinstance(create_user_data, schemas.UserCreateDataSchema):
        create_user_data = create_user_data.model_dump()

    # Check if user exists
    stmt = self.get_query().where(models.User.email == create_user_data['email'])
    existing_user = await self.select_one(stmt, session=session)
    if existing_user:
        raise exceptions.UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User with this email already exists'
        )

    create_user_data['password'] = crypt_context.hash(create_user_data['password'])
    return await self.create(create_user_data, session=session)

# In UserManager.authenticate()
async def authenticate(
    self, data: OAuth2PasswordRequestForm, session: AsyncSession = None
) -> models.User:
    stmt = self.get_query().where(models.User.email == data.username)
    user: models.User = await self.select_one(stmt, session=session)
    if not user:
        raise exceptions.UserNotFoundException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )
    if not self.verify_password(user, data.password):
        raise exceptions.UserNotFoundException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )
    return user
```

**Priority:** HIGH

---

### 2. Insecure Refresh Token Flow

**Location:** `minager/auth/api.py:41-51`

**Problem:**
- Line 48 uses `manager.get()` without `await`, potentially causing async issues
- No validation that refresh token hasn't been revoked
- No check if user account is still active
- Missing validation that token type is actually a refresh token

**Impact:** Security vulnerability, potential async bugs, inability to revoke sessions

**Current Code:**
```python
@auth_router.post('/refresh')
async def refresh_token(
    app: App, request_user: RequestUser, data: schemas.TokenRefreshDataSchema
) -> schemas.Tokens:
    if request_user:
        manager = app.state.users
        manager.validate_token(data.refresh)
        async with manager:
            db_user = manager.get(request_user.get('id'))  # Missing await!
        return manager.make_user_tokens(db_user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
```

**Recommendation:**
```python
@auth_router.post('/refresh')
async def refresh_token(
    app: App, request_user: RequestUser, data: schemas.TokenRefreshDataSchema
) -> schemas.Tokens:
    manager = app.state.users

    # Validate it's a refresh token (not access token)
    payload = manager.validate_token(data.refresh)
    if 'email' in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token type'
        )

    async with manager:
        db_user = await manager.get(request_user.get('id'))  # Fixed: added await
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        # Future: Check if user is active, token not revoked, etc.

    return manager.make_user_tokens(db_user)
```

**Priority:** CRITICAL

---

### 3. Password Validation Missing

**Location:** `minager/auth/managers.py:17`, `minager/auth/schemas.py:6`

**Problem:**
- No password strength requirements enforced
- Can create accounts with weak passwords like "123" or "password"
- No minimum length, complexity, or common password checks

**Impact:** Security vulnerability, accounts easily compromised

**Recommendation:**
```python
# In minager/auth/schemas.py
from pydantic import BaseModel, field_validator
import re

class UserCreateDataSchema(BaseModel):
    email: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        # Optional: check against common passwords list
        return v
```

**Priority:** HIGH

---

### 4. Email Verification Not Implemented

**Location:** `minager/auth/models.py:20`

**Problem:**
- `is_email_verified` field exists but is never set to `True`
- No email verification workflow implemented
- Users can use accounts without verifying email ownership
- No endpoint to send verification emails or verify tokens

**Impact:** Security risk (account takeover), spam accounts, email spoofing

**Recommendation:**
```python
# Add endpoints for email verification
@user_router.post('/verify-email/send')
async def send_verification_email(app: App, user: RequestDBUser):
    # Generate verification token
    # Send email with verification link
    pass

@user_router.post('/verify-email/confirm')
async def confirm_email(app: App, token: str):
    # Validate token
    # Set is_email_verified = True
    pass

# Optionally block unverified users from certain actions
@some_router.post('/protected-action')
async def protected_action(user: RequestDBUser):
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Email verification required'
        )
```

**Priority:** MEDIUM

---

## Security Concerns

### 5. No Rate Limiting

**Location:** All auth endpoints

**Problem:**
- Login endpoint vulnerable to brute force attacks
- Token refresh can be spammed
- User registration can be abused
- No protection against automated attacks

**Impact:** Account compromise, resource exhaustion, spam accounts

**Recommendation:**
```python
# Install: pip install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@auth_router.post('/token')
@limiter.limit("5/minute")  # 5 attempts per minute
async def get_token(request: Request, app: App, data: OAuth2PasswordRequestForm = Depends()):
    # ... existing code
    pass

@user_router.post('/')
@limiter.limit("3/hour")  # 3 registrations per hour per IP
async def create_user(request: Request, app: App, data: schemas.UserCreateDataSchema):
    # ... existing code
    pass
```

**Priority:** HIGH

---

### 6. Weak Token Payload

**Location:** `minager/auth/managers.py:52`

**Problem:**
- Access tokens contain full user data (id, email, is_email_verified)
- Larger tokens increase bandwidth and exposure if leaked
- Email in token can be used for profiling if token is intercepted

**Impact:** Privacy concern, increased token size, information disclosure

**Recommendation:**
```python
def make_user_tokens(self, user: models.User) -> schemas.Tokens:
    secret_key = config.secret_key.get_secret_value()

    # Minimal access token payload
    access_token_data = {
        'sub': str(user.id),  # Subject: user ID only
        'type': 'access'
    }
    access_expires = datetime.now(UTC) + timedelta(minutes=config.access_token_expire)
    access_token_data['exp'] = utils.to_unix_timestamp(access_expires.timestamp())
    access = encode(access_token_data, secret_key, algorithm=config.jwt_hashing_algorithm)

    # Minimal refresh token
    refresh_token_data = {
        'sub': str(user.id),
        'type': 'refresh'
    }
    refresh_expires = datetime.now(UTC) + timedelta(days=config.refresh_token_expire)
    refresh_token_data['exp'] = utils.to_unix_timestamp(refresh_expires.timestamp())
    refresh = encode(refresh_token_data, secret_key, algorithm=config.jwt_hashing_algorithm)

    return schemas.Tokens(access_token=access, refresh_token=refresh)
```

**Priority:** MEDIUM

---

### 7. No Token Revocation

**Location:** Token validation system

**Problem:**
- No way to invalidate tokens before expiration
- Cannot implement logout functionality
- Compromised tokens remain valid until expiry
- No session management

**Impact:** Security vulnerability, cannot revoke compromised sessions

**Recommendation:**
```python
# Option 1: Token blacklist (Redis-based)
class UserManager(PostgresDatabaseManager[models.User]):
    def __init__(self, *args, redis_client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = redis_client

    async def revoke_token(self, token: str):
        payload = self.validate_token(token)
        exp = payload.get('exp')
        ttl = exp - int(datetime.now(UTC).timestamp())
        await self.redis.setex(f'revoked_token:{token}', ttl, '1')

    def validate_token(self, token: str) -> dict:
        # Check if revoked
        if self.redis and await self.redis.exists(f'revoked_token:{token}'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token has been revoked'
            )
        # ... existing validation
        pass

# Option 2: Database-backed sessions
# Add session table with user_id, token_hash, expires_at, revoked
```

**Priority:** MEDIUM

---

### 8. Missing Audit Logging

**Location:** All authentication operations

**Problem:**
- No logging of authentication events
- Failed login attempts not tracked
- Cannot detect suspicious activity or brute force attempts
- No audit trail for security investigations

**Impact:** Cannot monitor security, detect attacks, or investigate incidents

**Recommendation:**
```python
import logging

audit_logger = logging.getLogger('audit.auth')

@auth_router.post('/token')
async def get_token(request: Request, app: App, data: OAuth2PasswordRequestForm = Depends()):
    manager = app.state.users
    try:
        async with manager:
            user = await manager.authenticate(data)

        audit_logger.info(
            'Login successful',
            extra={
                'user_id': str(user.id),
                'email': user.email,
                'ip': request.client.host,
                'user_agent': request.headers.get('user-agent')
            }
        )
        return manager.make_user_tokens(user)
    except Exception as e:
        audit_logger.warning(
            'Login failed',
            extra={
                'email': data.username,
                'ip': request.client.host,
                'reason': str(e)
            }
        )
        raise
```

**Priority:** MEDIUM

---

## Architecture Issues

### 9. Commented Code

**Location:** `minager/auth/models.py:16`

**Problem:**
```python
# is_active: bool = Field(default=True)
```
- Commented field should be implemented or removed
- If accounts can be disabled, this field is essential
- Currently no way to deactivate user accounts

**Impact:** Cannot disable accounts, technical debt

**Recommendation:**
- Implement `is_active` field properly
- Add endpoint to deactivate/reactivate accounts
- Check `is_active` during authentication

**Priority:** LOW

---

### 10. Inconsistent Error Responses

**Location:** `minager/auth/api.py:36`, `minager/auth/api.py:51`

**Problem:**
- Login failure returns `HTTP_403_FORBIDDEN`
- Token refresh failure returns `HTTP_403_FORBIDDEN`
- Should use `HTTP_401_UNAUTHORIZED` for authentication failures
- 403 is for authorization failures (user is authenticated but lacks permission)

**Impact:** Incorrect HTTP semantics, confusing error messages

**Recommendation:**
```python
@auth_router.post('/token')
async def get_token(app: App, data: OAuth2PasswordRequestForm = Depends()) -> schemas.Tokens:
    manager = app.state.users
    async with manager:
        user = await manager.authenticate(data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # Changed from 403
            detail='Invalid credentials',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    return manager.make_user_tokens(user)
```

**Priority:** LOW

---

### 11. Missing Type Hints

**Location:** `minager/core/api/dependencies.py:31`

**Problem:**
```python
RequestDBUser = Annotated[BaseModel, Depends(get_request_db_user)]
```
- Should be `Annotated[models.User, ...]` instead of `BaseModel`
- Reduces IDE support and type safety
- Makes code harder to understand

**Impact:** Poor IDE autocomplete, type checking issues

**Recommendation:**
```python
from minager.auth.models import User

RequestDBUser = Annotated[User, Depends(get_request_db_user)]
```

**Priority:** LOW

---

### 12. Transaction Safety

**Location:** `minager/auth/api.py:13-22`

**Problem:**
- User registration creates records in 3 systems:
  1. PostgreSQL (user)
  2. SurrealDB (palace node)
  3. MongoDB (user profile)
- No rollback mechanism if any operation fails
- Can end up with partial data (user created but no profile)
- Violates atomicity principle

**Impact:** Data inconsistency, orphaned records, corrupted state

**Current Code:**
```python
@user_router.post('/')
async def create_user(app: App, data: schemas.UserCreateDataSchema) -> schemas.UserDetailSchema:
    user_manager = app.state.users
    user_profile_manager = app.state.user_profiles
    palace_manager = app.state.nodes
    async with user_manager, user_profile_manager, palace_manager:
        user = await user_manager.add_user(data)  # Step 1
        node = await palace_manager.create(owner_id=str(user.id), title='Mind Palace')  # Step 2
        await user_profile_manager.create({'user_id': str(user.id), 'palace_root_id': node.id})  # Step 3
    return user
```

**Recommendation:**
```python
# Option 1: Saga pattern with compensating transactions
@user_router.post('/')
async def create_user(app: App, data: schemas.UserCreateDataSchema) -> schemas.UserDetailSchema:
    user_manager = app.state.users
    user_profile_manager = app.state.user_profiles
    palace_manager = app.state.nodes

    user = None
    node = None

    try:
        async with user_manager, user_profile_manager, palace_manager:
            # Step 1: Create user
            user = await user_manager.add_user(data)

            try:
                # Step 2: Create knowledge_tree node
                node = await palace_manager.create(
                    owner_id=str(user.id),
                    title='Mind Palace'
                )

                try:
                    # Step 3: Create user profile
                    await user_profile_manager.create({
                        'user_id': str(user.id),
                        'palace_root_id': node.id
                    })
                except Exception:
                    # Rollback: Delete node
                    if node:
                        await palace_manager.delete(node.id)
                    raise
            except Exception:
                # Rollback: Delete user
                if user:
                    await user_manager.delete(user.id)
                raise

        return user

    except Exception as e:
        audit_logger.error(f'User registration failed: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Registration failed'
        )

# Option 2: Use message queue/event-driven approach
# - Create user in PostgreSQL
# - Emit "user_created" event
# - Other services subscribe and create their records
# - Implement compensating actions for failures
```

**Priority:** HIGH

---

## Code Quality

### 13. Magic Numbers

**Location:** `minager/auth/utils.py:2`

**Problem:**
```python
def to_unix_timestamp(python_timestamp: int | float) -> int:
    return int(python_timestamp * 1000)
```
- Magic number `1000` without explanation
- Unclear why multiplication is needed
- Poor documentation

**Impact:** Code readability, maintainability

**Recommendation:**
```python
def to_unix_timestamp(python_timestamp: int | float) -> int:
    """Convert Python timestamp (seconds) to Unix timestamp (milliseconds).

    Args:
        python_timestamp: Timestamp in seconds since epoch

    Returns:
        Timestamp in milliseconds since epoch
    """
    MILLISECONDS_PER_SECOND = 1000
    return int(python_timestamp * MILLISECONDS_PER_SECOND)
```

**Priority:** LOW

---

### 14. Unused Code

**Location:** `minager/auth/schemas.py:17`

**Problem:**
```python
class LoginData(BaseModel):
    email: str
    password: str
```
- `LoginData` schema defined but never used
- `OAuth2PasswordRequestForm` used instead
- Dead code in codebase

**Impact:** Code clutter, confusion

**Recommendation:**
- Remove unused schema or document why it exists
- If needed for future use, add TODO comment

**Priority:** LOW

---

### 15. Missing Documentation

**Location:** All manager methods and API endpoints

**Problem:**
- No docstrings on `UserManager` methods
- API endpoints lack OpenAPI descriptions
- No `response_model` or `summary` parameters on endpoints
- Makes API harder to use and understand

**Impact:** Poor developer experience, unclear API documentation

**Recommendation:**
```python
class UserManager(PostgresDatabaseManager[models.User]):
    """Manages user authentication and database operations.

    Provides methods for user creation, authentication, password verification,
    JWT token generation, and token validation.
    """

    async def add_user(
        self,
        create_user_data: dict | schemas.UserCreateDataSchema,
        session: AsyncSession = None
    ) -> models.User:
        """Create a new user with hashed password.

        Args:
            create_user_data: User data including email and plain password
            session: Optional database session

        Returns:
            Created user model instance

        Raises:
            UserAlreadyExistsException: If email is already registered
        """
        # ... implementation

@user_router.post(
    '/',
    response_model=schemas.UserDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Register a new user',
    description='Creates a new user account with email and password. '
                'Also creates an associated user profile and Mind Palace root node.',
    responses={
        409: {'description': 'User with email already exists'},
        422: {'description': 'Invalid input data'}
    }
)
async def create_user(
    app: App,
    data: schemas.UserCreateDataSchema
) -> schemas.UserDetailSchema:
    """Register a new user account."""
    # ... implementation
```

**Priority:** MEDIUM

---

## Testing Gaps

### 16. No Test Files Found

**Location:** `tests/auth/` (missing)

**Problem:**
- Auth module lacks test coverage
- No tests for authentication flows
- No tests for token validation
- No tests for password hashing
- Cannot ensure correctness or catch regressions

**Impact:** Risk of bugs, breaking changes undetected

**Recommendation:**
```python
# tests/auth/test_user_manager.py
import pytest
from minager.auth.managers import UserManager
from minager.auth.schemas import UserCreateDataSchema

@pytest.mark.asyncio
async def test_add_user_hashes_password():
    manager = UserManager(db_session)
    data = UserCreateDataSchema(email='test@example.com', password='plaintext')
    user = await manager.add_user(data)
    assert user.password != 'plaintext'
    assert manager.verify_password(user, 'plaintext')

@pytest.mark.asyncio
async def test_authenticate_valid_credentials():
    # ... test implementation

@pytest.mark.asyncio
async def test_authenticate_invalid_credentials():
    # ... test implementation

def test_make_user_tokens():
    # ... test implementation

def test_validate_token_expired():
    # ... test implementation

# tests/auth/test_api.py
def test_create_user_success(client):
    # ... test implementation

def test_create_user_duplicate_email(client):
    # ... test implementation

def test_login_success(client):
    # ... test implementation

def test_login_invalid_credentials(client):
    # ... test implementation

def test_refresh_token(client):
    # ... test implementation
```

**Priority:** HIGH

---

## Potential Enhancements

### 17. Additional Features

**Priority:** LOW (Future work)

- **Password Reset**: Email-based password reset workflow
- **Account Lockout**: Lock account after N failed login attempts
- **Two-Factor Authentication**: TOTP-based 2FA support
- **OAuth2 Providers**: Social login (Google, GitHub, etc.)
- **Remember Me**: Longer-lived tokens for trusted devices
- **Session Management**: View and revoke active sessions
- **Security Questions**: Additional authentication factor
- **Login History**: Track user login times and locations

---

### 18. User Experience Improvements

**Priority:** LOW (Future work)

- **Timestamps**: Add `created_at`, `updated_at`, `last_login` fields
- **Multiple Sessions**: Support concurrent sessions per user
- **Device Management**: Track and manage login devices
- **Account Deletion**: Allow users to delete their accounts
- **Data Export**: GDPR compliance - export user data
- **Password History**: Prevent password reuse
- **Notification Settings**: Email notifications for security events

---

## Priority Summary

### Critical (Fix Immediately)
- Issue #2: Insecure refresh token flow (missing await)

### High Priority (Fix Soon)
- Issue #1: Missing exception handling
- Issue #3: Password validation missing
- Issue #5: No rate limiting
- Issue #12: Transaction safety in registration
- Issue #16: No test coverage

### Medium Priority (Plan to Fix)
- Issue #4: Email verification not implemented
- Issue #6: Weak token payload
- Issue #7: No token revocation
- Issue #8: Missing audit logging
- Issue #15: Missing documentation

### Low Priority (Technical Debt)
- Issue #9: Commented code
- Issue #10: Inconsistent error responses
- Issue #11: Missing type hints
- Issue #13: Magic numbers
- Issue #14: Unused code
- Issue #17-18: Future enhancements

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
1. Fix async await bug in refresh token endpoint
2. Implement proper exception handling
3. Add password validation
4. Implement rate limiting

### Phase 2: Security Hardening (Week 2-3)
1. Add comprehensive test coverage
2. Implement audit logging
3. Fix transaction safety in registration
4. Improve token payload structure

### Phase 3: Feature Completion (Week 4-6)
1. Implement email verification workflow
2. Add token revocation mechanism
3. Complete documentation
4. Refactor code quality issues

### Phase 4: Enhancements (Future)
1. Password reset functionality
2. Two-factor authentication
3. OAuth2 social login
4. Session management UI
