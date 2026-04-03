from typing import Callable

import pytest

from minager.node.managers import PalaceNodeManager
from minager.node.models import Node
from minager.node.schemas import NodeCreateSchema


@pytest.mark.asyncio
async def test_get_node_returns_node(test_palace_node_manager: PalaceNodeManager):
    node_data = NodeCreateSchema(
        title='Test Node', questions='What is a test node?', owner_id='user_123', content='{}'
    )
    created_node = await test_palace_node_manager.create(node_data)
    retrieved_node = await test_palace_node_manager.get(str(created_node.pk))

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


@pytest.mark.asyncio
async def test_create_node_returns_node(
    test_palace_node_manager: PalaceNodeManager, node_create_data_factory: Callable
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
