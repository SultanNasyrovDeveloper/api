import pytest

from minager.node.enums import NodeRelationType
from minager.node.requests.move import MoveNodeRequest
from minager.node.schemas import NodeCreateSchema


@pytest.mark.asyncio
async def test_move_node_first_child(test_palace_node_manager):
    manager = test_palace_node_manager

    # Create root and children
    root = await manager.create(NodeCreateSchema(title='Root', owner_id='user1'))
    child1 = await manager.create(
        NodeCreateSchema(title='Child1', owner_id='user1', order='aaaaaa')
    )
    child2 = await manager.create(
        NodeCreateSchema(title='Child2', owner_id='user1', order='aaaaab')
    )

    await manager.relate_child(child1.id, root.id)
    await manager.relate_child(child2.id, root.id)

    # Move Child2 as first child
    move_request = MoveNodeRequest(
        db=manager,
        config={
            'node_id': child2.id,
            'target_id': root.id,
            'move_position': NodeRelationType.first_child.value,
            'return_with_children': True,
        },
    )
    result = await move_request.perform()
    updated_node = result.data()['result']

    # Assert new parent and ordering
    assert updated_node['parent_id'] == root.id
    children_ids = [c['id'] for c in updated_node['children']]
    assert children_ids[0] == child2.id


# @pytest.mark.asyncio
# async def test_move_node_last_child(test_palace_node_manager):
#     manager = test_palace_node_manager
#
#     # Create root and children
#     root = await manager.create(NodeCreateSchema(title='Root', owner_id='user1'))
#     child1 = await manager.create(NodeCreateSchema(title='Child1', owner_id='user1'))
#     child2 = await manager.create(NodeCreateSchema(title='Child2', owner_id='user1'))
#
#     await manager.relate_child(child1.id, root.id)
#     await manager.relate_child(child2.id, root.id)
#
#     # Move Child1 as last child
#     move_request = MoveNodeRequest(
#         db=manager,
#         config={
#             'node_id': child1.id,
#             'target_id': root.id,
#             'move_position': NodeRelationType.last_child.value,
#             'return_with_children': True,
#         }
#     )
#     result = await move_request.perform()
#     updated_node = result.data()['result']
#
#     # Assert new parent and ordering
#     assert updated_node['parent_id'] == root.id
#     children_ids = [c['id'] for c in updated_node['children']]
#     assert children_ids[-1] == child1.id
#
#
# @pytest.mark.asyncio
# async def test_move_node_before(test_palace_node_manager):
#     manager = test_palace_node_manager
#
#     # Create root and children
#     root = await manager.create(NodeCreateSchema(title='Root', owner_id='user1'))
#     child1 = await manager.create(NodeCreateSchema(title='Child1', owner_id='user1'))
#     child2 = await manager.create(NodeCreateSchema(title='Child2', owner_id='user1'))
#
#     await manager.relate_child(child1.id, root.id)
#     await manager.relate_child(child2.id, root.id)
#
#     # Move Child2 before Child1
#     move_request = MoveNodeRequest(
#         db=manager,
#         config={
#             'node_id': child2.id,
#             'target_id': child1.id,
#             'move_position': NodeRelationType.before.value,
#             'return_with_children': True,
#         }
#     )
#     result = await move_request.perform()
#     updated_node = result.data()['result']
#
#     # Assert new parent and ordering
#     assert updated_node['parent_id'] == root.id
#     children_ids = [c['id'] for c in await manager.get_children(root.id)]
#     assert children_ids[0] == child2.id
#
#
# @pytest.mark.asyncio
# async def test_move_node_after(test_palace_node_manager):
#     manager = test_palace_node_manager
#
#     # Create root and children
#     root = await manager.create(NodeCreateSchema(title='Root', owner_id='user1'))
#     child1 = await manager.create(NodeCreateSchema(title='Child1', owner_id='user1'))
#     child2 = await manager.create(NodeCreateSchema(title='Child2', owner_id='user1'))
#
#     await manager.relate_child(child1.id, root.id)
#     await manager.relate_child(child2.id, root.id)
#
#     # Move Child1 after Child2
#     move_request = MoveNodeRequest(
#         db=manager,
#         config={
#             'node_id': child1.id,
#             'target_id': child2.id,
#             'move_position': NodeRelationType.after.value,
#             'return_with_children': True,
#         }
#     )
#     result = await move_request.perform()
#     updated_node = result.data()['result']
#
#     # Assert new parent and ordering
#     assert updated_node['parent_id'] == root.id
#     children_ids = [c['id'] for c in await manager.get_children(root.id)]
#     assert children_ids[-1] == child1.id
