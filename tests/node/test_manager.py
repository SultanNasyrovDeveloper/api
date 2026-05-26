from collections.abc import Callable

import pytest
from faker import Faker

from minager.auth.schemas import UserWithProfileSchema
from minager.node.dto import NodeSubtreeStatistics
from minager.node.enums import MovePosition
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
    child_node = await test_palace_node_manager.add_child(test_user_root_node.pk, node_create_data_factory())

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


@pytest.mark.asyncio
async def test_search_nodes_pagination(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    owner_id = 'user_list'
    for i in range(15):
        await test_palace_node_manager.create(node_create_data_factory(owner_id=owner_id))
    page1 = await test_palace_node_manager.search('', page=1, size=10, owner_id=owner_id)
    assert len(page1) == 10


@pytest.mark.asyncio
async def test_move_node_first_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    initial_new_parent_children_count = 3
    initial_parent = await test_palace_node_manager.create(node_create_data_factory())
    child = await test_palace_node_manager.add_child(initial_parent.pk, node_create_data_factory())
    new_parent = await test_palace_node_manager.create(node_create_data_factory())
    for _ in range(initial_new_parent_children_count):
        await test_palace_node_manager.add_child(new_parent.pk, node_create_data_factory())
    await test_palace_node_manager.move(child.pk, new_parent.pk, MovePosition.first_child)

    moved_node = await test_palace_node_manager.get(child.pk)
    assert moved_node.parent_pk == new_parent.pk
    updated_new_parent_children_list = await test_palace_node_manager.get_children(new_parent.pk)
    assert len(updated_new_parent_children_list) == initial_new_parent_children_count + 1
    assert updated_new_parent_children_list[0].pk == child.pk


@pytest.mark.asyncio
async def test_move_node_last_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    initial_new_parent_children_count = 3
    initial_parent = await test_palace_node_manager.create(node_create_data_factory())
    child = await test_palace_node_manager.add_child(initial_parent.pk, node_create_data_factory())
    new_parent = await test_palace_node_manager.create(node_create_data_factory())
    for _ in range(initial_new_parent_children_count):
        await test_palace_node_manager.add_child(new_parent.pk, node_create_data_factory())
    await test_palace_node_manager.move(child.pk, new_parent.pk, MovePosition.last_child)

    moved_node = await test_palace_node_manager.get(child.pk)
    assert moved_node.parent_pk == new_parent.pk
    updated_new_parent_children_list = await test_palace_node_manager.get_children(new_parent.pk)
    assert len(updated_new_parent_children_list) == initial_new_parent_children_count + 1
    assert updated_new_parent_children_list[-1].pk == child.pk


@pytest.mark.asyncio
async def test_move_node_after(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    initial_new_parent_children_count = 3
    initial_parent = await test_palace_node_manager.create(node_create_data_factory())
    child = await test_palace_node_manager.add_child(initial_parent.pk, node_create_data_factory())
    new_parent = await test_palace_node_manager.create(node_create_data_factory())
    to = None
    for index in range(initial_new_parent_children_count):
        is_second_child = index == 1
        node = await test_palace_node_manager.add_child(new_parent.pk, node_create_data_factory())
        if is_second_child:
            to = node
    await test_palace_node_manager.move(child.pk, to.pk, MovePosition.after)

    moved_node = await test_palace_node_manager.get(child.pk)
    assert moved_node.parent_pk == new_parent.pk
    updated_new_parent_children_list = await test_palace_node_manager.get_children(new_parent.pk)
    assert len(updated_new_parent_children_list) == initial_new_parent_children_count + 1
    assert updated_new_parent_children_list[2].pk == child.pk


@pytest.mark.asyncio
async def test_move_node_before(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    initial_new_parent_children_count = 3
    initial_parent = await test_palace_node_manager.create(node_create_data_factory())
    child = await test_palace_node_manager.add_child(initial_parent.pk, node_create_data_factory())
    new_parent = await test_palace_node_manager.create(node_create_data_factory())
    to = None
    for index in range(initial_new_parent_children_count):
        is_second_child = index == 1
        node = await test_palace_node_manager.add_child(new_parent.pk, node_create_data_factory())
        if is_second_child:
            to = node
    await test_palace_node_manager.move(child.pk, to.pk, MovePosition.before)

    moved_node = await test_palace_node_manager.get(child.pk)
    assert moved_node.parent_pk == new_parent.pk
    updated_new_parent_children_list = await test_palace_node_manager.get_children(new_parent.pk)
    assert len(updated_new_parent_children_list) == initial_new_parent_children_count + 1
    assert updated_new_parent_children_list[1].pk == child.pk


@pytest.mark.asyncio
async def test_search_provides_ancestor_context_for_disambiguation(
    test_palace_node_manager: PalaceNodeManager,
    test_user: UserWithProfileSchema,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
):
    """Multiple nodes with same title have ancestor context for UI disambiguation"""
    # Root -> Python -> Data Model
    python_node = await test_palace_node_manager.add_child(
        test_user_root_node.pk, node_create_data_factory(title='Python', owner_id=test_user.id)
    )
    python_data_model = await test_palace_node_manager.add_child(
        python_node.pk, node_create_data_factory(title='Data Model', owner_id=test_user.id)
    )

    # Root -> JavaScript -> Data Model
    javascript_node = await test_palace_node_manager.add_child(
        test_user_root_node.pk, node_create_data_factory(title='JavaScript', owner_id=test_user.id)
    )
    javascript_data_model = await test_palace_node_manager.add_child(
        javascript_node.pk, node_create_data_factory(title='Data Model', owner_id=test_user.id)
    )

    # Root -> SQL -> Data Model
    sql_node = await test_palace_node_manager.add_child(
        test_user_root_node.pk, node_create_data_factory(title='SQL', owner_id=test_user.id)
    )
    sql_data_model = await test_palace_node_manager.add_child(
        sql_node.pk, node_create_data_factory(title='Data Model', owner_id=test_user.id)
    )

    # ACT: Search for "Data Model"
    results = await test_palace_node_manager.search(query='Data Model', user_id=test_user.id)

    # ASSERT
    # Should return 3 nodes all named "Data Model"
    assert len(results) == 3, "Should find 3 'Data Model' nodes"

    # All should have title "Data Model"
    for result in results:
        assert result.title == 'Data Model'

    # Each should have ancestors field populated
    for result in results:
        assert hasattr(result, 'ancestors')
        assert isinstance(result.ancestors, list)
        assert len(result.ancestors) > 0

    # Extract immediate parent from each result (last ancestor)
    parent_titles = {result.ancestors[-1].title for result in results}

    # Verify each has different parent context
    assert 'Python' in parent_titles, 'Should have Data Model under Python'
    assert 'JavaScript' in parent_titles, 'Should have Data Model under JavaScript'
    assert 'SQL' in parent_titles, 'Should have Data Model under SQL'
