import pytest
from faker import Faker

from minager.node.models import Node
from minager.node.repositories import NodeRepository


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
