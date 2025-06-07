from typing import Any, Unpack
from urllib.parse import urljoin

import aiohttp
from aiohttp.client import _RequestOptions

from . import schemas


class PalaceNodeServiceClient:
    def __init__(self, url: str):
        self.service_url = url
        self.base_api_url = urljoin(url, 'api/v1/mind-palace/nodes/')
        self._client = aiohttp.ClientSession(base_url=self.base_api_url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.close()

    async def _request(self, method: str, url: str, **kwargs: Unpack[_RequestOptions]) -> Any:
        async with self._client.request(method, url, **kwargs) as response:
            return await response.json()

    async def get_node(self, id_: str) -> schemas.PalaceNode:
        node_data = await self._request('get', id_)
        return schemas.PalaceNode.model_validate(node_data)

    async def get_subtree_ids(self, root_id: str, limit: int = 30) -> list[str]:
        url = f'{root_id}/' + f'subtree-ids?limit={limit}'
        tree_ids = await self._request('get', url)
        return tree_ids

    async def update_node(self, node_id: str, data: dict) -> schemas.PalaceNode:
        updated_node = await self._request('patch', node_id, data=data)
        return schemas.PalaceNode.model_validate(updated_node)
