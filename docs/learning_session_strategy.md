# Learning Session Strategy

## Motivation

The current session implementation generates a flat shuffled queue of up to 50 nodes from a subtree. This is functional but ignores the structure of the knowledge tree and wastes session time on nodes that aren't due for review. The goal is to make sessions more purposeful by separating two orthogonal concerns: **what nodes to include** and **in what order to visit them**.

---

## Two Orthogonal Concepts

```
Session queue = FILTER (what nodes) + TRAVERSAL ORDER (how to visit them)
```

These compose independently. A "Due + BFS" session reviews only overdue nodes but visits them breadth-first. A "Fill + Random" session targets empty nodes in random order. This gives flexibility without combinatorial complexity in the codebase.

---

## Session Types

Before filter strategies, there is a higher-level distinction: sessions can have different **purposes** with different semantics.

**Review session** (current)
- Goal: test recall and update SM2 data
- User rates recall quality (0–5)
- SM2 algorithm updates difficulty, interval, next repetition date

**Fill session**
- Goal: write content for empty nodes
- User fills in content, not rating recall
- End action is "filled" or "skipped", not a 0–5 rating
- SM2 fields may not be updated

These are different enough in intent that they may warrant separate session types rather than being collapsed into a single model with a strategy flag.

---

## Filter Strategies

Determine which nodes from the subtree enter the queue.

| Strategy | Condition | Use case |
|---|---|---|
| **Due** | `next_optimal_repetition <= now` | Core SM2 — only review what's scheduled |
| **All** | no filter | Current behavior, full subtree |
| **Struggle** | `repetitions >= 3` and `last_rating < 3` | Remediation — nodes that won't stick |
| **First encounter** | `owner_views == 0` or `repetitions == 0` | Initial pass on newly added content |
| **Fill** | `size == 0` | Content creation session |

The existing `_strategy` parameter placeholder in `get_subtree_ids` is where this logic hooks in.

---

## Traversal Order

Determines the order of the filtered node set. Orthogonal to filter strategy.

**Random** (current)
- Simple shuffle. No structure awareness.

**BFS**
- Visits nodes closest to the subtree root first, then deeper levels.
- Nearly free: SurrealDB's `{..+collect}` modifier already returns nodes in BFS (level-by-level) order. Removing the current `ORDER BY next_optimal_repetition` override gives BFS for free.
- Sibling order within each level is not controllable from SurrealQL — acceptable tradeoff.

**Branch-grouped / nearly DFS**
- Goal: keep related nodes together so the user studies a topic continuously rather than jumping across branches.
- Strict DFS is not required. A branch-aware approximation achieves the same UX benefit.
- Discussed approach: store a traversal stack on the session document itself. Session starts with root's direct children on the stack. As each node is reviewed, its children are pushed to the stack (piggybacked onto the existing `get(node_id)` call in `perform_repetition` — no extra DB round trip). The stack stays small at all times (bounded by tree depth × branching factor, not total node count).
- Full strict DFS ordering is not the target. The goal is grouping by branch, which this achieves efficiently.

---

## Current State

- `TraverseStrategy` enum exists: `random`, `outdated`, `dfs`, `newest` — none fully implemented beyond shuffle.
- `get_subtree_ids` has a `_strategy` placeholder parameter.
- Session model has `traverse_strategy` and `repetition_strategy` fields already.

---

## Open Questions

- Should fill sessions be a separate session type in the model, or a filter strategy on a review session?
- What is the right default queue size per strategy? Due naturally self-limits; All needs a cap.
- Should traversal order be exposed as a separate field on the session, or collapsed into named presets for simpler API?
