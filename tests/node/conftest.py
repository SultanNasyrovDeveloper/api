from typing import Callable

import pytest
import pytest_asyncio
from faker import Faker

from minager.node.managers import PalaceNodeManager
from minager.node.schemas import NodeDetailSchema
from tests.conftest import UserTestContext

BASE = '/api/v1/node/nodes'


@pytest_asyncio.fixture
async def root_node(
    test_palace_node_manager: PalaceNodeManager,
    test_user: UserTestContext,
) -> NodeDetailSchema:
    """Fetches the palace root node that was created by the test_user fixture."""
    return await test_palace_node_manager.get(test_user.root_node_id)


@pytest.fixture
def node_create_data_factory(faker: Faker) -> Callable:
    def _factory(**kwargs):
        return {
            'title': faker.name(),
            'questions': faker.sentence(),
            'owner_id': faker.pystr(max_chars=20),
            'content': '{"root": {}}',
            'order': 'aaaaa',
            **kwargs,
        }

    return _factory
