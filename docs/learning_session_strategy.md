# Learning Session Strategy

## Motivation

The current session implementation generates a flat shuffled queue of up to 50 nodes from a single subtree. This ignores the structure of the knowledge tree and wastes session time on nodes that aren't due for review. The goal is to make sessions more purposeful by separating two orthogonal concerns: **what nodes to include** and **in what order to visit them**.

---

## Session Roots

A session now targets **one or more root nodes** rather than a single root. Each root contributes its full subtree to the session. Filters and traversal order apply uniformly across all roots.

Ordering between roots (which root's subtree is visited first) follows the same ordering rules as any other node — roots are treated as top-level entries in the traversal, not as a special case.

---

## Two Orthogonal Concepts

```
Session queue = FILTER (what nodes) + TRAVERSAL ORDER (how to visit them)
```

These compose independently. A "Due + BFS" session reviews only overdue nodes visiting them breadth-first. A "Fill + Random" session targets empty nodes in random order. This gives flexibility without combinatorial complexity in the codebase.

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

Determine which nodes from the subtree(s) enter the queue. Applied uniformly across all session roots — each root's subtree is queried, results are unioned.

| Strategy | Condition | Use case |
|---|---|---|
| **Due** | `next_optimal_repetition <= now` | Core SM2 — only review what's scheduled |
| **All** | no filter | Full subtree across all roots |
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
- Visits nodes closest to their subtree root first, then deeper levels.
- Nearly free: SurrealDB's `{..+collect}` modifier already returns nodes in BFS (level-by-level) order. Removing the current `ORDER BY next_optimal_repetition` override gives BFS for free.
- With multiple roots, BFS is applied per root sequentially — one root's subtree is finished before moving to the next. Interleaving BFS across roots would mix unrelated topics at the same depth, which is bad for learning.
- Sibling order within each level is not controllable from SurrealQL — acceptable tradeoff.

**Branch-grouped / nearly DFS**
- Goal: keep related nodes together so the user studies a topic continuously rather than jumping across branches.
- Strict DFS is not required. A branch-aware approximation achieves the same UX benefit with less implementation complexity.
- Implemented as a traversal stack stored on the session document. Session starts with all roots pushed to the stack (reversed by intended order). As each node is reviewed, its children are pushed to the stack, piggybacked onto the existing `get(node_id)` call in `perform_repetition` — no extra DB round trip. The stack stays small at all times (bounded by depth × branching factor, not total node count).
- Multiple roots are handled naturally: roots are just the first entries on the stack. The algorithm is unchanged; roots behave like top-level nodes.

---

## Queries

> **Status:** these queries are written against SurrealDB 2.x syntax (matching `surrealdb = "^2.0.0"` in `pyproject.toml`) and the recursive-path idiom already in use in `node/queries.py` and `node/managers.py`. They have **not** been validated with `surreal validate` — the locally installed CLI is 1.5.3, which predates the recursive-path idiom and rejects `{..+collect}`. Validate against a 2.x CLI or a live instance before relying on them.

### Relevant graph shape

The `child` relation points **from child to parent** (`in_` = child, `out` = parent). Therefore:

| Expression | Meaning |
|---|---|
| `->child.out` | Parent node ID |
| `<-child<-node` | Direct child nodes |
| `$node.{..+collect+inclusive}<-child<-node` | All descendants, BFS-ordered, including `$node` itself |

### Two ways to filter — pick the right one

This distinction matters and is easy to get wrong:

```surql
-- (A) Post-collect filter: traverse the WHOLE subtree, then keep matching nodes.
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE size = 0;

-- (B) Edge-level filter: PRUNES traversal — descent stops at the first
--     non-matching node, so matching descendants below it are never reached.
SELECT VALUE id FROM $root.{..+collect+inclusive}<-(child WHERE ...)<-node;
```

**All filter strategies below use form (A).** An empty node may well have non-empty ancestors; pruning on the filter condition would silently drop most of the queue. Form (B) is only appropriate if you deliberately want to stop descending a branch.

### Filter strategies

Each takes a single `$root`. Multiple roots are run as one query per root, concatenated in Python (see below).

```surql
-- Common prelude
LET $root = type::thing('node', $root_id);
```

**All** — current behavior, no filter.

```surql
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node;
```

**Due** — nodes whose SM2 schedule has come up. `next_optimal_repetition` is unset on never-reviewed nodes, so they are excluded here; use *First encounter* for those.

```surql
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE next_optimal_repetition != NONE
  AND next_optimal_repetition <= time::now();
```

**Struggle** — reviewed repeatedly, still failing.

```surql
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE repetitions >= 3 AND last_rating < 3;
```

**First encounter** — never seen or never reviewed.

```surql
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE owner_views = 0 OR repetitions = 0;
```

**Fill** — empty nodes, for a content-creation session.

```surql
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE size = 0;
```

### Traversal orders

**BFS** — free. `{..+collect}` documents that it returns each node once, ordered by distance from the origin (closest first). So the filter query above, **with no `ORDER BY`**, is already BFS.

The current `get_subtree_ids` adds `ORDER BY next_optimal_repetition`, which destroys that ordering. Removing it is the entire BFS implementation.

```surql
-- BFS + Due, one root. No ORDER BY.
LET $root = type::thing('node', $root_id);
SELECT VALUE id FROM $root.{..+collect+inclusive}<-child<-node
WHERE next_optimal_repetition != NONE
  AND next_optimal_repetition <= time::now()
LIMIT $limit;
```

Caveat: `+collect` guarantees ordering *between* depth levels, not *within* one. Sibling order (the lexorank `order` field) is not preserved and cannot be enforced from SurrealQL during traversal.

**Random** — same query, shuffled in Python (current `utils.shuffle`), or `ORDER BY rand()` server-side.

**Branch-grouped** — not a single query. Two queries, run at different times.

*(1) Session start — seed the stack with each root's direct children, correctly sibling-ordered:*

```surql
LET $root = type::thing('node', $root_id);
SELECT VALUE id FROM $root<-child<-node ORDER BY order ASC;
```

*(2) On each repetition — fetch the node and its children in one round trip.* This is the piggyback that avoids an extra DB hit: `perform_repetition` already calls `palace_client.get(node_id)`, so it returns children alongside the node data.

```surql
LET $node = type::thing('node', $node_id);
RETURN {
    node: (SELECT * FROM $node)[0],
    children: (SELECT VALUE id FROM $node<-child<-node ORDER BY order ASC),
};
```

Python pushes `children` reversed onto the session's traversal stack, then pops the next `current_node`. Filter strategies compose here by testing each child against the filter before pushing — or by pushing all and skipping non-matching nodes on pop.

### Multiple roots

Traversal is per-root sequential by design (see Traversal Order above), so the natural implementation is one query per root, concatenated in root order:

```python
node_ids = []
for root_id in session.targets:
    node_ids.extend(await palace_client.get_subtree_ids(root_id, strategy, limit))
```

A single-query union over all roots is possible but not obviously worth it: it would need `array::flatten` over a per-root subquery, it complicates applying a per-root `LIMIT`, and the round-trip saving is negligible for the handful of roots a session realistically has.

### Indexing

`next_optimal_repetition`, `size`, `repetitions`, and `last_rating` are filtered post-collect — the traversal itself drives node retrieval, so a standard index on these fields will not accelerate the recursive path. Do not add indexes for these strategies speculatively; measure first.

### surorm builder equivalent

The queries above are shown as raw SurrealQL for readability. In the codebase they are built with `surorm`, following the existing `get_subtree_ids` shape:

```python
query = surorm.Transaction(
    surorm.DefineVariable('root', surorm.F.type.thing('node', root_id)),
    surorm.DefineVariable(
        'descendants',
        surorm.Select('id')
        .from_(f'{surorm.Variable("root")}.{{..+collect+inclusive}}<-child<-node')
        .where('size = 0')   # ← filter strategy plugs in here
        .limit(limit),       # ← no order_by: preserves BFS
    ),
).return_(surorm.Variable('descendants'))
```

The `_strategy` placeholder parameter already present on `get_subtree_ids` is where the `.where(...)` clause is selected.

---

## Impact of Multiple Roots on Implementation

| Concern | Impact |
|---|---|
| Filter strategies | Minor — union results across N subtree queries |
| BFS traversal | Minor — process roots sequentially, not interleaved |
| Branch-grouped traversal | None — roots seed the stack, algorithm unchanged |
| `get_subtree_ids` query | Needs update — currently accepts a single `root_id`; needs to accept a list and union N subtree traversals |
| Root ordering | Needs a decision — what determines which root's subtree is visited first |

---

## Current State

- `TraverseStrategy` enum exists: `random`, `outdated`, `dfs`, `newest` — none fully implemented beyond shuffle.
- `get_subtree_ids` has a `_strategy` placeholder parameter and currently accepts a single root.
- Session model has `traverse_strategy` and `repetition_strategy` fields already.
- Session `target` field is being extended to support multiple roots.

---

## Open Questions

- Should fill sessions be a separate session type in the model, or a filter strategy on a review session?
- What is the right default queue size per strategy? Due naturally self-limits; All needs a cap.
- Should traversal order be exposed as a separate field on the session, or collapsed into named presets for a simpler API?
- What determines ordering between multiple roots when traversal order is branch-grouped or BFS?
