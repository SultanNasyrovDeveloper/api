#
# @pytest.mark.asyncio
# async def test_move_node_as_first_child(test_palace_node_manager: PalaceNodeManager):
#     parent_node = await test_palace_node_manager.create(
#         NodeCreateSchema(title='Parent', questions='Parent node?', owner_id='user_1', content='{}').model_dump()
#     )
#     child_node = await test_palace_node_manager.create(
#         NodeCreateSchema(title='Child', questions='Child node?', owner_id='user_1', content='{}').model_dump()
#     )
#
#     await MoveNodeService(test_palace_node_manager).move(
#         node_id=child_node.pk,
#         target_id=parent_node.pk,
#         move_position=NodeRelationType.first_child.value,
#     )
#
#     updated_child = await test_palace_node_manager.get(child_node.pk)
#
#     assert updated_child is not None
#     assert updated_child.pk == child_node.pk
#     assert updated_child.parent_id.id == parent_node.pk
#     assert updated_child.order < parent_node.order  # first child should have lower order


# @pytest.mark.asyncio
# async def test_move_node_as_last_child(test_palace_node_manager: PalaceNodeManager):
#     parent_node = await test_palace_node_manager.create(
#         NodeCreateSchema(title="Parent", questions="Parent node?", owner_id="user_2", content="{}")
#     )
#     child_node = await test_palace_node_manager.create(
#         NodeCreateSchema(title="Child", questions="Child node?", owner_id="user_2", content="{}")
#     )
#
#     await MoveService(test_palace_node_manager).move(
#         node_id=child_node.pk,
#         target_id=parent_node.pk,
#         move_position=NodeRelationType.last_child.value
#     )
#
#     updated_child = await test_palace_node_manager.get(child_node.pk)
#
#     assert updated_child.parent_id.id == parent_node.pk
#     # You can add additional assertions for order consistency
#
#
# @pytest.mark.asyncio
# async def test_move_node_before_another(test_palace_node_manager: PalaceNodeManager):
#     node_a = await test_palace_node_manager.create(
#         NodeCreateSchema(title="A", questions="Node A?", owner_id="user_3", content="{}")
#     )
#     node_b = await test_palace_node_manager.create(
#         NodeCreateSchema(title="B", questions="Node B?", owner_id="user_3", content="{}")
#     )
#
#     await MoveService(test_palace_node_manager).move(
#         node_id=node_b.pk,
#         target_id=node_a.pk,
#         move_position=NodeRelationType.before.value
#     )
#
#     updated_b = await test_palace_node_manager.get(node_b.pk)
#
#     assert updated_b is not None
#     assert updated_b.parent_id.id == node_a.parent_id.id
#     assert updated_b.order < node_a.order
#
#
# @pytest.mark.asyncio
# async def test_move_node_after_another(test_palace_node_manager: PalaceNodeManager):
#     node_a = await test_palace_node_manager.create(
#         NodeCreateSchema(title="A", questions="Node A?", owner_id="user_4", content="{}")
#     )
#     node_b = await test_palace_node_manager.create(
#         NodeCreateSchema(title="B", questions="Node B?", owner_id="user_4", content="{}")
#     )
#
#     await MoveService(test_palace_node_manager).move(
#         node_id=node_b.pk,
#         target_id=node_a.pk,
#         move_position=NodeRelationType.after.value
#     )
#
#     updated_b = await test_palace_node_manager.get(node_b.pk)
#
#     assert updated_b is not None
#     assert updated_b.parent_id.id == node_a.parent_id.id
#     assert updated_b.order > node_a.order
