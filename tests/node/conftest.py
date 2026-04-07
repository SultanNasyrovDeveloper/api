import random
from datetime import UTC, datetime, timedelta
from typing import Callable

import pytest
import pytest_asyncio
from faker import Faker

from minager.node.dto import NodeSubtreeStatistics
from minager.node.managers import PalaceNodeManager
from minager.node.models import Node

BASE = '/api/v1/node/nodes'


@pytest.fixture
def node_create_data_factory(faker: Faker) -> Callable[..., dict]:
    def _factory(**kwargs):
        return {
            'title': faker.name(),
            'questions': faker.sentence(),
            'owner_id': faker.pystr(max_chars=20),
            'content': '{"root": {}}',
            'order': 'aaaaa',
            **kwargs,
        }

    return _factory


@pytest_asyncio.fixture()
async def subtree(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
    faker: Faker,
) -> tuple[Node, NodeSubtreeStatistics]:
    root_node = await test_palace_node_manager.create(node_create_data_factory())
    assert root_node

    statistics = NodeSubtreeStatistics()

    def _generate_node_data(overall: NodeSubtreeStatistics) -> dict:
        last_rating = faker.pyint(min_value=1, max_value=6)
        difficulty = faker.pyfloat(right_digits=1, min_value=1, max_value=10)

        is_outdated = random.choice([True, False])
        is_visited = random.choice([True, False])
        is_empty = random.choice([True, False])

        size = faker.pyint() if not is_empty else 0
        owner_views = faker.pyint() if is_visited else 0
        repetitions = (
            faker.pyint(max_value=owner_views) - faker.pyint(max_value=owner_views)
            if is_visited
            else 0
        )

        overall.count += 1
        overall.average_rating = round((overall.average_rating + last_rating) / overall.count)
        overall.owner_views += owner_views
        overall.repetitions += repetitions
        overall.size += size
        overall.outdated += 1 if is_outdated else 0
        overall.not_visited += 1 if not is_visited else 0
        overall.empty += 1 if is_empty else 0

        return node_create_data_factory(
            last_rating=last_rating,
            difficulty=difficulty,
            repetitions=repetitions,
            owner_views=owner_views,
            size=size,
            next_optimal_repetition=(
                datetime.now(UTC)
                - timedelta(days=faker.pyint(max_value=5), hours=faker.pyint(max_value=23))
                if is_outdated
                else datetime.now(UTC)
                + timedelta(days=faker.pyint(max_value=5), hours=faker.pyint(max_value=23))
            ),
        )

    for _ in range(random.randint(3, 10)):
        new_node = await test_palace_node_manager.add_child(
            root_node.pk,
            _generate_node_data(statistics),
        )
        for _ in range(random.randint(3, 5)):
            await test_palace_node_manager.add_child(
                new_node.pk,
                _generate_node_data(statistics),
            )

    return root_node, statistics
