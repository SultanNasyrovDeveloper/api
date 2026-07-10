from collections.abc import Callable

import pytest

from minager.node.models import Node
from minager.node.repositories import NodeRepository


@pytest.mark.asyncio
async def test_delete_node(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    child = await create_child_node(root, node_create_data_factory())

    await test_palace_node_repository.delete(root.pk)
    assert await test_palace_node_repository.get(root.pk) is None
    assert await test_palace_node_repository.get(child.pk) is None
    # TODO: Test there is no relations also
