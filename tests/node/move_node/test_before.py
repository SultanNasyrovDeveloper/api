"""Tests for moving nodes before a sibling (before strategy).

Covers:
- Basic move before a sibling
- Moving before first child (becomes new first)
- Moving before last child
- Reordering within same parent
- Edge cases specific to before strategy
"""

from collections.abc import Callable

import pytest

from minager.node.enums import MovePosition
from minager.node.managers import PalaceNodeManager


@pytest.mark.asyncio
async def test_move_node_before_sibling(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to position before a target sibling.

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A
    ├── B (target)
    └── C

    Action:
    Move node_x before B

    Expected:
    parent_b
    ├── A
    ├── node_x (inserted before B)
    ├── B
    └── C
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x before node_b
    await test_palace_node_manager.move(node_x.pk, node_b.pk, MovePosition.before)

    # Assert: node_x moved to parent_b
    node_x_after = await test_palace_node_manager.get(node_x.pk)
    assert node_x_after.parent_pk == parent_b.pk, 'Node should have new parent'

    # Assert: Verify order is A, node_x, B, C
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_x.pk, 'node_x should be second (before B)'
    assert children[2].pk == node_b.pk, 'B should be third'
    assert children[3].pk == node_c.pk, 'C should be fourth'


@pytest.mark.asyncio
async def test_move_before_first_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node before the first child (should become new first child).

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A (first child)
    ├── B
    └── C

    Action:
    Move node_x before A

    Expected:
    parent_b
    ├── node_x (new first)
    ├── A
    ├── B
    └── C
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x before node_a (first child)
    await test_palace_node_manager.move(node_x.pk, node_a.pk, MovePosition.before)

    # Assert: node_x is now first child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_x.pk, 'node_x should be first'
    assert children[1].pk == node_a.pk, 'A should be second'
    assert children[2].pk == node_b.pk, 'B should be third'
    assert children[3].pk == node_c.pk, 'C should be fourth'


@pytest.mark.asyncio
async def test_move_before_last_child(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node before the last child.

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A
    ├── B
    └── C (last child)

    Action:
    Move node_x before C

    Expected:
    parent_b
    ├── A
    ├── B
    ├── node_x (before C)
    └── C
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x before node_c (last child)
    await test_palace_node_manager.move(node_x.pk, node_c.pk, MovePosition.before)

    # Assert: node_x is before last child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_b.pk, 'B should be second'
    assert children[2].pk == node_x.pk, 'node_x should be third (before C)'
    assert children[3].pk == node_c.pk, 'C should be fourth (last)'


@pytest.mark.asyncio
async def test_reorder_within_same_parent_using_before(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node before another sibling within the same parent.

    Setup:
    parent
    ├── A
    ├── B
    ├── C
    └── D

    Action:
    Move D before B

    Expected:
    parent
    ├── A
    ├── D (moved before B)
    ├── B
    └── C
    """
    # Arrange: Create parent with 4 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_d = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move D before B
    await test_palace_node_manager.move(node_d.pk, node_b.pk, MovePosition.before)

    # Assert: Order is now A, D, B, C
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 4, 'Parent should still have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_d.pk, 'D should be second (before B)'
    assert children[2].pk == node_b.pk, 'B should be third'
    assert children[3].pk == node_c.pk, 'C should be fourth'


@pytest.mark.asyncio
async def test_move_before_adjacent_sibling(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node before its immediately adjacent sibling (edge case).

    Setup:
    parent
    ├── A
    ├── B
    └── C

    Action:
    Move C before B (moving one position up)

    Expected:
    parent
    ├── A
    ├── C (moved before B)
    └── B
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move C before B (adjacent sibling)
    await test_palace_node_manager.move(node_c.pk, node_b.pk, MovePosition.before)

    # Assert: Order is now A, C, B
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_c.pk, 'C should be second (before B)'
    assert children[2].pk == node_b.pk, 'B should be third'


@pytest.mark.asyncio
async def test_move_before_with_single_target_sibling(
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node before the only child of target parent.

    Setup:
    parent_a
    └── node_x

    parent_b
    └── node_y (only child)

    Action:
    Move node_x before node_y

    Expected:
    parent_b
    ├── node_x (before node_y)
    └── node_y
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with single child
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_y = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x before node_y
    await test_palace_node_manager.move(node_x.pk, node_y.pk, MovePosition.before)

    # Assert: node_x is first, node_y is second
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 2, 'Parent should have 2 children'
    assert children[0].pk == node_x.pk, 'node_x should be first'
    assert children[1].pk == node_y.pk, 'node_y should be second'
