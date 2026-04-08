from collections.abc import Callable

import pytest
from faker import Faker

from minager.node.dto import NodeSubtreeStatistics
from minager.node.managers import PalaceNodeManager
from minager.node.models import Node


@pytest.mark.asyncio
async def test_create_node(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    node_data = node_create_data_factory()
    created_node = await test_palace_node_manager.create(node_data)

    assert isinstance(created_node, Node)
    assert created_node.pk is not None
    assert created_node.title == node_data['title']
    assert created_node.questions == node_data['questions']
    assert created_node.owner_id == node_data['owner_id']
    assert created_node.content == node_data['content']
    assert created_node.size == 0
    assert created_node.is_learn is True
    assert created_node.order is not None
    assert created_node.last_interval == 0
    assert created_node.last_rating == 0


@pytest.mark.asyncio
async def test_get_node(test_palace_node_manager: PalaceNodeManager, test_user_root_node: Node):
    retrieved_node = await test_palace_node_manager.get(str(test_user_root_node.pk))

    assert isinstance(retrieved_node, Node)
    assert retrieved_node.pk == test_user_root_node.pk
    assert retrieved_node.title == test_user_root_node.title
    assert retrieved_node.questions == test_user_root_node.questions
    assert retrieved_node.owner_id == test_user_root_node.owner_id
    assert retrieved_node.content == test_user_root_node.content


@pytest.mark.asyncio
async def test_get_node_nonexistent_id(test_palace_node_manager: PalaceNodeManager):
    result = await test_palace_node_manager.get('nonexistent_id')
    assert result is None


@pytest.mark.asyncio
async def test_add_child(
    test_palace_node_manager: PalaceNodeManager,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
):
    child_node = await test_palace_node_manager.add_child(
        test_user_root_node.pk, node_create_data_factory()
    )

    assert child_node is not None
    assert child_node.parent_pk == test_user_root_node.pk

    children = await test_palace_node_manager.get_children(test_user_root_node.pk)
    assert any(c.pk == child_node.pk for c in children)


@pytest.mark.asyncio
async def test_patch_node(
    test_palace_node_manager: PalaceNodeManager,
    test_user_root_node: Node,
    faker: Faker,
):
    update_data = {'title': faker.name(), 'questions': faker.sentence()}
    updated_node = await test_palace_node_manager.patch(test_user_root_node.pk, update_data)
    assert updated_node
    assert updated_node.title == update_data['title']
    assert updated_node.questions == update_data['questions']


@pytest.mark.asyncio
async def test_get_subtree(
    test_palace_node_manager: PalaceNodeManager,
    subtree: tuple[Node, NodeSubtreeStatistics],
):
    subtree_root, subtree_statistics = subtree
    tree = await test_palace_node_manager.get_subtree(subtree_root.pk)
    assert tree.pk == subtree_root.pk
    # TODO: Think how you can really test this
    assert len(tree.children) > 0


@pytest.mark.asyncio
async def test_get_subtree_statistics(
    test_palace_node_manager: PalaceNodeManager,
    subtree: tuple[Node, NodeSubtreeStatistics],
):
    subtree_root, expected_statistics = subtree
    subtree_statistics = await test_palace_node_manager.get_subtree_statistics(subtree_root.pk)
    assert subtree_statistics.count == expected_statistics.count
    assert subtree_statistics.owner_views == expected_statistics.owner_views
    assert subtree_statistics.repetitions == expected_statistics.repetitions
    assert subtree_statistics.size == expected_statistics.size
    assert subtree_statistics.empty == expected_statistics.empty
    assert subtree_statistics.outdated == expected_statistics.outdated
    assert subtree_statistics.not_visited == expected_statistics.not_visited


@pytest.mark.asyncio
async def test_delete_node(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    root = await test_palace_node_manager.create(node_create_data_factory())
    child = await test_palace_node_manager.add_child(root.pk, node_create_data_factory())

    await test_palace_node_manager.delete(root.pk)
    assert await test_palace_node_manager.get(root.pk) is None
    assert await test_palace_node_manager.get(child.pk) is None
    # TODO: Test there is no relations also


# @pytest.mark.asyncio
# async def test_list_nodes_pagination_and_search(test_palace_node_manager: PalaceNodeManager):
#     owner_id = 'user_list'
#     # Create 15 nodes
#     for i in range(15):
#         await test_palace_node_manager.create(
#             NodeCreateSchema(title=f'Node {i}', questions='?', owner_id=owner_id,
#                              content='{}').model_dump())
#
#     # First page
#     page1 = await test_palace_node_manager.list_(owner_id, '', page=1, per_page=10)
#     assert len(page1) == 10
#     # Second page
#     page2 = await test_palace_node_manager.list_(owner_id, '', page=2, per_page=10)
#     assert len(page2) == 5
#     # Search
#     search_results = await test_palace_node_manager.list_(owner_id, 'Node 1', page=1, per_page=10)
#     assert all('Node 1' in node.title for node in search_results)

# @pytest.mark.asyncio
# async def test_move_node_changes_parent(test_palace_node_manager: PalaceNodeManager):
#     parent = await test_palace_node_manager.create(
#         NodeCreateSchema(
#             title='Parent',
#             questions='?',
#             owner_id='user_move',
#             content='{}'
#         ).model_dump()
#     )
#     child = await test_palace_node_manager.create(
#         NodeCreateSchema(
#             title='Child',
#             questions='?',
#             owner_id='user_move',
#             content='{}'
#         ).model_dump()
#     )
#
#     moved_node = await test_palace_node_manager.move(child.pk, parent.pk, 1)  # last_child
#     assert moved_node is not None
#     updated_child = await test_palace_node_manager.get(child.pk)
#     assert updated_child.parent_id.id == parent.pk
#
