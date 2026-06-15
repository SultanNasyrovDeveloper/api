from typing import Any

from surrealdb import AsyncWsSurrealConnection

from ..statements import Expression


class Manager:
    def __init__(self, connection: AsyncWsSurrealConnection):
        self.connection = connection

    async def query(self, sql: Expression, variables: dict[str, Any] | None = None) -> Any | list[Any]:
        response = await self.connection.query(query=str(sql), vars=variables)
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        return response

    async def select(self, sql: Expression, variables: dict[str, Any] | None = None) -> list[Any]:
        response = await self.query(sql, variables)
        if not isinstance(response, list):
            return [response]
        return response

    async def select_one(self, sql: Expression, variables: dict[str, Any] | None = None) -> Any:
        response = await self.query(sql, variables)
        if isinstance(response, list):
            return response[0] if len(response) == 1 else None
        else:
            return response
