"""Tests for moving nodes as last child strategy.

Covers:
- Basic move to last child position
- Moving to empty parent
- Reordering within same parent
- Edge cases specific to last_child strategy
"""

from collections.abc import Callable

import pytest

from minager.node.enums import MovePosition
from minager.node.managers import KnowledgeTreeNodeManager


@pytest.mark.asyncio
async def test_move_node_as_last_child(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to be the last child of a new parent.

    Setup:
    - Create parent_a with child_1
    - Create parent_b with child_2 and child_3

    Action:
    - Move child_1 from parent_a to parent_b as last child

    Expected:
    - child_1 should now be a child of parent_b
    - child_1 should be the last child (after child_2 and child_3)
    - parent_b should have 3 children total
    """
    # Arrange: Create initial parent with a child
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    child_1 = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create new parent with existing children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    child_2 = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    child_3 = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move child_1 to be last child of parent_b
    await test_palace_node_manager.move(child_1.pk, parent_b.pk, MovePosition.last_child)

    # Assert: Verify child_1 moved to parent_b
    moved_node = await test_palace_node_manager.get(child_1.pk)
    assert moved_node.parent_pk == parent_b.pk, 'Node should have new parent'

    # Assert: Verify child_1 is the last child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 3, 'Parent should have 3 children'
    assert children[-1].pk == child_1.pk, 'Moved node should be last child'

    # Assert: Verify order is correct
    assert children[0].pk == child_2.pk, 'First child should remain first'
    assert children[1].pk == child_3.pk, 'Second child should remain second'


@pytest.mark.asyncio
async def test_move_to_empty_parent_as_last_child(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to a parent that has no children.

    Setup:
    parent_a
    └── node_1

    parent_b (no children)

    Action:
    Move node_1 to parent_b as last child

    Expected:
    - node_1 becomes first and only child of parent_b
    - Order is calculated correctly from empty list
    """
    # Arrange: Create node with parent
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_1 = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create empty parent
    parent_b = await test_palace_node_manager.create(node_create_data_factory())

    # Act: Move to empty parent
    await test_palace_node_manager.move(node_1.pk, parent_b.pk, MovePosition.last_child)

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
async def test_reorder_first_to_last_within_same_parent(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving first child to last position within the same parent.

    Setup:
    parent
    ├── A (first)
    ├── B
    └── C (last)

    Action:
    Move A to last position of same parent

    Expected:
    parent
    ├── B
    ├── C
    └── A (now last)
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move A to last position
    await test_palace_node_manager.move(node_a.pk, parent.pk, MovePosition.last_child)

    # Assert: All nodes still children of parent
    node_a_after = await test_palace_node_manager.get(node_a.pk)
    assert node_a_after.parent_pk == parent.pk, 'Node A should still be child of parent'

    # Assert: Order is now B, C, A
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_b.pk, 'B should be first'
    assert children[1].pk == node_c.pk, 'C should be second'
    assert children[2].pk == node_a.pk, 'A should be last'


@pytest.mark.asyncio
async def test_reorder_middle_to_last_within_same_parent(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a middle node to last position within the same parent.

    Setup:
    parent
    ├── A
    ├── B (middle)
    └── C (last)

    Action:
    Move B to last position

    Expected:
    parent
    ├── A
    ├── C
    └── B (now last)
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move B to last position
    await test_palace_node_manager.move(node_b.pk, parent.pk, MovePosition.last_child)

    # Assert: Order is now A, C, B
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_c.pk, 'C should be second'
    assert children[2].pk == node_b.pk, 'B should be last'


@pytest.mark.asyncio
async def test_move_already_last_child_is_noop(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to position it's already in (should complete without errors).

    Setup:
    parent
    ├── A
    ├── B
    └── C (already last)

    Action:
    Move C to last child of parent (same position)

    Expected:
    - Operation completes successfully
    - C remains last child
    - Order may be recalculated but relative position unchanged
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move C to last (where it already is)
    await test_palace_node_manager.move(node_c.pk, parent.pk, MovePosition.last_child)

    # Assert: C still child of parent
    node_c_after = await test_palace_node_manager.get(node_c.pk)
    assert node_c_after.parent_pk == parent.pk, 'C should still be child of parent'

    # Assert: C is still last
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[-1].pk == node_c.pk, 'C should still be last child'

    # Assert: Order sequence is preserved
    assert children[0].pk == node_a.pk, 'A should still be first'
    assert children[1].pk == node_b.pk, 'B should still be second'
