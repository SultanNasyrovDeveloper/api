from typing import TypedDict


class PaginatedResult[Item](TypedDict):
    page: int
    results: list[Item]
