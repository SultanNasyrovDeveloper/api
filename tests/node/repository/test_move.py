from collections.abc import Callable

import pytest

from minager.node.models import Child
from minager.node.repositories import NodeRepository


@pytest.mark.asyncio
async def test_get_move_validation_context(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    child = await test_palace_node_repository.create(node_create_data_factory())
    await test_palace_node_repository.relate(child, Child, parent)

    # child is a descendant of parent, so moving parent under child would create a cycle
    context = await test_palace_node_repository.get_move_validation_context(parent.pk, child.pk)
    assert context['source']
    assert context['target']
    assert context['has_cycle']

    # parent is not a descendant of child, so moving child under parent is fine
    context = await test_palace_node_repository.get_move_validation_context(child.pk, parent.pk)
    assert not context['has_cycle']

    context = await test_palace_node_repository.get_move_validation_context('nonexistent_id', child.pk)
    assert not context['source']


@pytest.mark.asyncio
async def test_get_sibling_order_context_before_and_after(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_repository.create(node_create_data_factory(order='aaaaa'))
    await test_palace_node_repository.relate(node_a, Child, parent)
    node_b = await test_palace_node_repository.create(node_create_data_factory(order='mmmmm'))
    await test_palace_node_repository.relate(node_b, Child, parent)
    node_c = await test_palace_node_repository.create(node_create_data_factory(order='zzzzz'))
    await test_palace_node_repository.relate(node_c, Child, parent)

    before_context = await test_palace_node_repository.get_sibling_order_context(node_b.pk, before=True)
    assert before_context['new_parent'] == parent.pk
    assert before_context['previous'] == 'aaaaa'
    assert before_context['next'] == 'mmmmm'

    after_context = await test_palace_node_repository.get_sibling_order_context(node_b.pk, before=False)
    assert after_context['new_parent'] == parent.pk
    assert after_context['previous'] == 'mmmmm'
    assert after_context['next'] == 'zzzzz'
