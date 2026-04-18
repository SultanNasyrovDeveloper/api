# QWEN.md - Minager Project Context

This file provides persistent context for Qwen Code when working with the Minager codebase.

## Project Overview

**Minager** is a mind management tool built with FastAPI that combines spaced repetition learning with a hierarchical node-based knowledge structure ("palace nodes").

### Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **Databases**:
  - SurrealDB - Palace node graph database with graph traversal
  - PostgreSQL - User/profile data (via SQLModel + SQLAlchemy)
  - MongoDB - Learning sessions (via Motor async driver)
- **Package Manager**: Poetry
- **ORM**: Custom SurORM (SurrealDB), SQLModel (PostgreSQL), Motor (MongoDB)

## Development Commands

### Running the Application
```bash
# Install dependencies
poetry install

# Run migrations (SurrealDB)
poetry run migrate upgrade

# Run the FastAPI development server
poetry run fastapi dev minager/app.py
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/node/test_node_api.py

# Run with verbose output
poetry run pytest -v
```

### Code Quality
```bash
# Run pre-commit hooks
pre-commit run --all-files

# Format code
black minager/
isort minager/
autoflake8 minager/
```

## Architecture

### Service-Oriented Pattern
The project follows a **monoservices** architectural pattern. Each app (except `core`) is a separate service with:
- **No direct dependencies** between apps
- **No foreign keys** across services (database relations made without FK)
- **Client classes** for cross-service communication (e.g., `LearningSessionClient` communicates with nodes API)

### Project Structure
```
minager/
├── app.py                 # FastAPI application entry point
├── lifespan.py            # App startup/shutdown, DB manager initialization
├── settings.py            # Pydantic settings with env vars
├── logger.py              # Logging configuration
├── dependencies.py        # Shared FastAPI dependencies
├── core/                  # Shared utilities
│   ├── surorm/            # Custom SurrealDB ORM
│   └── api/               # Core API utilities & dependencies
├── auth/                  # User authentication (JWT, bcrypt)
├── user_profile/          # User profile & settings
├── node/                  # Palace node management
│   ├── managers.py        # SurORM Manager implementations
│   ├── queries.py         # SurrealDB query definitions
│   └── requests/          # Request/Config pattern for operations
├── learning_session/      # Spaced repetition sessions
│   └── (SuperMemo2 algorithm, MongoDB sessions)
├── tag/                   # Tag management
├── message/               # Message handling
└── debate/                # Debate functionality
```

### Multi-Database Setup
Each service uses its own database:
1. **SurrealDB** (`palace_node_db`): Hierarchical node graph with traversal capabilities
2. **PostgreSQL** (`main_db`): User data, authentication, profiles
3. **MongoDB** (`learning_session_db`): Active learning sessions (Motor async driver)

Environment variables use nested delimiter `__` (e.g., `PALACE_NODE_DB__HOST`).

## Key Patterns & Conventions

### SurORM - Custom SurrealDB ORM
Located in `minager/core/surorm/`:
- **statements/**: Query builders (Select, Create, Update, Delete, Transaction)
- **orm/**: Model definitions, Manager base class, field types, serializers
- **functions/**: SurrealDB functions (array, datetime, math, object, type)
- **migrations/**: Auto-discovered migrations from `*/migrations/` folders

Example usage:
```python
from minager.core import surorm
from minager.node.queries import parent_id_query

query = (
    surorm.Select('id', 'title', surorm.Alias('parent_id', parent_id_query))
    .from_(surorm.F.type.thing('node', uid))
    .where('owner_id = $owner_id')
)
```

### Request/Config Pattern
Complex node operations use Config (Pydantic model) + Request classes:
- Config: Validates input data
- Request: Inherits from `AbstractRequest`, implements `perform()` method
- Located in `minager/node/requests/`
- Examples: `CreateChildRequest`, `MoveNodeRequest`, `ListNodesRequest`

### Manager Pattern
- Database operations encapsulated in manager classes
- Extend `surorm.Manager` or handle SQLAlchemy/Motor connections
- Managers are async context managers (`__aenter__`/`__aexit__`)
- Initialized in `lifespan.py` and stored in `app.state`

### Dependency Injection
FastAPI endpoints use custom dependencies from `minager/core/api/dependencies.py`:
- `RequestUser`: Extracts authenticated user from JWT
- `App`: Provides access to `app.state` managers

### Graph Operations (Palace Nodes)
Nodes form a directed graph using `child` relation in SurrealDB:
- **Descendants**: `node:id.{..+collect+inclusive}<-child<-node`
- **Ancestors**: `->child.out` traversal with recursion
- Subtree queries use custom SurrealDB functions from migrations

### Spaced Repetition (SM-2 Algorithm)
Node model includes:
- `difficulty`, `last_rating`, `repetitions`, `cpr` (consecutive positive ratings)
- `last_interval`, `last_repetition`, `next_optimal_repetition`
- Learning sessions queue nodes based on `next_optimal_repetition` dates

## Migration System

### SurrealDB Migrations
- Location: `minager/<service>/migrations/`
- Pattern: `XXXX_description.py` (exports `operations` list of `MigrationOperation`)
- Run: `poetry run migrate upgrade [--app node] [--number 0001]`
- Auto-discovered by walking directory tree

### PostgreSQL Migrations
- Location: `alembic/` directory
- Managed via Alembic standard tools

## Code Style & Formatting

- **Line length**: 110 characters (per pyproject.toml)
- **String quotes**: Single quotes (black's `skip-string-normalization`)
- **Import sorting**: Black-compatible profile (isort)
- **Pre-commit hooks**: black, isort, autoflake8, trailing whitespace, YAML validation

## Testing

- **Framework**: pytest + pytest-asyncio
- **Coverage**: 80% minimum (enforced in pyproject.toml)
- **Tools**: httpx for async test clients, Faker for test data, pytest-mock
- **Config**: All settings in `pyproject.toml` under `[tool.pytest.ini_options]`
- **Location**: `tests/` directory mirroring `minager/` structure

## Application Lifecycle

`minager/lifespan.py` handles:
- Database manager initialization (`PalaceNodeManager`, `UserManager`, etc.)
- SurrealDB connection testing before startup
- Storing managers in `app.state` for request handlers
- Proper cleanup on shutdown

## Important Notes

1. **Service Isolation**: Never create direct imports between service modules (node ↔ learning_session). Use client classes for cross-service calls.
2. **Async-First**: All database operations should be async. Use Motor for MongoDB, asyncpg for PostgreSQL.
3. **No Foreign Keys**: Cross-database relations are logical only, enforced at application level.
4. **Pydantic V2**: All models use Pydantic v2 syntax.
5. **Security**: JWT authentication via fastapi-users + custom JWT handling. Never log or expose secrets.
