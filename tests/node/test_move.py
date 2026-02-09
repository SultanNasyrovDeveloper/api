"""
Tests for node move operations using SurrealDB.
"""

import pytest

from minager.node.enums import NodeRelationType


class TestMoveNode:
    """Test suite for moving nodes in the tree structure."""

    @pytest.mark.asyncio
    async def test_move_as_first_child(self, palace_node_db, node_factory):
        """Test moving a node to be the first child of a target parent."""
        # Arrange: Create tree structure
        #   parent
        #   ├── existing_child1 (order: 'aaa')
        #   └── existing_child2 (order: 'zzz')
        #   node_to_move (separate, order: 'mmm')

        parent = await node_factory(title='Parent')
        existing_child1 = await node_factory(parent_id=parent.id, title='Child 1', order='aaa')
        existing_child2 = await node_factory(parent_id=parent.id, title='Child 2', order='zzz')
        node_to_move = await node_factory(title='Node to Move', order='mmm')

        # Act: Move node as first child
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=parent.id,
            move_position=NodeRelationType.first_child.value,
        )

        # Assert
        assert result is not None
        assert result.id == node_to_move.id
        assert result.parent_id == parent.id

        # Verify order is before existing_child1
        assert result.order < existing_child1.order

        # Verify children list
        children = await palace_node_db.get_children(parent.id)
        child_ids = [c.id for c in children]
        assert node_to_move.id in child_ids
        assert len(children) == 3

    @pytest.mark.asyncio
    async def test_move_as_last_child(self, palace_node_db, node_factory):
        """Test moving a node to be the last child of a target parent."""
        # Arrange
        parent = await node_factory(title='Parent')
        existing_child1 = await node_factory(parent_id=parent.id, title='Child 1', order='aaa')
        existing_child2 = await node_factory(parent_id=parent.id, title='Child 2', order='mmm')
        node_to_move = await node_factory(title='Node to Move')

        # Act
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=parent.id,
            move_position=NodeRelationType.last_child.value,
        )

        # Assert
        assert result is not None
        assert result.parent_id == parent.id
        assert result.order > existing_child2.order

        children = await palace_node_db.get_children(parent.id)
        assert len(children) == 3
        # Last child should be node_to_move
        sorted_children = sorted(children, key=lambda c: c.order)
        assert sorted_children[-1].id == node_to_move.id

    @pytest.mark.asyncio
    async def test_move_before_sibling(self, palace_node_db, node_factory):
        """Test moving a node before an existing sibling."""
        # Arrange
        parent = await node_factory(title='Parent')
        child1 = await node_factory(parent_id=parent.id, title='Child 1', order='aaa')
        child2 = await node_factory(parent_id=parent.id, title='Child 2', order='mmm')
        child3 = await node_factory(parent_id=parent.id, title='Child 3', order='zzz')
        node_to_move = await node_factory(title='Node to Move')

        # Act: Move before child2
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=child2.id,
            move_position=NodeRelationType.before.value,
        )

        # Assert
        assert result is not None
        assert result.parent_id == parent.id
        # Order should be between child1 and child2
        assert child1.order < result.order < child2.order

        children = await palace_node_db.get_children(parent.id)
        sorted_children = sorted(children, key=lambda c: c.order)
        child_ids = [c.id for c in sorted_children]

        # Order should be: child1, node_to_move, child2, child3
        assert child_ids == [child1.id, node_to_move.id, child2.id, child3.id]

    @pytest.mark.asyncio
    async def test_move_after_sibling(self, palace_node_db, node_factory):
        """Test moving a node after an existing sibling."""
        # Arrange
        parent = await node_factory(title='Parent')
        child1 = await node_factory(parent_id=parent.id, title='Child 1', order='aaa')
        child2 = await node_factory(parent_id=parent.id, title='Child 2', order='mmm')
        child3 = await node_factory(parent_id=parent.id, title='Child 3', order='zzz')
        node_to_move = await node_factory(title='Node to Move')

        # Act: Move after child2
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=child2.id,
            move_position=NodeRelationType.after.value,
        )

        # Assert
        assert result is not None
        assert result.parent_id == parent.id
        # Order should be between child2 and child3
        assert child2.order < result.order < child3.order

        children = await palace_node_db.get_children(parent.id)
        sorted_children = sorted(children, key=lambda c: c.order)
        child_ids = [c.id for c in sorted_children]

        # Order should be: child1, child2, node_to_move, child3
        assert child_ids == [child1.id, child2.id, node_to_move.id, child3.id]

    @pytest.mark.asyncio
    async def test_move_with_children_preserves_subtree(self, palace_node_db, node_factory):
        """Test that moving a node preserves its subtree."""
        # Arrange: Create node with children
        old_parent = await node_factory(title='Old Parent')
        node_to_move = await node_factory(parent_id=old_parent.id, title='Node to Move')
        grandchild1 = await node_factory(parent_id=node_to_move.id, title='Grandchild 1')
        grandchild2 = await node_factory(parent_id=node_to_move.id, title='Grandchild 2')

        new_parent = await node_factory(title='New Parent')

        # Act: Move node with its children
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=new_parent.id,
            move_position=NodeRelationType.first_child.value,
        )

        # Assert: Node moved
        assert result.parent_id == new_parent.id

        # Assert: Children still belong to node_to_move
        children = await palace_node_db.get_children(node_to_move.id)
        child_ids = [c.id for c in children]
        assert grandchild1.id in child_ids
        assert grandchild2.id in child_ids
        assert len(children) == 2

    @pytest.mark.asyncio
    async def test_move_before_first_sibling(self, palace_node_db, node_factory):
        """Test moving a node before the first sibling."""
        # Arrange
        parent = await node_factory(title='Parent')
        first_child = await node_factory(parent_id=parent.id, title='First Child', order='aaa')
        node_to_move = await node_factory(title='Node to Move')

        # Act: Move before first child
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=first_child.id,
            move_position=NodeRelationType.before.value,
        )

        # Assert
        assert result is not None
        assert result.order < first_child.order

    @pytest.mark.asyncio
    async def test_move_after_last_sibling(self, palace_node_db, node_factory):
        """Test moving a node after the last sibling."""
        # Arrange
        parent = await node_factory(title='Parent')
        last_child = await node_factory(parent_id=parent.id, title='Last Child', order='zzz')
        node_to_move = await node_factory(title='Node to Move')

        # Act: Move after last child
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=last_child.id,
            move_position=NodeRelationType.after.value,
        )

        # Assert
        assert result is not None
        assert result.order > last_child.order

    @pytest.mark.asyncio
    async def test_move_updates_parent_reference(self, palace_node_db, node_factory):
        """Test that moving a node correctly updates parent reference."""
        # Arrange
        old_parent = await node_factory(title='Old Parent')
        new_parent = await node_factory(title='New Parent')
        node_to_move = await node_factory(parent_id=old_parent.id, title='Node to Move')

        # Act
        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id=new_parent.id,
            move_position=NodeRelationType.first_child.value,
        )

        # Assert: Node is child of new parent
        assert result.parent_id == new_parent.id

        # Assert: Node is not in old parent's children
        old_children = await palace_node_db.get_children(old_parent.id)
        old_child_ids = [c.id for c in old_children]
        assert node_to_move.id not in old_child_ids

        # Assert: Node is in new parent's children
        new_children = await palace_node_db.get_children(new_parent.id)
        new_child_ids = [c.id for c in new_children]
        assert node_to_move.id in new_child_ids


class TestMoveNodeEdgeCases:
    """Test edge cases and error conditions for move operations."""

    @pytest.mark.asyncio
    async def test_move_nonexistent_node(self, palace_node_db, node_factory):
        """Test moving a node that doesn't exist."""
        parent = await node_factory(title='Parent')

        result = await palace_node_db.move(
            node_id='nonexistent_id',
            target_id=parent.id,
            move_position=NodeRelationType.first_child.value,
        )

        # Should handle gracefully (return None or raise exception)
        # Adjust based on your actual implementation
        assert result is None or isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_move_to_nonexistent_target(self, palace_node_db, node_factory):
        """Test moving a node to a target that doesn't exist."""
        node_to_move = await node_factory(title='Node to Move')

        result = await palace_node_db.move(
            node_id=node_to_move.id,
            target_id='nonexistent_target',
            move_position=NodeRelationType.first_child.value,
        )

        # Should handle gracefully
        assert result is None or isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_move_with_invalid_position(self, palace_node_db, node_factory):
        """Test moving a node with an invalid position value."""
        parent = await node_factory(title='Parent')
        node_to_move = await node_factory(title='Node to Move')

        result = await palace_node_db.move(
            node_id=node_to_move.id, target_id=parent.id, move_position=999  # Invalid position
        )

        assert result is None
