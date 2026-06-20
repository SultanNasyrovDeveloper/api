# Learning Session Strategy

## Motivation

The current session implementation generates a flat shuffled queue of up to 50 nodes from a subtree. This is functional but ignores the structure of the knowledge tree and wastes session time on nodes that aren't due for review. The goal is to make sessions more purposeful by separating two orthogonal concerns: **what nodes to include** and **in what order to visit them**.

---

## Two Orthogonal Concepts

```
Session queue = FILTER (what nodes) + TRAVERSAL ORDER (how to visit them)
```

These compose independently. A "Due + BFS" session reviews only overdue nodes but visits them breadth-first. An "All + Random" session targets the full subtree in random order. This gives flexibility without combinatorial complexity in the codebase.

---

## Session Types

Sessions have two distinct types with different interaction models.

**Review session** (default)
- Goal: test recall and update SM2 data
- User rates recall quality (0–5) via `perform_repetition`
- SM2 algorithm updates difficulty, interval, next repetition date
- Always excludes empty nodes (`size == 0`) — reviewing empty content is meaningless
- Supports `bad_repetition_queue` for nodes rated < 3

**Fill session**
- Goal: write content for empty nodes
- Always targets only empty nodes (`size == 0`) — type implies filter
- User signals `filled` or `skipped` via `perform_repetition` (action-only, no rating)
- No SM2 update on completion
- No `bad_repetition_queue` — skipped nodes are dropped, not re-queued
- `filter_strategy` is ignored (fill is always `size == 0`)

Combined session type (fill + review in one session) is deferred — needs more design work.

---

## Enums

### `SessionType`
| Value | Description |
|---|---|
| `review` | Default. Test recall, SM2 update |
| `fill` | Write content for empty nodes |

### `FilterStrategy` (review sessions only)
| Value | Condition | Default |
|---|---|---|
| `all` | No filter — full subtree | ✅ |
| `due` | `next_optimal_repetition <= now` | |
| `struggle` | `repetitions >= 3 AND last_rating < 3` | |
| `first_encounter` | `repetitions == 0` | |

### `TraversalOrder`
| Value | Description | Default |
|---|---|---|
| `random` | Simple shuffle | ✅ |
| `bfs` | Level-by-level (free via SurrealDB `{..+collect}` natural order) | |

`branch_grouped` (DFS approximation) is deferred — requires extra child lookup per repetition and no batching is available.

---

## Queue

- Type: `list[str]` (node IDs) — unchanged
- Cap: configured via env variable, default 50. Always applied regardless of filter strategy — a large subtree can produce hundreds of matches even under `due` or `struggle`.
- `regenerate_queue` is the natural continuation mechanism when the queue drains.

---

## Model Changes

Single `LearningSession` model (no split). Changes:
- Add `session_type: SessionType` (default `review`)
- Replace `traverse_strategy` with `filter_strategy: FilterStrategy` (default `all`) and `traversal_order: TraversalOrder` (default `random`)
- `bad_repetition_queue` stays — semantically review-only, ignored for fill sessions
- Delete `TraverseStrategy` enum entirely (was never implemented)

---

## `perform_repetition` Refactor

Single unified endpoint for both session types.

**Request payload (flat):**
```
{
  node_id: str,
  rating?: int (0–5),   # review sessions
  action?: "filled" | "skipped"  # fill sessions
}
```

Validation of correct fields (rating vs. action) happens server-side after loading the session. Manager dispatches to the appropriate strategy class based on `session_type`.

**Strategy classes** (in `repetition/`):
- `sm2.py` — existing SM2 review logic (unchanged)
- `fill.py` — new, action-only, no SM2 update

---

## `get_subtree_ids` Changes

Add conditional `WHERE` clause based on `filter_strategy` and conditional `ORDER BY` based on `traversal_order`.

| filter_strategy | WHERE clause |
|---|---|
| `all` | none |
| `due` | `next_optimal_repetition <= time::now()` |
| `struggle` | `repetitions >= 3 AND last_rating < 3` |
| `first_encounter` | `repetitions == 0` |

Fill sessions always use `WHERE size == 0`.

| traversal_order | ORDER BY |
|---|---|
| `random` | none (shuffle in Python after fetch) |
| `bfs` | none (SurrealDB `{..+collect}` returns BFS order naturally — remove current `ORDER BY next_optimal_repetition`) |

---

## Session Start Defaults

| Field | Default |
|---|---|
| `session_type` | `review` |
| `filter_strategy` | `all` |
| `traversal_order` | `random` |
