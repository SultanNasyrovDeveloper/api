from pydantic import BaseModel

from .mixins import NodeStatisticsMixin


class NodeSubtreeStatistics(BaseModel):
    count: int = 0
    average_rating: float = 0
    owner_views: int = 0
    repetitions: int = 0
    size: int = 0

    outdated: int = 0
    not_visited: int = 0
    empty: int = 0


class NodeIndexesInfo(BaseModel):
    overall_index: float
    node_index: float
    subtree_index: float
    weights: dict[str, float]
    node_components: dict[str, float]
    subtree_components: dict[str, float]


class NodeOverallStatistics(BaseModel):
    indexes: NodeIndexesInfo
    subtree: NodeSubtreeStatistics
    node: NodeStatisticsMixin
