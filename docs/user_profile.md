# User Profile Application

## Overview

The User Profile application is a simple component of Minager that manages user profile information including display names, usernames, biographical information, and experience points. It serves as a bridge between the authentication system and user-facing profile data, storing references to each user's Mind Palace root node.

The application uses PostgreSQL for profile storage and follows the monoservices architectural pattern, maintaining a loose coupling with the authentication service through user IDs rather than foreign keys.

## Architecture

### Database
- **Database Type**: PostgreSQL
- **Table**: `userprofile` (SQLModel default naming)
- **Connection**: Async SQLAlchemy via `PostgresDatabaseManager`
- **Configuration**: Via core database settings

### Key Components

```
minager/user_profile/
├── api.py                    # FastAPI router and endpoints
├── managers.py               # UserProfileManager for database operations
├── models.py                 # SQLModel UserProfile model
└── schemas.py                # Pydantic models for data validation
```

**Note:** No migrations directory exists, suggesting the table may be auto-created by SQLModel or migrations managed elsewhere.

## Core Concepts

### UserProfile Model

The UserProfile model represents extended user information beyond authentication credentials.

**Fields:**
- `user_id` (str): Primary key, references auth.users.id (max 50 chars)
- `username` (str): Unique username for display/lookup (max 30 chars, indexed)
- `name` (str): Display name or full name (max 250 chars, default: empty string)
- `bio` (str): User biography/description (max 500 chars, default: empty string)
- `experience` (int): Experience points for gamification (default: 0)
- `palace_root_id` (str): Reference to root node in SurrealDB Mind Palace (max 50 chars, required)

**Location:** `minager/user_profile/models.py:4`

**Constraints:**
- Primary key: `user_id`
- Unique constraint: `username`
- Index: `username` (for fast lookups)

### UserProfileManager

The `UserProfileManager` is a minimal extension of `PostgresDatabaseManager` with custom configuration.

**Configuration:**
- `id_field_name`: Set to `'user_id'` (instead of default `'id'`)
- `model_class`: `UserProfile`

**Inherited Methods:**
All standard database operations are inherited from `PostgresDatabaseManager`:
- `get(user_id)`: Retrieve profile by user ID
- `list_(page, per_page)`: Paginated list of profiles
- `create(data)`: Create new profile
- `update(user_id, data)`: Update existing profile
- `delete(user_id)`: Delete profile

**Location:** `minager/user_profile/managers.py:6`

## API Endpoints

### Profile Router (`/user-profiles`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/user-profiles/` | List all profiles (paginated) | No |
| GET | `/user-profiles/my` | Get current user's profile | Yes |
| GET | `/user-profiles/{user_id}` | Get specific user's profile | No |
| PATCH | `/user-profiles/{user_id}` | Update user profile | No* |

**Note:** The PATCH endpoint lacks authorization - any user can update any profile. This is a security vulnerability.

### Endpoint Details

#### List Profiles
```http
GET /user-profiles/?page=1&per_page=10
```

**Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 10): Items per page

**Response:**
```json
{
  "count": 0,
  "page": 1,
  "per_page": 10,
  "results": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John Doe",
      "bio": "Learning enthusiast",
      "experience": 1500,
      "palace_root_id": "node:abc123"
    }
  ]
}
```

**Location:** `minager/user_profile/api.py:11`

**Issue:** The `count` field is hardcoded to `0` instead of returning actual total count.

#### Get My Profile
```http
GET /user-profiles/my
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "bio": "Learning enthusiast",
  "experience": 1500,
  "palace_root_id": "node:abc123"
}
```

**Location:** `minager/user_profile/api.py:21`

#### Get User Profile by ID
```http
GET /user-profiles/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Jane Smith",
  "bio": "Memory knowledge_tree builder",
  "experience": 2300,
  "palace_root_id": "node:xyz789"
}
```

**Location:** `minager/user_profile/api.py:29`

#### Update User Profile
```http
PATCH /user-profiles/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "name": "John Updated",
  "bio": "New bio text"
}
```

**Request Body:** Partial update - only include fields to change
- `name` (optional str): New display name
- `bio` (optional str): New biography

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Updated",
  "bio": "New bio text",
  "experience": 1500,
  "palace_root_id": "node:abc123"
}
```

**Location:** `minager/user_profile/api.py:37`

**Security Issue:** No authentication or authorization check. Any user can update any profile.

## Schemas

### UserProfileSchema

Output schema for user profile data. Contains all profile fields.

```python
{
    "user_id": str,
    "name": str,
    "bio": str,
    "experience": int,
    "palace_root_id": str
}
```

**Location:** `minager/user_profile/schemas.py:6`

### UserProfileEditSchema

Input schema for profile updates. All fields are optional for partial updates.

```python
{
    "name": Optional[str],
    "bio": Optional[str]
}
```

**Notable:** Cannot update `experience` or `palace_root_id` through the API.

**Location:** `minager/user_profile/schemas.py:16`

## Integration with Other Services

### Auth Service Integration

**Profile Creation:**
During user registration in the auth service, a user profile is automatically created:

```python
# In minager/auth/api.py:13-22
user = await user_manager.add_user(data)
node = await palace_manager.create(owner_id=str(user.id), title='Mind Palace')
await user_profile_manager.create({
    'user_id': str(user.id),
    'palace_root_id': node.id
})
```

**Fields Created:**
- `user_id`: From created user
- `palace_root_id`: From created Mind Palace root node
- `username`: **Not set during registration** (potential bug)
- Other fields use defaults (empty strings, 0 experience)

### Palace Node Service Integration

The `palace_root_id` field stores a reference to the user's root node in SurrealDB:
- Created during user registration
- Used to identify the top-level node of a user's Mind Palace
- Never updated after creation
- No cascade delete behavior defined

### Application Lifespan

The `UserProfileManager` is initialized during application startup:

```python
# In minager/lifespan.py:23
app.state.user_profiles = UserProfileManager()

# Entered during startup (line 32)
await app.state.user_profiles.__aenter__()

# Exited during shutdown (line 38)
await app.state.user_profiles.__aexit__(None, None, None)
```

## Data Flow

### User Registration Flow
1. User submits email/password to auth service
2. Auth service creates user in PostgreSQL
3. Auth service creates Mind Palace root node in SurrealDB
4. Auth service creates user profile with `user_id` and `palace_root_id`
5. User profile is created with default values for name, bio, username, experience

### Profile Update Flow
1. Client sends PATCH request with new name/bio
2. API extracts data from `UserProfileEditSchema`
3. Manager updates profile in PostgreSQL
4. Updated profile is returned

### Profile Retrieval Flow
1. Client requests profile by user_id or "my" endpoint
2. For "my" endpoint: JWT token is decoded to get user_id
3. Manager fetches profile from PostgreSQL
4. Profile data is returned as `UserProfileSchema`

## Usage Examples

### Get Current User's Profile
```python
GET /user-profiles/my
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response:
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "",
    "bio": "",
    "experience": 0,
    "palace_root_id": "node:user_palace_root"
}
```

### Update Profile
```python
PATCH /user-profiles/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
    "name": "Alice Johnson",
    "bio": "Passionate learner using spaced repetition"
}

Response:
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Alice Johnson",
    "bio": "Passionate learner using spaced repetition",
    "experience": 0,
    "palace_root_id": "node:user_palace_root"
}
```

### List All Profiles
```python
GET /user-profiles/?page=1&per_page=20

Response:
{
    "count": 0,
    "page": 1,
    "per_page": 20,
    "results": [
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Alice Johnson",
            "bio": "Passionate learner",
            "experience": 1200,
            "palace_root_id": "node:alice_palace"
        },
        {
            "user_id": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Bob Smith",
            "bio": "Memory enthusiast",
            "experience": 800,
            "palace_root_id": "node:bob_palace"
        }
    ]
}
```

## Testing Considerations

### Unit Testing
- Test profile creation with valid data
- Test profile updates with partial data
- Test profile retrieval by user_id
- Test pagination in list endpoint

### Integration Testing
- Test profile creation during user registration
- Test profile updates persist to database
- Test username uniqueness constraint
- Test user_id references valid users

### Security Testing
- **Critical:** Test unauthorized profile updates (currently unprotected)
- Test SQL injection prevention
- Test field length constraints
- Test invalid user_id handling

## Common Patterns

### Accessing User Profile in Endpoints
```python
from minager.core.api.dependencies import RequestUser, App

@router.get('/custom')
async def custom_route(user: RequestUser, app: App):
    manager = app.state.user_profiles
    async with manager:
        profile = await manager.get(user['id'])
    return profile
```

### Updating Profile with Validation
```python
from minager.user_profile.schemas import UserProfileEditSchema

@router.patch('/my-profile')
async def update_my_profile(
    user: RequestUser,
    app: App,
    data: UserProfileEditSchema
):
    manager = app.state.user_profiles
    async with manager:
        updated = await manager.update(
            user['id'],
            data.model_dump(mode='json', exclude_unset=True)
        )
    return updated
```

## Database Schema

### userprofile Table

```sql
CREATE TABLE userprofile (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(250) DEFAULT '',
    bio VARCHAR(500) DEFAULT '',
    experience INTEGER DEFAULT 0,
    palace_root_id VARCHAR(50) NOT NULL
);

CREATE INDEX idx_userprofile_username ON userprofile(username);
```

**Notes:**
- No foreign key to auth.users (following monoservices pattern)
- No foreign key to palace nodes (different database system)
- Username has unique constraint and index for fast lookups

## Known Issues and Limitations

### Security Issues

1. **No Authorization on Update Endpoint** (minager/user_profile/api.py:37)
   - Any user can update any profile
   - Should require authentication and check if `user_id` matches authenticated user
   - Critical security vulnerability

2. **No Authorization on Patch Endpoint** (minager/user_profile/api.py:37)
   - Endpoint accepts `user_id` parameter but doesn't validate ownership
   - Should use `RequestUser` dependency to ensure users can only update their own profiles

### Data Integrity Issues

3. **Missing Username During Registration**
   - Username field is required (unique, indexed) but not set during user registration
   - Will likely cause database constraint errors or default to NULL
   - Should be set during profile creation in auth service

4. **Hardcoded Count in Pagination** (minager/user_profile/api.py:18)
   - `count` field always returns `0` instead of actual total
   - Makes pagination UI impossible to implement correctly
   - Should query total count from database

5. **No Username Uniqueness Validation**
   - Username must be unique but there's no API endpoint to set it
   - No endpoint to check username availability
   - Update endpoint doesn't include username field

### Missing Features

6. **No Username Management**
   - Cannot set or update username through API
   - `UserProfileEditSchema` doesn't include username field
   - Need endpoint for setting initial username and checking availability

7. **No Experience Point Management**
   - Experience field exists but cannot be updated through API
   - No system to award experience points
   - Should be updated when completing learning sessions or reviews

8. **No Profile Picture Support**
   - No field for avatar/profile picture URL
   - Common feature for user profiles

9. **No Privacy Settings**
   - All profiles publicly readable
   - No concept of private/public profiles
   - No field to control profile visibility

10. **No Timestamps**
    - No `created_at` or `updated_at` fields
    - Cannot track when profiles were created or last modified
    - Useful for analytics and audit trails

### Code Quality Issues

11. **Missing Error Handling**
    - No handling for profile not found scenarios
    - No custom exceptions for profile-specific errors
    - Generic database errors exposed to clients

12. **No Input Validation**
    - No validation for bio/name content (profanity, spam, etc.)
    - No username format validation (alphanumeric, special chars, etc.)
    - Field length validation only at database level

13. **Missing Documentation**
    - No docstrings on endpoints
    - No OpenAPI descriptions
    - No examples in API documentation

## Recommended Enhancements

### Immediate Fixes (High Priority)

1. **Add Authorization to Update Endpoint**
```python
@router.patch('/my')
async def update_my_profile(
    user: RequestUser,
    app: App,
    data: schemas.UserProfileEditSchema
) -> schemas.UserProfileSchema:
    manager = app.state.user_profiles
    async with manager:
        updated = await manager.update(user['id'], data.model_dump(mode='json'))
    return updated

# Remove or protect the /{user_id} PATCH endpoint
```

2. **Fix Username Management**
```python
# Add username to creation in auth service
await user_profile_manager.create({
    'user_id': str(user.id),
    'palace_root_id': node.id,
    'username': generate_default_username(user.email)  # or require in registration
})

# Add username to edit schema
class UserProfileEditSchema(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None

# Add username availability endpoint
@router.get('/check-username/{username}')
async def check_username_available(username: str, app: App) -> dict:
    # Check if username exists
    pass
```

3. **Fix Pagination Count**
```python
@router.get('/')
async def list_(
    app: App, page: int = 1, per_page: int = 10
) -> PaginatedResponse[schemas.UserProfileSchema]:
    manager = app.state.user_profiles
    async with manager:
        profiles = await manager.list_(page=page, per_page=per_page)
        total_count = await manager.count()  # Add count method
    return PaginatedResponse(
        count=total_count,
        page=page,
        per_page=per_page,
        results=profiles
    )
```

### Future Enhancements (Medium Priority)

1. **Add Timestamps**
```python
from datetime import datetime
from sqlmodel import Field

class UserProfile(SQLModel, table=True):
    # ... existing fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

2. **Add Experience Point System**
- Create service to award experience points
- Add endpoint to track experience history
- Implement leveling system based on experience

3. **Add Profile Visibility Controls**
```python
class UserProfile(SQLModel, table=True):
    # ... existing fields
    is_public: bool = Field(default=True)
    show_experience: bool = Field(default=True)
```

4. **Add Profile Picture Support**
```python
class UserProfile(SQLModel, table=True):
    # ... existing fields
    avatar_url: Optional[str] = Field(default=None, max_length=500)
```

5. **Add Input Validation**
```python
from pydantic import field_validator
import re

class UserProfileEditSchema(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', v):
            raise ValueError('Username must be 3-30 alphanumeric characters or underscores')
        return v

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) > 500:
            raise ValueError('Bio must be 500 characters or less')
        # Add profanity filter here
        return v
```

## Monitoring and Analytics

Recommended metrics to track:
- Profile completion rate (users with filled name/bio vs empty)
- Username adoption rate
- Average experience points per user
- Profile update frequency
- Most active users by experience

## Best Practices

1. **Always validate ownership** before allowing profile updates
2. **Use RequestUser dependency** to get authenticated user info
3. **Implement proper error handling** for not found scenarios
4. **Validate username format and availability** before accepting
5. **Sanitize user input** for name and bio fields
6. **Index frequently queried fields** (username already indexed)
7. **Use partial updates** via PATCH instead of full replacement

## Migration Considerations

If database schema changes are needed:
1. Create Alembic migration for PostgreSQL
2. Handle existing users without usernames (set defaults)
3. Add timestamps to existing records (use creation date from auth.users if available)
4. Consider data migration scripts for bulk updates
