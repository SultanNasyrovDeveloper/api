# SurORM - SurrealDB Object-Relational Mapper

This file provides guidance for working with SurORM, a custom query builder and ORM for SurrealDB.

## Overview

SurORM is a lightweight, type-safe query builder for SurrealDB that provides:
- Fluent API for building SurrealDB queries
- Composable query components
- Async database manager
- Migration system with auto-discovery
- Model-based data mapping

**Architecture:** Builder pattern with direct SQL rendering through `sql()` methods.

## Core Concepts

### 1. Renderable Protocol

All query components implement the `Renderable` protocol:

```python
from minager.core.surorm import Renderable


class Renderable(metaclass=ABCMeta):
    @abstractmethod
    def sql(self) -> str:
        """Convert this object to a SurrealDB query string"""
        pass

    def __str__(self) -> str:
        return self.sql()
```

**Key principle:** Every query component knows how to render itself to SQL. Composition is achieved through recursive rendering.

### 2. Query Building

Queries are built using a fluent API with method chaining:

```python

from minager.core import surorm

# Select query
query = (
    surorm.Select('id', 'title', 'created_at')
    .from_('node')
    .where('owner_id = $owner_id', 'deleted_at = NONE')
    .order_by('created_at', direction='desc')
    .limit(10)
)

# Execute
sql = query.sql()  # "select id,title,created_at from node where ..."
result = await manager.query(sql, {'owner_id': user_id})
```

### 3. Statement Types

Located in `minager/surorm/statements/`:

- **Select**: Query records with filtering, ordering, grouping
- **Create**: Insert new records
- **Update**: Modify existing records (set/content/merge/patch)
- **Delete**: Remove records
- **Transaction**: Group multiple operations
- **Define**: Schema definitions (tables, fields, indexes)
- **Relate**: Create graph relations
- **Graph**: Graph traversal queries

### 4. Functions

SurrealDB functions are available through the `F` namespace:

```python

from minager.core import surorm

# Array functions
surorm.F.array.first(field)
surorm.F.array.append(array, value)

# Type functions
surorm.F.type.thing('node', uid)  # Creates record ID: node:uid
surorm.F.type.string(value)

# Math functions
surorm.F.math.ceil(value)
surorm.F.math.floor(value)

# Time functions
surorm.F.time.now()
surorm.F.time.unix()

# Object functions (custom)
surorm.F.object.entries(field)
```

Located in `minager/surorm/functions/`: `array.py`, `datetime.py`, `math.py`, `object.py`, `time.py`, `type.py`

### 5. Mixins

Reusable query behaviors through mixins in `minager/surorm/mixins.py`:

- **Filterable**: Adds `where()` and `get_filter_sql()` methods
- **Returnable**: Adds `return_()` for controlling return values (none/before/after/diff)
- **Overridable**: Adds `overwrite()` flag
- **IfExists**: Adds `if_exists()` conditional
- **IfNotExists**: Adds `if_not_exists()` conditional
- **Commentable**: Adds `comment()` for documentation

**Usage:**
```python
class Update(Filterable, Returnable, Renderable):
    # Inherits where() from Filterable
    # Inherits return_() from Returnable
    pass
```

### 6. Manager Pattern

Database operations use async context managers:

```python
from minager.core.surorm.orm import Manager
from minager.core.surorm.core import SurrealConfig

config = SurrealConfig(
    host='localhost',
    port=8000,
    namespace='minager',
    name='palace_node_db'
)

async with Manager(config) as manager:
    result = await manager.query(query, variables={'owner_id': '123'})
```

The manager handles:
- Connection lifecycle (`__aenter__`/`__aexit__`)
- Authentication
- Namespace/database selection
- Query execution

### 7. Model System

Define models in `minager/surorm/orm/models.py`:

```python
from minager.core.surorm import Model
from minager.core.surorm.orm import Field


class Node(Model):
    __table__ = 'node'

    id = Field()
    title = Field()
    owner_id = Field()
    created_at = Field()
```

### 8. Migration System

Migrations are auto-discovered from `*/migrations/` directories:

**Migration file format:** `XXXX_description.py`

```python
# minager/node/migrations/0001_add_node_table.py
from minager.core.surorm.migrations import MigrationOperation

operations = [
    MigrationOperation(
        'define_table_node',
        'DEFINE TABLE node SCHEMAFULL;'
    ),
    MigrationOperation(
        'define_field_title',
        'DEFINE FIELD title ON TABLE node TYPE string;'
    )
]
```

**Run migrations:**
```bash
poetry run migrate upgrade              # Run all migrations
poetry run migrate upgrade --app node   # Run specific app
poetry run migrate upgrade --number 0001 # Run specific migration
```

## Common Patterns

### Building Complex Queries

**With aliases:**

```python
from minager.core.surorm import Alias

parent_query = surorm.Select('id').from_('->child.out').limit(1)

query = surorm.Select(
    'id',
    'title',
    Alias('parent_id', parent_query)  # AS syntax
).from_(surorm.F.type.thing('node', uid))
```

**With subqueries:**
```python
subquery = surorm.Select('id').from_('node').where('active = true')

query = surorm.Select('*').from_(subquery).limit(10)
```

**Graph traversal:**
```python
# Get all descendants
descendants = surorm.Select('*').from_(
    f'node:{node_id}.{{..+collect+inclusive}}<-child<-node'
)

# Get ancestors (use custom function from migrations)
ancestors = surorm.Select('id', 'title').from_(
    surorm.F.get_ancestors(node_id)  # Custom function
)
```

### Transactions

```python
from minager.core.surorm import Transaction

tx = Transaction(
    surorm.Create('node').content({'title': 'New Node'}),
    surorm.Update('user:123').set('node_count += 1'),
).return_('$node')  # Return variable from transaction

result = await manager.query(tx)
```

### Variables

```python
from minager.core.surorm import Variable

# LET statement
var = Variable('parent_id').value(
    surorm.Select('id').from_('->child.out').limit(1)
)

query = surorm.Select('id', '$parent_id').from_('node')
```

## Known Issues & Workarounds

### 1. Where Clause Order Non-Deterministic

**Issue:** `Filterable._where` uses `set()`, causing non-deterministic query output.

**Location:** `minager/surorm/mixins.py:13`

**Workaround:** Avoid relying on where clause order for testing. Use a single compound condition if order matters.

```python
# Non-deterministic (avoid for tests)
query.where('a = 1', 'b = 2')

# Deterministic
query.where('a = 1 AND b = 2')
```

### 2. Transaction return_() Bug

**Issue:** `Transaction.return_()` always overwrites value (missing `else` on line 31).

**Location:** `minager/surorm/statements/transaction.py:31`

**Current:**
```python
def return_(self, value: Expression) -> Self:
    if isinstance(value, TransactionReturn):
        self._return = value
    self._return = TransactionReturn(value)  # ← Always executes!
    return self
```

**Workaround:** Always pass raw expressions, not `TransactionReturn` objects.

### 3. RecursivePath Not Implemented

**Issue:** `RecursivePath.sql()` returns empty string.

**Workaround:** Use raw graph traversal syntax strings for recursive paths:

```python
# Don't use RecursivePath
query = surorm.Select('*').from_(
    'node:id.{..+collect}<-child<-node'  # Use raw string
)
```

### 4. String Escaping Limited

**Issue:** No comprehensive string escaping for identifiers or values.

**Workaround:** Use parameterized queries with variables:

```python
# Safe - uses parameters
result = await manager.query(
    surorm.Select('*').from_('node').where('title = $title'),
    {'title': user_input}  # Escaped by SurrealDB driver
)

# Unsafe - string interpolation
query.where(f'title = {user_input}')  # DON'T DO THIS
```

## Best Practices

### 1. Use Variables for Dynamic Values

Always use SurrealDB variables (`$name`) instead of string interpolation:

```python
# Good
query = surorm.Select('*').from_('node').where('owner_id = $owner_id')
await manager.query(query, {'owner_id': user_id})

# Bad - potential injection
query = surorm.Select('*').from_('node').where(f'owner_id = {user_id}')
```

### 2. Leverage Mixins for Reusable Behaviors

When creating custom statement classes, use mixins:

```python
from minager.core.surorm import Statement
from minager.core.surorm.mixins import Filterable, Returnable


class CustomQuery(Filterable, Returnable, Statement):
    def sql(self) -> str:
        parts = ['CUSTOM QUERY']
        if filter_expr := self.get_filter_sql():
            parts.append(filter_expr)
        if return_expr := self.get_return_sql():
            parts.append(return_expr)
        return ' '.join(parts)
```

### 3. Keep Complex Queries in Separate Files

For complex domain-specific queries, create query modules:

```python
# minager/node/queries.py
from minager import surorm

# Reusable query fragments
parent_id_query = (
    surorm.Select('id')
    .from_('->child.out')
    .limit(1)
)

def get_node_detail_query(node_id: str):
    return (
        surorm.Select('id', 'title', surorm.Alias('parent_id', parent_id_query))
        .from_(surorm.F.type.thing('node', node_id))
    )
```

### 4. Use Manager as Context Manager

Always use `async with` to ensure proper connection cleanup:

```python
# Good
async with Manager(config) as manager:
    result = await manager.query(query)

# Bad - connection may leak
manager = Manager(config)
await manager.__aenter__()
result = await manager.query(query)
# Forgot to call __aexit__!
```

### 5. Type Hints Everywhere

SurORM uses modern Python type hints - maintain this:

```python
from typing import Self
from minager.core.surorm import Expression


def custom_method(self, value: Expression) -> Self:
    # Type-safe method chaining
    return self
```

## Testing

When testing SurORM queries:

```python
import pytest
from minager.core import surorm


def test_query_building():
    query = surorm.Select('id', 'title').from_('node').where('active = true')

    expected = 'select id,title from node where active = true'
    assert query.sql() == expected


async def test_query_execution(manager):
    query = surorm.Select('*').from_('node').limit(1)
    result = await manager.query(query)
    assert isinstance(result, dict)
```

**Note:** Due to the `set()` bug in where clauses, tests with multiple conditions may be flaky.

## File Structure

```
minager/surorm/
├── __init__.py              # Public API exports
├── base.py                  # Renderable, Function, Statement base classes
├── types.py                 # Type definitions (Expression, etc.)
├── utils.py                 # render() utility
├── constants.py             # Constants
├── mixins.py                # Reusable behaviors (Filterable, Returnable, etc.)
├── core/
│   ├── __init__.py
│   ├── settings.py          # SurrealConfig
│   ├── response.py          # Response handling
│   └── tester.py            # Testing utilities
├── data_model/
│   ├── __init__.py
│   └── object.py            # Data type definitions
├── functions/               # SurrealDB functions
│   ├── __init__.py
│   ├── array.py
│   ├── datetime.py
│   ├── math.py
│   ├── object.py
│   ├── time.py
│   └── type.py
├── migrations/
│   └── __init__.py          # Migration discovery and runner
├── operators/
│   └── __init__.py          # Comparison operators
├── orm/
│   ├── __init__.py
│   ├── field.py             # Field definitions
│   ├── manager.py           # Database manager
│   ├── models.py            # Model base class
│   └── serializers.py       # Data serialization
└── statements/              # Query builders
    ├── __init__.py
    ├── alias.py
    ├── create.py
    ├── define.py
    ├── delete.py
    ├── graph.py
    ├── info.py
    ├── relation.py
    ├── remove.py
    ├── select.py
    ├── transaction.py
    ├── update.py
    └── variable.py
```

## Architecture Notes

**Design Pattern:** Visitor-like pattern where each component renders itself.

**Data Flow:**
1. Build query using fluent API
2. Call `query.sql()` to render to string
3. Execute via `manager.query(sql, variables)`
4. Receive results from SurrealDB

**No intermediate compilation phase:** Queries go directly from objects → strings. This is simple but limits introspection and validation.

## Future Improvements

Consider these enhancements:

1. **Add compilation phase:** `query.compile()` returns validated `CompiledQuery`
2. **Fix critical bugs:** Transaction.return_(), where clause ordering
3. **Improve error handling:** Replace assertions with exceptions
4. **Add query validation:** Check for required fields before rendering
5. **Complete serializer:** Handle all SurrealDB data types
6. **Query optimization:** Detect and optimize common patterns
7. **Better testing:** Comprehensive test suite with mocked SurrealDB
8. **Documentation:** Add docstrings to all public methods

## Related Files

- Main CLAUDE.md: `/Users/sultan/Documents/Projects/minager/api/CLAUDE.md`
- Migration script: `scripts/migrate.py`
- Node queries: `minager/node/queries.py`
- Node manager: `minager/node/managers.py`
- Learning session DB client: `minager/learning_session/db.py`
