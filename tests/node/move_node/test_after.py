"""Tests for moving nodes after a sibling (after strategy).

Covers:
- Basic move after a sibling
- Moving after last child (becomes new last)
- Moving after first child
- Reordering within same parent
- Edge cases specific to after strategy
"""

from collections.abc import Callable

import pytest

from minager.node.enums import MovePosition
from minager.node.managers import KnowledgeTreeNodeManager


@pytest.mark.asyncio
async def test_move_node_after_sibling(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node to position after a target sibling.

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A
    ├── B (target)
    └── C

    Action:
    Move node_x after B

    Expected:
    parent_b
    ├── A
    ├── B
    ├── node_x (inserted after B)
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

    # Act: Move node_x after node_b
    await test_palace_node_manager.move(node_x.pk, node_b.pk, MovePosition.after)

    # Assert: node_x moved to parent_b
    node_x_after = await test_palace_node_manager.get(node_x.pk)
    assert node_x_after.parent_pk == parent_b.pk, 'Node should have new parent'

    # Assert: Verify order is A, B, node_x, C
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_b.pk, 'B should be second'
    assert children[2].pk == node_x.pk, 'node_x should be third (after B)'
    assert children[3].pk == node_c.pk, 'C should be fourth'


@pytest.mark.asyncio
async def test_move_after_last_child(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node after the last child (should become new last child).

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A
    ├── B
    └── C (last child)

    Action:
    Move node_x after C

    Expected:
    parent_b
    ├── A
    ├── B
    ├── C
    └── node_x (new last)
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with children
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x after node_c (last child)
    await test_palace_node_manager.move(node_x.pk, node_c.pk, MovePosition.after)

    # Assert: node_x is now last child
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_b.pk, 'B should be second'
    assert children[2].pk == node_c.pk, 'C should be third'
    assert children[3].pk == node_x.pk, 'node_x should be fourth (last)'


@pytest.mark.asyncio
async def test_move_after_first_child(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node after the first child.

    Setup:
    parent_a
    └── node_x

    parent_b
    ├── A (first child)
    ├── B
    └── C

    Action:
    Move node_x after A

    Expected:
    parent_b
    ├── A
    ├── node_x (after A)
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

    # Act: Move node_x after node_a (first child)
    await test_palace_node_manager.move(node_x.pk, node_a.pk, MovePosition.after)

    # Assert: node_x is second child (after first)
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 4, 'Parent should have 4 children'
    assert children[0].pk == node_a.pk, 'A should be first'
    assert children[1].pk == node_x.pk, 'node_x should be second (after A)'
    assert children[2].pk == node_b.pk, 'B should be third'
    assert children[3].pk == node_c.pk, 'C should be fourth'


@pytest.mark.asyncio
async def test_reorder_within_same_parent_using_after(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node after another sibling within the same parent.

    Setup:
    parent
    ├── A
    ├── B
    ├── C
    └── D

    Action:
    Move A after C

    Expected:
    parent
    ├── B
    ├── C
    ├── A (moved after C)
    └── D
    """
    # Arrange: Create parent with 4 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_d = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move A after C
    await test_palace_node_manager.move(node_a.pk, node_c.pk, MovePosition.after)

    # Assert: Order is now B, C, A, D
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 4, 'Parent should still have 4 children'
    assert children[0].pk == node_b.pk, 'B should be first'
    assert children[1].pk == node_c.pk, 'C should be second'
    assert children[2].pk == node_a.pk, 'A should be third (after C)'
    assert children[3].pk == node_d.pk, 'D should be fourth'


@pytest.mark.asyncio
async def test_move_after_adjacent_sibling(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node after its immediately adjacent sibling (edge case).

    Setup:
    parent
    ├── A
    ├── B
    └── C

    Action:
    Move A after B (moving one position down)

    Expected:
    parent
    ├── B
    ├── A (moved after B)
    └── C
    """
    # Arrange: Create parent with 3 children
    parent = await test_palace_node_manager.create(node_create_data_factory())
    node_a = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_manager.add_child(parent.pk, node_create_data_factory())

    # Act: Move A after B (adjacent sibling)
    await test_palace_node_manager.move(node_a.pk, node_b.pk, MovePosition.after)

    # Assert: Order is now B, A, C
    children = await test_palace_node_manager.get_children(parent.pk)
    assert len(children) == 3, 'Parent should still have 3 children'
    assert children[0].pk == node_b.pk, 'B should be first'
    assert children[1].pk == node_a.pk, 'A should be second (after B)'
    assert children[2].pk == node_c.pk, 'C should be third'


@pytest.mark.asyncio
async def test_move_after_with_single_target_sibling(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_create_data_factory: Callable[..., dict],
):
    """
    Test moving a node after the only child of target parent.

    Setup:
    parent_a
    └── node_x

    parent_b
    └── node_y (only child)

    Action:
    Move node_x after node_y

    Expected:
    parent_b
    ├── node_y
    └── node_x (after node_y)
    """
    # Arrange: Create source node
    parent_a = await test_palace_node_manager.create(node_create_data_factory())
    node_x = await test_palace_node_manager.add_child(parent_a.pk, node_create_data_factory())

    # Arrange: Create target parent with single child
    parent_b = await test_palace_node_manager.create(node_create_data_factory())
    node_y = await test_palace_node_manager.add_child(parent_b.pk, node_create_data_factory())

    # Act: Move node_x after node_y
    await test_palace_node_manager.move(node_x.pk, node_y.pk, MovePosition.after)

    # Assert: node_y is first, node_x is second
    children = await test_palace_node_manager.get_children(parent_b.pk)
    assert len(children) == 2, 'Parent should have 2 children'
    assert children[0].pk == node_y.pk, 'node_y should be first'
    assert children[1].pk == node_x.pk, 'node_x should be second (after node_y)'
