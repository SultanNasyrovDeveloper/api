from collections.abc import Callable

import pytest

from minager.node.models import Child, Node
from minager.node.repositories import NodeRepository


@pytest.mark.asyncio
async def test_get_last_child_order_and_create_child(
    test_palace_node_repository: NodeRepository,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    last_order = await test_palace_node_repository.get_last_child_order(test_user_root_node.pk)
    assert last_order in (None, '')

    child_data = node_create_data_factory(order='mmmmm')
    child_node = await create_child_node(test_user_root_node, child_data)

    assert child_node is not None
    assert child_node.parent_pk == test_user_root_node.pk
    assert child_node.order == 'mmmmm'

    children = await test_palace_node_repository.get_children(test_user_root_node.pk)
    assert any(c.pk == child_node.pk for c in children)


@pytest.mark.asyncio
async def test_get_first_child_order(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    assert await test_palace_node_repository.get_first_child_order(parent.pk) in (None, '')

    first_child = await test_palace_node_repository.create(node_create_data_factory(order='bbbbb'))
    await test_palace_node_repository.relate(first_child, Child, parent)
    second_child = await test_palace_node_repository.create(node_create_data_factory(order='mmmmm'))
    await test_palace_node_repository.relate(second_child, Child, parent)

    assert await test_palace_node_repository.get_first_child_order(parent.pk) == 'bbbbb'
