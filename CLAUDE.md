# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Minager is a mind management tool built with FastAPI that combines spaced repetition learning with a hierarchical
node-based knowledge structure ("palace nodes"). The application uses SurrealDB for the palace node graph database,
PostgreSQL for user/profile data, and MongoDB for learning sessions.

## Development Commands

### Running the application
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

### Code quality
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Format code with black
black minager/

# Sort imports with isort
isort minager/

# Auto-fix unused imports
autoflake8 minager/
```

## Architecture
Project follow monoservices architectural pattern. This means that each app except core may be considered as a separate
service. That is why there should be no dependencies between apps in this app. All database relation made without
foreign key usage. Calls to public service api is encapsulated in client classes. Like for example Learning session
database client communicates with nodes application.

### Multi-Database Setup
Because of the usage of architectural pattern all services uses its own database. To make deployment easier
some application share suitable database but it will change later when will be fully in production.
The application uses three different database systems:

1. **SurrealDB** (`palace_node_db`): Stores the hierarchical node graph structure with graph traversal capabilities
2. **PostgreSQL** (`main_db`): Postgresql for all data that do not need
3. **MongoDB** (`learning_session_db`): Stores active learning sessions with Motor async driver

Configuration is managed through environment variables with nested delimiter `__` (e.g., `PALACE_NODE_DB__HOST`).

### Core Modules

- **minager/node/**: Palace node management (CRUD, tree operations, statistics)
  - Uses custom SurORM for SurrealDB queries
  - Implements graph traversal for ancestors/descendants
  - Handles spaced repetition metadata (difficulty, intervals, next repetition dates)

- **minager/learning_session/**: Learning session management
  - Implements SuperMemo2 spaced repetition algorithm
  - MongoDB-based session tracking with queue management
  - Handles rating-based node scheduling

- **minager/auth/**: User authentication and management
  - JWT-based authentication
  - Password hashing with bcrypt

- **minager/user_profile/**: User profile and settings

### SurORM - Custom SurrealDB ORM

SurORM is a custom query builder for SurrealDB located in `minager/surorm/`. Key components:

- **statements/**: Query builders (Select, Create, Update, Delete, Transaction, etc.)
- **orm/**: Model definitions, Manager base class, field types, serializers
- **functions/**: SurrealDB functions (array, datetime, math, object, type)
- **migrations/**: Migration system that discovers and runs migrations from `*/migrations/` folders
- **data_model/**: Type definitions for SurrealDB fields

Example usage in `minager/node/managers.py`:

```python

from minager.core import surorm
from minager.node.queries import parent_id_query

uid = 'node_id'

query = (
    surorm.Select('id', 'title', surorm.Alias('parent_id', parent_id_query))
    .from_(surorm.F.type.thing('node', uid))
    .where('owner_id = $owner_id')
)
```

### Request Pattern

Node operations use a request/config pattern (`minager/node/requests/`):
- Each complex operation has a Config (Pydantic model) and Request class
- Request classes inherit from `AbstractRequest` and implement `perform()`
- Examples: `CreateChildRequest`, `MoveNodeRequest`, `ListNodesRequest`

### Application Lifespan

`minager/lifespan.py` manages application startup/shutdown:
- Initializes database managers (`PalaceNodeManager`, `UserManager`, `UserProfileManager`, `LearningSessionClient`)
- Tests SurrealDB connection before startup
- Stores managers in `app.state` for request handlers
- Ensures proper cleanup on shutdown

### Migration System

SurrealDB migrations are in `minager/node/migrations/` with pattern `XXXX_description.py`:
- Each migration exports an `operations` list of `MigrationOperation` objects
- Run with: `poetry run migrate upgrade [--app node] [--number 0001]`
- Migrations are auto-discovered by walking the directory tree

PostgreSQL migrations use Alembic in the `alembic/` directory.

## Code Formatting

- Line length: 100 characters
- String quotes: Single quotes preferred (black's `skip-string-normalization`)
- Import sorting: Black-compatible profile (isort)
- Pre-commit hooks enforce: black, isort, autoflake8, trailing whitespace, YAML validation

## Important Patterns

### Manager Pattern
Database operations are encapsulated in manager classes that extend `surorm.Manager` or handle SQLAlchemy/Motor connections.
Managers are async context managers (`__aenter__`/`__aexit__`).

### Dependency Injection
FastAPI endpoints use custom dependencies from `minager/core/api/dependencies.py`:
- `RequestUser`: Extracts authenticated user from JWT
- `App`: Provides access to `app.state` managers

### Graph Operations
Palace nodes form a directed graph using a `child` relation in SurrealDB. Common patterns:
- Descendants: `node:id.{..+collect+inclusive}<-child<-node`
- Ancestors: `->child.out` traversal with recursion
- Subtree queries use custom SurrealDB functions defined in migrations

### Spaced Repetition Fields
Node model includes SM-2 algorithm fields:
- `difficulty`, `last_rating`, `repetitions`, `cpr` (consecutive positive ratings)
- `last_interval`, `last_repetition`, `next_optimal_repetition`
- Learning sessions queue nodes based on `next_optimal_repetition` dates
