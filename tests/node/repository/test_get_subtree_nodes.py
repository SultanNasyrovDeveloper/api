from collections.abc import Callable

import pytest

from minager.node.models import Node
from minager.node.repositories import NodeRepository


@pytest.mark.asyncio
async def test_get_subtree_nodes(
    test_palace_node_repository: NodeRepository,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    await create_child_node(test_user_root_node, node_create_data_factory(order='aaaaa'))

    nodes = await test_palace_node_repository.get_subtree_nodes(test_user_root_node.pk)
    assert isinstance(nodes, list)
    assert len(nodes) >= 2
