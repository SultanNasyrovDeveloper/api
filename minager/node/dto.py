from pydantic import BaseModel

from .schemas import NodeStatisticsMixin


class NodeSubtreeStatistics(BaseModel):
    count: int
    average_rating: float
    owner_views: int
    repetitions: int
    size: int

    outdated: int
    not_visited: int
    empty: int


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
