# Node Index System Architecture

**Status:** Design Phase - Architecture Finalized
**Version:** 2.0
**Date:** 2026-05-22
**Previous Version:** 1.0 (2026-05-21)
**Purpose:** Define high-level architecture for composite node understanding index

---

## Overview

The index system provides a single **Overall Understanding Index (0-100)** that measures both individual node quality and collective subtree health across two dimensions:

### The 2×2 Index Matrix

```
                    Individual Node    |    Subtree Aggregate
──────────────────────────────────────────────────────────────
Content/Quality     Node Content       |    Subtree Data
(what exists)       Index              |    Index
                                       |
Understanding       Node Understanding |    Subtree Understanding
(how well learned)  Index              |    Index
```

**Primary Use Cases:**
- Gamification and progress tracking
- Leaderboards and competition
- Identifying nodes that need attention
- Measuring knowledge base quality

---

## Core Architecture Decisions

### 1. Calculation Strategy: On-Demand + Caching

**Decision:** Calculate on-demand with aggressive caching. No materialized fields (for MVP).

```
Read Path:
  User requests statistics
    → Check cache (TTL-based)
    → If miss: calculate via efficient graph query
    → Cache result
    → Return

Write Path:
  User updates node
    → Update database (fast)
    → Invalidate cache (optional)
    → Return success
```

**Rationale:**
- Simple to implement
- Leverages graph database strengths
- No write amplification
- Can optimize later with materialization if needed

**Future optimization:** Background worker to pre-calculate popular nodes

---

### 2. Two-Stage Evaluation: Gates → Calculation

**Decision:** All indexes use a two-stage process:

#### Stage 1: Gates (Pass/Fail Checks)

Gates prevent absurd scores by enforcing fundamental requirements:

```python
def calculate_dimension_index(data):
    # STAGE 1: GATES
    if not passes_gates(data):
        return 0  # or None (exclude dimension)

    # STAGE 2: CALCULATION
    # All properties participate with dynamic weights
    return calculate_index_with_dynamic_weights(data)
```

**Gate Types:**

1. **Logical/Semantic Gates** - Prevent impossible states
   - Example: Can't have `last_rating > 0` if `size == 0`

2. **Quality Gates** - Prevent absurd scores
   - Example: `size == 0` → Node Content Index = 0
   - Example: `owner_views == 0` → Node Understanding Index = 0

**Gate Matrix:**

| Dimension | Gate Condition | Result if Failed |
|-----------|---------------|------------------|
| **Node Content** | `size > 0` | Index = 0 |
| **Node Understanding** | `size > 0 AND owner_views > 0` | Index = 0 |
| **Subtree Data** | `subtree_count > 1` | Exclude dimension |
| **Subtree Understanding** | `subtree_count > 1 AND subtree_repetitions > 0` | Exclude dimension |

**Key Insight:** Gates enforce sanity, dynamic weights handle quality.

---

### 3. Dynamic Weights System

**Decision:** Property weights adapt based on current values (bottleneck-based weighting).

#### The Problem with Static Weights

```python
# Static weights
weights = {'size': 0.33, 'views': 0.33, 'rating': 0.33}

# Scenario: size=0.1, views=0.9, rating=0.9
index = 0.33×0.1 + 0.33×0.9 + 0.33×0.9 = 0.63 (63/100)

# Problem: Size is the bottleneck, but only contributes 33%
# User might focus on already-good areas instead
```

#### Dynamic Weights Solution

**Principle:** Low-scoring properties get higher weight (bottleneck prioritization)

```python
def calculate_dynamic_weights(scores: dict[str, float]) -> dict[str, float]:
    """
    Weights based on criticality (inverse of score)

    Low score → High criticality → High weight
    High score → Low criticality → Low weight
    """

    # Step 1: Calculate criticality for each property
    # Using inverse function: 1/(1 + 2×score)
    criticalities = {}
    for prop, score in scores.items():
        criticality = 1 / (1 + 2 * score)
        # score=0.0 → criticality=1.0
        # score=0.5 → criticality=0.5
        # score=1.0 → criticality=0.33
        criticalities[prop] = criticality

    # Step 2: Blend with default weights for stability
    default_weights = get_default_weights(dimension)

    blended = {}
    for prop in scores.keys():
        # 70% dynamic, 30% default
        dynamic_normalized = criticalities[prop] / sum(criticalities.values())
        blended[prop] = 0.7 * dynamic_normalized + 0.3 * default_weights[prop]

    # Step 3: Normalize to sum to 1
    total = sum(blended.values())
    return {k: v/total for k, v in blended.items()}
```

**Example:**
```python
scores = {'size': 0.1, 'views': 0.8, 'rating': 0.9}

# Criticalities
size_crit = 1/(1 + 2×0.1) = 0.83
views_crit = 1/(1 + 2×0.8) = 0.38
rating_crit = 1/(1 + 2×0.9) = 0.36

# Normalized dynamic weights
size_weight = 53%  (bottleneck!)
views_weight = 24%
rating_weight = 23%

# Overall = 0.53×0.1 + 0.24×0.8 + 0.23×0.9 = 0.45 (45/100)
# Clear signal: improve size first
```

**Benefits:**
- Automatically identifies bottlenecks
- Provides clear improvement guidance
- Non-compensatory behavior (can't ignore weak areas)
- Smooth (no discontinuities)

**Configuration:**
```python
# config/weights/v1_0_0.py
VERSION = "1.0.0"

DYNAMIC_WEIGHT_CONFIG = {
    'criticality_function': 'inverse',  # 1/(1 + k×score)
    'criticality_factor': 2.0,          # k parameter
    'blend_ratio': 0.7,                 # 70% dynamic, 30% default
}

NODE_CONTENT_DEFAULT_WEIGHTS = {
    'size': 0.4,
    'structure': 0.3,
    'engagement': 0.3
}
```

---

### 4. Index Structure: Tree Evaluation (2×2 Matrix)

**Decision:** Four distinct dimension indexes combine into overall index.

```
Overall Understanding Index (0-100)
│
├─ Node Content Index (0-1)
│  ├─ Size Score (content volume)
│  ├─ Structure Score (block diversity, depth, richness)
│  └─ Engagement Score (owner views)
│
├─ Node Understanding Index (0-1)
│  ├─ Retention Score (CPR, difficulty, rating)
│  ├─ Frequency Score (total repetitions)
│  └─ Recency Score (time since last review)
│
├─ Subtree Data Index (0-1)
│  ├─ Coverage Score (% visited, % filled, % current)
│  ├─ Quality Score (avg size, avg structure)
│  └─ Balance Score (optimal size for depth)
│
└─ Subtree Understanding Index (0-1)
   ├─ Avg Retention Score (avg CPR, avg rating)
   ├─ Practice Coverage (% of nodes practiced)
   └─ Currency Score (% not outdated)
```

**Calculation Flow:**

```python
def calculate_overall_index(node, subtree_stats):
    # 1. Calculate four dimension indexes (with gates)
    node_content = calculate_node_content_index(node)
    node_understanding = calculate_node_understanding_index(node)
    subtree_data = calculate_subtree_data_index(subtree_stats)
    subtree_understanding = calculate_subtree_understanding_index(subtree_stats)

    # 2. Collect valid dimensions (some may be None/excluded)
    dimensions = {}
    if node_content is not None:
        dimensions['node_content'] = node_content
    if node_understanding is not None:
        dimensions['node_understanding'] = node_understanding
    if subtree_data is not None:
        dimensions['subtree_data'] = subtree_data
    if subtree_understanding is not None:
        dimensions['subtree_understanding'] = subtree_understanding

    # 3. Calculate adaptive weights (based on subtree size, repetitions, etc.)
    weights = calculate_adaptive_dimension_weights(node, subtree_stats)

    # 4. Combine with chosen method (geometric mean recommended)
    overall = weighted_geometric_mean(dimensions, weights)

    # 5. Scale to 0-100
    return overall * 100
```

---

### 5. Normalization: Versioned Configuration

**Decision:** All normalization functions are versioned and configuration-based.

**Why Versioning:**
- Scores calculated at different times remain comparable
- Can recalculate old nodes with new config
- Audit trail for index changes
- A/B testing of different formulas

**Configuration Structure:**

```python
# config/normalization/v1_0_0.py
VERSION = "1.0.0"
CREATED = "2026-05-22"
DESCRIPTION = "Initial normalization functions"

# Each property has a normalization config
NORMALIZATIONS = {
    'size': {
        'type': 'sigmoid',
        'params': {
            'inflection_point': 1000,  # 50% score at 1000 chars
            'steepness': 0.003,
        }
    },

    'owner_views': {
        'type': 'exponential_decay',
        'params': {
            'decay_rate': 0.3,  # Diminishing returns
        }
    },

    'repetitions': {
        'type': 'logarithmic',
        'params': {
            'base': 21,  # log(x+1)/log(21), caps at ~20 reps
        }
    },

    'cpr': {
        'type': 'exponential_decay',
        'params': {
            'decay_rate': 0.4,  # 1 - exp(-0.4×cpr)
        }
    },

    # ... etc for all properties
}
```

**Normalization Functions:**

```python
class SigmoidNormalizer:
    """For metrics that have a natural midpoint"""
    def normalize(self, value: float) -> float:
        return 1 / (1 + math.exp(-self.steepness * (value - self.inflection_point)))

class ExponentialDecayNormalizer:
    """For metrics with diminishing returns"""
    def normalize(self, value: float) -> float:
        return 1 - math.exp(-self.decay_rate * value)

class LogarithmicNormalizer:
    """For metrics where early gains matter most"""
    def normalize(self, value: float) -> float:
        return math.log(value + 1) / math.log(self.base)
```

**Usage:**

```python
def get_normalizer(property_name: str, version: str = "1.0.0"):
    config = load_normalization_config(version)
    norm_config = config['NORMALIZATIONS'][property_name]

    if norm_config['type'] == 'sigmoid':
        return SigmoidNormalizer(**norm_config['params'])
    elif norm_config['type'] == 'exponential_decay':
        return ExponentialDecayNormalizer(**norm_config['params'])
    # ... etc
```

---

### 6. Context-Aware Evaluation

#### Depth-Dependent Optimal Subtree Size

**Decision:** Optimal subtree size decreases with depth.

**Rationale:**
- Root-level concepts (depth=0) → broad (can have 1000 child nodes)
- Mid-level concepts (depth=2) → moderate (250 nodes)
- Deep concepts (depth=4) → focused (60 nodes)

```python
def get_optimal_subtree_size(node_depth: int) -> int:
    """
    Exponential decay with depth

    depth=0: 1000 nodes
    depth=1: 500 nodes
    depth=2: 250 nodes
    depth=3: 125 nodes
    depth=4: 62 nodes
    """
    base_size = 1000
    decay_factor = 0.5

    return int(base_size * (decay_factor ** node_depth))

def calculate_subtree_balance_score(subtree_count: int, node_depth: int) -> float:
    """Score based on proximity to optimal size"""
    optimal = get_optimal_subtree_size(node_depth)

    if subtree_count == optimal:
        return 1.0
    elif subtree_count < optimal:
        # Too small: linear penalty
        return subtree_count / optimal
    else:
        # Too large: exponential penalty
        excess = subtree_count - optimal
        return math.exp(-0.01 * excess)
```

#### Adaptive Dimension Weights

**Decision:** Dimension weights adapt based on node context.

```python
def calculate_adaptive_dimension_weights(node, subtree_stats):
    """
    Adjust dimension weights based on:
    - Subtree size (leaf vs. large tree)
    - Learning stage (new vs. mastered)
    - Node depth (root vs. deep)
    """

    # Base weights (default)
    weights = {
        'node_content': 0.25,
        'node_understanding': 0.25,
        'subtree_data': 0.25,
        'subtree_understanding': 0.25,
    }

    # Adjustment 1: Subtree size
    if subtree_stats.count == 0:
        # Leaf node: no subtree dimensions
        weights['subtree_data'] = 0
        weights['subtree_understanding'] = 0
        weights['node_content'] = 0.5
        weights['node_understanding'] = 0.5

    elif subtree_stats.count < 5:
        # Small tree: emphasize individual node
        weights['node_content'] = 0.4
        weights['node_understanding'] = 0.3
        weights['subtree_data'] = 0.2
        weights['subtree_understanding'] = 0.1

    elif subtree_stats.count > 50:
        # Large tree: emphasize subtree
        weights['node_content'] = 0.15
        weights['node_understanding'] = 0.15
        weights['subtree_data'] = 0.35
        weights['subtree_understanding'] = 0.35

    # Adjustment 2: Learning stage
    if node.repetitions <= 2:
        # New node: quality matters most
        weights['node_content'] *= 1.5
        weights['node_understanding'] *= 0.5

    elif node.repetitions > 10:
        # Mastered node: subtree becomes important
        weights['node_understanding'] *= 1.3
        weights['subtree_understanding'] *= 1.2

    # Normalize to sum to 1
    total = sum(weights.values())
    return {k: v/total for k, v in weights.items()}
```

---

## Detailed Gate Definitions

### Gate Configuration (Versioned)

```python
# config/gates/v1_0_0.py
VERSION = "1.0.0"

DIMENSION_GATES = {
    'node_content': {
        'conditions': [
            {'field': 'size', 'operator': '>', 'value': 0}
        ],
        'on_fail': 'zero',  # Set index to 0
        'rationale': 'Empty node has no content to evaluate'
    },

    'node_understanding': {
        'conditions': [
            {'field': 'size', 'operator': '>', 'value': 0},
            {'field': 'owner_views', 'operator': '>', 'value': 0}
        ],
        'logic': 'AND',
        'on_fail': 'zero',
        'rationale': 'Cannot have understanding without content and engagement'
    },

    'subtree_data': {
        'conditions': [
            {'field': 'subtree_count', 'operator': '>', 'value': 1}
        ],
        'on_fail': 'exclude',  # Exclude dimension from calculation
        'rationale': 'Single node has no subtree to evaluate'
    },

    'subtree_understanding': {
        'conditions': [
            {'field': 'subtree_count', 'operator': '>', 'value': 1},
            {'field': 'subtree_total_repetitions', 'operator': '>', 'value': 0}
        ],
        'logic': 'AND',
        'on_fail': 'exclude',
        'rationale': 'Cannot evaluate subtree understanding without practice'
    }
}

# Logical/semantic consistency checks
SEMANTIC_GATES = {
    'learning_data_consistency': {
        'conditions': [
            # If has rating, must have content and views
            {
                'if': {'field': 'last_rating', 'operator': '>', 'value': 0},
                'then': [
                    {'field': 'size', 'operator': '>', 'value': 0},
                    {'field': 'owner_views', 'operator': '>', 'value': 0}
                ]
            },
            # If has repetitions, must have content
            {
                'if': {'field': 'repetitions', 'operator': '>', 'value': 0},
                'then': [
                    {'field': 'size', 'operator': '>', 'value': 0}
                ]
            }
        ],
        'on_fail': 'zero',
        'rationale': 'Logically inconsistent data (e.g., rating without content)'
    }
}
```

---

## Content Structure Analysis

### Node Content JSON Analysis

The `content` field is a JSON structure that can be analyzed for quality beyond simple character count.

**Example Content Structure:**
```json
{
  "root": {
    "children": [
      {"type": "paragraph", "content": "..."},
      {"type": "heading", "level": 2, "content": "..."},
      {"type": "list", "items": [...]},
      {"type": "code", "language": "python", "content": "..."},
      {"type": "table", "rows": [...]}
    ]
  }
}
```

**Analysis Metrics:**

```python
def analyze_content_structure(content_json: str) -> dict:
    """
    Analyze content structure for quality indicators
    """
    content = json.loads(content_json)
    root = content.get('root', {})

    return {
        # Quantitative
        'block_count': count_blocks(root),
        'depth': calculate_nesting_depth(root),
        'total_chars': get_content_size(root),

        # Qualitative
        'block_diversity': calculate_block_diversity(root),
        'has_lists': has_block_type(root, 'list'),
        'has_tables': has_block_type(root, 'table'),
        'has_code': has_block_type(root, 'code'),
        'has_media': has_block_type(root, ['image', 'video']),
        'has_headings': has_block_type(root, 'heading'),
    }

def calculate_block_diversity(root: dict) -> float:
    """
    Shannon entropy of block types
    Higher = more diverse (lists + tables + code vs. just paragraphs)
    """
    block_types = get_all_block_types(root)
    type_counts = Counter(block_types)

    if not block_types:
        return 0.0

    # Shannon entropy
    entropy = 0
    total = len(block_types)
    for count in type_counts.values():
        p = count / total
        entropy -= p * math.log2(p)

    # Normalize to [0, 1] (max entropy for ~6 block types ≈ 2.6)
    return min(entropy / 2.6, 1.0)
```

**Content Structure Score:**

```python
def calculate_content_structure_score(content_json: str) -> float:
    """
    Combines multiple structure metrics
    """
    analysis = analyze_content_structure(content_json)

    # Block count score (logarithmic)
    block_score = math.log(analysis['block_count'] + 1) / math.log(51)  # cap at 50

    # Diversity score (already 0-1)
    diversity_score = analysis['block_diversity']

    # Richness score (binary features)
    richness_features = [
        analysis['has_lists'],
        analysis['has_tables'],
        analysis['has_code'],
        analysis['has_media'],
        analysis['has_headings'],
    ]
    richness_score = sum(richness_features) / len(richness_features)

    # Combine with weights
    weights = {'block': 0.3, 'diversity': 0.4, 'richness': 0.3}

    return (
        weights['block'] * block_score +
        weights['diversity'] * diversity_score +
        weights['richness'] * richness_score
    )
```

---

## Complete Calculation Example

### Example Node Data

```python
node = {
    'size': 850,
    'owner_views': 3,
    'last_rating': 4,
    'repetitions': 5,
    'cpr': 3,
    'difficulty': 2.4,
    'content': '{"root": {"children": [...]}}',  # Diverse blocks
}

subtree_stats = {
    'count': 12,
    'avg_rating': 3.5,
    'total_size': 8500,
    'outdated': 2,
    'not_visited': 1,
    'empty': 0,
    'total_repetitions': 45,
}

node_depth = 1
```

### Step-by-Step Calculation

**1. Check Semantic Gates**
```python
# Check if data is logically consistent
if node.last_rating > 0 and node.size == 0:
    return 0  # FAIL: Can't rate empty content

# All semantic checks pass ✓
```

**2. Calculate Node Content Index**

```python
# Gate check
if node.size == 0:
    node_content_index = 0
else:
    # Gate passed, calculate

    # Size score (sigmoid)
    size_score = 1 / (1 + exp(-0.003 * (850 - 1000)))
              = 1 / (1 + exp(0.45))
              = 1 / 1.57
              = 0.64

    # Structure score (from content analysis)
    structure_score = analyze_structure(node.content) = 0.72

    # Engagement score (exponential decay)
    engagement_score = 1 - exp(-0.3 * 3) = 0.59

    # Scores dict
    scores = {'size': 0.64, 'structure': 0.72, 'engagement': 0.59}

    # Dynamic weights
    criticality = {
        'size': 1/(1 + 2*0.64) = 0.44,
        'structure': 1/(1 + 2*0.72) = 0.41,
        'engagement': 1/(1 + 2*0.59) = 0.46
    }
    total = 1.31

    weights = {
        'size': 0.44/1.31 = 0.34,
        'structure': 0.41/1.31 = 0.31,
        'engagement': 0.46/1.31 = 0.35
    }

    # Combine
    node_content_index = 0.34*0.64 + 0.31*0.72 + 0.35*0.59
                       = 0.22 + 0.22 + 0.21
                       = 0.65
```

**3. Calculate Node Understanding Index**

```python
# Gate check
if node.size == 0 or node.owner_views == 0:
    node_understanding_index = 0
else:
    # Gates passed

    # Retention score (CPR-based)
    cpr_score = 1 - exp(-0.4 * 3) = 0.70
    rating_score = 4 / 5 = 0.80
    difficulty_score = (2.4 - 1.3) / 1.3 = 0.85
    retention_score = (0.70^0.5) * (0.80^0.25) * (0.85^0.25) = 0.81

    # Frequency score
    frequency_score = log(5+1) / log(21) = 0.59

    # Recency score (assume 2 days until due)
    recency_score = 0.8 + 0.2 * (2/7) = 0.86

    scores = {'retention': 0.81, 'frequency': 0.59, 'recency': 0.86}

    # Dynamic weights (frequency is bottleneck)
    weights = {'retention': 0.30, 'frequency': 0.42, 'recency': 0.28}

    node_understanding_index = 0.30*0.81 + 0.42*0.59 + 0.28*0.86
                              = 0.24 + 0.25 + 0.24
                              = 0.73
```

**4. Calculate Subtree Data Index**

```python
# Gate check
if subtree_stats.count <= 1:
    subtree_data_index = None  # Exclude
else:
    # Gates passed (count=12)

    # Coverage score
    visited_ratio = 1 - (1/12) = 0.92
    filled_ratio = 1 - (0/12) = 1.0
    current_ratio = 1 - (2/12) = 0.83
    coverage_score = (0.92 * 1.0 * 0.83)^(1/3) = 0.91

    # Quality score
    avg_size = 8500 / 12 = 708
    avg_size_score = 1 / (1 + exp(-0.003 * (708 - 1000))) = 0.55
    avg_rating_score = 3.5 / 5 = 0.70
    quality_score = (0.55 * 0.70)^0.5 = 0.62

    # Balance score (depth=1, optimal=500)
    # count=12 < 500 → linear penalty
    balance_score = 12 / 500 = 0.02 (very low!)

    scores = {'coverage': 0.91, 'quality': 0.62, 'balance': 0.02}

    # Dynamic weights (balance is huge bottleneck)
    weights = {'coverage': 0.14, 'quality': 0.23, 'balance': 0.63}

    subtree_data_index = 0.14*0.91 + 0.23*0.62 + 0.63*0.02
                       = 0.13 + 0.14 + 0.01
                       = 0.28
```

**5. Calculate Subtree Understanding Index**

```python
# Gate check
if subtree_stats.count <= 1 or subtree_stats.total_repetitions == 0:
    subtree_understanding_index = None
else:
    # Gates passed

    # Avg retention (simplified)
    avg_retention_score = 3.5 / 5 = 0.70

    # Practice coverage (assume 10/12 have reps > 0)
    practice_coverage = 10 / 12 = 0.83

    # Currency (not outdated)
    currency_score = 1 - (2/12) = 0.83

    scores = {'retention': 0.70, 'coverage': 0.83, 'currency': 0.83}

    # Dynamic weights (retention is bottleneck)
    weights = {'retention': 0.43, 'coverage': 0.29, 'currency': 0.28}

    subtree_understanding_index = 0.43*0.70 + 0.29*0.83 + 0.28*0.83
                                 = 0.30 + 0.24 + 0.23
                                 = 0.77
```

**6. Combine with Adaptive Weights**

```python
dimensions = {
    'node_content': 0.65,
    'node_understanding': 0.73,
    'subtree_data': 0.28,
    'subtree_understanding': 0.77,
}

# Adaptive weights (subtree_count=12, repetitions=5)
# Small tree case
weights = {
    'node_content': 0.4,
    'node_understanding': 0.3,
    'subtree_data': 0.2,
    'subtree_understanding': 0.1,
}

# Weighted geometric mean
overall = (0.65^0.4) * (0.73^0.3) * (0.28^0.2) * (0.77^0.1)
        = 0.87 * 0.91 * 0.74 * 0.98
        = 0.57

# Scale to 0-100
overall_index = 57
```

**Final Result:**
```json
{
  "overall_index": 57,
  "dimensions": {
    "node_content": {"index": 65, "weight": 40},
    "node_understanding": {"index": 73, "weight": 30},
    "subtree_data": {"index": 28, "weight": 20},
    "subtree_understanding": {"index": 77, "weight": 10}
  },
  "recommendation": "Improve subtree_data (currently limiting overall score)"
}
```

**Key Insight:** Subtree balance is terrible (12 nodes at depth=1, optimal=500), dragging down subtree_data_index to 28, which limits overall score.

---

## API Response Structure

### Endpoint

```
GET /api/v1/node/nodes/{uid}/statistics
```

### Response Schema

```python
class NodeOverallStatistics(BaseModel):
    # Top-level index
    overall_index: float  # 0-100

    # Four dimension indexes
    indexes: NodeIndexesInfo

    # Raw subtree data
    subtree: NodeSubtreeStatistics

    # Raw node data
    node: NodeStatisticsMixin

    # Metadata
    config_version: str  # "1.0.0"
    calculated_at: datetime

class NodeIndexesInfo(BaseModel):
    overall_index: float  # 0-100

    # Dimension indexes
    node_content_index: float | None  # 0-100 or None if excluded
    node_understanding_index: float | None
    subtree_data_index: float | None
    subtree_understanding_index: float | None

    # Applied weights
    dimension_weights: dict[str, float]

    # Component breakdowns
    node_content_components: dict[str, ComponentInfo] | None
    node_understanding_components: dict[str, ComponentInfo] | None
    subtree_data_components: dict[str, ComponentInfo] | None
    subtree_understanding_components: dict[str, ComponentInfo] | None

class ComponentInfo(BaseModel):
    score: float  # 0-1 normalized
    weight: float  # Applied weight
    contribution: float  # score × weight
    raw_value: Any  # Original value before normalization
```

**Example Response:**

```json
{
  "overall_index": 57.2,
  "indexes": {
    "overall_index": 57.2,
    "node_content_index": 65.0,
    "node_understanding_index": 73.0,
    "subtree_data_index": 28.0,
    "subtree_understanding_index": 77.0,

    "dimension_weights": {
      "node_content": 0.40,
      "node_understanding": 0.30,
      "subtree_data": 0.20,
      "subtree_understanding": 0.10
    },

    "node_content_components": {
      "size": {
        "score": 0.64,
        "weight": 0.34,
        "contribution": 0.22,
        "raw_value": 850
      },
      "structure": {
        "score": 0.72,
        "weight": 0.31,
        "contribution": 0.22,
        "raw_value": {"block_count": 12, "diversity": 0.72}
      },
      "engagement": {
        "score": 0.59,
        "weight": 0.35,
        "contribution": 0.21,
        "raw_value": 3
      }
    },

    "subtree_data_components": {
      "coverage": {"score": 0.91, "weight": 0.14, "contribution": 0.13},
      "quality": {"score": 0.62, "weight": 0.23, "contribution": 0.14},
      "balance": {"score": 0.02, "weight": 0.63, "contribution": 0.01}
    }
  },

  "subtree": {
    "count": 12,
    "avg_rating": 3.5,
    "total_size": 8500,
    "outdated": 2,
    "not_visited": 1,
    "empty": 0
  },

  "node": {
    "size": 850,
    "owner_views": 3,
    "last_rating": 4,
    "repetitions": 5,
    "cpr": 3,
    "difficulty": 2.4
  },

  "config_version": "1.0.0",
  "calculated_at": "2026-05-22T14:30:00Z"
}
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

1. **Configuration System**
   - Create `config/normalization/v1_0_0.py`
   - Create `config/gates/v1_0_0.py`
   - Create `config/weights/v1_0_0.py`
   - Implement config loader with versioning

2. **Normalization Functions**
   - Implement `SigmoidNormalizer`
   - Implement `ExponentialDecayNormalizer`
   - Implement `LogarithmicNormalizer`
   - Unit tests for each

3. **Gate System**
   - Implement gate validator
   - Add semantic consistency checks
   - Unit tests for gate logic

### Phase 2: Component Calculators (Week 2)

1. **Content Analysis**
   - Implement JSON content parser
   - Block counting, diversity, richness
   - Unit tests with sample content

2. **Score Normalization**
   - Wire up normalizers for all properties
   - Validate ranges [0, 1]

3. **Dynamic Weights**
   - Implement criticality function
   - Implement blending logic
   - Unit tests with various score distributions

### Phase 3: Dimension Indexes (Week 2-3)

1. **Node Content Index**
   - Combine size, structure, engagement
   - Apply dynamic weights
   - Gate checks

2. **Node Understanding Index**
   - Retention, frequency, recency
   - Dynamic weights
   - Gate checks

3. **Subtree Data Index**
   - Coverage, quality, balance
   - Depth-dependent optimal size
   - Gate checks

4. **Subtree Understanding Index**
   - Avg retention, coverage, currency
   - Gate checks

### Phase 4: Overall Index (Week 3)

1. **Adaptive Weights**
   - Implement context-based weight adjustment
   - Test with leaf, small, large trees

2. **Combination Logic**
   - Implement geometric mean
   - Handle excluded dimensions
   - Scale to 0-100

3. **API Integration**
   - Update `NodeOverallStatistics` schema
   - Update manager method
   - Update API endpoint

### Phase 5: Caching & Optimization (Week 4)

1. **Cache Layer**
   - Implement TTL cache (cachetools or Redis)
   - Cache invalidation strategy
   - Performance testing

2. **Query Optimization**
   - Single-query subtree stats fetch
   - Database indexes if needed

### Phase 6: Validation & Tuning (Week 4-5)

1. **Calculate for Real Data**
   - Run on entire knowledge base
   - Review top/bottom 50 nodes manually

2. **Parameter Tuning**
   - Adjust normalization inflection points
   - Tune dynamic weight blending ratio
   - Adjust adaptive weight thresholds

3. **User Testing**
   - Show indexes to users
   - Collect feedback
   - Iterate on formulas

---

## Configuration Versioning Strategy

### Version Format

`MAJOR.MINOR.PATCH` (Semantic Versioning)

- **MAJOR:** Breaking changes (scores not comparable to previous versions)
- **MINOR:** New features (new components, optional changes)
- **PATCH:** Bug fixes (formula corrections, no semantic change)

### Migration Path

```python
# When deploying new config version
def migrate_indexes(from_version: str, to_version: str):
    """
    Recalculate all node indexes with new config
    Can be done async/background
    """
    nodes = await get_all_nodes()

    for node in nodes:
        # Calculate with new config
        new_index = calculate_overall_index(node, version=to_version)

        # Store both old and new for comparison
        await store_index_history(
            node_id=node.id,
            version=to_version,
            index=new_index,
            previous_version=from_version
        )
```

---

## Open Questions & Future Enhancements

### Immediate Questions

1. **Combination method:** Geometric mean vs. arithmetic mean for combining dimension indexes?
2. **Subtree size bonus:** Should larger subtrees get a multiplier bonus for difficulty?
3. **Cache TTL:** 5 minutes? 30 minutes? Per-user configuration?
4. **Force recalc:** Should users have a "refresh my score" button?

### Future Enhancements

1. **Historical tracking:** Store index over time, show trend graphs
2. **Peer comparison:** Percentile ranking among all users
3. **Recommendations engine:** "To reach 80/100, add 500 chars to content"
4. **Badges/achievements:** Unlock badges at index milestones
5. **A/B testing:** Test different formulas with subset of users
6. **Machine learning:** Learn optimal weights from user behavior

---

## Appendix: Mathematical Formulas Reference

### Geometric Mean (Weighted)

```
GM = (x₁^w₁ × x₂^w₂ × ... × xₙ^wₙ)^(1/Σw)

Where:
- xᵢ = component score [0, 1]
- wᵢ = weight for component i
- Σw = sum of all weights

Properties:
- Non-compensatory: all components must be > 0
- Sensitive to balance
- If any xᵢ = 0, result = 0
```

### Sigmoid Normalization

```
normalized = 1 / (1 + e^(-k(x - x₀)))

Where:
- x = raw value
- x₀ = inflection point (50% score)
- k = steepness

Properties:
- S-curve shape
- Output range: [0, 1]
- Good for values with natural midpoint
```

### Exponential Decay

```
normalized = 1 - e^(-λx)

Where:
- x = raw value
- λ = decay rate

Properties:
- Diminishing returns
- Output range: [0, 1)
- Good for "more is better, but with limits"
```

### Logarithmic

```
normalized = log(x + 1) / log(max + 1)

Where:
- x = raw value
- max = maximum expected value

Properties:
- Early gains matter most
- Output range: [0, 1]
- Good for count-based metrics
```

### Criticality (Dynamic Weights)

```
criticality(x) = 1 / (1 + k×x)

Where:
- x = normalized score [0, 1]
- k = sensitivity factor (default: 2)

Properties:
- Inverse relationship
- x=0 → criticality=1 (max weight)
- x=1 → criticality=1/(1+k) (min weight)
```

---

## Version History

### v2.0 (2026-05-22)
- Added two-stage evaluation (gates → calculation)
- Added dynamic weights system with mathematical formulas
- Added 2×2 index matrix structure
- Added versioned configuration system
- Added depth-dependent optimal subtree sizes
- Added complete calculation example
- Added content structure analysis

### v1.0 (2026-05-21)
- Initial architecture draft
- Decision point exploration
- Options analysis
