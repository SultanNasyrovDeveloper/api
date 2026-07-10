import pytest

from minager.node.models import Node
from minager.node.repositories import NodeRepository


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
