# Database Access Patterns and Architecture

## Overview

Minager implements a multi-database architecture following the monoservices pattern, where each application module operates independently with its own database system. The project uses three distinct database technologies, each optimized for specific data access patterns and requirements.

This document analyzes the database access patterns, connection management, transaction handling, and architectural decisions across the codebase.

## Database Architecture

### Multi-Database Strategy

The application uses three separate database systems:

| Database | Type | Purpose | Configuration |
|----------|------|---------|---------------|
| **PostgreSQL** | Relational | User authentication, user profiles | `main_db` |
| **SurrealDB** | Graph/Document | Palace nodes (hierarchical graph) | `palace_node_db` |
| **MongoDB** | Document | Learning sessions (transient data) | `learning_session_db` |

**Configuration Location:** `minager/settings.py:31-34`

```python
class ApplicationConfig(BaseSettings):
    # Databases
    main_db: DBConnectionConfig
    palace_node_db: SurrealConfig
    learning_session_db: DBConnectionConfig
```

### Rationale

**Why Multiple Databases?**

1. **Monoservices Pattern**: Each service can be deployed independently
2. **No Cross-Service Foreign Keys**: Loose coupling between services
3. **Technology Optimization**: Each database chosen for its strengths
   - PostgreSQL: ACID transactions for user data
   - SurrealDB: Graph traversal for hierarchical nodes
   - MongoDB: Flexible schema for session state

**Trade-offs:**
- ✅ Service independence and scalability
- ✅ Technology-specific optimizations
- ❌ No cross-database transactions
- ❌ Data consistency challenges
- ❌ Multiple connection pools to manage

## Database Configuration

### Configuration Classes

#### DBConnectionConfig

Generic database connection configuration supporting multiple drivers.

**Location:** `minager/core/settings/db.py:11`

```python
class DBConnectionConfig(BaseModel):
    driver: DBDriver = 'postgresql+asyncpg'  # postgresql+asyncpg, motor, surreal
    name: str                                # Database name
    test_name: str | None = None            # Test database name
    namespace: str | None = None            # For SurrealDB
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None

    def to_url(self, **kwargs) -> URL:
        """Build connection URL using yarl"""
        pass

    def to_str(self, **kwargs) -> str:
        """Get connection string"""
        pass
```

**Supported Drivers:**
- `postgresql+asyncpg`: Async PostgreSQL via asyncpg
- `postgresql`: Standard PostgreSQL
- `motor`: MongoDB async driver
- `surreal`: SurrealDB

#### SurrealConfig

Specialized configuration for SurrealDB connections.

**Location:** `minager/surorm/core/settings.py:4`

```python
class SurrealConfig(BaseModel):
    driver: str = 'surreal'
    name: str                    # Database name
    namespace: str | None = None # SurrealDB namespace
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None
```

### Environment-Based Configuration

Configuration uses Pydantic's settings with nested delimiter `__`:

```bash
# .env file example
MAIN_DB__DRIVER=postgresql+asyncpg
MAIN_DB__HOST=localhost
MAIN_DB__PORT=5432
MAIN_DB__NAME=minager_db
MAIN_DB__USERNAME=postgres
MAIN_DB__PASSWORD=secret

PALACE_NODE_DB__DRIVER=surreal
PALACE_NODE_DB__HOST=localhost
PALACE_NODE_DB__PORT=8000
PALACE_NODE_DB__NAMESPACE=minager
PALACE_NODE_DB__NAME=palace_nodes

LEARNING_SESSION_DB__DRIVER=motor
LEARNING_SESSION_DB__HOST=localhost
LEARNING_SESSION_DB__PORT=27017
LEARNING_SESSION_DB__NAME=learning_sessions
```

**Configuration Loading:** `minager/settings.py:38`

```python
model_config = SettingsConfigDict(
    env_nested_delimiter='__',
    env_file=('.env.local', '.env')
)
```

### Connection Pool Initialization

Connection pools are created at module level in `minager/settings.py:43-47`:

```python
# PostgreSQL connection pools
main_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
main_db = async_sessionmaker(main_db_engine, expire_on_commit=False)

user_profile_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
user_profile_db = async_sessionmaker(user_profile_db_engine, expire_on_commit=False)
```

**Issue:** Duplicate connection pools for the same database (`main_db` and `user_profile_db` point to same database).

## Manager Patterns

### PostgreSQL Manager Pattern

#### BaseManager

Generic async manager providing session management.

**Location:** `minager/core/db/managers.py:16`

```python
class BaseManager[ModelT: Model]:
    id_field_name: str = 'id'
    model_class: Type[ModelT]
    _session_factory: async_sessionmaker[AsyncSession]

    def __init__(
        self,
        session: AsyncSession = None,
        session_factory: async_sessionmaker[AsyncSession] = main_db,
    ):
        self.session = session
        self._session_factory = session_factory

    async def __aenter__(self):
        self.session = self._session_factory()
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.commit()  # Auto-commit on exit
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None
```

**Key Characteristics:**
- Async context manager protocol
- Auto-commit on successful exit
- Session lifecycle management
- Generic type support via `[ModelT]`

#### DatabaseManager

Extends `BaseManager` with CRUD operations.

**Location:** `minager/core/db/managers.py:59`

**Methods:**
- `count(*positional_query, **keyword_query)`: Count records
- `get(id_)`: Retrieve single record by ID
- `list_(page, per_page)`: Paginated list
- `create(data)`: Create single record
- `bulk_create(items)`: Bulk insert
- `update(id_, data)`: Update record
- `bulk_update(items, batch_size)`: Batch updates
- `delete(id_)`: Delete record
- `delete_many(ids)`: Bulk delete (not implemented)

**Query Building:**
```python
def get_query(self) -> select:
    return select(self.model_class)

async def get(self, id_: int | str, session: AsyncSession = None) -> ModelT:
    id_field = getattr(self.model_class, self.id_field_name)
    return await self.select_one(self.get_query().where(id_field == id_), session)
```

#### PostgresDatabaseManager

Specialized manager with PostgreSQL-specific features.

**Location:** `minager/core/db/managers.py:152`

**Enhanced Methods:**
- `bulk_create()`: Supports `on_conflict_do_nothing()` via `fail_silently` parameter

```python
async def bulk_create(
    self,
    items: list[dict | BaseModel | ModelT],
    session: AsyncSession = None,
    fail_silently: bool = False,
) -> list[ModelT]:
    stmt = postgres_insert(self.model_class)
    if fail_silently:
        stmt = stmt.on_conflict_do_nothing()  # PostgreSQL-specific
    stmt = stmt.returning(self.model_class)
    # ... execution
```

**Usage Example:**

```python
# UserManager extends PostgresDatabaseManager
class UserManager(PostgresDatabaseManager[models.User]):
    model_class = models.User

# Usage in endpoints
async with user_manager:
    user = await user_manager.add_user(data)
```

### SurrealDB Manager Pattern (SurORM)

#### Manager

Custom ORM manager for SurrealDB with query builder pattern.

**Location:** `minager/surorm/orm/manager.py:11`

```python
class Manager[ModelT: Model]:
    def __init__(self, config: SurrealConfig, logger: Logger = None):
        self._config = config
        self._base_url = f'ws://{self._config.host}:{self._config.port}'
        self._connection = None

    async def __aenter__(self):
        self._connection = AsyncSurreal(self._base_url)
        await self._connection.__aenter__()

        # Authentication
        if self._config.username and self._config.password:
            await self._connection.signin({
                'username': self._config.username,
                'password': self._config.password.get_secret_value(),
            })

        # Namespace/database selection
        await self._connection.use(
            namespace=self._config.namespace,
            database=self._config.name
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._connection.__aexit__(exc_type, exc_val, exc_tb)
        self._connection = None

    async def query(
        self, sql: Expression, variables: dict[str, Any] | None = None
    ) -> Any | list[Any]:
        response = await self._connection.query(query=str(sql), vars=variables)
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        return response
```

**Key Characteristics:**
- WebSocket connection (`ws://` protocol)
- Authentication with username/password
- Namespace and database selection required
- Query builder pattern with `Expression` objects
- Response unwrapping (single-item lists → item)

#### PalaceNodeManager

Domain-specific manager extending SurORM Manager.

**Location:** `minager/node/managers.py:10`

```python
class PalaceNodeManager(surorm.Manager):
    async def create(self, **kwargs) -> schemas.NodeDetailSchema:
        root_schema = schemas.NodeCreateSchema.model_validate(kwargs)
        query = surorm.Create('node').content(
            root_schema.model_dump_surreal()
        ).return_('after')
        response = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(response[0])

    async def get(self, node_id: str) -> schemas.NodeDetailSchema | None:
        query = surorm.Select(
            surorm.Alias('parent_id', surorm.F.array.first('->child.out')),
            surorm.Alias('ancestors', queries.ancestors_query),
            all_=True,
        ).from_(surorm.F.type.thing('node', node_id))
        node_data: dict | None = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(node_data) if node_data else None

    async def get_subtree(self, uid: str) -> schemas.TreeNodeItemSchema:
        # Graph traversal query
        stmt = surorm.Select('id', 'title', 'order', ...).from_(
            f'{surorm.F.type.thing('node', uid)}.{{1..2+collect+inclusive}}<-child<-node'
        )
        nodes = await self.query(stmt)
        tree_root = utils.construct_tree(nodes)
        return schemas.TreeNodeItemSchema.model_validate(tree_root)
```

**Query Builder Pattern:**

SurORM uses fluent API for building SurrealDB queries:

```python

from minager.core import surorm

# Select with aliases and graph traversal
query = (
    surorm.Select('id', 'title', surorm.Alias('parent_id', parent_query))
    .from_(surorm.F.type.thing('node', node_id))
    .where('owner_id = $owner_id')
    .limit(10)
)

# Execute with variables
result = await manager.query(query, {'owner_id': user_id})
```

**See:** `docs/surorm/CLAUDE.md` for complete SurORM documentation

### MongoDB Manager Pattern

#### MongoDBManager

Generic async MongoDB manager using Motor driver.

**Location:** `minager/core/db/mongo.py:27`

```python
class MongoDBManager[ModelT]:
    collection: str
    model_class: ModelT

    def __init__(self, config: DBConnectionConfig):
        assert self.collection
        self._config = config
        self.client = AsyncMongoClient(self._config.to_str(scheme='mongodb'))
        self.client.get_io_loop = get_running_loop  # Motor requirement
        self.connection = self.client[self._config.name][self.collection]

    async def create(self, data: dict) -> ModelT:
        response = await self.connection.insert_one(data)
        new_item = await self.connection.find_one({'_id': response.inserted_id})
        return self.model_class.model_validate(new_item)
```

**Key Characteristics:**
- No context manager protocol (connection stays open)
- Direct Motor client usage
- Collection-level access
- Pydantic model validation

#### LearningSessionManager

Domain-specific MongoDB manager.

**Location:** `minager/learning_session/managers.py:17`

```python
class LearningSessionManager:
    COLLECTION = 'session'

    def __init__(self, config: DBConnectionConfig, palace_client: PalaceNodeServiceClient):
        self._config = config
        self._url = config.to_str(scheme='mongodb')
        self.palace_client = palace_client  # Cross-service client
        self.client: Optional[motor.AsyncIOMotorClient] = None
        self.connection = None

    async def __aenter__(self):
        self.client = motor.AsyncIOMotorClient(self._url)
        self.client.get_io_loop = asyncio.get_running_loop
        self.connection = self.client[self._config.name][self.COLLECTION]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
```

**Cross-Service Integration:**

The `LearningSessionManager` depends on `PalaceNodeServiceClient` for node operations:

```python
async def perform_repetition(self, session_id: str, node_id: str, rating: int, user_id: str):
    session = await self.get(session_id)
    repeated_node = await self.palace_client.get(node_id)  # Cross-service call

    # Update node in SurrealDB
    await self.palace_client.update(node_id, {
        'last_repetition': datetime.now(UTC),
        'difficulty': study_result.difficulty,
        # ...
    })

    # Update session in MongoDB
    return await self.update(session.id, session_update_data)
```

**Issue:** No transaction coordination between SurrealDB and MongoDB updates.

## Connection Management

### Application Lifespan

Database connections are managed through FastAPI's lifespan context manager.

**Location:** `minager/lifespan.py:15`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Test SurrealDB connection
    tester = SurrealConnectionTester(config.palace_node_db)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with knowledge_tree db.')

    # Initialize managers
    app.state.nodes = PalaceNodeManager(config.palace_node_db)
    app.state.users = UserManager()
    app.state.user_profiles = UserProfileManager()

    palace_service_client = PalaceNodeServiceClient(config=config.palace_node_db)
    await palace_service_client.__aenter__()

    app.state.learning_session = LearningSessionManager(
        config=config.learning_session_db,
        palace_client=palace_service_client,
    )

    # Enter all managers
    await app.state.nodes.__aenter__()
    await app.state.users.__aenter__()
    await app.state.user_profiles.__aenter__()
    await app.state.learning_session.__aenter__()

    yield

    # Shutdown: Close all connections
    await palace_service_client.__aexit__(None, None, None)
    await app.state.nodes.__aexit__(None, None, None)
    await app.state.users.__aexit__(None, None, None)
    await app.state.user_profiles.__aexit__(None, None, None)
    await app.state.learning_session.__aexit__(None, None, None)
```

**Connection Lifecycle:**

1. **Startup Phase:**
   - Test SurrealDB connectivity
   - Initialize all managers
   - Enter all context managers (open connections)
   - Store managers in `app.state`

2. **Request Phase:**
   - Managers accessed via `app.state.{manager_name}`
   - Each request gets manager from app state
   - Manager uses existing connection pool

3. **Shutdown Phase:**
   - Exit all context managers (close connections)
   - Cleanup resources

### Per-Request Usage Pattern

Managers are accessed via dependency injection:

```python
from minager.core.api.dependencies import App

@router.get('/nodes/{node_id}')
async def get_node(node_id: str, app: App):
    manager = app.state.nodes
    async with manager:  # Gets session from pool
        node = await manager.get(node_id)
    return node  # Auto-commits on context exit
```

**Pattern:**
1. Get manager from `app.state`
2. Enter context manager (gets connection/session)
3. Perform operations
4. Exit context manager (auto-commit)

### Session Lifecycle

#### PostgreSQL Sessions

**Session Creation:** From connection pool via `async_sessionmaker`

```python
async def __aenter__(self):
    self.session = self._session_factory()  # Gets session from pool
    await self.session.__aenter__()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.session.commit()  # Auto-commit on success
    await self.session.__aexit__(exc_type, exc_val, exc_tb)
    self.session = None
```

**Key Points:**
- Session acquired from pool on `__aenter__`
- Auto-commit on successful exit
- Auto-rollback on exception (SQLAlchemy default)
- Session returned to pool on `__aexit__`

#### SurrealDB Connections

**Connection per Manager Entry:**

```python
async def __aenter__(self):
    self._connection = AsyncSurreal(self._base_url)
    await self._connection.__aenter__()
    await self._connection.signin({...})
    await self._connection.use(namespace=..., database=...)
    return self
```

**Key Points:**
- New WebSocket connection per context entry
- Authentication and namespace selection required
- Connection closed on exit
- No connection pooling (creates new connection each time)

**Performance Concern:** Creating new WebSocket connections is expensive.

#### MongoDB Connections

**Connection per Manager Entry:**

```python
async def __aenter__(self):
    self.client = motor.AsyncIOMotorClient(self._url)
    self.client.get_io_loop = asyncio.get_running_loop
    self.connection = self.client[self._config.name][self.COLLECTION]
    return self
```

**Key Points:**
- New Motor client per context entry
- Collection-level access
- Closed on exit via `client.close()`

## Transaction Patterns

### PostgreSQL Transactions

#### Implicit Transactions

The `BaseManager` provides implicit transaction management:

```python
async with manager:
    # All operations in implicit transaction
    user = await manager.create(user_data)
    profile = await manager.create(profile_data)
    # Auto-commits on successful exit
```

**Behavior:**
- Transaction starts on session creation
- All operations within context are in same transaction
- Auto-commit on successful `__aexit__`
- Auto-rollback on exception

#### Explicit Transactions

For finer control, use SQLAlchemy's `session.begin()`:

```python
async with session.begin():
    # Explicit transaction block
    await session.execute(stmt1)
    await session.execute(stmt2)
    # Commits at end of block
```

**Used in:** `DatabaseManager.bulk_create()` (line 107)

```python
async with session.begin():
    created_items = await session.scalars(stmt, create_data)
```

#### Manual Commits

Some operations manually commit:

```python
async def update(self, id_: int, data: dict, session: AsyncSession = None) -> ModelT:
    stmt = (
        update(self.model_class)
        .where(self.model_class.id.expression == id_)
        .values(**data)
        .returning(self.model_class)
    )
    session = self.get_session(session)
    updated = await session.scalar(stmt)
    await session.commit()  # Manual commit
    return updated
```

**Location:** `minager/core/db/managers.py:121`

**Issue:** Redundant commit - context manager already commits on exit.

### SurrealDB Transactions

SurORM supports explicit transactions via `Transaction` statement:

```python
from minager.core.surorm import Transaction

tx = Transaction(
    surorm.Create('node').content({'title': 'New Node'}),
    surorm.Update('user:123').set('node_count += 1'),
).return_('$node')

result = await manager.query(tx)
```

**Characteristics:**
- Multiple operations in single atomic transaction
- Can return variables from transaction
- All-or-nothing execution

**Current Usage:** Limited usage in codebase, mostly individual operations.

### MongoDB Transactions

**No Transaction Support in Current Code**

The `LearningSessionManager` does not use MongoDB transactions:

```python
async def perform_repetition(self, session_id: str, node_id: str, rating: int, user_id: str):
    # Update node in SurrealDB
    await self.palace_client.update(node_id, {...})

    # Update session in MongoDB (separate operation)
    return await self.update(session.id, session_update_data)
```

**Issue:** No atomicity between SurrealDB and MongoDB updates. If second operation fails, first update is not rolled back.

### Cross-Database Transaction Issues

#### User Registration Flow

**Location:** `minager/auth/api.py:13-22`

```python
@user_router.post('/')
async def create_user(app: App, data: schemas.UserCreateDataSchema):
    user_manager = app.state.users
    user_profile_manager = app.state.user_profiles
    palace_manager = app.state.nodes

    async with user_manager, user_profile_manager, palace_manager:
        # Step 1: Create user in PostgreSQL
        user = await user_manager.add_user(data)

        # Step 2: Create knowledge_tree node in SurrealDB
        node = await palace_manager.create(owner_id=str(user.id), title='Mind Palace')

        # Step 3: Create user profile in PostgreSQL
        await user_profile_manager.create({
            'user_id': str(user.id),
            'palace_root_id': node.id
        })

    return user
```

**Problems:**

1. **No Atomicity Across Databases**
   - If step 2 fails, user is created but no palace node
   - If step 3 fails, user and node exist but no profile
   - No way to rollback across databases

2. **Multiple Context Managers**
   - Each manager has its own transaction
   - PostgreSQL operations are in separate transactions
   - No coordination between transactions

3. **Partial Failure State**
   - Can end up with orphaned records
   - Manual cleanup required
   - Data inconsistency

**Recommended Solutions:**

1. **Saga Pattern**: Implement compensating transactions
2. **Event-Driven**: Use message queue for async operations
3. **Single Database**: Move all data to one system (breaking monoservices)
4. **Accept Inconsistency**: Implement eventual consistency with background jobs

## Error Handling

### PostgreSQL Error Handling

#### IntegrityError Handling

**Location:** `minager/core/db/managers.py:89`

```python
async def create(self, data: dict, session: AsyncSession = None) -> ModelT:
    item = self.model_class(**data)
    session = self.get_session(session)
    try:
        session.add(item)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    # ...
```

**Issues:**

1. **Catches too early**: Exception won't be raised until commit
2. **Generic error**: Doesn't distinguish between constraint types
3. **Loses error details**: Original error message lost

**Better Approach:**

```python
try:
    session.add(item)
    await session.flush()  # Force write to DB
except IntegrityError as e:
    if 'unique constraint' in str(e):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Record already exists'
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f'Database constraint violation: {e}'
    )
```

#### Missing Error Handling

**Issues Across Codebase:**

1. **No null checks**: `await manager.get(id)` can return None
2. **No not found errors**: Delete operations don't check if record exists
3. **No validation errors**: Assume all data is valid

**Example from UserProfileManager:**

```python
@router.get('/{user_id}')
async def get_user_profile(user_id: str, app: App):
    manager = app.state.user_profiles
    async with manager:
        profile = await manager.get(user_id)  # Can return None
    return profile  # Will return None → 200 OK with null body
```

**Should be:**

```python
@router.get('/{user_id}')
async def get_user_profile(user_id: str, app: App):
    manager = app.state.user_profiles
    async with manager:
        profile = await manager.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail='Profile not found')
    return profile
```

### SurrealDB Error Handling

**No Error Handling in SurORM Manager:**

```python
async def query(self, sql: Expression, variables: dict[str, Any] | None = None):
    response = await self._connection.query(query=str(sql), vars=variables)
    if isinstance(response, list) and len(response) == 1:
        response = response[0]
    return response
```

**Issues:**

1. No exception handling
2. No response validation
3. Errors bubble up as raw SurrealDB errors
4. No custom exceptions for common errors

### MongoDB Error Handling

**No Error Handling in LearningSessionManager:**

All operations assume success. No handling for:
- Document not found
- Duplicate keys
- Connection errors
- Write concerns

## Query Patterns

### PostgreSQL Query Patterns

#### Basic CRUD

```python
# Get by ID
stmt = select(User).where(User.id == user_id)
user = await session.scalar(stmt)

# List with filtering
stmt = select(User).where(User.email.like('%@example.com')).limit(10)
users = await session.scalars(stmt)

# Count
stmt = select(func.count(User.id)).where(User.is_active == True)
count = await session.scalar(stmt)
```

#### Pagination

**Location:** `minager/core/db/managers.py:70`

```python
async def list_(self, *, page: int | None = None, per_page: int | None = None):
    stmt = self.get_query().where(*positional_query, **keyword_query)
    if page and per_page:
        stmt.limit(per_page).offset(per_page * (page - 1))
    return list(await self.select(stmt, session))
```

**Issue:** Missing `stmt =` assignment, method chaining returns new object

```python
# Should be:
if page and per_page:
    stmt = stmt.limit(per_page).offset(per_page * (page - 1))
```

#### Bulk Operations

**Insert with RETURNING:**

```python
stmt = insert(self.model_class).returning(self.model_class)
async with session.begin():
    created_items = await session.scalars(stmt, create_data)
```

**PostgreSQL ON CONFLICT:**

```python
stmt = postgres_insert(self.model_class)
stmt = stmt.on_conflict_do_nothing()  # or on_conflict_do_update()
stmt = stmt.returning(self.model_class)
```

### SurrealDB Query Patterns

#### Record ID Construction

```python

from minager.core import surorm

# Create record ID: node:abc123
record_id = surorm.F.type.thing('node', 'abc123')

# Use in queries
query = surorm.Select('*').from_(record_id)
```

#### Graph Traversal

**Get children:**

```python
# node:id -> child relation -> out nodes
query = surorm.Select('id', 'title').from_('->child.out')
```

**Get descendants (recursive):**

```python
# Traverse 1 to 2+ levels deep, collect all
query = surorm.Select('*').from_(
    f'{record_id}.{{1..2+collect+inclusive}}<-child<-node'
)
```

**Custom graph functions:**

```python
# From migration-defined functions
ancestors_query = surorm.Select('id').from_('get_ancestors($node_id)')
```

#### Aliases and Subqueries

```python
from minager.core.surorm import Alias

parent_query = surorm.Select('id').from_('->child.out').limit(1)

query = surorm.Select(
    'id',
    'title',
    Alias('parent_id', parent_query)  # Adds AS clause
).from_(surorm.F.type.thing('node', node_id))
```

#### Aggregations

```python
query = surorm.Select(
    surorm.Alias('total_nodes', surorm.F.count()),
    surorm.Alias('average_rating', surorm.F.math.mean('last_rating')),
    surorm.Alias('total_size', surorm.F.math.sum('size')),
).from_('node').where('owner_id = $owner_id')
```

### MongoDB Query Patterns

#### Basic Operations

```python
# Find one
doc = await connection.find_one({'_id': ObjectId(id)})

# Find with filter
docs = await connection.find({'user_id': user_id, 'is_active': True}).to_list()

# Insert
result = await connection.insert_one(data)

# Update
result = await connection.update_one(
    {'_id': ObjectId(id)},
    {'$set': data}
)

# Find and update (atomic)
updated_doc = await connection.find_one_and_update(
    {'_id': ObjectId(id)},
    {'$set': data},
    return_document=ReturnDocument.AFTER
)
```

#### Array Operations

**Location:** `minager/learning_session/managers.py:121-144`

```python
# Remove item from array
if node_id in session.queue:
    session.queue.remove(node_id)  # Python list operation

# Append to array
session_update_data['bad_repetition_queue'] = [
    *session.bad_repetition_queue,
    node_id,
]

# Replace entire array
session_update_data['queue'] = session.queue[1:]
```

**Issue:** Array operations done in Python memory, not using MongoDB operators

**Better approach:**

```python
# Use MongoDB array operators
await connection.update_one(
    {'_id': session_id},
    {
        '$pull': {'queue': node_id},          # Remove from array
        '$push': {'bad_queue': node_id},      # Add to array
        '$set': {'last_activity': datetime.now()}
    }
)
```

## Performance Considerations

### Connection Pooling

#### PostgreSQL

**Good:** Uses SQLAlchemy connection pool
- Pool size configurable via engine parameters
- Connection reuse across requests
- Automatic connection recycling

**Missing Configuration:**

```python
# Should configure pool settings
main_db_engine = create_async_engine(
    config.main_db.to_str(),
    echo=True,
    pool_size=20,          # Max connections
    max_overflow=10,       # Extra connections under load
    pool_pre_ping=True,    # Test connections before use
    pool_recycle=3600,     # Recycle after 1 hour
)
```

#### SurrealDB

**Bad:** No connection pooling
- New WebSocket connection per request
- Expensive connection setup (authentication, namespace selection)
- No connection reuse

**Recommendation:** Implement connection pool for SurrealDB

```python
# Potential solution
class SurrealConnectionPool:
    def __init__(self, config, pool_size=10):
        self.pool = asyncio.Queue(maxsize=pool_size)
        # Pre-create connections

    async def acquire(self):
        return await self.pool.get()

    async def release(self, conn):
        await self.pool.put(conn)
```

#### MongoDB

**Bad:** New Motor client per request
- Motor has internal connection pooling, but client creation is expensive
- Should reuse Motor client across requests

**Recommendation:** Create Motor client once at startup

```python
# In lifespan
mongo_client = AsyncMongoClient(config.learning_session_db.to_str())
app.state.mongo_client = mongo_client

# In manager
def __init__(self, client):
    self.client = client  # Reuse existing client
    self.connection = client[db][collection]
```

### Query Optimization

#### N+1 Query Problem

**Example from node operations:**

```python
# Get subtree
nodes = await self.query(stmt)  # Gets all nodes

# Then for each node, might need additional queries
for node in nodes:
    parent = await self.get(node.parent_id)  # N additional queries!
```

**Solution:** Use graph traversal or joins to fetch related data

```python
# Fetch everything in one query
query = surorm.Select(
    'id', 'title', 'parent_id',
    surorm.Alias('parent', 'parent_id.{id, title}')  # Fetch relation data
).from_(...)
```

#### Missing Indexes

**PostgreSQL:**
- Username field indexed in UserProfile ✓
- Email field unique in User (implicit index) ✓
- Missing indexes on frequently queried fields (owner_id, etc.)

**SurrealDB:**
- Index definitions in migrations
- No explicit index management in code

**MongoDB:**
- No index definitions found
- Should index: `user_id`, `is_active`, `target`

### Pagination Issues

**Count query not implemented:**

```python
# Returns hardcoded 0
return PaginatedResponse(count=0, page=page, per_page=per_page, results=profiles)
```

**Should implement:**

```python
total_count = await manager.count()
return PaginatedResponse(
    count=total_count,
    page=page,
    per_page=per_page,
    results=profiles
)
```

## Data Consistency Patterns

### Strong Consistency

**PostgreSQL Operations:**
- ACID transactions guarantee consistency
- Operations within single database are atomic
- Read-your-writes consistency

### Eventual Consistency

**Cross-Database Operations:**
- No atomicity guarantees
- User registration can leave partial state
- Learning session updates span two databases

**Mitigation Strategies:**

1. **Idempotent Operations**: Design operations to be safely retryable
2. **Compensation**: Implement cleanup for partial failures
3. **Status Tracking**: Add status fields to track operation progress
4. **Background Jobs**: Reconciliation jobs to fix inconsistencies

### Data Integrity

**No Foreign Keys:** Following monoservices pattern
- User ID in profile doesn't reference auth.users
- Palace root ID doesn't reference SurrealDB nodes
- No cascade delete behavior

**Implications:**
- Can have orphaned records
- Must manually maintain referential integrity
- Need cleanup jobs for orphaned data

## Testing Database Code

### Current State

**No Test Files Found** for database layers

**Missing Tests:**
- Manager CRUD operations
- Transaction handling
- Error scenarios
- Connection management
- Query building (SurORM)

### Recommended Test Structure

```python
# tests/db/test_base_manager.py
@pytest.fixture
async def db_session():
    # Create test database session
    pass

@pytest.mark.asyncio
async def test_manager_create(db_session):
    manager = TestManager(session=db_session)
    async with manager:
        item = await manager.create({'name': 'Test'})
        assert item.id is not None

# tests/surorm/test_query_builder.py
def test_select_query():
    query = surorm.Select('id', 'title').from_('node')
    assert query.sql() == 'select id,title from node'

# tests/integration/test_user_registration.py
@pytest.mark.asyncio
async def test_user_registration_rollback_on_error():
    # Test that failures don't leave partial data
    pass
```

## Migration Management

### PostgreSQL Migrations (Alembic)

**Location:** `alembic/`

**Structure:**
- `env.py`: Alembic configuration
- `script.py.mako`: Migration template
- `versions/`: Migration files (not found in scan)

**Auth migrations:** `minager/auth/migrations/1749725817_add_auth_user_model.py`

**Usage:**
```bash
alembic revision -m "description"
alembic upgrade head
alembic downgrade -1
```

### SurrealDB Migrations

**Custom migration system** with auto-discovery

**Location:** Migrations in `*/migrations/` folders

**Format:** `XXXX_description.py`

```python
from minager.core.surorm import MigrationOperation

operations = [
    MigrationOperation(
        'operation_name',
        'DEFINE TABLE node SCHEMAFULL;'
    ),
]
```

**Usage:**
```bash
poetry run migrate upgrade
poetry run migrate upgrade --app node
poetry run migrate upgrade --number 0001
```

**Auto-Discovery:** Walks directory tree to find migration files

### MongoDB Migrations

**No Migration System** - Schema-less database

**Issues:**
- No version control for schema changes
- No way to track applied changes
- Manual schema evolution

**Recommendation:** Implement migration system or use tools like `pymongo-migrate`

## Recommendations

### High Priority

1. **Fix Connection Pooling**
   - Implement SurrealDB connection pool
   - Reuse Motor client across requests
   - Configure PostgreSQL pool parameters

2. **Add Error Handling**
   - Handle null returns from get() operations
   - Custom exceptions for common errors
   - Proper HTTP status codes

3. **Fix Transaction Issues**
   - Remove redundant commits
   - Fix pagination limit/offset assignment
   - Add transaction coordination for cross-database operations

4. **Add Comprehensive Tests**
   - Unit tests for managers
   - Integration tests for cross-database operations
   - Test error scenarios

5. **Implement Saga Pattern**
   - Add compensation logic for user registration
   - Handle partial failures gracefully
   - Log transaction state for debugging

### Medium Priority

6. **Add Database Indexes**
   - Index frequently queried fields
   - Document index strategy
   - Monitor query performance

7. **Optimize Query Patterns**
   - Fix N+1 query problems
   - Use bulk operations where possible
   - Implement proper pagination with counts

8. **Improve Error Messages**
   - Add context to database errors
   - Log full error details
   - Return user-friendly messages

9. **Add Connection Monitoring**
   - Track connection pool usage
   - Monitor slow queries
   - Alert on connection failures

10. **Document Data Model**
    - Entity relationship diagrams
    - Data flow documentation
    - Consistency guarantees

### Low Priority

11. **Consolidate Database Connections**
    - Remove duplicate connection pools (`main_db` vs `user_profile_db`)
    - Single configuration per database

12. **Add Query Logging**
    - Log slow queries
    - Track query patterns
    - Performance profiling

13. **Implement Read Replicas**
    - Split read/write operations
    - Load balance read queries
    - Improve read scalability

## Security Considerations

### SQL Injection Prevention

**Good:** Using parameterized queries

```python
# Safe - uses SQLAlchemy ORM
stmt = select(User).where(User.email == email)

# Safe - uses SurrealDB variables
query = surorm.Select('*').from_('node').where('owner_id = $owner_id')
await manager.query(query, {'owner_id': user_id})
```

**Risky:** String interpolation in SurORM

```python
# Potentially unsafe if uid comes from user input
query = surorm.Select('*').from_(f'node:{uid}')
```

### Credential Management

**Good:** Using SecretStr for passwords

```python
password: SecretStr | None = None
password.get_secret_value()  # Explicit access
```

**Good:** Environment-based configuration

**Missing:**
- Credential rotation mechanism
- Secrets management integration (Vault, etc.)
- Database permission auditing

### Connection Security

**Missing:**
- SSL/TLS configuration for database connections
- Certificate validation
- Encrypted connection enforcement

**Recommendation:**

```python
# PostgreSQL with SSL
main_db_engine = create_async_engine(
    config.main_db.to_str(),
    connect_args={
        'ssl': True,
        'ssl_ca': '/path/to/ca.pem'
    }
)

# MongoDB with SSL
mongo_client = AsyncMongoClient(
    url,
    tls=True,
    tlsCAFile='/path/to/ca.pem'
)
```

## Summary

### Strengths

1. ✅ Clear separation of concerns with monoservices pattern
2. ✅ Async throughout using modern Python patterns
3. ✅ Type hints with generics for type safety
4. ✅ Context managers for resource management
5. ✅ Custom ORM (SurORM) optimized for SurrealDB

### Critical Issues

1. ❌ No transaction coordination across databases
2. ❌ Poor connection pooling (SurrealDB, MongoDB)
3. ❌ Missing error handling and validation
4. ❌ No test coverage for database layer
5. ❌ Data consistency issues in multi-database operations

### Architectural Decisions

**Multi-Database Strategy:**
- Optimizes each service for its use case
- Enables independent scaling
- Complicates consistency guarantees
- Increases operational complexity

**Trade-off:** Service independence vs. data consistency

**Recommendation:** Consider long-term if benefits outweigh complexities. For smaller deployments, single database might be simpler.
