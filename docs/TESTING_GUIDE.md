# Testing Guide for Minager

## Overview

This guide explains the testing infrastructure for Minager, particularly for SurrealDB (palace nodes).

## Test Infrastructure

### Database Fixtures

#### SurrealDB Fixtures

1. **`surrealdb_test_config`** (session-scoped)
   - Creates test configuration for SurrealDB
   - Uses separate namespace/database for tests (`_test` suffix)
   - Isolates test data from production

2. **`surrealdb_test_manager`** (session-scoped)
   - Creates PalaceNodeManager with test configuration
   - Runs migrations once per test session
   - Reused across all tests for performance

3. **`palace_node_db`** (function-scoped)
   - Provides clean database for each test
   - Automatically cleans up after test (deletes all nodes and relations)
   - Main fixture to use in tests

4. **`node_factory`** (function-scoped)
   - Factory function for creating test nodes
   - Handles both root nodes and children
   - Auto-generates fake data with Faker

5. **`node_tree_factory`** (function-scoped)
   - Creates complete node trees for testing
   - Configurable depth and breadth
   - Useful for testing tree operations

### PostgreSQL Fixtures

1. **`main_db_test_engine`** (session-scoped)
   - Creates test database and runs Alembic migrations
   - Cleans up after test session

2. **`main_db`** (function-scoped)
   - Provides clean database session
   - Automatic rollback after each test

## Writing Tests

### Basic Node Test

```python
import pytest

@pytest.mark.asyncio
async def test_create_node(palace_node_db, node_factory):
    # Create a node
    node = await node_factory(title='Test Node')

    # Assert
    assert node is not None
    assert node.title == 'Test Node'

    # Query directly
    result = await palace_node_db.get(node.id)
    assert result.id == node.id
```

### Testing with Tree Structure

```python
@pytest.mark.asyncio
async def test_subtree_operation(palace_node_db, node_factory):
    # Create parent with children
    parent = await node_factory(title='Parent')
    child1 = await node_factory(parent_id=parent.id, title='Child 1')
    child2 = await node_factory(parent_id=parent.id, title='Child 2')

    # Test operation
    children = await palace_node_db.get_children(parent.id)
    assert len(children) == 2
```

### Using Tree Factory

```python
@pytest.mark.asyncio
async def test_deep_tree(palace_node_db, node_tree_factory):
    # Create tree with depth=3, 2 children per level
    tree = await node_tree_factory(depth=3, children_per_level=2)

    # Tree structure:
    # root
    #   ├── Node L1 #1
    #   │   ├── Node L2 #1
    #   │   │   ├── Node L3 #1
    #   │   │   └── Node L3 #2
    #   │   └── Node L2 #2
    #   │       ├── Node L3 #3
    #   │       └── Node L3 #4
    #   └── Node L1 #2
    #       └── ...

    assert tree.title == 'Root'
    assert len(tree.children) == 2
```

### Custom Node Data

```python
@pytest.mark.asyncio
async def test_custom_node(palace_node_db, node_factory):
    # Create node with custom fields
    node = await node_factory(
        title='Custom Node',
        content='Custom content',
        order='aaa',
        difficulty=2.5,
        last_rating=4,
    )

    assert node.difficulty == 2.5
    assert node.last_rating == 4
```

## Running Tests

### Run All Tests

```bash
poetry run pytest
```

### Run Specific Test File

```bash
poetry run pytest tests/node/test_move.py
```

### Run Specific Test

```bash
poetry run pytest tests/node/test_move.py::TestMoveNode::test_move_as_first_child
```

### Run with Verbose Output

```bash
poetry run pytest -v
```

### Run with Print Statements

```bash
poetry run pytest -s
```

### Run in Parallel (if pytest-xdist installed)

```bash
poetry run pytest -n auto
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── TESTING_GUIDE.md        # This file
├── node/
│   ├── __init__.py
│   ├── test_move.py        # Move operation tests
│   ├── test_crud.py        # Create/Read/Update/Delete tests
│   └── test_tree.py        # Tree traversal tests
├── auth/
│   └── test_api.py
└── core/
    └── test_lexorank.py
```

### Test Class Organization

Group related tests in classes:

```python
class TestMoveNode:
    """Test suite for moving nodes."""

    async def test_move_as_first_child(self, ...):
        pass

    async def test_move_as_last_child(self, ...):
        pass


class TestMoveNodeEdgeCases:
    """Test edge cases for move operations."""

    async def test_move_nonexistent_node(self, ...):
        pass
```

## Best Practices

### 1. Use Fixtures for Setup

Don't create nodes manually in tests:

```python
# Bad
async def test_something(palace_node_db):
    node_data = {'title': 'Test', 'owner_id': 'test_owner', 'content': 'Test content'}
    node = await palace_node_db.create(node_data)

# Good
async def test_something(palace_node_db, node_factory):
    node = await node_factory(title='Test')
```

### 2. Test One Thing Per Test

```python
# Bad - testing multiple things
async def test_node_operations(palace_node_db, node_factory):
    node = await node_factory()
    assert node.title
    updated = await palace_node_db.update(node.id, {'title': 'New'})
    assert updated.title == 'New'
    await palace_node_db.delete(node.id)
    result = await palace_node_db.get(node.id)
    assert result is None

# Good - separate tests
async def test_create_node(palace_node_db, node_factory):
    node = await node_factory()
    assert node.title

async def test_update_node(palace_node_db, node_factory):
    node = await node_factory()
    updated = await palace_node_db.update(node.id, {'title': 'New'})
    assert updated.title == 'New'

async def test_delete_node(palace_node_db, node_factory):
    node = await node_factory()
    await palace_node_db.delete(node.id)
    result = await palace_node_db.get(node.id)
    assert result is None
```

### 3. Use Descriptive Test Names

```python
# Bad
async def test_move(palace_node_db, node_factory):
    pass

# Good
async def test_move_as_first_child_updates_order_correctly(palace_node_db, node_factory):
    pass
```

### 4. Arrange-Act-Assert Pattern

```python
async def test_something(palace_node_db, node_factory):
    # Arrange - Set up test data
    parent = await node_factory(title='Parent')
    child = await node_factory(parent_id=parent.id, title='Child')

    # Act - Perform the operation
    result = await palace_node_db.get_children(parent.id)

    # Assert - Verify the result
    assert len(result) == 1
    assert result[0].id == child.id
```

### 5. Clean Up Is Automatic

The `palace_node_db` fixture automatically cleans up after each test, so you don't need to manually delete nodes.

### 6. Isolate Tests

Each test should be independent:

```python
# Bad - depends on test execution order
async def test_create(palace_node_db, node_factory):
    global created_node
    created_node = await node_factory()

async def test_update(palace_node_db):
    await palace_node_db.update(created_node.id, {'title': 'Updated'})

# Good - self-contained
async def test_update(palace_node_db, node_factory):
    node = await node_factory()
    updated = await palace_node_db.update(node.id, {'title': 'Updated'})
    assert updated.title == 'Updated'
```

## Debugging Tests

### View SurrealDB Queries

Set `echo=True` in manager (for debugging only):

```python
@pytest.fixture
async def palace_node_db_debug(surrealdb_test_config):
    manager = PalaceNodeManager(surrealdb_test_config)
    manager._echo = True  # If supported
    async with manager:
        yield manager
```

### Print Node State

```python
async def test_debug(palace_node_db, node_factory):
    node = await node_factory()

    # Print node data
    print(f"Node ID: {node.id}")
    print(f"Node data: {node.model_dump()}")

    # Query raw data
    result = await palace_node_db.query(f'SELECT * FROM {node.id};')
    print(f"Raw query result: {result}")
```

### Use pytest-pdb for Debugging

```bash
poetry run pytest --pdb  # Drop into debugger on failure
poetry run pytest --trace  # Drop into debugger at start
```

## Common Issues

### 1. Fixture Not Found

If you see "fixture 'palace_node_db' not found":
- Make sure `conftest.py` is in the tests directory
- Check that the fixture is defined in `conftest.py`

### 2. Connection Errors

If SurrealDB connection fails:
- Ensure SurrealDB is running: `docker ps` or check local process
- Check configuration in `.env.local` or `.env`
- Verify test config namespace is accessible

### 3. Migration Errors

If migrations fail during test setup:
- Check migration files for syntax errors
- Ensure migration dependencies are in correct order
- Verify SurrealDB version compatibility

### 4. Test Isolation Issues

If tests pass individually but fail when run together:
- Check for shared state between tests
- Verify cleanup is working (inspect database after test)
- Use `pytest -x` to stop on first failure

## Performance Tips

### 1. Use Session-Scoped Fixtures for Expensive Setup

The `surrealdb_test_manager` is session-scoped, so migrations run only once.

### 2. Minimize Database Queries

```python
# Bad - multiple queries
async def test_inefficient(palace_node_db, node_factory):
    node1 = await node_factory()
    node2 = await node_factory()
    node3 = await node_factory()

# Good - if possible, use tree factory
async def test_efficient(palace_node_db, node_tree_factory):
    tree = await node_tree_factory(depth=1, children_per_level=3)
    # Creates parent + 3 children efficiently
```

### 3. Use Markers for Slow Tests

```python
@pytest.mark.slow
async def test_large_tree(palace_node_db, node_tree_factory):
    tree = await node_tree_factory(depth=10, children_per_level=5)
```

Run fast tests only:
```bash
poetry run pytest -m "not slow"
```

## CI/CD Considerations

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      surrealdb:
        image: surrealdb/surrealdb:latest
        ports:
          - 8000:8000
        options: >-
          --health-cmd "curl -f http://localhost:8000/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: poetry install
      - run: poetry run pytest
```

## Further Reading

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [SurrealDB documentation](https://surrealdb.com/docs)
- Project CLAUDE.md for architecture details
