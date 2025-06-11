from logging import Logger, getLogger
from typing import Any

from surrealdb import AsyncSurreal

from .query import Expression
from .query.utils import render
from .response import Response
from .settings import SurrealConfig


class SurrealDBManager:
    def __init__(self, config: SurrealConfig, logger: Logger = None):
        assert config.driver == 'surreal'
        self._config = config
        self._base_url = f'ws://{self._config.host}:{self._config.port}'
        self._logger = logger or getLogger(__name__)
        self._connection = None

    async def __aenter__(self):
        assert self._config.namespace
        assert self._config.name
        self._connection = AsyncSurreal(self._base_url)
        await self._connection.__aenter__()
        if self._config.username and self._config.password:
            await self._connection.signin(
                {
                    'username': self._config.username,
                    'password': self._config.password.get_secret_value(),
                }
            )
        await self._connection.use(namespace=self._config.namespace, database=self._config.name)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._connection.__aexit__(exc_type, exc_val, exc_tb)
        self._connection = None

    def _check_connection(self):
        assert self._connection

    async def query(self, sql: Expression, variables: dict[str, Any] | None = None) -> Response:
        response = await self._connection.query(query=render(sql), vars=variables)
        return Response(data=response)
