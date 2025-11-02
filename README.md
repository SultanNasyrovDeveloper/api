CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project Overview
Minager is a mind management tool built with FastAPI that combines spaced repetition learning with a hierarchical node-based knowledge structure ("palace nodes"). The application uses SurrealDB for the palace node graph database, PostgreSQL for user/profile data, and MongoDB for learning sessions.

Development Commands
Running the application
# Install dependencies
poetry install

# Run migrations (SurrealDB)
poetry run migrate upgrade

# Run the FastAPI development server
poetry run fastapi dev minager/app.py
Testing

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test module
poetry run pytest tests/auth/

# Run specific test file
poetry run pytest tests/auth/test_managers.py

# Run with verbose output
poetry run pytest -v

# Run with coverage report
poetry run pytest --cov=minager --cov-report=html
```

## Test Infrastructure

The test suite uses pytest with automatic database setup and teardown for both PostgreSQL and SurrealDB.

### Test Database Setup

**PostgreSQL (`main_db`):**
- Automatically creates `test_<db_name>` database before tests
- Runs Alembic migrations to set up schema
- Each test gets an isolated session with automatic rollback
- Database is dropped after test session completes
- Fixture: `main_db` (session-level)

**SurrealDB (`palace_node_db`):**
- Creates `test_palace` database namespace
- Runs SurORM migrations automatically
- Data is cleaned between tests
- Fixture: `db_client` (session-level)

### Available Test Fixtures

**Database Fixtures** (`tests/conftest.py`):
- `main_db_engine`: PostgreSQL test database engine (session-scoped)
- `main_db_session_factory`: Async session factory for PostgreSQL
- `main_db`: Async database session with automatic rollback per test
- `db_client`: SurrealDB manager for palace nodes
- `app_config`: Test configuration with modified database names

**Auth Fixtures** (`tests/conftest.py`):
- `test_user`: Pre-created user with plain password stored for auth tests
- `api_user`: Mock user data dict for JWT tokens
- `api_client`: TestClient with bearer token authentication
- `unauthorized_api_client`: TestClient without authentication

**Utility Fixtures**:
- `fake`: Faker instance for generating test data
- `monkeypatch_session`: Session-scoped monkeypatch for config modifications

### Test Organization

Tests are organized by application module:
```
tests/
├── conftest.py              # Global fixtures (DB setup, auth)
├── auth/                    # Auth application tests
│   ├── conftest.py         # Auth-specific fixtures
│   ├── test_utils.py       # Utility function tests
│   ├── test_managers.py    # UserManager business logic tests
│   └── test_api.py         # Auth API endpoint tests
└── node/                    # Node application tests (existing)
```

### Test Workflow

1. **Session Setup** (once per test session):
   - Create test databases (`test_minager` for PostgreSQL, `test_palace` for SurrealDB)
   - Run migrations (Alembic for PostgreSQL, SurORM for SurrealDB)
   - Set up database engines and session factories

2. **Per-Test Execution**:
   - Create isolated database session via `main_db` fixture
   - Run test (can use fixtures like `test_user` to create test data)
   - Automatic rollback ensures no data persists between tests
   - SurrealDB data cleaned via DELETE statements

3. **Session Teardown** (after all tests):
   - Close all database connections
   - Drop test databases
   - Clean up resources

### Writing Tests

Example test structure:
```python
async def test_add_user(user_manager, user_data, main_db):
    """Test user creation with password hashing"""
    user = await user_manager.add_user(user_data, session=main_db)

    assert user.email == user_data['email']
    assert user.password != user_data['password']  # Should be hashed
    assert user.password.startswith('$2b$')  # Bcrypt hash
```

**Best Practices**:
- Use fixtures for test data creation (`user_data`, `test_user`)
- Tests are automatically isolated via database rollback
- Mock external dependencies (other services) when testing specific modules
- Use descriptive test names that explain what is being tested
Code quality
# Run pre-commit hooks manually
pre-commit run --all-files

# Format code with black
black minager/

# Sort imports with isort
isort minager/

# Auto-fix unused imports
autoflake8 minager/
Architecture
Multi-Database Setup
The application uses three different database systems:

SurrealDB (palace_node_db): Stores the hierarchical node graph structure with graph traversal capabilities
PostgreSQL (main_db, learning_session_db): Stores user authentication and profile data via SQLAlchemy/SQLModel
MongoDB (learning_session_db): Stores active learning sessions with Motor async driver
Configuration is managed through environment variables with nested delimiter __ (e.g., PALACE_NODE_DB__HOST).

Core Modules
minager/node/: Palace node management (CRUD, tree operations, statistics)

Uses custom SurORM for SurrealDB queries
Implements graph traversal for ancestors/descendants
Handles spaced repetition metadata (difficulty, intervals, next repetition dates)
minager/learning_session/: Learning session management

Implements SuperMemo2 spaced repetition algorithm
MongoDB-based session tracking with queue management
Handles rating-based node scheduling
minager/auth/: User authentication and management

JWT-based authentication
Password hashing with bcrypt
minager/user_profile/: User profile and settings

SurORM - Custom SurrealDB ORM
SurORM is a custom query builder for SurrealDB located in minager/surorm/. Key components:

statements/: Query builders (Select, Create, Update, Delete, Transaction, etc.)
orm/: Model definitions, Manager base class, field types, serializers
functions/: SurrealDB functions (array, datetime, math, object, type)
migrations/: Migration system that discovers and runs migrations from */migrations/ folders
data_model/: Type definitions for SurrealDB fields
Example usage in minager/node/managers.py:

query = (
    surorm.Select('id', 'title', surorm.Alias('parent_id', queries.parent_id_query))
    .from_(surorm.F.type.thing('node', uid))
    .where('owner_id = $owner_id')
)
Request Pattern
Node operations use a request/config pattern (minager/node/requests/):

Each complex operation has a Config (Pydantic model) and Request class
Request classes inherit from AbstractRequest and implement perform()
Examples: CreateChildRequest, MoveNodeRequest, ListNodesRequest
Application Lifespan
minager/lifespan.py manages application startup/shutdown:

Initializes database managers (PalaceNodeManager, UserManager, UserProfileManager, LearningSessionClient)
Tests SurrealDB connection before startup
Stores managers in app.state for request handlers
Ensures proper cleanup on shutdown
Migration System
SurrealDB migrations are in minager/node/migrations/ with pattern XXXX_description.py:

Each migration exports an operations list of MigrationOperation objects
Run with: poetry run migrate upgrade [--app node] [--number 0001]
Migrations are auto-discovered by walking the directory tree
PostgreSQL migrations use Alembic in the alembic/ directory.

Code Formatting
Line length: 100 characters
String quotes: Single quotes preferred (black's skip-string-normalization)
Import sorting: Black-compatible profile (isort)
Pre-commit hooks enforce: black, isort, autoflake8, trailing whitespace, YAML validation
Important Patterns
Manager Pattern
Database operations are encapsulated in manager classes that extend surorm.Manager or handle SQLAlchemy/Motor connections. Managers are async context managers (__aenter__/__aexit__).

Dependency Injection
FastAPI endpoints use custom dependencies from minager/core/api/dependencies.py:

RequestUser: Extracts authenticated user from JWT
App: Provides access to app.state managers
Graph Operations
Palace nodes form a directed graph using a child relation in SurrealDB. Common patterns:

Descendants: node:id.{..+collect+inclusive}<-child<-node
Ancestors: ->child.out traversal with recursion
Subtree queries use custom SurrealDB functions defined in migrations
Spaced Repetition Fields
Node model includes SM-2 algorithm fields:

difficulty, last_rating, repetitions, cpr (consecutive positive ratings)
last_interval, last_repetition, next_optimal_repetition
Learning sessions queue nodes based on next_optimal_repetition dates
