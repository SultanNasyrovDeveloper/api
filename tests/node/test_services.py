from collections.abc import Callable

import pytest
from faker import Faker

from minager.node.dto import NodeSubtreeStatistics
from minager.node.exceptions import NodeNotFoundError
from minager.node.models import Node
from minager.node.services import NodeService


@pytest.mark.asyncio
async def test_get_increments_owner_views_when_viewer_is_owner(
    test_palace_node_service: NodeService,
    test_user_root_node: Node,
):
    initial_views = test_user_root_node.owner_views

    node = await test_palace_node_service.get(test_user_root_node.pk, viewer_id=test_user_root_node.owner_id)

    assert node.owner_views == initial_views + 1


@pytest.mark.asyncio
async def test_get_does_not_increment_owner_views_for_non_owner(
    test_palace_node_service: NodeService,
    test_user_root_node: Node,
):
    initial_views = test_user_root_node.owner_views

    node = await test_palace_node_service.get(test_user_root_node.pk, viewer_id='someone_else')

    assert node.owner_views == initial_views


@pytest.mark.asyncio
async def test_get_raises_not_found_for_missing_node(test_palace_node_service: NodeService):
    with pytest.raises(NodeNotFoundError):
        await test_palace_node_service.get('nonexistent_id', viewer_id='someone')


@pytest.mark.asyncio
async def test_add_child_computes_order_after_existing_children(
    test_palace_node_service: NodeService,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
):
    first_child = await test_palace_node_service.add_child(test_user_root_node.pk, node_create_data_factory())
    second_child = await test_palace_node_service.add_child(
        test_user_root_node.pk, node_create_data_factory()
    )

    assert first_child.parent_pk == test_user_root_node.pk
    assert second_child.parent_pk == test_user_root_node.pk
    assert second_child.order > first_child.order


@pytest.mark.asyncio
async def test_get_statistics_assembles_node_and_subtree_data(
    test_palace_node_service: NodeService,
    subtree: tuple[Node, NodeSubtreeStatistics],
):
    subtree_root, expected_statistics = subtree
    statistics = await test_palace_node_service.get_statistics(subtree_root.pk)

    assert statistics.node.owner_views == subtree_root.owner_views
    assert statistics.subtree.count == expected_statistics.count
    assert statistics.subtree.owner_views == expected_statistics.owner_views
    assert statistics.subtree.repetitions == expected_statistics.repetitions
    assert statistics.subtree.size == expected_statistics.size


@pytest.mark.asyncio
async def test_get_statistics_raises_not_found_for_missing_node(test_palace_node_service: NodeService):
    with pytest.raises(NodeNotFoundError):
        await test_palace_node_service.get_statistics('nonexistent_id')


@pytest.mark.asyncio
async def test_update_returns_updated_node(
    test_palace_node_service: NodeService,
    test_user_root_node: Node,
    faker: Faker,
):
    update_data = {'title': faker.name(), 'questions': faker.sentence()}
    updated_node = await test_palace_node_service.update(test_user_root_node.pk, update_data)
    assert updated_node.title == update_data['title']
    assert updated_node.questions == update_data['questions']


@pytest.mark.asyncio
async def test_update_raises_not_found_for_missing_node(test_palace_node_service: NodeService):
    with pytest.raises(NodeNotFoundError):
        await test_palace_node_service.update('nonexistent_id', {'title': 'New title'})


@pytest.mark.asyncio
async def test_get_subtree_builds_nested_tree(
    test_palace_node_service: NodeService,
    subtree: tuple[Node, NodeSubtreeStatistics],
):
    subtree_root, _subtree_statistics = subtree
    tree = await test_palace_node_service.get_subtree(subtree_root.pk)
    assert tree.pk == subtree_root.pk
    assert len(tree.children) > 0
