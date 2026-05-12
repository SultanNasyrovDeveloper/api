"""Cross-strategy validation tests for move node functionality.

These tests verify validations that apply to ALL move strategies:
- Cycle detection (moving node to its own descendant)
- Self-reference prevention (moving node to itself)
- Non-existent node handling
- Authorization/ownership checks
"""

from collections.abc import Callable

import pytest

from minager.node.enums import MovePosition
from minager.node.managers import PalaceNodeManager


@pytest.mark.xfail(reason='Cycle detection not yet implemented')
@pytest.mark.asyncio
async def test_move_node_prevents_cycle_creation(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test that moving a node to one of its own descendants is prevented.

    Setup:
    A
    └── B
        └── C

    Action:
    Try to move A to C (making A a child of its own descendant)

    Expected:
    - Should raise an error or return error status
    - Tree structure should remain unchanged
    - No cycle should be created
    """
    # Arrange: Create tree A -> B -> C
    node_a = await test_palace_node_manager.create(node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(node_a.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(node_b.pk, node_create_data_factory())

    # Act & Assert: Try to move A to C (its grandchild)
    # TODO: Define expected error type - ValueError, or custom CycleDetectedError?
    with pytest.raises(Exception):  # Replace with specific exception when implemented
        await test_palace_node_manager.move(node_a.pk, node_c.pk, MovePosition.last_child)

    # Assert: Verify tree structure unchanged
    node_a_after = await test_palace_node_manager.get(node_a.pk)
    node_b_after = await test_palace_node_manager.get(node_b.pk)
    node_c_after = await test_palace_node_manager.get(node_c.pk)

    assert node_a_after.parent_pk is None, 'A should still have no parent'
    assert node_b_after.parent_pk == node_a.pk, 'B should still be child of A'
    assert node_c_after.parent_pk == node_b.pk, 'C should still be child of B'


@pytest.mark.xfail(reason='Self-reference check not yet implemented')
@pytest.mark.asyncio
async def test_move_node_prevents_self_reference(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test that moving a node to itself as a child is prevented.

    Setup:
    A (standalone node)

    Action:
    Try to move A to A (making it its own child)

    Expected:
    - Should raise an error
    - Node A should remain unchanged
    """
    # Arrange: Create standalone node
    node_a = await test_palace_node_manager.create(node_create_data_factory())

    # Act & Assert: Try to move A to itself
    with pytest.raises(Exception):  # Replace with specific exception when implemented
        await test_palace_node_manager.move(node_a.pk, node_a.pk, MovePosition.last_child)

    # Assert: Verify node unchanged
    node_a_after = await test_palace_node_manager.get(node_a.pk)
    assert node_a_after.parent_pk is None, 'A should still have no parent'


@pytest.mark.xfail(reason='Error handling for non-existent nodes not yet implemented')
@pytest.mark.asyncio
async def test_move_nonexistent_node_fails(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test that moving a non-existent node returns appropriate error.

    Action:
    Try to move node with invalid ID

    Expected:
    - Should return None or raise NotFoundError
    - No database changes
    """
    # Arrange: Create valid parent
    parent = await test_palace_node_manager.create(node_create_data_factory())

    # Act: Try to move non-existent node
    result = await test_palace_node_manager.move('nonexistent_id', parent.pk, MovePosition.last_child)

    # Assert: Should return None or raise error
    assert result is None, 'Moving non-existent node should return None'

    # Assert: Parent should have no children
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 0, 'Parent should have no children'


@pytest.mark.xfail(reason='Error handling for non-existent parent not yet implemented')
@pytest.mark.asyncio
async def test_move_to_nonexistent_parent_fails(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test that moving a node to non-existent parent returns appropriate error.

    Action:
    Try to move valid node to invalid parent ID

    Expected:
    - Should return None or raise NotFoundError
    - Node should remain in original position
    """
    # Arrange: Create node with parent
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Act: Try to move to non-existent parent
    result = await test_palace_node_manager.move(node.pk, 'nonexistent_parent_id', MovePosition.last_child)

    # Assert: Should return None
    assert result is None, 'Moving to non-existent parent should return None'

    # Assert: Node should still be child of parent_a
    node_after = await test_palace_node_manager.get(node.pk)
    assert node_after.parent_pk == parent_a.pk, 'Node should remain with original parent'


@pytest.mark.asyncio
async def test_move_node_with_subtree(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test that moving a node also moves all its children (entire subtree).

    Setup:
    parent_a
    └── B
        ├── C
        └── D

    parent_x (separate tree)

    Action:
    Move B to parent_x

    Expected:
    parent_x
    └── B
        ├── C
        └── D

    (All descendants move together)
    """
    # Arrange: Create tree with parent_a -> B -> {C, D}
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(node_b.pk, node_create_data_factory())
    node_d = await test_palace_node_manager.add_child(node_b.pk, node_create_data_factory())

    # Arrange: Create separate parent
    parent_x = await test_palace_node_manager.create(node_create_data_factory())

    # Act: Move B (with its children) to parent_x
    await test_palace_node_manager.move(node_b.pk, parent_x.pk, MovePosition.last_child)

    # Assert: B is now child of parent_x
    node_b_after = await test_palace_node_manager.get(node_b.pk)
    assert node_b_after.parent_pk == parent_x.pk, 'B should be child of parent_x'

    # Assert: C and D are still children of B
    node_c_after = await test_palace_node_manager.get(node_c.pk)
    node_d_after = await test_palace_node_manager.get(node_d.pk)
    assert node_c_after.parent_pk == node_b.pk, 'C should still be child of B'
    assert node_d_after.parent_pk == node_b.pk, 'D should still be child of B'

    # Assert: Verify subtree structure
    children_of_b = await test_palace_node_manager.get_children(node_b.pk)
    assert len(children_of_b) == 2, 'B should still have 2 children'
    child_pks = {child.pk for child in children_of_b}
    assert node_c.pk in child_pks, 'C should be in children'
    assert node_d.pk in child_pks, 'D should be in children'
