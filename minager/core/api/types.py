from fastapi import Query
from pydantic import BaseModel


class PaginationData(BaseModel):
    page: int = Query(default=1, ge=1)
    per_page: int = Query(default=20, ge=1)


type QueryParams = dict[int | float | str, int | float | str | list]
