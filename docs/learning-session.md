# Learning Session Application

## Overview

The Learning Session application is a core component of Minager that implements spaced repetition learning for palace nodes. It manages active learning sessions, generates queues of nodes to review, tracks repetition performance, and applies spaced repetition algorithms to optimize learning schedules.

The application uses MongoDB for session storage and integrates with the Palace Node service to retrieve node information and update learning statistics.

## Architecture

### Database
- **Database Type**: MongoDB
- **Connection**: Async Motor driver (`motor_asyncio`)
- **Collection**: `session`
- **Configuration**: Via `DBConnectionConfig` with environment variable `LEARNING_SESSION_DB__*`

### Key Components

```
minager/learning_session/
├── api.py                    # FastAPI router and endpoints
├── db.py                     # LearningSessionClient (MongoDB operations)
├── schemas.py                # Pydantic models for data validation
├── enums.py                  # Enums for strategies
├── fields.py                 # Custom Pydantic field types (MongoDBId)
├── utils.py                  # Utility functions (shuffle)
└── repetition/               # Spaced repetition algorithms
    ├── base.py               # BaseLearningStrategy interface
    └── sm2.py                # SuperMemo2 implementation
```

## Core Concepts

### Learning Session

A learning session represents an active study session for a user. It contains:
- **Target node**: The root node of the subtree to study
- **Current node**: The node currently being reviewed
- **Queue**: Ordered list of node IDs to review next
- **Bad repetition queue**: Nodes that were rated poorly (rating < 3) and need re-review
- **Strategies**: Traverse and repetition strategies to use
- **Activity tracking**: Start time, last activity time, and finish time
- **Status**: Whether the session is active or completed

### Queue Management

The application maintains two queues:

1. **Main Queue** (`queue`): Contains nodes from the target subtree that haven't been reviewed yet
2. **Bad Repetition Queue** (`bad_repetition_queue`): Contains nodes that received poor ratings (< 3)

**Queue Flow**:
1. When a session starts, fetch subtree node IDs (up to 50) from the target node
2. Shuffle the nodes using a batch-based shuffle algorithm (10% batches)
3. Pop the first node as `current_node`, remaining nodes go to `queue`
4. After each repetition:
   - If rating >= 3: Move to next node in queue
   - If rating < 3: Add node to bad repetition queue
5. When main queue is empty, switch to bad repetition queue
6. Session ends when both queues are empty or user manually finishes

### Spaced Repetition

The application uses the **SuperMemo2 (SM2)** algorithm to calculate optimal repetition intervals.

**Node Metadata** (stored in palace nodes):
- `difficulty`: Node difficulty factor (default: 2.5)
- `last_interval`: Days until next optimal repetition
- `next_optimal_repetition`: Calculated next review date
- `repetitions`: Total number of times reviewed
- `cpr`: Consecutive Positive Ratings (resets to 0 on rating < 3)
- `last_repetition`: Timestamp of last review

**Rating Scale**: 0-5 (where 3+ is considered "passing")

## Database Schema

### LearningSessionSchema (MongoDB Document)

```python
{
    "_id": ObjectId,                          # MongoDB ID
    "is_active": bool,                        # Whether session is active
    "user_id": str,                           # Owner user ID
    "start_datetime": datetime,               # When session started
    "last_activity_datetime": datetime,       # Last interaction time
    "finish_datetime": datetime | None,       # When session finished
    "current_node": str | None,               # Current node ID being reviewed
    "target": str,                            # Root node ID of subtree
    "queue": list[str],                       # Main review queue
    "bad_repetition_queue": list[str],        # Nodes needing re-review
    "traverse_strategy": TraverseStrategy,    # How to order nodes (default: outdated)
    "repetition_strategy": RepetitionStrategy # Which algorithm to use (default: sm2)
}
```

## API Endpoints

### GET `/learning-sessions/active`

Get the user's currently active learning session.

**Response**: `LearningSessionSchema` (without `queue` field) or `null`

**Behavior**:
- Returns active session for authenticated user
- Automatically finishes sessions inactive for > 1 hour
- Returns `null` if no active session or session expired

---

### POST `/learning-sessions/start`

Start a new learning session.

**Request Body**:
```json
{
    "target": "node:xyz"  // Root node ID
}
```

**Response**: `LearningSessionSchema` (without `queue` field)

**Behavior**:
1. Check if user already has an active session
2. If active session exists and not expired, return it
3. If active session expired, finish it automatically
4. Fetch subtree node IDs from target (limit: 50)
5. Shuffle nodes using batch-based algorithm
6. Create new session with first node as current, rest in queue

---

### POST `/learning-sessions/{id}/generate-queue`

Regenerate the session queue from the target subtree.

**Response**: `LearningSessionSchema` (without `queue` field)

**Behavior**:
- Fetches fresh subtree node IDs
- Shuffles and replaces current queue
- Resets current node to first in new queue

---

### POST `/learning-sessions/{id}/repeat`

Record a repetition for the current node.

**Request Body**:
```json
{
    "node_id": "node:xyz",
    "rating": 3  // 0-5
}
```

**Response**: `LearningSessionSchema` (without `queue` field)

**Behavior**:
1. Validate node is in session
2. Apply SM2 algorithm to calculate new difficulty and interval
3. Update node metadata in palace node service:
   - `last_repetition`
   - `difficulty`
   - `last_interval`
   - `next_optimal_repetition`
   - `repetitions` (increment)
   - `cpr` (increment if rating >= 3, else reset to 0)
4. Update session:
   - Remove node from queue if present
   - If node is current_node, advance to next node
   - Add to bad_repetition_queue if rating < 3
   - Update `last_activity_datetime`

---

### POST `/learning-sessions/{id}/finish`

Manually finish a learning session.

**Response**: `LearningSessionSchema` (without `queue` field)

**Behavior**:
- Sets `is_active` to `false`
- Sets `finish_datetime` to current time
- Clears `current_node` and `queue`

## LearningSessionClient

The `LearningSessionClient` class in `db.py` handles all MongoDB operations and business logic.

### Initialization

```python
client = LearningSessionClient(
    config=DBConnectionConfig,
    palace_client=PalaceNodeServiceClient
)
```

**Dependencies**:
- `DBConnectionConfig`: MongoDB connection settings
- `PalaceNodeServiceClient`: Interface to palace node service for node operations

### Key Methods

#### `get_my_active_session(user_id: str) -> LearningSessionSchema | None`
- Finds active session for user
- Auto-expires sessions inactive > 1 hour
- Returns `None` if no active session or expired

#### `start(user_id: str, data: dict) -> LearningSessionSchema`
- Creates new learning session
- Prevents duplicate active sessions per user
- Generates initial queue from target subtree

#### `perform_repetition(session_id, node_id, rating, user_id) -> LearningSessionSchema`
- Records node repetition
- Applies SM2 algorithm
- Updates node metadata in palace service
- Manages queue advancement and bad repetition queue

#### `regenerate_queue(id_: str) -> LearningSessionSchema`
- Fetches fresh subtree from target
- Regenerates and shuffles queue
- Useful when tree structure changes

#### `finish(id_: str) -> LearningSessionSchema`
- Marks session as inactive
- Clears current node and queues
- Sets finish timestamp

## Spaced Repetition: SuperMemo2 Algorithm

Implementation in `repetition/sm2.py`.

### Algorithm Details

Based on the [SuperMemo2 algorithm](https://www.supermemo.com/ru/archives1990-2015/english/ol/sm2).

**Inputs**:
- `node`: Current node with learning metadata
- `rating`: User's quality rating (0-5)

**Outputs** (`StudyNodeResult`):
- `difficulty`: New difficulty factor
- `interval`: Days until next optimal review
- `next_repetition`: Calculated next review datetime

### Calculation Logic

```python
if rating >= 3:  # Positive rating
    # Update difficulty using SM2 formula
    new_difficulty = difficulty + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))

    # Calculate interval based on consecutive positive ratings
    if cpr == 0:
        interval = 1  # First positive: repeat tomorrow
    elif cpr == 1:
        interval = 4  # Second positive: 4 days (SM2 suggests 6)
    else:
        interval = last_interval * difficulty
else:  # Negative rating (< 3)
    interval = 1  # Reset to tomorrow
    # Difficulty unchanged

next_repetition = now() + timedelta(days=interval)
```

**Key Points**:
- Difficulty clamped to 1 decimal place
- `cpr` (consecutive positive ratings) determines interval growth
- First positive repetition: 1 day
- Second positive repetition: 4 days
- Subsequent: interval grows multiplicatively by difficulty factor
- Negative ratings reset interval to 1 day

### Differences from Standard SM2

1. **Modified second interval**: Uses 4 days instead of SM2's 6 days
2. **Difficulty rounding**: Quantized to 1 decimal place
3. **No minimum difficulty**: Standard SM2 typically has a floor of 1.3

## Enums

### RepetitionStrategy
```python
class RepetitionStrategy(IntEnum):
    sm2 = 1  # SuperMemo2 algorithm
```

Currently only SM2 is implemented, but the design allows for additional strategies.

### TraverseStrategy
```python
class TraverseStrategy(IntEnum):
    random = 1    # Random order
    outdated = 2  # Prioritize nodes overdue for review (default)
    dfs = 3       # Depth-first search order
    newest = 4    # Newest nodes first
```

**Note**: Current implementation doesn't fully utilize traverse strategies. Queue generation currently just shuffles the subtree nodes. This is a potential area for future enhancement.

## Utility Functions

### shuffle(array: list) -> list
Custom shuffle implementation in `utils.py`.

**Algorithm**:
1. Divide array into 10% batches (minimum batch size: 1)
2. Randomly shuffle within each batch
3. Concatenate shuffled batches

**Purpose**: Provides partial randomization while maintaining some locality. This is useful for:
- Keeping related nodes somewhat together
- Avoiding extreme randomization that might break conceptual groupings
- Balancing variety with coherent learning sequences

**Example**:
```python
# Input: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# 10% batches = 1 item each, so equivalent to full shuffle

# Input: [1..100]
# 10% batches = 10 items each
# Batch 1: [1..10] shuffled within batch
# Batch 2: [11..20] shuffled within batch
# etc.
```

## Integration Points

### Palace Node Service

The learning session application depends on the palace node service through `PalaceNodeServiceClient`.

**Used Methods**:
- `get_subtree_ids(node_id: str, limit: int) -> list[str]`: Fetch nodes to review
- `get(node_id: str) -> NodeDetailSchema`: Get node details for repetition
- `update(node_id: str, data: dict) -> NodeDetailSchema`: Update node metadata after repetition

### Application State

Registered in `minager/lifespan.py`:

```python
app.state.learning_session = LearningSessionClient(
    config=settings.LEARNING_SESSION_DB,
    palace_client=palace_node_client
)
```

Accessed in API endpoints via dependency injection:
```python
async def endpoint(app: App, user: RequestUser):
    client = app.state.learning_session
```

## Session Lifecycle

```
1. User requests to start session
   └─> POST /learning-sessions/start {"target": "node:xyz"}

2. System fetches subtree nodes (limit: 50)
   └─> palace_client.get_subtree_ids("node:xyz", 50)

3. Nodes shuffled and session created
   ├─> current_node = shuffled[0]
   ├─> queue = shuffled[1:]
   └─> is_active = True

4. User reviews current node
   └─> POST /learning-sessions/{id}/repeat {"node_id": "...", "rating": 4}

5. System updates node metadata
   ├─> Apply SM2 algorithm
   ├─> Update palace node (difficulty, interval, etc.)
   └─> Advance to next node in queue

6. If rating < 3
   └─> Add node to bad_repetition_queue

7. When main queue empty
   └─> Switch to bad_repetition_queue

8. User finishes session (or auto-expires after 1 hour)
   └─> POST /learning-sessions/{id}/finish
   └─> is_active = False
```

## Configuration

Environment variables (using `__` nested delimiter):

```bash
LEARNING_SESSION_DB__HOST=localhost
LEARNING_SESSION_DB__PORT=27017
LEARNING_SESSION_DB__NAME=learning_sessions
LEARNING_SESSION_DB__USER=username
LEARNING_SESSION_DB__PASSWORD=password
```

Connection string format: `mongodb://user:pass@host:port/database`

## Error Handling

### Session Expiration
- Sessions automatically expire after 1 hour of inactivity
- Checked on `get_my_active_session()` calls
- Expired sessions are auto-finished

### Duplicate Sessions
- Only one active session per user allowed
- Starting a new session returns existing active session if not expired

### Invalid Node IDs
- Node validation delegated to palace node service
- Invalid IDs will raise errors from palace_client calls

## Future Enhancements

### Traverse Strategies
The `TraverseStrategy` enum defines multiple strategies, but current implementation only uses basic shuffling. Potential implementations:

1. **Outdated**: Sort by `next_optimal_repetition`, prioritize overdue nodes
2. **DFS**: Traverse tree depth-first, maintaining hierarchical relationships
3. **Newest**: Sort by creation date descending
4. **Random**: Full random shuffle (already partially implemented)

### Queue Size
- Current limit: 50 nodes per session
- Could be made configurable or dynamic based on user preferences

### Multiple Active Sessions
- Allow multiple concurrent sessions for different target nodes
- Would require updating uniqueness constraint from `user_id + is_active` to include `target`

### Repetition History
- Currently only tracks metadata on nodes themselves
- Could add separate collection for detailed repetition history logs
- Would enable analytics: learning curves, difficulty progression, optimal intervals

### Advanced Algorithms
- SM-15, SM-17 (newer SuperMemo algorithms)
- Anki's algorithm
- Custom adaptive algorithms based on user performance patterns

### Session Analytics
- Time spent per node
- Average rating per session
- Completion rate
- Difficulty progression over time

### Interruption Handling
- Save partial progress more frequently
- Allow resuming from interrupted sessions
- Checkpoint queue state

## Testing

Currently, there are no tests in `tests/learning_session/`. Recommended test coverage:

1. **Unit Tests**:
   - SM2 algorithm calculations
   - Queue management logic
   - Shuffle algorithm behavior
   - Session expiration logic

2. **Integration Tests**:
   - Full session lifecycle
   - MongoDB operations
   - Palace node service integration
   - API endpoint responses

3. **Edge Cases**:
   - Empty subtrees
   - Single-node trees
   - Bad repetition queue exhaustion
   - Concurrent session attempts
   - Expired session handling

## Dependencies

**Direct**:
- `motor`: Async MongoDB driver
- `pymongo`: MongoDB utilities (ReturnDocument, ObjectId)
- `pydantic`: Schema validation and serialization
- `fastapi`: API framework

**Internal**:
- `minager.core.clients.palace`: Palace node service client
- `minager.core.settings.db`: Database configuration
- `minager.node.schemas`: Node data models

## Code Quality Notes

### TODO Comments
1. Line 16 in `db.py`: "Move to some factory method"
   - `learning_strategy` is a global singleton
   - Should be injected or created via factory for better testability

2. Line 57 in `api.py`: "Consider returning only new current node cause only this value actually changes"
   - Current implementation returns full session schema
   - Could optimize response size by returning delta

### Design Patterns

**Client Pattern**: `LearningSessionClient` encapsulates MongoDB operations
- Pros: Clear separation of concerns, testable
- Cons: Couples business logic with data access (could split into repository + service)

**Strategy Pattern**: `BaseLearningStrategy` with `SuperMemo2LearningStrategy` implementation
- Allows plugging in different spaced repetition algorithms
- Clean extensibility point

**Dependency Injection**: FastAPI dependencies for user auth and app state
- Clean, testable, follows framework conventions

### Potential Improvements

1. **Separate business logic from data access**: Create a service layer between API and client
2. **Add input validation**: More comprehensive validation for node_id, rating ranges
3. **Add logging**: Structured logging for session events and errors
4. **Add metrics**: Track session duration, node throughput, rating distribution
5. **Optimize MongoDB queries**: Add indexes on `user_id + is_active`, `user_id + last_activity_datetime`
6. **Type safety**: More precise types for node IDs (potentially NewType or custom classes)
7. **Error messages**: More descriptive error responses for common failure cases

## Summary

The Learning Session application is a well-structured spaced repetition system built on MongoDB. It implements the SuperMemo2 algorithm to optimize learning schedules, manages review queues intelligently (including a bad repetition queue for struggling items), and integrates cleanly with the palace node service.

The architecture is extensible with clear interfaces for adding new repetition algorithms and traverse strategies. The main areas for improvement are completing the traverse strategy implementations, adding comprehensive tests, and potentially separating business logic into a dedicated service layer.
