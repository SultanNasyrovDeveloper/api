from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from surorm.data_model import Datetime

from minager.node import enums
from minager.node.models import Node
from minager.node.repositories import NodeRepository


def _past(days: int = 1) -> Datetime:
    return Datetime(datetime.now(UTC) - timedelta(days=days))


def _future(days: int = 1) -> Datetime:
    return Datetime(datetime.now(UTC) + timedelta(days=days))


@pytest.mark.asyncio
async def test_single_root_returns_the_whole_subtree(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    children = [await create_child_node(root, node_create_data_factory()) for _ in range(3)]

    ids = await test_palace_node_repository.get_subtree_ids([root.pk])

    assert set(ids) == {c.pk for c in children} | {root.pk}


@pytest.mark.asyncio
async def test_multiple_roots_combine_both_subtrees(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root_a = await test_palace_node_repository.create(node_create_data_factory())
    root_b = await test_palace_node_repository.create(node_create_data_factory())
    children_a = [await create_child_node(root_a, node_create_data_factory()) for _ in range(2)]
    children_b = [await create_child_node(root_b, node_create_data_factory()) for _ in range(2)]

    ids = await test_palace_node_repository.get_subtree_ids([root_a.pk, root_b.pk])

    assert set(ids) == {c.pk for c in children_a + children_b} | {root_a.pk, root_b.pk}


@pytest.mark.asyncio
async def test_deduplicates_when_same_root_passed_twice(
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
async def test_filter_due_returns_only_nodes_scheduled_on_or_before_now(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(
        node_create_data_factory(next_optimal_repetition=_future())
    )
    overdue = await create_child_node(root, node_create_data_factory(next_optimal_repetition=_past()))
    await create_child_node(root, node_create_data_factory(next_optimal_repetition=_future()))
    await create_child_node(root, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], filter_=enums.SubtreeFilter.due)

    assert set(ids) == {overdue.pk}


@pytest.mark.asyncio
async def test_filter_struggling_returns_repeatedly_reviewed_low_rated_nodes(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(repetitions=0, last_rating=5))
    struggling = await create_child_node(root, node_create_data_factory(repetitions=3, last_rating=2))
    await create_child_node(root, node_create_data_factory(repetitions=3, last_rating=4))
    await create_child_node(root, node_create_data_factory(repetitions=2, last_rating=1))

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], filter_=enums.SubtreeFilter.struggling)

    assert set(ids) == {struggling.pk}


@pytest.mark.asyncio
async def test_filter_never_reviewed_returns_unseen_or_unrepeated_nodes(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(owner_views=5, repetitions=5))
    unseen = await create_child_node(root, node_create_data_factory(owner_views=0, repetitions=5))
    unrepeated = await create_child_node(root, node_create_data_factory(owner_views=5, repetitions=0))
    await create_child_node(root, node_create_data_factory(owner_views=1, repetitions=1))

    ids = await test_palace_node_repository.get_subtree_ids(
        [root.pk], filter_=enums.SubtreeFilter.never_reviewed
    )

    assert set(ids) == {unseen.pk, unrepeated.pk}


@pytest.mark.asyncio
async def test_filter_empty_returns_nodes_without_content(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(size=100))
    empty = await create_child_node(root, node_create_data_factory(size=0))
    await create_child_node(root, node_create_data_factory(size=50))

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], filter_=enums.SubtreeFilter.empty)

    assert set(ids) == {empty.pk}


@pytest.mark.asyncio
async def test_filter_keeps_descending_past_a_non_matching_node(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(size=100))
    filled_child = await create_child_node(root, node_create_data_factory(size=100))
    empty_grandchild = await create_child_node(filled_child, node_create_data_factory(size=0))

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], filter_=enums.SubtreeFilter.empty)

    assert set(ids) == {empty_grandchild.pk}


@pytest.mark.asyncio
async def test_filter_defaults_to_all(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(size=0))
    child = await create_child_node(root, node_create_data_factory(size=100))

    defaulted = await test_palace_node_repository.get_subtree_ids([root.pk])
    explicit = await test_palace_node_repository.get_subtree_ids([root.pk], filter_=enums.SubtreeFilter.all)

    assert set(defaulted) == set(explicit) == {root.pk, child.pk}


@pytest.mark.asyncio
async def test_order_bfs_returns_nodes_level_by_level(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    child_a = await create_child_node(root, node_create_data_factory())
    child_b = await create_child_node(root, node_create_data_factory())
    grandchild = await create_child_node(child_a, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], order=enums.TraversalOrder.bfs)

    position = {id_: index for index, id_ in enumerate(ids)}
    assert position[root.pk] < min(position[child_a.pk], position[child_b.pk])
    assert max(position[child_a.pk], position[child_b.pk]) < position[grandchild.pk]


@pytest.mark.asyncio
async def test_order_defaults_to_bfs(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    child = await create_child_node(root, node_create_data_factory())
    grandchild = await create_child_node(child, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root.pk])

    assert ids == [root.pk, child.pk, grandchild.pk]


@pytest.mark.asyncio
async def test_order_due_first_sorts_by_next_optimal_repetition(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(
        node_create_data_factory(next_optimal_repetition=_past(2))
    )
    least_overdue = await create_child_node(root, node_create_data_factory(next_optimal_repetition=_past(1)))
    most_overdue = await create_child_node(root, node_create_data_factory(next_optimal_repetition=_past(3)))

    ids = await test_palace_node_repository.get_subtree_ids([root.pk], order=enums.TraversalOrder.due_first)

    assert ids == [most_overdue.pk, root.pk, least_overdue.pk]


@pytest.mark.asyncio
async def test_order_random_returns_the_same_set_in_varying_orders(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory())
    for _ in range(9):
        await create_child_node(root, node_create_data_factory())

    orderings = [
        await test_palace_node_repository.get_subtree_ids([root.pk], order=enums.TraversalOrder.random)
        for _ in range(5)
    ]

    assert all(set(ordering) == set(orderings[0]) for ordering in orderings)
    assert len({tuple(ordering) for ordering in orderings}) > 1


@pytest.mark.asyncio
async def test_order_dfs_is_reserved_but_not_yet_implemented(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
):
    root = await test_palace_node_repository.create(node_create_data_factory())

    with pytest.raises(AssertionError):
        await test_palace_node_repository.get_subtree_ids([root.pk], order=enums.TraversalOrder.dfs)


@pytest.mark.asyncio
async def test_filter_and_order_compose(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(
        node_create_data_factory(next_optimal_repetition=_future())
    )
    due_child = await create_child_node(root, node_create_data_factory(next_optimal_repetition=_past(1)))
    due_grandchild = await create_child_node(
        due_child, node_create_data_factory(next_optimal_repetition=_past(3))
    )

    ids = await test_palace_node_repository.get_subtree_ids(
        [root.pk], filter_=enums.SubtreeFilter.due, order=enums.TraversalOrder.bfs
    )

    assert ids == [due_child.pk, due_grandchild.pk]


@pytest.mark.asyncio
async def test_limit_is_total_across_roots(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root_a = await test_palace_node_repository.create(node_create_data_factory())
    root_b = await test_palace_node_repository.create(node_create_data_factory())
    for _ in range(4):
        await create_child_node(root_a, node_create_data_factory())
    for _ in range(4):
        await create_child_node(root_b, node_create_data_factory())

    ids = await test_palace_node_repository.get_subtree_ids([root_a.pk, root_b.pk], limit=3)

    assert len(ids) == 3


@pytest.mark.asyncio
async def test_limit_caps_matching_nodes_not_visited_nodes(
    test_palace_node_repository: NodeRepository,
    node_create_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_create_data_factory(size=100))
    for _ in range(3):
        filled = await create_child_node(root, node_create_data_factory(size=100))
        await create_child_node(filled, node_create_data_factory(size=0))

    ids = await test_palace_node_repository.get_subtree_ids(
        [root.pk], filter_=enums.SubtreeFilter.empty, limit=3
    )

    assert len(ids) == 3
