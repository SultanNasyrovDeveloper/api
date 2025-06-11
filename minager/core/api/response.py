from pydantic import BaseModel, Field


class PaginatedResponse[ResponseItem: BaseModel](BaseModel):
    count: int = 0
    page: int = 1
    per_page: int = 20
    results: list[ResponseItem] = Field(default_factory=list)
