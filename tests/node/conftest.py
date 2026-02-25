import pytest_asyncio
from httpx import AsyncClient

from minager.node.managers import PalaceNodeManager
from minager.node.schemas import NodeDetailSchema
from tests.conftest import UserTestContext

BASE = '/api/v1/node/nodes'


# ─── helpers ─────────────────────────────────────────────────────────────────


def node_body(**overrides) -> dict:
    """Minimal valid request body for POST …/add-child."""
    return {
        'title': 'Test Node',
        'questions': 'What is this node about?',
        'content': '{"root": {}}',
        'is_learn': True,
        'tags': [],
        **overrides,
    }


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def root_node(
    test_palace_node_manager: PalaceNodeManager,
    test_user: UserTestContext,
) -> NodeDetailSchema:
    """Fetches the palace root node that was created by the test_user fixture."""
    return await test_palace_node_manager.get(test_user.root_node_id)


@pytest_asyncio.fixture
async def child_node(
    app_client: AsyncClient,
    root_node: NodeDetailSchema,
    auth_headers: dict,
) -> dict:
    """A single child node under the palace root, created via the API."""
    resp = await app_client.post(
        f'{BASE}/{root_node.id.id}/add-child',
        json=node_body(title='Child Node'),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def two_children(
    app_client: AsyncClient,
    root_node: NodeDetailSchema,
    auth_headers: dict,
) -> tuple[dict, dict]:
    """
    Two sibling child nodes under the palace root.
    child_a is created first (lower lexorank order), child_b second (higher order).
    """
    r1 = await app_client.post(
        f'{BASE}/{root_node.id.id}/add-child',
        json=node_body(title='Child A'),
        headers=auth_headers,
    )
    r2 = await app_client.post(
        f'{BASE}/{root_node.id.id}/add-child',
        json=node_body(title='Child B'),
        headers=auth_headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    return r1.json(), r2.json()
