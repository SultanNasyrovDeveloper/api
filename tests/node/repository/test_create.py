from collections.abc import Callable

import pytest

from minager.node.models import Node
from minager.node.repositories import NodeRepository


@pytest.mark.asyncio
async def test_create_node(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    node_data = node_create_data_factory()
    created_node = await test_palace_node_repository.create(node_data)

    assert isinstance(created_node, Node)
    assert created_node.pk is not None
    assert created_node.title == node_data['title']
    assert created_node.questions == node_data['questions']
    assert created_node.owner_id == node_data['owner_id']
    assert created_node.content == node_data['content']
    assert created_node.size == 0
    assert created_node.is_learn == True  # noqa: E712 -- Boolean is an int subclass, not `bool`
    assert created_node.order is not None
    assert created_node.last_interval == 0
    assert created_node.last_rating == 0
