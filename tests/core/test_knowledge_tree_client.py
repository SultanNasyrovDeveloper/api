"""The knowledge_tree seam must carry the subtree strategies, not just the node repository.

Consumers (learning_session) are typed against AbstractKnowledgeTreeClient, so every test here
annotates the client as the port rather than the concrete impl — that is the contract under test.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from faker import Faker
from surorm import Session
from surorm.data_model import Datetime
from surrealdb import AsyncWsSurrealConnection

from minager.core.clients.knowledge_tree import KnowledgeTreeClient, SubtreeFilter, TraversalOrder
from minager.core.clients.knowledge_tree.base import AbstractKnowledgeTreeClient
from minager.node.models import Child, Node
from minager.node.repositories import NodeRepository


def _past(days: int = 1) -> Datetime:
    return Datetime(datetime.now(UTC) - timedelta(days=days))


def _future(days: int = 1) -> Datetime:
    return Datetime(datetime.now(UTC) + timedelta(days=days))


@pytest.fixture()
def knowledge_tree_client(
    surreal_test_connection: AsyncWsSurrealConnection,
) -> AbstractKnowledgeTreeClient:
    return KnowledgeTreeClient(session=Session(connection=surreal_test_connection))


@pytest.fixture()
def node_data_factory(faker: Faker) -> Callable[..., dict]:
    def _factory(**kwargs) -> dict:
        return {
            'title': faker.name(),
            'questions': faker.sentence(),
            'owner_id': faker.pystr(max_chars=20),
            'content': '{"root": {}}',
            'order': 'aaaaa',
            **kwargs,
        }

    return _factory


@pytest.fixture()
def create_child_node(test_palace_node_repository: NodeRepository) -> Callable[..., Node]:
    async def _create_child(parent: Node, data: dict) -> Node:
        child = await test_palace_node_repository.create(data)
        await test_palace_node_repository.relate(child, Child, parent)
        return await test_palace_node_repository.get(child.pk)

    return _create_child


@pytest.mark.asyncio
async def test_client_forwards_filter_to_the_subtree_query(
    knowledge_tree_client: AbstractKnowledgeTreeClient,
    test_palace_node_repository: NodeRepository,
    node_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_data_factory(next_optimal_repetition=_future()))
    overdue = await create_child_node(root, node_data_factory(next_optimal_repetition=_past()))
    await create_child_node(root, node_data_factory(next_optimal_repetition=_future()))

    ids = await knowledge_tree_client.get_subtree_ids([root.pk], filter_=SubtreeFilter.due)

    assert set(ids) == {overdue.pk}


@pytest.mark.asyncio
async def test_client_forwards_order_to_the_subtree_query(
    knowledge_tree_client: AbstractKnowledgeTreeClient,
    test_palace_node_repository: NodeRepository,
    node_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_data_factory(next_optimal_repetition=_past(4)))
    soonest = await create_child_node(root, node_data_factory(next_optimal_repetition=_past(10)))
    latest = await create_child_node(root, node_data_factory(next_optimal_repetition=_past(1)))

    ids = await knowledge_tree_client.get_subtree_ids([root.pk], order=TraversalOrder.due_first)

    assert ids == [soonest.pk, root.pk, latest.pk]


@pytest.mark.asyncio
async def test_client_composes_filter_and_order(
    knowledge_tree_client: AbstractKnowledgeTreeClient,
    test_palace_node_repository: NodeRepository,
    node_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_data_factory(next_optimal_repetition=_future()))
    soonest = await create_child_node(root, node_data_factory(next_optimal_repetition=_past(10)))
    latest = await create_child_node(root, node_data_factory(next_optimal_repetition=_past(1)))
    await create_child_node(root, node_data_factory(next_optimal_repetition=_future()))

    ids = await knowledge_tree_client.get_subtree_ids(
        [root.pk], filter_=SubtreeFilter.due, order=TraversalOrder.due_first
    )

    assert ids == [soonest.pk, latest.pk]


@pytest.mark.asyncio
async def test_client_defaults_to_the_whole_subtree_in_bfs_order(
    knowledge_tree_client: AbstractKnowledgeTreeClient,
    test_palace_node_repository: NodeRepository,
    node_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_data_factory())
    children = [await create_child_node(root, node_data_factory()) for _ in range(3)]

    ids = await knowledge_tree_client.get_subtree_ids([root.pk])

    assert set(ids) == {c.pk for c in children} | {root.pk}


@pytest.mark.asyncio
async def test_client_forwards_limit(
    knowledge_tree_client: AbstractKnowledgeTreeClient,
    test_palace_node_repository: NodeRepository,
    node_data_factory: Callable[..., dict],
    create_child_node: Callable[..., Node],
):
    root = await test_palace_node_repository.create(node_data_factory())
    for _ in range(4):
        await create_child_node(root, node_data_factory())

    ids = await knowledge_tree_client.get_subtree_ids([root.pk], limit=2)

    assert len(ids) == 2
