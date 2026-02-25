import pytest
from httpx import AsyncClient

from minager.node.schemas import NodeDetailSchema
from tests.node.conftest import BASE


@pytest.mark.asyncio
async def test_get_node_returns_node_detail(
    app_client: AsyncClient,
    root_node: NodeDetailSchema,
    auth_headers: dict,
):
    url = f'{BASE}/{root_node.pk}'
    response = await app_client.get(url, headers=auth_headers)
    assert response.status_code == 200
    response_body = response.json()
    assert response_body['id'] == root_node.id.id
    assert response_body['title'] == root_node.title
