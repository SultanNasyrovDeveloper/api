# CLAUDE.md

**Project:** Minager - Learning system with hierarchical knowledge trees and spaced repetition (MVP stage)

**Tech Stack:** FastAPI, SurrealDB (knowledge tree), PostgreSQL (users/auth), MongoDB (learning sessions)

**Learning Principles:**
1. Decomposition: Hierarchical tree structure
2. Spaced repetition: SuperMemo2 algorithm
3. Active repetition: Questions-based review

---

## Architecture

**Monoservices Pattern:** Single repo, single deployment + separate DBs per service

**Services:**
- `minager/node/` - Knowledge tree (SurrealDB)
- `minager/learning_session/` - Sessions/repetitions (MongoDB)
- `minager/auth/` - Authentication (PostgreSQL)
- `minager/user_profile/` - User profiles (PostgreSQL)
- `minager/core/` - Shared infrastructure

**Critical Rules:**

1. **NO cross-service imports** - Use `minager/core/clients/` abstractions instead
   ```python
   # ❌ from minager.learning_session.models import LearningSession
   # ✅ from minager.core.clients.knowledge_tree import KnowledgeTreeClient
   ```

2. **NO database foreign keys** - Logical relations only (different DBs)

3. **ALWAYS use managers** - Never access models directly
   ```python
   # ❌ node = await Node.get(id)
   # ✅ async with PalaceNodeManager(config) as mgr: node = await mgr.get(id)
   ```

---

## Databases

**SurrealDB** - Knowledge tree (graph operations, horizontal scaling)
- Graph traversal: `{..+collect+inclusive}<-child<-node` (descendants)
- Parent reference: `->child.out`
- Custom SurORM query builder in `minager/core/surorm/`

**MongoDB** - Learning sessions (flexible schema, queue management, horizontal scaling)

**PostgreSQL** - Users/auth (ACID guarantees, relational data, slow growth)

**Config:** Environment variables only, delimiter `__`:
```bash
PALACE_NODE_DB__DRIVER=surreal
PALACE_NODE_DB__NAME=minager
PALACE_NODE_DB__HOST=localhost
```

---

## Project Layout

**Overall Structure:**

```
minager/
├── core/              # Shared infrastructure (can be imported by all services)
├── node/              # Knowledge tree service (SurrealDB)
├── learning_session/  # Learning sessions & repetitions service (MongoDB)
├── auth/              # Authentication service (PostgreSQL)
├── user_profile/      # User profiles service (PostgreSQL)
├── tag/               # Tag service (planned)
├── debate/            # Debate system (planned)
├── message/           # Messaging service (planned)
├── app.py             # FastAPI application entry point
├── lifespan.py        # Application startup/shutdown lifecycle
└── settings.py        # Global configuration export
```

**Service/Application Structure:**

Each service follows a Django-inspired file structure. Most modules are optional; the minimal setup is `api.py`, `models.py`, and `schemas.py`.

### Standard Application Modules

**Required/Common Modules:**

- **`api.py`** - REST API endpoint definitions (FastAPI routes)
  - Defines HTTP endpoints for the service
  - Uses dependency injection for managers and auth
  - Example: `@router.get('/nodes/{node_id}')`

- **`models.py`** - Core entity/model definitions
  - Pydantic models or SurORM models
  - Represents database entities
  - Example: `Node`, `LearningSession`, `User`

- **`schemas.py`** - API serialization schemas
  - Similar to Django REST Framework serializers
  - Request/response schemas for API endpoints
  - Input validation and output formatting
  - Example: `CreateNodeSchema`, `UpdateNodeSchema`, `NodeResponseSchema`

**Optional Modules:**

- **`managers.py`** - Database access layer (Repository pattern)
  - Similar to Django managers
  - Abstracts all database operations
  - **IMPORTANT**: Never use models directly in API or elsewhere; always use managers
  - Inherit from `surorm.Manager`, or implement async context manager pattern
  - Example: `PalaceNodeManager`, `LearningSessionManager`

- **`migrations/`** - Database migrations (provider-agnostic)
  - SurORM migrations for SurrealDB (e.g., `minager/node/migrations/`)
  - Alembic migrations for PostgreSQL (in `alembic/` at root)
  - Migration files follow pattern: `XXXX_description.py`

- **`dependencies.py`** - FastAPI dependency injection definitions
  - Custom dependencies for routes
  - Example: extracting current user, getting managers from app state

- **`dto.py`** - Data Transfer Objects
  - Complementary entities not at model-level priority
  - Internal data structures for complex operations
  - Example: `NodeSubtreeStatistics`, `NodeOverallStatistics`

- **`services/`** - Complex business logic
  - Folder or file for multi-step operations
  - Encapsulates complex domain logic that doesn't fit in managers
  - Example: `MoveNodeService`, `StatisticsCalculationService`

- **`utils.py`** - Utility functions
  - Helper functions specific to the application
  - Example: `construct_tree()`, `shuffle()`

- **`queries.py`** - Pre-defined query helpers (node-specific currently)
  - Reusable SurORM query fragments
  - Example: `parent_id_query`, `ancestors_query`, `get_node_statistics_query()`

- **`enums.py`** - Application-level enumerations
  - Python Enums for type safety
  - Example: `MovePosition`, `SessionStatus`

- **`mixins.py`** - Reusable class mixins
  - Shared behavior across multiple classes
  - Example: timestamp mixins, soft delete mixins

- **`constants.py`** - Application-level configuration and constants
  - Static configuration values
  - Magic numbers, default values

### Example Application Structure

**Fully-featured service (minager/node/):**

```
node/
├── __init__.py
├── api.py              # REST endpoints for node operations
├── models.py           # Node, TreeNode, ListNode models
├── schemas.py          # CreateNodeSchema, UpdateNodeSchema, etc.
├── managers.py         # PalaceNodeManager (database access)
├── queries.py          # Reusable query fragments
├── dto.py              # NodeSubtreeStatistics, NodeOverallStatistics
├── enums.py            # MovePosition enum
├── utils.py            # construct_tree() helper
├── mixins.py           # Shared node behaviors
├── migrations/         # SurrealDB migrations
│   ├── 0001_initial_schema.py
│   └── 0002_add_statistics_fields.py
└── services/           # Complex business logic
    ├── move_node.py    # MoveNodeService
    └── node_index/     # Statistics calculation
```

**Minimal service (minager/learning_session/):**

```
learning_session/
├── __init__.py
├── api.py              # Learning session endpoints
├── models.py           # LearningSession model
├── schemas.py          # Session request/response schemas
├── managers.py         # LearningSessionManager
├── enums.py            # SessionStatus enum
├── utils.py            # shuffle() helper
└── repetition/         # SM2 algorithm implementation
    └── sm2.py
```

### Core Module Structure

**`minager/core/`** contains shared infrastructure that all services can import:

```
core/
├── __init__.py
├── surorm/                    # Custom SurrealDB ORM/query builder
│   ├── statements/            # Select, Create, Update, Delete, Transaction
│   ├── orm/                   # Manager, Model, Field, Serializer
│   ├── functions/             # SurrealDB functions (math, array, etc.)
│   └── migrations/            # Migration discovery and execution
├── clients/                   # Inter-service client abstractions
│   └── knowledge_tree/        # KnowledgeTreeClient for node service
│       ├── base.py            # AbstractPalaceClient interface
│       └── client.py          # PalaceNodeServiceClient implementation
├── api/                       # Shared API utilities
│   ├── dependencies.py        # Common FastAPI dependencies (RequestUser, App)
│   ├── permissions.py         # Permission checking utilities
│   ├── permission_classes.py  # Permission class definitions
│   ├── filters.py             # Query filtering helpers
│   ├── response.py            # Standard response formats
│   └── types.py               # Shared API types
├── settings/                  # Configuration management
│   ├── db.py                  # DBConnectionConfig
│   ├── auth.py                # Auth settings
│   ├── cors.py                # CORS settings
│   └── logging.py             # Logging configuration
├── db/                        # Shared database utilities
├── lexorank.py                # Lexicographic ranking for ordering
├── types.py                   # Shared type definitions
└── utils.py                   # Shared utility functions
```

### Key Patterns

**1. Manager Pattern - ALWAYS use managers for database access:**

```python
# ❌ NEVER DO THIS - Direct model usage
from minager.node.models import Node
node = await Node.get(node_id)  # WRONG!

# ✅ DO THIS - Use manager
from minager.node.managers import PalaceNodeManager
async with PalaceNodeManager(config) as manager:
    node = await manager.get(node_id)  # CORRECT!
```

**2. API Dependency Injection:**

```python
# minager/node/api.py
from minager.core.api.dependencies import RequestUser, App

@router.get('/nodes/{node_id}')
async def get_node(
    node_id: str,
    user: RequestUser,  # Injected authenticated user
    app: App,           # Injected app state with managers
):
    async with app.state.nodes as manager:
        node = await manager.get(node_id)
        return node
```

**3. Service Layer for Complex Logic:**

```python
# minager/node/services/move_node.py
class MoveNodeService:
    def __init__(self, manager: PalaceNodeManager):
        self.manager = manager

    async def move(self, node_id: str, target_id: str, position: MovePosition):
        # Complex multi-step operation
        # 1. Validate move
        # 2. Update relations
        # 3. Recalculate order
        # 4. Return result
        pass
```

**4. Minimal Application Setup:**

For new services, start with:
- `models.py` - Define your entities
- `schemas.py` - Define API request/response formats
- `api.py` - Define endpoints

Add other modules as complexity grows.

---

## Code Organization & Patterns

**Layered Architecture:**

Minager follows a clear separation of concerns with distinct layers:

```
API Layer (api.py)
    ↓ calls
Manager Layer (managers.py)
    ↓ calls (for complex logic)
Service Layer (services/)
    ↓ uses
Database (via SurORM/Motor/SQLAlchemy)
```

### API Layer (`api.py`)

**Responsibility:** HTTP endpoint definitions, request/response handling, basic validation

**Pattern:**
```python
from fastapi import APIRouter
from minager.core.api.dependencies import App, RequestUser

router = APIRouter(prefix='/nodes')

@router.get('/{uid}')
async def get_node(
    uid: str,
    app: App,           # Injected app state (has managers)
    user: RequestUser   # Injected authenticated user
) -> schemas.NodeDetailSchema:
    # 1. Get data from manager
    node = await app.state.nodes.get(uid)

    # 2. Simple validation/authorization
    if not node:
        raise HTTPException(status_code=404)

    # 3. Return response (FastAPI handles serialization)
    return node
```

**When to add logic in API layer:**
- ✅ HTTP-specific validation (path params, query params)
- ✅ Simple authorization checks (ownership, permissions)
- ✅ Response transformation (pagination, filtering)
- ❌ Business logic (delegate to manager or service)
- ❌ Database queries (use manager)
- ❌ Complex calculations (use service)

### Manager Layer (`managers.py`)

**Responsibility:** Database access abstraction, basic CRUD operations, simple queries

**Pattern:**
```python
from minager.core import surorm

class PalaceNodeManager(surorm.Manager):
    model = models.Node

    async def get(self, node_id: str) -> models.Node | None:
        """Simple database query - belongs in manager"""
        query = surorm.Select(
            surorm.Alias('parent_id', surorm.F.array.first('->child.out')),
            all_=True
        ).from_(surorm.F.type.thing('node', node_id))

        node_data = await self.select_one(query)
        return models.Node.model_validate(node_data) if node_data else None

    async def move(self, id_: str, to: str, position: MovePosition):
        """Complex operation - delegates to service"""
        service = MoveNodeService(manager=self)
        return await service.move(id_, to, position)
```

**Manager responsibilities:**
- ✅ CRUD operations (get, create, update, delete)
- ✅ Simple queries and filters
- ✅ Database connection management (async context manager)
- ✅ Model validation and serialization
- ✅ Delegating complex operations to services
- ❌ Complex multi-step business logic (use service)
- ❌ Cross-service operations (use clients + service)
- ❌ Heavy computations (use service)

**Manager Pattern Requirements:**
```python
class MyManager(surorm.Manager):
    # Must be async context manager
    async def __aenter__(self):
        # Initialize connection
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Close connection
        pass
```

### Service Layer (`services/`)

**Responsibility:** Complex business logic, multi-step operations, algorithms, strategies

**When to create a service:**
- Multi-step operations requiring multiple database queries
- Complex algorithms or calculations
- Operations that need multiple strategies (Strategy Pattern)
- Business logic that doesn't fit naturally in a manager

**Pattern 1: Simple Service**

```python
# minager/node/services/content_generation.py
class HuggingFaceNodeContentGenerator:
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key

    @classmethod
    def from_config(cls):
        # Factory method using app config
        return cls(
            model_name=config.ai_model,
            api_key=config.ai_api_key
        )

    async def generate(self, node: Node) -> str:
        # Complex content generation logic
        # Multiple steps, external API calls
        pass
```

**Pattern 2: Strategy Pattern Service**

Used when an operation has multiple algorithms/implementations:

```python
# minager/node/services/move_node.py

# 1. Define strategy interface
class MoveNodeStrategy(metaclass=ABCMeta):
    def __init__(self, manager: surorm.Manager):
        self.manager = manager

    @abstractmethod
    async def move(self, id_: str, to: str): ...

# 2. Implement concrete strategies
class MoveNodeAsFirstChild(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        # Calculate first child position
        # Update node order
        # Update relations
        pass

class MoveNodeAsLastChild(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        # Calculate last child position
        pass

class MoveNodeBefore(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        # Calculate sibling position
        pass

# 3. Service selects strategy
class MoveNodeService:
    STRATEGY_MAP = {
        MovePosition.first_child.value: MoveNodeAsFirstChild,
        MovePosition.last_child.value: MoveNodeAsLastChild,
        MovePosition.before.value: MoveNodeBefore,
        MovePosition.after.value: MoveNodeAfter,
    }

    def __init__(self, manager: surorm.Manager):
        self.manager = manager

    async def move(self, id_: str, to: str, position: MovePosition):
        strategy_class = self.STRATEGY_MAP.get(position)
        if not strategy_class:
            raise ValueError('Invalid move position')

        strategy = strategy_class(manager=self.manager)
        return await strategy.move(id_, to)
```

**Pattern 3: Calculator/Index Pattern**

Used for complex calculations with multiple components:

```python
# minager/node/services/node_index/node_indexes.py

class BaseNodeIndex(metaclass=ABCMeta):
    @abstractmethod
    def calculate(self) -> dict:
        """Calculate index and return result with components"""
        pass

class NodeIndex(BaseNodeIndex):
    """Calculates understanding index for a single node"""

    def __init__(self, node: Node):
        self.node = node

    def _repetition_score(self) -> float:
        # Component calculation
        reps = max(self.node.repetitions or 0, 0)
        return 1 - math.exp(-0.5 * reps)

    def _rating_score(self) -> float:
        # Another component
        rating = self.node.last_rating or 0
        return clamp((rating - 1) / 4)

    def calculate(self) -> dict:
        # Combine components
        components = {
            'rep_score': self._repetition_score(),
            'rating_score': self._rating_score(),
        }

        # Calculate weighted index
        index_value = geometric_mean([
            (3, components['rep_score']),
            (2, components['rating_score']),
        ])

        return {
            'index': index_value,
            'components': components
        }

# Used in manager:
class PalaceNodeManager:
    async def get_statistics(self, node_id: str):
        node = await self.get(node_id)
        subtree_stats = await self.get_subtree_statistics(node_id)

        # Service handles complex calculation
        index = NodeOverallIndex(node, subtree_stats)
        data = index.calculate()

        return NodeOverallStatistics.model_validate({...})
```

### Schema Layer (`schemas.py`)

**Responsibility:** API request/response validation, serialization

**Pattern:**

```python
from pydantic import BaseModel, Field

# Input schema - what API accepts
class NodeCreateSchema(BaseModel):
    title: str
    questions: str
    is_learn: bool = True
    order: str = Field(default='aaaaaa')

# Output schema - what API returns
class NodeDetailSchema(BaseModel):
    id: str
    title: str
    questions: str
    content: str
    created: datetime | None = None
    owner_id: str | None = None
    ancestors: list[ListNode] = Field(default_factory=list)

# Update schema - partial updates
class NodeEditSchema(BaseModel):
    title: str = ''
    questions: str = ''
    is_learn: bool = True
```

**Schema best practices:**
- Use mixins for common field groups
- Separate input/output schemas (different validation rules)
- Use `Field()` for defaults and validation
- Use `model_dump(exclude_unset=True)` for PATCH operations

**Mixin Pattern:**

```python
# minager/node/mixins.py
class NodeContentMixin(BaseModel):
    content: str = ''

class NodeStatisticsMixin(BaseModel):
    difficulty: float = 0.5
    repetitions: int = 0
    last_rating: int = 0

# Use in schemas
class NodeEditSchema(NodeContentMixin, NodeStatisticsMixin, BaseModel):
    title: str = ''
    questions: str = ''
```

### Decision Tree: Where Does Logic Go?

```
Is it HTTP-specific (status codes, headers, auth)?
├─ YES → API Layer
└─ NO
   └─ Is it a simple database operation (get, create, update)?
      ├─ YES → Manager Layer
      └─ NO
         └─ Is it complex business logic?
            ├─ YES → Service Layer
            │   ├─ Multiple strategies? → Strategy Pattern Service
            │   ├─ Complex calculation? → Calculator/Index Pattern
            │   └─ Multi-step operation? → Simple Service
            └─ NO → Reconsider if it belongs in this service at all
```

### Common Patterns Summary

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Manager** | Basic CRUD, simple queries | `nodes.get(id)`, `nodes.create(data)` |
| **Simple Service** | Complex multi-step logic | `ContentGenerationService` |
| **Strategy Service** | Multiple algorithms for same operation | `MoveNodeService` with position strategies |
| **Calculator/Index** | Complex calculations with components | `NodeOverallIndex` with sub-indexes |
| **Mixin** | Shared field groups in schemas | `NodeStatisticsMixin`, `NodeContentMixin` |
| **Client** | Cross-service communication | `KnowledgeTreeClient` in learning_session |

### Anti-Patterns to Avoid

❌ **Don't:** Put business logic in API endpoints
```python
# BAD
@router.post('/{uid}/move')
async def move_node(uid: str, target: str, position: str):
    # Complex order calculation in API layer
    current_order = await app.state.nodes.query(...)
    new_order = Lexorank.middle(current_order, next_order)
    await app.state.nodes.update(uid, {'order': new_order})
```

✅ **Do:** Delegate to manager or service
```python
# GOOD
@router.post('/{uid}/move')
async def move_node(uid: str, config: NodeMoveConfiguration):
    return await app.state.nodes.move(uid, config.target_id, config.position)
```

❌ **Don't:** Access models directly without managers
```python
# BAD
from minager.node.models import Node
node = await Node.get(uid)  # Direct model access
```

✅ **Do:** Always use managers
```python
# GOOD
async with PalaceNodeManager(config) as manager:
    node = await manager.get(uid)
```

❌ **Don't:** Import across service boundaries
```python
# BAD - in minager/node/
from minager.learning_session.models import LearningSession
```

✅ **Do:** Use client abstractions
```python
# GOOD - in minager/learning_session/
from minager.core.clients.knowledge_tree import KnowledgeTreeClient
```

---

## Core Domain Models & Concepts

### Knowledge Tree Node Model

The `Node` model (in `minager/node/models.py`) is the core entity representing a knowledge tree node. It combines hierarchical structure, learning content, and spaced repetition metadata.

**Node Model Structure:**

```python
class Node(Model):
    __table_name__ = 'node'

    # Identity & Relations
    id: RecordID                         # SurrealDB record ID (e.g., node:abc123)
    parent_id: RecordID | None           # Parent node (computed via ->child.out)
    ancestors: list[ListNode]            # Ancestor chain (computed)
    children: list[ListNode]             # Direct children (computed)

    # Core Content
    title: str                           # Node title/name
    questions: str                       # Questions to test understanding (active repetition)
    content: str                         # Main content (JSON)
    size: int                            # Content size (default: 0)

    # Tree Structure
    order: str                           # Lexicographic order (lexorank) for sibling position
    owner_id: str                        # User who owns this node

    # Learning Flags
    is_learn: bool                       # Whether to include in learning sessions

    # Spaced Repetition Fields (SuperMemo2)
    difficulty: float                    # Easiness factor (default: 2.6, range ~1.3-2.5+)
    last_rating: float                   # Last repetition rating (0-5 scale)
    repetitions: int                     # Total number of repetitions (default: 0)
    cpr: int                             # Consecutive Positive Ratings (rating >= 3)
    last_interval: int                   # Days since last repetition
    last_repetition: datetime            # When node was last reviewed
    next_optimal_repetition: datetime    # When node should be reviewed next

    # Statistics
    owner_views: int                     # Number of times owner viewed this node (default: 0)
```

### Node Model Variants

**1. Node (Full Model)**
- Used in managers for database operations
- Contains all fields including spaced repetition metadata
- SurORM model with field type definitions

**2. ListNode (Minimal)**
- Used for displaying lists and references (ancestors, children)
- Contains only: `id`, `title`, `order`
- Lightweight for performance

**3. TreeNode (Hierarchical)**
- Used for displaying subtree structures
- Contains: `id`, `title`, `order`, `parent_id`, `ancestors`, `children`
- Recursive structure with nested children

```python
# Example usage
class TreeNode(BaseModel):
    id: str
    title: str
    order: str
    parent_id: str | None
    ancestors: list[ListNode]
    children: list[TreeNode]  # Recursive!
```

### Spaced Repetition Fields Explained

**SuperMemo2 Algorithm Fields:**

1. **`difficulty` (float, default: 2.6)**
   - Also called "easiness factor" (EF) in SuperMemo literature
   - Range: typically 1.3 to 2.5+
   - Higher = easier (longer intervals between reviews)
   - Adjusted based on rating: good ratings increase it, poor ratings decrease it

2. **`last_rating` (float, 0-5 scale)**
   - User's last quality rating of their recall
   - **0-2**: Failed recall (negative)
   - **3**: Barely remembered (minimum passing)
   - **4**: Recalled with effort
   - **5**: Perfect recall

3. **`cpr` (int, Consecutive Positive Ratings)**
   - Counter for ratings >= 3
   - Resets to 0 on any rating < 3
   - Used to determine interval progression:
     - `cpr = 0`: First positive rating → 1 day interval
     - `cpr = 1`: Second positive rating → 4 days interval
     - `cpr >= 2`: Interval = `last_interval * difficulty`

4. **`repetitions` (int)**
   - Total count of all repetitions (positive or negative)
   - Never resets
   - Used for statistics and progress tracking

5. **`last_interval` (int, days)**
   - Number of days that passed between last two reviews
   - Used to calculate next interval: `last_interval * difficulty`

6. **`last_repetition` (datetime)**
   - Timestamp of last review
   - Used for statistics and recency calculations

7. **`next_optimal_repetition` (datetime)**
   - Calculated optimal date for next review
   - Used to build learning session queues
   - Nodes with `next_optimal_repetition <= now` are "outdated" and prioritized

### SuperMemo2 Algorithm Implementation

**How the algorithm works (from `learning_session/repetition/sm2.py`):**

```python
def study_node(node: Node, rating: int) -> StudyNodeResult:
    """
    SuperMemo2 spaced repetition algorithm.
    Returns: difficulty, interval, next_repetition
    """

    # 1. Check if rating is positive (>= 3)
    if rating >= 3:
        # 2. Update difficulty (easiness factor)
        # Formula: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        new_difficulty = difficulty + (0.1 - (5-rating) * (0.08 + (5-rating) * 0.02))

        # 3. Calculate next interval based on CPR
        if cpr == 0:
            interval = 1  # First positive: review tomorrow
        elif cpr == 1:
            interval = 4  # Second positive: review in 4 days (SM2 suggests 6)
        else:
            # Subsequent: exponential growth
            interval = round(last_interval * difficulty, 1)
    else:
        # Rating < 3: Failed recall
        interval = 1      # Review tomorrow
        # difficulty unchanged
        # cpr will be reset to 0 by the manager

    # 4. Calculate next review date
    next_repetition = now + timedelta(days=interval)

    return StudyNodeResult(difficulty, interval, next_repetition)
```

**Rating Scale Interpretation:**

- **0**: Complete blackout (no recall)
- **1**: Incorrect with familiar feeling
- **2**: Incorrect but remembered after seeing answer
- **3**: Correct with serious difficulty
- **4**: Correct after hesitation
- **5**: Perfect response

**Algorithm Goals:**

- Maximize retention (minimize forgetting)
- Minimize review time (optimal intervals)
- Adapt to individual node difficulty

### Learning Session Model

**LearningSession (MongoDB document):**

```python
class LearningSession(MongoDBModel):
    # Identity
    id: MongoDBId                        # MongoDB _id
    user_id: str                         # Owner of the session
    target: str                          # Root node ID of subtree being studied

    # State
    is_active: bool                      # True if session is ongoing

    # Queue System
    current_node: str | None             # Node currently being reviewed
    queue: list[str]                     # Main queue of node IDs to review
    bad_repetition_queue: list[str]      # Nodes with rating < 3 (retry queue)

    # Timestamps
    start_datetime: datetime             # Session start time
    last_activity_datetime: datetime     # Last interaction
    finish_datetime: datetime | None     # When finished (if completed)

    # Strategies
    traverse_strategy: TraverseStrategy  # How to order nodes (outdated, random, dfs, newest)
    repetition_strategy: RepetitionStrategy  # Algorithm (sm2)

    # Computed Properties
    @property
    def is_expired(self) -> bool:
        """True if inactive for > 1 hour"""
        return last_activity < now - timedelta(hours=1)

    @property
    def total_nodes_remaining(self) -> int:
        """Count of nodes in both queues"""
        return len(queue) + len(bad_repetition_queue)
```

**Session Lifecycle:**

1. **Start**: `LearningSessionManager.start(user_id, target_node_id)`
   - Fetches subtree IDs from target node
   - Builds queue based on traverse strategy
   - Shuffles queue
   - Sets `current_node` to first item
   - Marks `is_active = True`

2. **Review Loop**:
   - User reviews `current_node`
   - Submits rating (0-5)
   - `perform_repetition()` updates node's SM2 fields
   - If rating < 3: add to `bad_repetition_queue`
   - Move to next node in queue
   - Update `last_activity_datetime`

3. **Queue Management**:
   - When main `queue` is empty, switch to `bad_repetition_queue`
   - Retry failed nodes before finishing
   - `current_node = None` when all queues exhausted

4. **Finish**:
   - `is_active = False`
   - Set `finish_datetime`
   - Clear `current_node` and queues

**Traverse Strategies:**

```python
class TraverseStrategy(IntEnum):
    random = 1      # Random order
    outdated = 2    # Prioritize next_optimal_repetition <= now
    dfs = 3         # Depth-first traversal
    newest = 4      # Recently created first
```

### Node Hierarchical Structure

**Graph Relation:**

Nodes form a directed graph using SurrealDB's `child` relation:

```
Parent Node ---child---> Child Node
```

**Key Operations:**

- **Get parent**: `->child.out` (follow outgoing child edge)
- **Get children**: `<-child<-node` (follow incoming child edges)
- **Get descendants**: `{..+collect+inclusive}<-child<-node` (recursive traversal)
- **Get ancestors**: Computed by recursively following `->child.out`

### Node Ordering (Lexorank)

Nodes use **lexicographic ranking** for consistent ordering among siblings.

**Why Lexorank:**
- Allows O(1) reordering without updating all siblings
- String-based ordering (e.g., "aaaaaa", "aaaaab", "b")
- Can insert between any two nodes by choosing middle string

**Implementation:**

```python
from minager.core.lexorank import Lexorank

# Insert as first child
order = Lexorank.middle(next_='current_first_order')

# Insert as last child
order = Lexorank.middle(previous='current_last_order')

# Insert between two nodes
order = Lexorank.middle(previous='node_before', next_='node_after')
```

**Example:**

```
Existing nodes: ["a", "c", "d"]
Insert between "a" and "c": Lexorank.middle("a", "c") → "b"
Result: ["a", "b", "c", "d"]
```

### Node Statistics & Indexes

**NodeSubtreeStatistics:**

Aggregated metrics across entire subtree:

```python
class NodeSubtreeStatistics:
    count: int              # Total nodes in subtree
    average_rating: float   # Mean of all last_rating values
    owner_views: int        # Sum of all owner_views
    repetitions: int        # Sum of all repetitions
    size: int               # Sum of all content sizes

    # Health indicators
    outdated: int           # Count of nodes needing review (next_optimal_repetition <= now)
    not_visited: int        # Count of nodes with owner_views = 0
    empty: int              # Count of nodes with size = 0
```

**Node Indexes:**

Quality metrics calculated in `services/node_index/`:

1. **Node Index (Self Understanding)**:
   - Measures user's mastery of this specific node
   - Components: repetition_score, cpr_score, rating_score, recency_score, difficulty_balance
   - Weighted geometric mean

2. **Subtree Index (Knowledge Health)**:
   - Measures completeness and quality of subtree
   - Components: coverage, rating_score, empty_penalty, outdated_penalty, visit_penalty
   - Weighted geometric mean

3. **Overall Index**:
   - Blends node index and subtree index
   - Adaptive weighting based on subtree size
   - Small subtree → emphasize node (80/20)
   - Large subtree → emphasize subtree (20/80)

### Key Relationships

**1. User → Nodes (Ownership)**
- Logical relationship via `node.owner_id` field
- No database foreign key (different databases: PostgreSQL users, SurrealDB nodes)
- Enforced at application level

**2. Node → Node (Parent-Child)**
- Physical relationship via SurrealDB `child` relation
- Graph structure: `parent_node->child->child_node`
- Directional: can have one parent, multiple children

**3. LearningSession → Nodes (Queue References)**
- Logical relationship via node ID strings in queues
- MongoDB session stores: `current_node`, `queue`, `bad_repetition_queue`
- No referential integrity (nodes can be deleted independently)

**4. LearningSession → User**
- Logical relationship via `session.user_id`
- Different databases: MongoDB sessions, PostgreSQL users

**Relationship Diagram:**

```
User (PostgreSQL)
  └─ owns ─→ Nodes (SurrealDB)
                ├─ child ─→ Child Nodes (graph relation)
                └─ referenced by ─→ LearningSession.queue (MongoDB)
                                      └─ belongs to ─→ User
```

### Domain Concepts Summary

| Concept | Description | Key Fields |
|---------|-------------|------------|
| **Knowledge Tree Node** | Single unit of knowledge with content and metadata | `title`, `content`, `questions`, `owner_id` |
| **Spaced Repetition** | Algorithm for optimal review scheduling | `difficulty`, `cpr`, `next_optimal_repetition` |
| **Learning Session** | Active study session on a subtree | `queue`, `current_node`, `is_active` |
| **Node Hierarchy** | Parent-child graph structure | `parent_id`, `children`, `order` |
| **SuperMemo2** | Specific spaced repetition algorithm | Rating 0-5, EF calculation, interval progression |
| **Node Statistics** | Aggregated metrics and quality indexes | Subtree stats, node/subtree/overall indexes |

---

## Testing Strategy

**Testing Framework:**

Minager uses **pytest** with **pytest-asyncio** for all testing. Tests are organized in the `tests/` directory mirroring the application structure.

### Test Organization

```
tests/
├── conftest.py                   # Global fixtures (app_client, test_user, auth_headers)
├── fixtures/
│   ├── surreal_db.py            # SurrealDB test database fixtures
│   └── postgres_db.py           # PostgreSQL test database fixtures
├── node/
│   ├── conftest.py              # Node-specific fixtures
│   ├── test_api.py              # Node API integration tests
│   └── test_manager.py          # Node manager unit tests
├── learning_session/
│   └── test_api.py              # Learning session tests
├── auth/
│   ├── conftest.py              # Auth fixtures
│   └── test_manager.py          # Auth manager tests
└── core/
    ├── api/
    │   └── test_permissions.py  # Permission system tests
    └── surorm/
        └── ...                  # SurORM query builder tests
```

### Test Types

**1. Unit Tests (Manager Layer)**

Test managers directly without HTTP layer.

```python
# tests/node/test_manager.py
@pytest.mark.asyncio
async def test_create_node(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    node_data = node_create_data_factory()
    created_node = await test_palace_node_manager.create(node_data)

    assert isinstance(created_node, Node)
    assert created_node.pk is not None
    assert created_node.title == node_data['title']
```

**When to write unit tests:**
- ✅ Manager CRUD operations
- ✅ Service layer algorithms (SM2, statistics calculations)
- ✅ Query builder functionality (SurORM)
- ✅ Business logic in services
- ❌ Simple getters/setters
- ❌ Trivial utility functions

**2. Integration Tests (API Layer)**

Test full HTTP request/response cycle using AsyncClient.

```python
# tests/node/test_api.py
@pytest.mark.asyncio
async def test_add_child_creates_node(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    auth_headers: dict,
    faker: Faker,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'title': faker.name(), 'questions': faker.sentence()}
    response = await app_client.post(url, json=data, headers=auth_headers)

    # Assert HTTP response
    assert response.status_code == 201

    # Verify database state
    new_node = await test_palace_node_manager.get(response.json()['id'])
    assert new_node.parent_pk == test_user_root_node.pk
```

**When to write integration tests:**
- ✅ All API endpoints
- ✅ Authentication/authorization flows
- ✅ Request validation (422 errors)
- ✅ Multi-step workflows
- ✅ Cross-service interactions

### Test Fixtures

**Global Fixtures (tests/conftest.py):**

```python
@pytest_asyncio.fixture(scope='session')
async def app_client() -> AsyncClient:
    """FastAPI test client for integration tests"""
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app)) as client:
            yield client

@pytest_asyncio.fixture()
async def test_user() -> UserWithProfileSchema:
    """Creates test user with cleanup"""
    # Setup: create user, profile, root node
    yield user
    # Teardown: delete user data

@pytest.fixture()
def auth_headers(test_user_context: UserTestContext) -> dict[str, str]:
    """JWT authorization headers"""
    token = jwt_service.create_access_token(test_user_context.sub)
    return {'Authorization': f'Bearer {token}'}
```

**Database Fixtures (tests/fixtures/surreal_db.py):**

```python
@pytest.fixture(scope='session', autouse=True)
def surreal_test_config():
    """Switch to test database config"""
    settings.config.palace_node_db = original_config.test
    yield settings.config.palace_node_db
    settings.config.palace_node_db = original_config

@pytest_asyncio.fixture(scope='session', autouse=True)
async def palace_node_db_setup(manager: PalaceNodeManager):
    """Create test database and run migrations once per session"""
    await manager.query(surorm.DefineNamespace(namespace).if_not_exists(True))
    await manager.query(surorm.DefineDatabase(db_name).if_not_exists(True))
    await surorm.PerformMigrationCommand(manager, base_path).upgrade()
    yield
    # Cleanup: drop test database
    await manager.query(surorm.Remove('database', db_name).if_exists(True))

@pytest_asyncio.fixture(autouse=True)
async def palace_node_db(test_palace_node_manager: PalaceNodeManager):
    """Clean up data after each test (keeps schema)"""
    yield
    await test_palace_node_manager.query(surorm.Delete('node'))
    await test_palace_node_manager.query(surorm.Delete('child'))
```

**Factory Fixtures:**

```python
@pytest.fixture
def node_create_data_factory(faker: Faker) -> Callable[..., dict]:
    """Factory for node test data with Faker"""
    def _factory(**kwargs):
        return {
            'title': faker.name(),
            'questions': faker.sentence(),
            'owner_id': faker.pystr(max_chars=20),
            'content': '{"root": {}}',
            **kwargs,  # Allow overrides
        }
    return _factory

# Usage:
node_data = node_create_data_factory(title='Custom', is_learn=False)
```

### Test Naming Conventions

Pattern: `test_<operation>_<expected_behavior>`

```python
# Good
test_add_child_requires_auth
test_add_child_validates_required_fields
test_get_node_returns_404_for_nonexistent_id

# Bad
test_add_child           # What behavior?
test_auth                # Too vague
test_1                   # Meaningless
```

### Test Structure (Arrange-Act-Assert)

```python
@pytest.mark.asyncio
async def test_move_node_first_child(manager, factory):
    # ARRANGE: Set up test data
    parent = await manager.create(factory())
    child = await manager.add_child(parent.pk, factory())
    new_parent = await manager.create(factory())

    # ACT: Perform operation
    await manager.move(child.pk, new_parent.pk, MovePosition.first_child)

    # ASSERT: Verify outcome
    moved_node = await manager.get(child.pk)
    assert moved_node.parent_pk == new_parent.pk
    children = await manager.get_children(new_parent.pk)
    assert children[0].pk == child.pk
```

### What to Test

**API Tests - For each endpoint:**

1. **Authentication**
   ```python
   async def test_endpoint_requires_auth(app_client):
       response = await app_client.get(url)
       assert response.status_code == 401
   ```

2. **Validation**
   ```python
   async def test_endpoint_validates_fields(app_client, auth_headers):
       response = await app_client.post(url, json={}, headers=auth_headers)
       assert response.status_code == 422
   ```

3. **Happy Path**
   ```python
   async def test_endpoint_creates_resource(app_client, auth_headers):
       response = await app_client.post(url, json=data, headers=auth_headers)
       assert response.status_code == 201
   ```

4. **Error Cases**
   ```python
   async def test_endpoint_returns_404_for_nonexistent():
       response = await app_client.get(f'{url}/nonexistent_id')
       assert response.status_code == 404
   ```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific file
poetry run pytest tests/node/test_api.py

# Run specific test
poetry run pytest tests/node/test_api.py::test_add_child_creates_node

# Verbose output
poetry run pytest -v

# With coverage
poetry run pytest --cov=minager --cov-report=html

# Stop on first failure
poetry run pytest -x

# Show print statements
poetry run pytest -s
```

### Coverage Requirements

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = ["--cov=minager", "--cov-fail-under=80"]

[tool.coverage.run]
omit = ["*/migrations/*", "*/tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 50  # Minimum to pass CI
```

**Coverage Goals:**
- **Target**: 80% overall coverage
- **Minimum**: 50% to pass CI
- **Focus**: Business logic, managers, services, API endpoints
- **Exclude**: Migrations, tests, init files

### Test Markers

```python
# Required for async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()

# Expected failures (known issues)
@pytest.mark.xfail
async def test_feature_not_implemented():
    pass

# Skip with reason
@pytest.mark.skip(reason="Waiting for feature X")
async def test_future_feature():
    pass
```

### Best Practices

**DO:**
- ✅ Use fixtures for shared setup/teardown
- ✅ Use factories for test data (Faker)
- ✅ Test success and failure paths
- ✅ Clean up after each test (yield fixtures)
- ✅ Test database state, not just HTTP responses
- ✅ Mock external services
- ✅ Use session-scoped fixtures for expensive setup

**DON'T:**
- ❌ Test implementation details
- ❌ Share state between tests
- ❌ Make tests order-dependent
- ❌ Hard-code test data
- ❌ Skip cleanup
- ❌ Leave commented tests without xfail marker

### Example: Complete Test Suite

```python
BASE_URL = '/api/v1/node/nodes/'

# Authentication
@pytest.mark.asyncio
async def test_add_child_requires_auth(app_client, test_user_root_node):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    response = await app_client.post(url, json={})
    assert response.status_code == 401

# Validation
@pytest.mark.asyncio
async def test_add_child_validates_required_fields(
    app_client, test_user_root_node, auth_headers
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    response = await app_client.post(url, json={}, headers=auth_headers)
    assert response.status_code == 422

# Happy Path
@pytest.mark.asyncio
async def test_add_child_creates_node(
    app_client, test_user_root_node, manager, auth_headers, faker
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'title': faker.name(), 'questions': faker.sentence()}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 201

    # Verify in database
    new_node = await manager.get(response.json()['id'])
    assert new_node.parent_pk == test_user_root_node.pk
```

---
