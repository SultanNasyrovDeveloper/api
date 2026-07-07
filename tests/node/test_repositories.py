from collections.abc import Callable

import pytest
from faker import Faker

from minager.node.models import Child, Node
from minager.node.repositories import NodeRepository
from minager.user.schemas import UserWithProfileSchema


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


@pytest.mark.asyncio
async def test_get_node(test_palace_node_repository: NodeRepository, test_user_root_node: Node):
    retrieved_node = await test_palace_node_repository.get(str(test_user_root_node.pk))

    assert isinstance(retrieved_node, Node)
    assert retrieved_node.pk == test_user_root_node.pk
    assert retrieved_node.title == test_user_root_node.title
    assert retrieved_node.questions == test_user_root_node.questions
    assert retrieved_node.owner_id == test_user_root_node.owner_id
    assert retrieved_node.content == test_user_root_node.content


@pytest.mark.asyncio
async def test_get_node_nonexistent_id(test_palace_node_repository: NodeRepository):
    result = await test_palace_node_repository.get('nonexistent_id')
    assert result is None


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
async def test_update_node(
    test_palace_node_repository: NodeRepository,
    test_user_root_node: Node,
    faker: Faker,
):
    update_data = {'title': faker.name(), 'questions': faker.sentence()}
    updated_node = await test_palace_node_repository.update(test_user_root_node, **update_data)
    assert updated_node
    assert updated_node.title == update_data['title']
    assert updated_node.questions == update_data['questions']


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


@pytest.mark.asyncio
async def test_search_nodes_pagination(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    owner_id = 'user_list'
    for _ in range(15):
        await test_palace_node_repository.create(node_create_data_factory(owner_id=owner_id))
    page1 = await test_palace_node_repository.search('', page=1, size=10, owner_id=owner_id)
    assert len(page1) == 10


@pytest.mark.asyncio
async def test_get_subtree_ids_single_root(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    children = [await create_child_node(root, node_create_data_factory()) for _ in range(3)]

    ids = await test_palace_node_repository.get_subtree_ids([root.pk])

    all_pks = {c.pk for c in children} | {root.pk}
    assert all_pks == set(ids)


@pytest.mark.asyncio
async def test_get_subtree_ids_multiple_roots_combines_both_subtrees(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root_a = await test_palace_node_repository.create(node_create_data_factory())
    root_b = await test_palace_node_repository.create(node_create_data_factory())
    children_a = [await create_child_node(root_a, node_create_data_factory()) for _ in range(2)]
    children_b = [await create_child_node(root_b, node_create_data_factory()) for _ in range(2)]

    ids = await test_palace_node_repository.get_subtree_ids([root_a.pk, root_b.pk])

    all_expected = {c.pk for c in children_a + children_b} | {root_a.pk, root_b.pk}
    assert all_expected == set(ids)


@pytest.mark.asyncio
async def test_get_subtree_ids_deduplicates_when_same_root_passed_twice(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    for _ in range(3):
        await create_child_node(root, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root.pk, root.pk])

    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_get_subtree_ids_respects_limit(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root_a = await test_palace_node_repository.create(node_create_data_factory())
    root_b = await test_palace_node_repository.create(node_create_data_factory())
    for _ in range(5):
        await create_child_node(root_a, node_create_data_factory())
    for _ in range(5):
        await create_child_node(root_b, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root_a.pk, root_b.pk], limit=3)

    assert len(ids) <= 3


@pytest.mark.asyncio
async def test_search_provides_ancestor_context_for_disambiguation(
    test_palace_node_repository: NodeRepository,
    test_user: UserWithProfileSchema,
    test_user_root_node: Node,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    """Multiple nodes with same title have ancestor context for UI disambiguation"""
    # Root -> Python -> Data Model
    python_node = await create_child_node(
        test_user_root_node, node_create_data_factory(title='Python', owner_id=str(test_user.id))
    )
    await create_child_node(
        python_node, node_create_data_factory(title='Data Model', owner_id=str(test_user.id))
    )

    # Root -> JavaScript -> Data Model
    javascript_node = await create_child_node(
        test_user_root_node, node_create_data_factory(title='JavaScript', owner_id=str(test_user.id))
    )
    await create_child_node(
        javascript_node, node_create_data_factory(title='Data Model', owner_id=str(test_user.id))
    )

    # Root -> SQL -> Data Model
    sql_node = await create_child_node(
        test_user_root_node, node_create_data_factory(title='SQL', owner_id=str(test_user.id))
    )
    await create_child_node(
        sql_node, node_create_data_factory(title='Data Model', owner_id=str(test_user.id))
    )

    # ACT: Search for "Data Model"
    results = await test_palace_node_repository.search(query='Data Model', owner_id=str(test_user.id))

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
