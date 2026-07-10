from collections.abc import Callable

import pytest

from minager.node.models import Node
from minager.node.repositories import NodeRepository
from minager.user.schemas import UserWithProfileSchema


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

    results = await test_palace_node_repository.search(query='Data Model', owner_id=str(test_user.id))

    assert len(results) == 3, "Should find 3 'Data Model' nodes"

    for result in results:
        assert result.title == 'Data Model'

    for result in results:
        assert hasattr(result, 'ancestors')
        assert isinstance(result.ancestors, list)
        assert len(result.ancestors) > 0
