from logging import Logger, getLogger
from typing import Any

from aiohttp import BasicAuth, ClientSession

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
        if self._connection:
            self._logger.warning('Surreal db client already instantiated. No need to do it twice.')
        else:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _check_connection(self):
        assert self._connection

    async def connect(self):
        assert self._config.namespace
        assert self._config.name
        self._connection = ClientSession(
            base_url=self._base_url,
            headers={
                'Accept': 'application/json',
                'surreal-ns': self._config.namespace,
                'surreal-db': self._config.name,
            },
            auth=BasicAuth(
                login=self._config.username, password=self._config.password.get_secret_value()
            ),
        )
        return self._connection

    async def close(self):
        await self._connection.close()
        self._connection = None

    async def query(self, sql: Expression, variables: dict[str, Any] | None = None) -> Response:
        client_response = await self._connection.post('/sql', data=render(sql), params=variables)
        response_data = await client_response.json()
        return Response(data=response_data)
