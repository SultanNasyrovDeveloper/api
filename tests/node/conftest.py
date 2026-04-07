from typing import Callable

import pytest
from faker import Faker

BASE = '/api/v1/node/nodes'


@pytest.fixture
def node_create_data_factory(faker: Faker) -> Callable:
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
