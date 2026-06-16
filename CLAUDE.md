# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server
poetry run uvicorn minager.app:app --reload --host 0.0.0.0 --port 8000

# Tests
poetry run pytest                                          # all tests
poetry run pytest tests/node/test_api.py                  # single file
poetry run pytest tests/node/test_api.py::test_name       # single test
poetry run pytest -x                                      # stop on first failure
poetry run pytest -s                                      # show stdout

# Lint / format
poetry run ruff check .
poetry run ruff check . --fix
poetry run ruff format .

# Migrations
poetry run migrate                        # SurrealDB (custom runner via scripts/migrate.py)
poetry run alembic upgrade head           # PostgreSQL
poetry run alembic revision --autogenerate -m "description"
```

## Architecture

**Monoservices:** single repo + deployment, one DB per service domain.

```
minager/
├── core/              # Shared infrastructure — imported by all services
├── node/              # Knowledge tree  →  SurrealDB
├── learning_session/  # Study sessions  →  MongoDB
├── auth/              # Auth/users       →  PostgreSQL
└── user_profile/      # Profiles         →  PostgreSQL
```

**Layers within each service:** `api.py` → `managers.py` → `services/` → database. API endpoints never touch models directly; they always go through a manager.

### App startup / dependency wiring

`lifespan.py` opens connections and stores them on `app.state` (surreal, mongo, postgres_engine, etc.). `minager/dependencies.py` exposes them as FastAPI dependency functions (`get_surreal_connection`, `get_postgres_session`). Service `dependencies.py` files inject the right connection into the right manager and annotate it with `Annotated[..., Depends(...)]`.

Tests override these low-level dependency functions via `app.dependency_overrides` — not by mutating global state.

### SurORM (custom SurrealDB query builder)

`minager/core/surorm/` is a custom query builder, **not** a traditional ORM. It builds SurrealQL strings via a fluent API and executes them through `surrealdb.AsyncSurreal`. All SurrealDB access goes through `surorm.Manager` subclasses. Key primitives:

- `surorm.Select(...)`, `surorm.Create(...)`, `surorm.Update(...)`, `surorm.Delete()`
- `surorm.F` — SurrealDB function namespace (e.g. `surorm.F.array.first(...)`)
- `surorm.Alias('name', expr)` — computed field in SELECT
- `surorm.F.type.thing('node', id)` — construct a record ID

SurrealDB graph traversal syntax used throughout `queries.py`:

| Expression | Meaning |
|---|---|
| `->child.out` | Parent node ID |
| `<-child<-node` | Direct child nodes |
| `{..+collect+inclusive}<-child<-node` | All descendants (recursive) |

### Cross-service boundary

Services must not import from each other. `minager/core/clients/knowledge_tree/client.py` provides `KnowledgeTreeClient` — currently it is simply `KnowledgeTreeNodeManager` subclassed (same implementation, isolated import path). Use it whenever a non-node service needs to read/write nodes (e.g. `auth/api.py` during signup creates the root node via this client).

### Test isolation

**SurrealDB:** A single session-scoped connection is shared across all tests. Each test starts with a `DELETE node; DELETE child;` pre-wipe (the `clean_surreal_data` autouse fixture runs before each test, not after). The test DB name is auto-derived as `test_<production_name>` via a validator in `SurrealConfig`.

**PostgreSQL:** Each test wraps all writes in a transaction that is never committed. The `pg_connection` fixture opens a raw connection and begins an outer transaction; `pg_session` uses `join_transaction_mode='create_savepoint'` so `session.commit()` inside test code only releases a savepoint. Everything rolls back when the fixture tears down.

Both overrides are applied via `app.dependency_overrides` in autouse fixtures in `tests/fixtures/`.

### Configuration

All config uses `__` as the nested delimiter. `settings.py` at the package root is the single import point for `config`, `postgres_engine`, `postgres_connection_factory`, `surreal`, `mongo`, and auth helpers.

```bash
SECRET_KEY=...
POSTGRES__HOST=... POSTGRES__NAME=... POSTGRES__USER=... POSTGRES__PASSWORD=...
SURREAL__HOST=... SURREAL__PORT=... SURREAL__NAMESPACE=... SURREAL__NAME=...
SURREAL__USERNAME=... SURREAL__PASSWORD=...
MONGO__HOST=... MONGO__PORT=... MONGO__NAME=...
```

## Critical rules

1. **No cross-service imports** — use `minager/core/clients/` for inter-service data access.
2. **No DB foreign keys** — services live in different databases; relationships are logical (string IDs).
3. **Always use managers** — never instantiate or query models directly.
