# Node Application - Request Pattern Migration Plan

**Status:** Draft
**Created:** 2026-02-25
**Author:** Analysis of current codebase

---

## Executive Summary

The node application currently uses a Request/Config pattern that adds unnecessary abstraction layers. This plan outlines migrating from the Request pattern to direct manager methods, simplifying the codebase and improving maintainability.

**Goals:**
- Reduce code complexity and indirection
- Improve code readability
- Eliminate dead code
- Maintain 100% functionality
- Preserve all business logic

**Estimated Effort:** 8-12 hours
**Risk Level:** Low (well-isolated changes)

---

## Current State Analysis

### Request Pattern Overview

The current pattern consists of:
1. **Config** (TypedDict) - Defines parameters for the operation
2. **Request** (AbstractRequest subclass) - Encapsulates operation logic
3. **Manager** - Calls request.perform() and processes response

**Example - CreateChild Flow:**
```python
# Manager method (managers.py:27-36)
async def create_child(self, parent_uid: str, data: dict) -> NodeDetailSchema:
    config = CreateChildConfig(parent_id=parent_uid, data=data)
    request = CreateChildRequest(db=self, config=config)
    new_node = await request.perform()
    return await self.get(new_node.get('id').id)

# Request class (requests/create_child.py)
class CreateChildRequest(AbstractRequest[CreateChildConfig]):
    async def perform(self) -> dict | None:
        # 46 lines of logic
        ...
```

### Files Inventory

**Currently Used (3 files):**
- `requests/create_child.py` - Used in `managers.py:32`
- `requests/list.py` - Used in `managers.py:59`
- `requests/move.py` - Used in `managers.py:136`

**Dead Code (3 files):**
- `requests/get_detail.py` - Never imported
- `requests/get_palace_root.py` - Never imported
- `requests/get_statistics.py` - Never imported

**Infrastructure (1 file):**
- `requests/abstract.py` - Base class (can be deleted after migration)

---

## Problems with Current Approach

### 1. Unnecessary Indirection
```python
# Current: 3 layers of indirection
API → Manager.create_child() → CreateChildRequest.perform() → Database

# Proposed: 2 layers (standard pattern)
API → Manager.create_child() → Database
```

### 2. Code Duplication
The Manager often duplicates logic:
```python
# Manager wraps request, then calls another manager method
async def create_child(self, parent_uid, data):
    request = CreateChildRequest(db=self, config=config)
    new_node = await request.perform()
    return await self.get(new_node.get('id').id)  # Duplicate get() call
```

### 3. Testing Complexity
- Need to test Request classes separately
- Need to test Manager methods separately
- Config TypedDicts are not validated (dict instead of Pydantic)

### 4. Discoverability
- Logic is split across multiple files
- IDE "Go to Definition" jumps to request, not actual implementation
- Harder to understand flow

### 5. Inconsistency
Some manager methods use requests, others don't:
- `create_child()` - Uses CreateChildRequest ✗
- `create()` - Direct implementation ✓
- `get()` - Direct implementation ✓
- `patch()` - Direct implementation ✓

---

## Migration Strategy

### Phase 1: Remove Dead Code (1 hour)

**Steps:**
1. Delete `requests/get_detail.py`
2. Delete `requests/get_palace_root.py`
3. Delete `requests/get_statistics.py`
4. Run tests to ensure nothing breaks

**Risk:** None (files are not imported anywhere)

---

### Phase 2: Migrate CreateChildRequest (2-3 hours)

**Current Implementation:** `requests/create_child.py` (47 lines)

**Migration Steps:**

1. **Create new manager method** (inline the logic):

```python
# In managers.py
async def create_child(
    self, parent_uid: str, data: dict | schemas.NodeCreateSchema
) -> schemas.NodeDetailSchema | None:
    """
    Create a new child node under the specified parent.

    Args:
        parent_uid: Parent node ID
        data: Node creation data

    Returns:
        Created node with full details
    """
    self._check_connection()

    # Step 1: Get last child order for lexorank calculation
    last_child_order_query = queries.get_last_child_order_query(parent_uid)
    last_child_order: str | list = await self.query(last_child_order_query)

    if isinstance(last_child_order, list):
        last_child_order = last_child_order[0] if last_child_order else None

    # Step 2: Prepare node data with calculated order
    create_data = (
        schemas.NodeCreateSchema.model_validate(data)
        if isinstance(data, dict)
        else data
    )
    create_data.order = Lexorank.middle(previous=last_child_order)

    # Step 3: Create node and relation in transaction
    child_var = surorm.Variable('child')
    create_query = surorm.Transaction(
        surorm.DefineVariable(
            'child',
            surorm.Create('node', only=True).content(
                create_data.model_dump_surreal(exclude_unset=True, exclude_defaults=True)
            ),
        ),
        surorm.Relate('child').from_(child_var).to(surorm.Record('node', parent_uid)),
    ).return_(child_var)

    new_node = await self.query(create_query)

    if not new_node:
        return None

    # Step 4: Return full node details
    return await self.get(new_node.get('id').id)
```

2. **Update imports** - Remove CreateChildRequest, CreateChildConfig imports
3. **Run tests** - Ensure create_child still works
4. **Delete** `requests/create_child.py`

**Benefits:**
- Logic is visible in one place
- Easier to debug
- Better IDE support

---

### Phase 3: Migrate ListNodesRequest (1-2 hours)

**Current Implementation:** `requests/list.py` (37 lines, simplest migration)

**Migration Steps:**

1. **Inline the logic into manager**:

```python
# In managers.py
async def list_(
    self,
    owner_id: str,
    search: str | None = None,
    page: int = 1,
    per_page: int = 10,
) -> list[schemas.NodeListItemSchema] | None:
    """
    List nodes with optional search and pagination.

    Args:
        owner_id: Filter by owner ID
        search: Optional full-text search query
        page: Page number (1-indexed)
        per_page: Results per page

    Returns:
        List of nodes matching criteria
    """
    self._check_connection()

    # Build query
    query = (
        surorm.Select('node')
        .columns(
            'id',
            'title',
            surorm.Alias(
                'parent',
                surorm.Traverse('@')
                .alias('parent')
                .relation('->child->node')
                .columns('id', 'title'),
            ),
        )
        .limit(per_page)
        .start(per_page * (page - 1))
    )

    # Apply filters
    if owner_id:
        query.where(f'owner_id == {surorm.String(owner_id)}')

    if search:
        query.where(f'title @@ {surorm.String(search)}')

    # Execute and parse
    response = await self.query(query.sql())
    nodes = response.data()

    return (
        [schemas.NodeListItemSchema.model_validate(node) for node in nodes]
        if isinstance(nodes, list)
        else None
    )
```

2. **Remove imports and delete** `requests/list.py`

**Benefits:**
- Simplest migration
- Most straightforward code
- Easy to add new filters

---

### Phase 4: Migrate MoveNodeRequest (4-6 hours, most complex)

**Current Implementation:** `requests/move.py` (278 lines)

**Challenge:** This is the most complex request with **Strategy Pattern**:
- 4 move strategies (FirstChild, LastChild, Before, After)
- Each strategy has similar but slightly different logic
- 200+ lines of duplicated code

**Migration Options:**

#### Option A: Keep Strategy Pattern (Recommended)

Move strategies to separate module but integrate with manager:

```python
# Create new file: minager/node/services/move_strategies.py

from abc import ABC, abstractmethod
from minager.core import surorm
from minager.core.lexorank import Lexorank


class MoveStrategy(ABC):
    """Base class for node move operations."""

    def __init__(self, manager, node_id: str, target_id: str):
        self.manager = manager
        self.node_id = node_id
        self.target_id = target_id

    @abstractmethod
    async def execute(self) -> dict:
        """Execute the move operation and return updated node."""
        pass


class MoveAsFirstChild(MoveStrategy):
    async def execute(self) -> dict:
        # Get current first child order
        query = surorm.Select(...).where(...)
        current_first = await self.manager.query(query)

        # Calculate new order
        order = Lexorank.middle(next_=current_first or '')

        # Move node
        return await self._move_with_order(order, self.target_id)

    async def _move_with_order(self, order: str, new_parent_id: str) -> dict:
        """Shared logic for executing move with calculated order."""
        move_query = surorm.Transaction(
            f'delete child where in == node:{self.node_id};',
            f'relate node:{self.node_id}->child->node:{new_parent_id};',
            surorm.DefineVariable(
                'updated',
                f'update only node:{self.node_id} set order = "{order}";'
            ),
        ).return_(...)

        response = await self.manager.query(move_query.sql())
        result = response.data().get('result', {})
        result['parent_id'] = new_parent_id
        return result


class MoveAsLastChild(MoveStrategy):
    async def execute(self) -> dict:
        # Similar to FirstChild but with desc order
        ...


class MoveBefore(MoveStrategy):
    async def execute(self) -> dict:
        # Get target and previous sibling orders
        ...


class MoveAfter(MoveStrategy):
    async def execute(self) -> dict:
        # Get target and next sibling orders
        ...


# Strategy registry
MOVE_STRATEGIES = {
    1: MoveAsFirstChild,    # first_child
    2: MoveAsLastChild,     # last_child
    3: MoveBefore,          # before
    4: MoveAfter,           # after
}
```

Then in manager:

```python
# In managers.py
from .services.move_strategies import MOVE_STRATEGIES

async def move(
    self, node_id: str, target_id: str, move_position: int
) -> schemas.UpdatedNodeSchema | None:
    """
    Move a node to a new position in the tree.

    TODO: Add validation for:
      - Node exists
      - Target exists
      - Not moving node to itself
      - Not creating cycles
      - Not moving node to be its own descendant

    Args:
        node_id: Node to move
        target_id: Target node (parent or sibling depending on position)
        move_position: Position type (1=first_child, 2=last_child, 3=before, 4=after)

    Returns:
        Updated node with new parent and order
    """
    self._check_connection()

    # Get strategy class
    strategy_class = MOVE_STRATEGIES.get(move_position)
    if not strategy_class:
        raise ValueError(f'Invalid move position: {move_position}')

    # Execute move
    strategy = strategy_class(self, node_id, target_id)
    result = await strategy.execute()

    return schemas.UpdatedNodeSchema.model_validate(result) if result else None
```

**Benefits:**
- Keeps strategy pattern (good design)
- Removes Request/Config abstraction
- Moves to more standard service layer
- Can refactor to reduce duplication later

#### Option B: Inline All Logic (Not Recommended)

Put all 4 strategies directly in manager method. This would create a 300+ line method, which is not maintainable.

---

### Phase 5: Cleanup (1 hour)

After all migrations:

1. **Delete infrastructure**:
   - Delete `requests/abstract.py`
   - Delete `requests/__init__.py`
   - Delete `requests/` directory

2. **Update documentation**:
   - Remove request pattern from CLAUDE.md
   - Update architecture docs
   - Add docstrings to new manager methods

3. **Code quality**:
   - Run linters
   - Fix any import issues
   - Verify all tests pass

---

## Testing Strategy

### Before Migration
```bash
# Capture baseline
poetry run pytest tests/node/test_api.py -v > baseline.txt
```

### During Migration
For each phase:

```bash
# Run tests for affected functionality
poetry run pytest tests/node/test_api.py::test_add_child_* -v
poetry run pytest tests/node/test_api.py::test_get_children_* -v
poetry run pytest tests/node/test_api.py::test_move_node_* -v
```

### After Migration
```bash
# Full regression test
poetry run pytest tests/node/test_api.py -v
diff baseline.txt current.txt  # Should be identical
```

### Manual Testing Checklist
- [ ] Create root node
- [ ] Add child node
- [ ] Add multiple children (verify order)
- [ ] Move node as first child
- [ ] Move node as last child
- [ ] Move node before sibling
- [ ] Move node after sibling
- [ ] Search nodes
- [ ] List nodes with pagination
- [ ] Delete node with subtree

---

## Implementation Roadmap

### Sprint 1: Dead Code Removal (Day 1, 1 hour)
- [ ] Delete unused request files
- [ ] Run tests
- [ ] Commit: "Remove unused request files"

### Sprint 2: Simple Migrations (Day 1-2, 3-4 hours)
- [ ] Migrate ListNodesRequest
- [ ] Test list functionality
- [ ] Commit: "Migrate list request to manager"
- [ ] Migrate CreateChildRequest
- [ ] Test create_child functionality
- [ ] Commit: "Migrate create_child request to manager"

### Sprint 3: Complex Migration (Day 2-3, 4-6 hours)
- [ ] Create move_strategies.py service
- [ ] Implement MoveAsFirstChild strategy
- [ ] Implement MoveAsLastChild strategy
- [ ] Implement MoveBefore strategy
- [ ] Implement MoveAfter strategy
- [ ] Update manager.move() method
- [ ] Test all move operations
- [ ] Commit: "Migrate move request to service layer"

### Sprint 4: Cleanup (Day 3, 1 hour)
- [ ] Delete requests/ directory
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Commit: "Complete request pattern migration"

**Total Time:** 1-2 days (8-12 hours)

---

## Rollback Plan

Each phase is isolated and can be rolled back independently:

1. **Git commits** - Each phase is a separate commit
2. **Feature flags** - Not needed (changes are atomic)
3. **Database** - No schema changes, no rollback needed

**Rollback Process:**
```bash
# Revert last commit
git revert HEAD

# Or revert specific phase
git revert <commit-hash>
```

---

## Success Criteria

### Functional
- [ ] All existing tests pass
- [ ] No change in API behavior
- [ ] All node operations work identically

### Code Quality
- [ ] Reduced total lines of code
- [ ] Removed 4-7 files
- [ ] Improved code locality
- [ ] Better IDE navigation

### Performance
- [ ] No performance regression
- [ ] Same or fewer database queries

### Documentation
- [ ] All manager methods have docstrings
- [ ] Architecture docs updated
- [ ] Migration notes in git history

---

## Future Improvements (Post-Migration)

After removing the request pattern, additional improvements become easier:

### 1. Reduce Strategy Duplication
The 4 move strategies have ~70% duplicated code. Could be refactored to:

```python
class MoveStrategy:
    async def execute(self):
        order_info = await self.get_order_info()  # Abstract method
        order = Lexorank.middle(order_info['previous'], order_info['next'])
        return await self._execute_move(order, order_info['parent'])

    @abstractmethod
    async def get_order_info(self) -> dict:
        """Get previous, next, parent info based on strategy."""
        pass
```

### 2. Add Validation Service
Extract validation logic into `services/node_validator.py`:

```python
class NodeMoveValidator:
    async def validate_move(self, node_id: str, target_id: str):
        await self.check_node_exists(node_id)
        await self.check_target_exists(target_id)
        await self.check_not_self(node_id, target_id)
        await self.check_no_cycle(node_id, target_id)
```

### 3. Add Result Types
Replace dict returns with proper types:

```python
@dataclass
class MoveResult:
    node_id: str
    parent_id: str
    order: str
    children: list[dict]
```

### 4. Improve Error Handling
Replace generic exceptions with specific node errors:

```python
class NodeNotFoundError(Exception): pass
class CyclicMoveError(Exception): pass
class InvalidPositionError(Exception): pass
```

---

## Appendix A: Code Size Comparison

### Before Migration
```
requests/abstract.py          14 lines
requests/create_child.py      47 lines
requests/list.py              37 lines
requests/move.py             278 lines
requests/get_detail.py        30 lines (unused)
requests/get_palace_root.py   23 lines (unused)
requests/get_statistics.py    35 lines (unused)
──────────────────────────────────────
Total:                       464 lines
```

### After Migration
```
managers.py additions        ~150 lines (net increase)
services/move_strategies.py  ~200 lines (new file)
──────────────────────────────────────
Total:                       ~350 lines
```

**Net Reduction:** ~114 lines (-24%)
**Files Deleted:** 7
**Files Created:** 1

---

## Appendix B: Alternative Approaches Considered

### Approach 1: Keep Request Pattern but Modernize
**Pros:** Less code change
**Cons:** Still maintains unnecessary abstraction
**Decision:** Rejected - doesn't solve the core problem

### Approach 2: Move to Service Layer Only
**Pros:** Clean separation of concerns
**Cons:** Adds another layer (Manager → Service → Database)
**Decision:** Rejected - for now, inline into manager. Can extract services later if needed

### Approach 3: Use FastAPI Depends for Requests
**Pros:** Uses framework features
**Cons:** Requests aren't dependency injection candidates
**Decision:** Rejected - misuse of Depends

---

## Questions & Answers

**Q: Why not keep the request pattern?**
A: It adds indirection without providing value. The pattern makes sense for complex command objects with undo/redo, but node operations are simple CRUD.

**Q: Won't manager methods become too large?**
A: For simple operations (create_child, list), no. For complex operations (move), we extract to service layer instead of request pattern.

**Q: What about testability?**
A: Manager methods are already tested through API tests. No loss of testability.

**Q: Can we do this incrementally?**
A: Yes! Each phase is independent. Can migrate one request at a time.

**Q: What if we need the pattern later?**
A: Git history preserves it. Can reintroduce if genuinely needed. But unlikely - pattern hasn't added value in practice.

---

## Conclusion

The request pattern was likely introduced with good intentions (separation of concerns, testability), but in practice it adds complexity without benefit. Modern FastAPI + Manager pattern is sufficient for node operations.

**Recommendation:** Proceed with migration in 4 sprints over 1-2 days.

**Next Steps:**
1. Review this plan with team
2. Schedule 1-2 day sprint for migration
3. Create feature branch: `feature/remove-request-pattern`
4. Execute phases 1-5
5. Code review and merge

---

**Document Version:** 1.0
**Last Updated:** 2026-02-25
