# Minager API

A learning system built around hierarchical knowledge trees and spaced repetition. Organize knowledge as a tree of nodes, then study them through AI-scheduled review sessions powered by the SuperMemo2 algorithm.

## Features

- **Knowledge Tree** — build a hierarchical tree of notes/concepts with lexicographic ordering
- **Spaced Repetition** — SuperMemo2 scheduling with per-node difficulty, interval, and rating tracking
- **Learning Sessions** — queue-based study sessions with configurable traversal strategies
- **AI Content Generation** — generate node content via HuggingFace LLMs
- **JWT Authentication** — access + refresh token pair, bcrypt password hashing

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12) |
| Knowledge Tree | SurrealDB (graph DB) |
| Learning Sessions | MongoDB |
| Users / Auth | PostgreSQL |
| ORM / Migrations | Custom SurORM + SQLAlchemy + Alembic |
| Package Manager | Poetry |

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- SurrealDB
- PostgreSQL
- MongoDB

## Installation

```bash
# Install dependencies
poetry install

# Copy environment config
cp .env.local.example .env.local  # edit with your DB credentials
```

## Configuration

All settings use environment variables with `__` as the nested delimiter.

```bash
# Required
SECRET_KEY=your-secret-key

# PostgreSQL (users / auth)
POSTGRES__HOST=localhost
POSTGRES__PORT=5432
POSTGRES__NAME=minager
POSTGRES__USER=postgres
POSTGRES__PASSWORD=postgres

# SurrealDB (knowledge tree)
SURREAL__HOST=localhost
SURREAL__PORT=8000
SURREAL__NAME=minager
SURREAL__NAMESPACE=minager
SURREAL__USER=root
SURREAL__PASSWORD=root

# MongoDB (learning sessions)
MONGO__HOST=localhost
MONGO__PORT=27017
MONGO__NAME=minager

# Optional
DEBUG=false
HUGGINGFACE_API_TOKEN=hf_...
HUGGINGFACE_LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

## Running

```bash
# Development
poetry run uvicorn minager.app:app --reload --host 0.0.0.0 --port 8000

# Production (Docker)
docker build -t minager-api .
docker run -p 8000:8000 --env-file .env minager-api
```

Interactive API docs are available at `http://localhost:8000/docs`.

## Database Migrations

```bash
# SurrealDB migrations (custom runner)
poetry run migrate

# PostgreSQL migrations (Alembic)
poetry run alembic upgrade head
```

## API Overview

All routes are prefixed with `/api/v1`.

### Authentication — `/auth`

| Method | Path | Description |
|---|---|---|
| `POST` | `/token` | Get JWT access + refresh token pair |
| `POST` | `/refresh` | Exchange refresh token for new access token |

### Users — `/auth/users`

| Method | Path | Description |
|---|---|---|
| `POST` | `/signup` | Register (creates user, profile, and root knowledge tree node) |
| `GET` | `/me` | Get current user with profile |
| `PATCH` | `/me` | Update current user |
| `GET` | `/me/profile` | Get user profile |
| `PATCH` | `/me/profile` | Update user profile |

### Knowledge Tree — `/node/nodes`

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Search nodes (paginated) |
| `GET` | `/{id}` | Get node detail (increments view count) |
| `POST` | `/{id}/add-child` | Add a child node |
| `PATCH` | `/{id}` | Update node fields |
| `DELETE` | `/{id}` | Delete node |
| `POST` | `/{id}/move` | Move node (first-child / last-child / before / after) |
| `GET` | `/{id}/children` | List direct children (paginated) |
| `GET` | `/{id}/subtree` | Get full subtree as nested tree |
| `GET` | `/{id}/subtree/ids` | Get all descendant IDs (limited) |
| `GET` | `/{id}/statistics` | Overall node + subtree quality index |
| `GET` | `/{id}/subtree/statistics` | Subtree aggregate stats |
| `GET` | `/{id}/generate-content` | Generate content via LLM |

### Learning Sessions — `/learning-session/learning-sessions`

| Method | Path | Description |
|---|---|---|
| `GET` | `/active` | Get user's active session |
| `POST` | `/start` | Start a new session on a subtree |
| `POST` | `/{id}/repeat` | Submit rating (0–5) for current node |
| `POST` | `/{id}/finish` | Finish the session |
| `POST` | `/{id}/generate-queue` | Regenerate the review queue |

#### Traverse Strategies (for session start)

| Value | Behaviour |
|---|---|
| `1` — random | Shuffle all nodes |
| `2` — outdated | Nodes past their `next_optimal_repetition` first |
| `3` — dfs | Depth-first traversal order |
| `4` — newest | Recently created nodes first |

## Architecture

Minager follows a **modular monolith** pattern — single repo and deployment, separate database per logical service.

```
minager/
├── app.py                  # FastAPI application
├── lifespan.py             # Startup / shutdown lifecycle
├── settings.py             # Global config
├── core/                   # Shared infrastructure (surorm, clients, types)
├── node/                   # Knowledge tree service  →  SurrealDB
├── learning_session/       # Sessions & repetition   →  MongoDB
├── auth/                   # Authentication          →  PostgreSQL
└── user_profile/           # User profiles           →  PostgreSQL
```

**Layer responsibilities:**

```
API (api.py)  →  Manager (managers.py)  →  Service (services/)  →  Database
```

- No cross-service imports — services communicate via `core/clients/` abstractions.
- No database foreign keys — logical relationships only (IDs stored as strings across DBs).
- Always access data through managers, never directly via models.

### Inter-module communication

Services never import each other directly. `core/clients/` is the seam between them, following a Ports & Adapters (hexagonal) pattern: an abstract port + a stable DTO contract + a concrete adapter that, today, calls the target service's Business layer in-process. That keeps the door open to swap in a network-backed adapter later, without touching any call site. See `CLAUDE.md` for the full rationale and known debt.

### Auth & identity

Permission checks (`is_active`, `is_verified`, `is_superuser`) hit PostgreSQL live through auth's Business layer on every request — deliberate while this is a single-process monolith, since it's cheap in-process and gives instant-effect revocation for free. JWT-embedded claims or gateway-verified trusted headers are a documented future direction, not current behavior — see `CLAUDE.md`.

## Testing

```bash
# Run all tests
poetry run pytest

# Single file or test
poetry run pytest tests/node/test_api.py
poetry run pytest tests/node/test_api.py::test_add_child_creates_node

# Coverage report
poetry run pytest --cov=minager --cov-report=html
```

Tests use real databases (not mocks). A separate test namespace/database is created for SurrealDB and a separate schema with rollback is used for PostgreSQL. The minimum coverage threshold to pass CI is **75%**.

## Project Status

MVP stage. Planned services: tags, debates, messaging.
