import math
from abc import ABCMeta, abstractmethod

from minager.node.dto import NodeSubtreeStatistics
from minager.node.models import Node


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(v, hi))


def safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else a / b


def geometric_mean(weights_and_values: list[tuple[float, float]]) -> float:
    """
    weights_and_values = [(weight, value_normalized_0_1), ...]
    """
    total_weight = sum(w for w, _ in weights_and_values)
    if total_weight == 0:
        return 0.0

    product = 1.0
    for w, v in weights_and_values:
        v = clamp(v)
        if v <= 0:
            return 0.0
        product *= v**w

    return product ** (1 / total_weight)


class BaseIndexComponent(metaclass=ABCMeta):
    name: str


class BaseNodeIndex(metaclass=ABCMeta):

    components: list[BaseIndexComponent]

    @abstractmethod
    def calculate(self):
        pass

    def get_components(self):
        pass

    def get_weights(self, values: dict):
        pass


# -----------------------------
# NODE (SELF UNDERSTANDING INDEX)
# -----------------------------


class NodeIndex(BaseNodeIndex):
    """
    Measures user's understanding of THIS node only.
    """

    def __init__(self, node: Node):
        self.node = node

    def _repetition_score(self):
        # diminishing returns curve
        reps = max(self.node.repetitions or 0, 0)
        return 1 - math.exp(-0.5 * reps)

    def _cpr_score(self):
        cpr = max(self.node.cpr or 0, 0)
        return clamp(cpr / 10)

    def _rating_score(self):
        # expects rating in range 1..5 (gracefully handles missing)
        rating = self.node.last_rating or 0
        return clamp((rating - 1) / 4)

    def _recency_score(self):
        """
        Recency = exp(-days / λ)

        Assumes node.last_repetition is datetime or None.
        You may replace days_since with your real value later.
        """
        if not self.node.last_repetition:
            return 0.0

        days_since = getattr(self.node, 'days_since_last_rep', 0) or 0
        return math.exp(-days_since / 14)  # λ = 14 days decay

    def _difficulty_balance(self):
        """
        Ideal difficulty ≈ 0.5
        """
        diff = clamp(self.node.difficulty or 0.5)
        return 1 - abs(diff - 0.5) / 0.5

    def calculate(self) -> dict:
        components = {
            'rep_score': self._repetition_score(),
            'cpr_score': self._cpr_score(),
            'rating_score': self._rating_score(),
            'recency_score': self._recency_score(),
            'difficulty_balance': self._difficulty_balance(),
        }

        weights = [
            (3, components['rep_score']),
            (2, components['cpr_score']),
            (3, components['rating_score']),
            (2, components['recency_score']),
            (1, components['difficulty_balance']),
        ]

        index_value = geometric_mean(weights)

        return {
            'index': index_value,
            'components': components,
        }


# -----------------------------
# SUBTREE INDEX (KNOWLEDGE HEALTH)
# -----------------------------


class NodeSubtreeIndex(BaseNodeIndex):
    """
    Measures completeness, freshness, and quality of subtree knowledge.
    """

    def __init__(self, statistics: NodeSubtreeStatistics):
        self.statistics = statistics

    def _coverage(self):
        return safe_div(self.statistics.count, self.statistics.size)

    def _empty_penalty(self):
        return 1 - safe_div(self.statistics.empty, self.statistics.size)

    def _outdated_penalty(self):
        frac = safe_div(self.statistics.outdated, self.statistics.size)
        return 1 - clamp(frac)

    def _visit_penalty(self):
        return 1 - safe_div(self.statistics.not_visited, self.statistics.size)

    def _rating_score(self):
        avg = self.statistics.average_rating or 0
        return clamp((avg - 1) / 4)

    def calculate(self) -> dict:

        if self.statistics.size == 0:
            # no subtree exists — report explicitly
            return {
                'index': 0.0,
                'components': {},
                'empty': True,
            }

        components = {
            'coverage': self._coverage(),
            'rating_score': self._rating_score(),
            'empty_penalty': self._empty_penalty(),
            'outdated_penalty': self._outdated_penalty(),
            'visit_penalty': self._visit_penalty(),
        }

        weights = [
            (3, components['coverage']),
            (2, components['rating_score']),
            (2, components['empty_penalty']),
            (2, components['outdated_penalty']),
            (2, components['visit_penalty']),
        ]

        index_value = geometric_mean(weights)

        return {
            'index': index_value,
            'components': components,
            'empty': False,
        }


# -----------------------------
# OVERALL INDEX (GLOBAL SIGNAL)
# -----------------------------


class NodeOverallIndex(BaseNodeIndex):
    """
    Blends:
      - node understanding index
      - subtree knowledge health index

    with adaptive weights depending on subtree size / coverage.
    """

    def __init__(self, node: Node, statistics: NodeSubtreeStatistics):
        self.node = node
        self.statistics = statistics
        self._cache: dict | None = None

    def _compute_weights(self, subtree_index: float) -> tuple[float, float]:
        """
        Adaptive weighting:
          small subtree  -> emphasize node
          large subtree  -> emphasize subtree
        """

        size = self.statistics.size or 0

        if size == 0:
            return 1.0, 0.0  # node only

        # smoothly increase subtree weight with size
        subtree_weight = clamp(math.log(size + 1) / 5, 0.2, 0.8)

        # if subtree is very weak -> penalize harder
        if subtree_index < 0.3:
            subtree_weight = max(subtree_weight, 0.6)

        node_weight = 1 - subtree_weight
        return node_weight, subtree_weight

    def calculate(self) -> dict:

        if self._cache:
            return self._cache

        node_idx = NodeIndex(self.node).calculate()
        subtree_idx = NodeSubtreeIndex(self.statistics).calculate()

        node_value = node_idx['index']
        subtree_value = subtree_idx['index']

        wn, ws = self._compute_weights(subtree_value)

        overall = geometric_mean(
            [
                (wn, node_value),
                (ws, subtree_value),
            ]
        )

        self._cache = {
            'overall_index': overall,
            'node_index': node_value,
            'subtree_index': subtree_value,
            'weights': {'node': wn, 'subtree': ws},
            'node_components': node_idx.get('components'),
            'subtree_components': subtree_idx.get('components'),
        }

        return self._cache
