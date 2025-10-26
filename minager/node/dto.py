from pydantic import BaseModel


class SubtreeStatistics(BaseModel):
    total_nodes: int
    average_rating: float
    total_owner_view: int
    total_repetitions: int
    total_size: int

    total_outdated: int
    total_not_visited: int
    total_empty: int
