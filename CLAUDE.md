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

**Modular monolith:** single repo + deployment, one DB per service domain.

```
minager/
├── core/              # Shared infrastructure — imported by all services
├── node/              # Knowledge tree  →  SurrealDB
├── learning_session/  # Study sessions  →  MongoDB
├── auth/              # Auth/users       →  PostgreSQL
└── user_profile/      # Profiles         →  PostgreSQL
```

### Layered architecture

Every service follows a standard 4-layer architecture. This replaces the old "manager" pattern (a single class per entity that mixed business logic and direct DB access) — managers are being removed service by service.

| Layer | Responsibility | Files |
|---|---|---|
| **Presentation** | Accepts input, renders output. FastAPI routing, request/response shaping. | `api.py`, `schemas.py` |
| **Business** | Business rules, validation, workflows. | `services.py` or `services/` package |
| **Persistence** | Translates between the business layer and the database — query building, data access. | `repositories.py` |
| **Database** | Physical storage. | `core/db/*`, `core/surorm` (transitional, see below), the DB drivers themselves |

**Rules:**

1. **Strict pipeline, no ad-hoc skipping.** `api.py` calls the Business layer; the Business layer calls the Persistence layer. A Repository is never called directly from `api.py`, *except* for resources that are deliberately pure CRUD with no business rules at all — that's a decision made once per resource (there's simply no `services.py` entry for it), not a shortcut taken per-endpoint. The moment a resource needs any business rule, all of its endpoints go through the Business layer.
2. **Repositories return DB/ORM models directly** (SQLAlchemy models for Postgres services, the ORM models of whatever SurrealDB layer `node` ends up on). There are no separate "business objects" or DTOs — the Business layer works with the same model classes the Repository does.
3. **Repositories are concrete classes**, not interfaces/`Protocol`/`ABC`. There's no second implementation to swap in, and tests hit real databases (see Testing below), so an abstraction layer here would have no consumer.
4. **The Business layer accepts Pydantic schemas as input** (e.g. `UserService.register(data: RegisterUserSchema)`) — `api.py` passes through what FastAPI already parsed, no manual unpacking into primitives. But schema usage is **one-directional**: the Business layer never constructs a *response* schema. Translating a model into an API response shape stays in `api.py`, which is the only layer allowed to know what responses look like.
5. **All business-rule validation lives in the Business layer** — uniqueness checks, permission checks, state-transition rules, and also the *interpretation* of DB-level errors (e.g. translating a Postgres unique-constraint `IntegrityError` into "email already registered" is business logic about what the error means, even though the DB enforces it mechanically). `api.py` and Repositories never contain business-rule validation. Presentation-layer/format validation (types, required fields, string length) stays in Pydantic schemas.
6. **Business-layer classes may be a plain `Service` (multiple methods on one class per entity/aggregate) or an extracted `UseCase` (single-purpose class for a complex, multi-step operation).** Both live together in the same `services.py`/`services/` package — `services` always means "Business layer," regardless of which pattern a given piece of logic uses. There is currently no fixed rule for *when* to extract a UseCase instead of adding a method to the Service class — this heuristic is still being defined; don't invent one, ask if it's unclear.

### node: SurORM migration

`node` is migrating from the in-repo `minager/core/surorm/` package (built around a `surorm.Manager` base class) to an external `surorm` package (see `pyproject.toml`), whose native primitive is a `Repository` base class — a direct match for the Persistence layer above. This migration happens *as part of* adopting the layered architecture for `node`, not as a separate effort: `node/managers.py` becomes `node/repositories.py` (classes subclassing the external library's `Repository`), and `node/services/` (today holding `content_generation.py`, `move_node.py` as standalone helpers) becomes the Business layer — those two modules get folded in as Services/UseCases rather than living in a parallel structure.

Until this migration completes for a given piece of `node`, code may still reference the in-repo `core/surorm/` — don't assume it's gone.

SurrealDB graph traversal syntax used throughout `queries.py`:

| Expression | Meaning |
|---|---|
| `->child.out` | Parent node ID |
| `<-child<-node` | Direct child nodes |
| `{..+collect+inclusive}<-child<-node` | All descendants (recursive) |

### Open architectural questions (not yet decided — don't assume an answer)

- **UseCase-extraction heuristic.** When a Service method should be pulled out into its own UseCase class is not yet codified.
- **`core/clients/` → Ports & Adapters rename.** The pattern itself is decided (see "Inter-module communication" below), but the renamed layout (e.g. `core/ports/<domain>/`) and the timing of migrating it across existing clients is not — don't rename ad hoc.
- **Identity port implementation.** Hoisting `JWTService`/`CurrentUserID` out of `auth` into `core` is a stated direction (see "Identity & permissions across services" below), not yet implemented — don't assume `core` already exposes it.

### App startup / dependency wiring

`lifespan.py` opens connections and stores them on `app.state` (surreal, mongo, postgres_engine, etc.). `minager/dependencies.py` exposes them as FastAPI dependency functions (`get_surreal_connection`, `get_postgres_session`). Service `dependencies.py` files inject the right connection into the right Repository/Service and annotate it with `Annotated[..., Depends(...)]`.

There is no Unit-of-Work abstraction — `AsyncSession` (and the equivalent native session/connection type for other DBs) already provides transactional semantics (`commit()`/rollback) and is used directly, injected per-request via `Depends`, same as any other connection.

Tests override these low-level dependency functions via `app.dependency_overrides` — not by mutating global state.

### Inter-module communication: Ports & Adapters

Services must not import from each other directly. `minager/core/clients/` provides the seam, following a Ports & Adapters (hexagonal architecture) pattern:

- **Port** — an abstract contract (e.g. `AbstractPalaceClient`) stating only what a consumer needs from another service. Owned in `core`, not by either side of the call.
- **Contract/DTO** — a stable Pydantic schema crossing the boundary (e.g. `PalaceNode`), deliberately decoupled from the target service's internal models. Never pass a target service's ORM/DB model across this boundary — see rule 4 below, which is about *within*-service layering, not this cross-service seam.
- **Adapter** — a concrete implementation of the port. Today these are in-process (same deployment, same request), calling the target service directly. If a service is ever extracted into its own deployment, a second adapter (HTTP/gRPC) can implement the same port without touching any call site.

**Decided:** adapters call the target service's Business layer (`services.py`), never its Repository/Persistence layer directly. A Repository method assumes a shared process and shared DB connection — neither survives service extraction, so depending on it is debt you will be forced to repay later. A Service method maps ~1:1 onto what a future network endpoint looks like, so today's in-process call becomes tomorrow's adapter swap, not a rewrite.

**Known debt:** `KnowledgeTreeClient` (`minager/core/clients/knowledge_tree/client.py`) predates this decision — it subclasses `KnowledgeTreeNodeManager` directly (inheritance, not composition) and reaches Persistence, not Business. Fix this as part of `node`'s SurORM/layered-architecture migration, not as a standalone task.

`core/clients/` is the current location/naming for this pattern; expect it to be renamed toward a `core/ports/<domain>/{base.py, schemas.py, adapter(s)}` layout once more domains adopt it (see open questions above) — don't rename ad hoc.

### Identity & permissions across services

`node` and `learning_session` currently import `CurrentUserID` directly from `minager.auth.dependencies` — a cross-service import that predates the decision above and still needs fixing. No code has changed as a result of this design pass; this section documents direction, not current state.

Two different concerns are bundled together in `auth/dependencies.py` today:

1. **Token decoding** (`JWTService`, `get_jwt_payload`, `get_current_user_id` → `CurrentUserID`) — pure crypto against the configured secret, no database access. This doesn't structurally belong to `auth`. Planned direction: hoist `JWTService` and identity-only resolution into `core`, so every service (`auth` included) depends on a `core`-owned `CurrentUserID` instead of reaching into `auth`.
2. **Permission/data resolution** (`CurrentUser`, `CurrentVerifiedUser`, `CurrentSuperuser`, `CurrentUserProfile`) — these need real, live data (`is_active`, `is_verified`, `is_superuser`, profile fields) and stay behind a proper Business-layer-backed adapter, per the Ports & Adapters rule above.

**Decided for now:** while this is a single-process monolith, permission checks hit PostgreSQL live on every request via auth's Business layer (`UserService`, `UserProfileService`). This is deliberate, not a stopgap — in-process DB access is cheap here, and it gives correctness for free (e.g. deactivating a user takes effect immediately, no staleness window to reason about). Do not replace this with JWT-embedded permission claims while there is no separate gateway/edge process verifying tokens on the app's behalf — claims-based permissions only pay off once verification genuinely happens somewhere other than the service consuming them.

**Deferred (roadmap, not designed in detail):** if an API gateway or reverse proxy is ever introduced in front of (possibly split-out) services, it would terminate/verify the JWT and inject trusted identity/permission data as request headers. At that point, a second adapter behind the same identity port (e.g. a header-reading adapter) would replace the DB-backed one, and the instant-vs-token-lifetime-bounded revocation tradeoff above would need revisiting. Nothing here should be built preemptively — it has no consumer until a gateway exists.

### Test isolation

**SurrealDB:** A single session-scoped connection is shared across all tests. Each test starts with a `DELETE node; DELETE child;` pre-wipe (the `clean_surreal_data` autouse fixture runs before each test, not after). The test DB name is auto-derived as `test_<production_name>` via a validator in `SurrealConfig`.

**PostgreSQL:** Each test wraps all writes in a transaction that is never committed. The `pg_connection` fixture opens a raw connection and begins an outer transaction; `pg_session` uses `join_transaction_mode='create_savepoint'` so `session.commit()` inside test code only releases a savepoint. Everything rolls back when the fixture tears down.

Both overrides are applied via `app.dependency_overrides` in autouse fixtures in `tests/fixtures/`.

Tests hit real databases — not mocked Repositories. Test file layout mirrors the layer files: `test_api.py` (Presentation), `test_services.py` (Business), `test_repositories.py` (Persistence), per service.

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
3. **Always go through the layers** — Presentation → Business → Persistence → Database. Never query a model directly from `api.py` or a Service; that's the Repository's job. The only exception is a resource with no `services.py` entry at all (pure CRUD, no business rules), where `api.py` may call the Repository directly.
4. **No business objects/DTOs** — Repositories return real DB/ORM models; the Business layer uses those models directly.
5. **Schemas flow one way** — the Business layer may receive a Pydantic schema as input, but never constructs one for a response.
