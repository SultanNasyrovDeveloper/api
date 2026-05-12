"""Tests for moving nodes as first child strategy.

Covers:
- Basic move to first child position
- Moving to empty parent
- Reordering within same parent
- Edge cases specific to first_child strategy
"""

from collections.abc import Callable

import pytest

from minager.node.enums import MovePosition
from minager.node.managers import PalaceNodeManager


@pytest.mark.asyncio
async def test_move_node_as_first_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to be the first child of a new parent.

    Setup:
    parent_a
    └── child_1

    parent_b
    ├── child_2
    └── child_3

    Action:
    Move child_1 from parent_a to parent_b as first child

    Expected:
    parent_b
    ├── child_1 (now first)
    ├── child_2
    └── child_3
    """
    # Arrange: Create initial parent with a child
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    child_1 = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create new parent with existing children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    child_2 = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    child_3 = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move child_1 to be first child of parent_b
    await test_palace_node_manager.move(child_1.pk, parent_b.pk, MovePosition.first_child)

    # Assert: Verify child_1 moved to parent_b
    moved_node = await test_palace_node_manager.get(child_1.pk)
    assert moved_node.parent_pk == parent_b.pk, 'Node should have new parent'

    # Assert: Verify child_1 is the first child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 3, 'Parent should have 3 children'
    assert children[0].pk == child_1.pk, 'Moved node should be first child'

    # Assert: Verify order is correct
    assert children[1].pk == child_2.pk, 'Second child should remain second'
    assert children[2].pk == child_3.pk, 'Third child should remain third'


@pytest.mark.asyncio
async def test_move_to_empty_parent_as_first_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to a parent that has no children (as first child).

    Setup:
    parent_a
    └── node_1

    parent_b (no children)

    Action:
    Move node_1 to parent_b as first child

    Expected:
    - node_1 becomes first and only child of parent_b
    - Order is calculated correctly from empty list
    """
    # Arrange: Create node with parent
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_1 = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create empty parent
    parent_b = await test_palace_node_manager.create(node_create_data_factory())

    # Act: Move to empty parent as first child
    await test_palace_node_manager.move(node_1.pk, parent_b.pk, MovePosition.first_child)

    # Assert: node_1 is now child of parent_b
    node_1_after = await test_palace_node_manager.get(node_1.pk)
    assert node_1_after.parent_pk == parent_b.pk, 'Node should have new parent'

    # Assert: parent_b has exactly one child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 1, 'Parent should have exactly one child'
    assert children[0].pk == node_1.pk, 'Node should be the only child'

    # Assert: parent_a has no children
    children_a = await test_palace_node_manager.get_children(parent_a.pk)
    assert len(children_a) == 0, 'Old parent should have no children'


@pytest.mark.asyncio
async def test_reorder_last_to_first_within_same_parent(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving last child to first position within the same parent.

    Setup:
    parent
    ├── A (first)
    ├── B
    └── C (last)

    Action:
    Move C to first position of same parent

    Expected:
    parent
    ├── C (now first)
    ├── A
    └── B
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move C to first position
    await test_palace_node_manager.move(node_c.pk, parent.pk, MovePosition.first_child)

    # Assert: All nodes still children of parent
    node_c_after = await test_palace_node_manager.get(node_c.pk)
    assert node_c_after.parent_pk == parent.pk, 'Node C should still be child of parent'

    # Assert: Order is now C, A, B
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_c.pk, 'C should be first'
    assert children[1].pk == node_a.pk, 'A should be second'
    assert children[2].pk == node_b.pk, 'B should be third'


@pytest.mark.asyncio
async def test_reorder_middle_to_first_within_same_parent(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a middle node to first position within the same parent.

    Setup:
    parent
    ├── A (first)
    ├── B (middle)
    └── C (last)

    Action:
    Move B to first position

    Expected:
    parent
    ├── B (now first)
    ├── A
    └── C
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move B to first position
    await test_palace_node_manager.move(node_b.pk, parent.pk, MovePosition.first_child)

    # Assert: Order is now B, A, C
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_b.pk, 'B should be first'
    assert children[1].pk == node_a.pk, 'A should be second'
    assert children[2].pk == node_c.pk, 'C should be third'


@pytest.mark.asyncio
async def test_move_already_first_child_is_noop(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to position it's already in (should complete without errors).

    Setup:
    parent
    ├── A (already first)
    ├── B
    └── C

    Action:
    Move A to first child of parent (same position)

    Expected:
    - Operation completes successfully
    - A remains first child
    - Order may be recalculated but relative position unchanged
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move A to first (where it already is)
    await test_palace_node_manager.move(node_a.pk, parent.pk, MovePosition.first_child)

    # Assert: A still child of parent
    node_a_after = await test_palace_node_manager.get(node_a.pk)
    assert node_a_after.parent_pk == parent.pk, 'A should still be child of parent'

    # Assert: A is still first
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_a.pk, 'A should still be first child'

    # Assert: Order sequence is preserved
    assert children[1].pk == node_b.pk, 'B should still be second'
    assert children[2].pk == node_c.pk, 'C should still be third'
