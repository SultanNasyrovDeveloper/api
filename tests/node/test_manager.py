import pytest

from minager.node.managers import PalaceNodeManager
from minager.node.models import Node
from minager.node.schemas import NodeCreateSchema

# @pytest.mark.asyncio
# async def test_node_create(test_palace_node_manager: PalaceNodeManager):
#     pass


@pytest.mark.asyncio
async def test_get_node_returns_node(test_palace_node_manager: PalaceNodeManager):
    node_data = NodeCreateSchema(
        title='Test Node', questions='What is a test node?', owner_id='user_123', content='{}'
    )
    created_node = await test_palace_node_manager.create(node_data)
    retrieved_node = await test_palace_node_manager.get(created_node.pk)

    assert isinstance(retrieved_node, Node)

    assert retrieved_node.pk == created_node.pk
    assert retrieved_node.title == node_data.title
    assert retrieved_node.questions == node_data.questions
    assert retrieved_node.owner_id == node_data.owner_id
    assert retrieved_node.content == node_data.content


@pytest.mark.asyncio
async def test_get_node_nonexistent_returns_none(test_palace_node_manager: PalaceNodeManager):
    result = await test_palace_node_manager.get('nonexistent_id')
    assert result is None
