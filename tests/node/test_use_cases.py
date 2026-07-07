from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

from minager.node.enums import MovePosition
from minager.node.exceptions import NodeNotFoundError
from minager.node.models import Node
from minager.node.repositories import NodeRepository
from minager.node.services import NodeService
from minager.node.use_cases import GenerateNodeContentUseCase, MoveNodeUseCase


@pytest.mark.asyncio
async def test_generate_content_raises_not_found_for_missing_node(
    test_generate_node_content_use_case: GenerateNodeContentUseCase,
):
    with pytest.raises(NodeNotFoundError):
        await test_generate_node_content_use_case.execute('nonexistent_id')


@pytest.mark.asyncio
@patch('minager.node.use_cases.content_generation.HuggingFaceNodeContentGenerator.from_config')
async def test_generate_content_calls_huggingface(
    mock_from_config,
    test_generate_node_content_use_case: GenerateNodeContentUseCase,
    test_user_root_node: Node,
):
    mock_generator = AsyncMock()
    mock_generator.generate.return_value = '<p>Generated content</p>'
    mock_from_config.return_value = mock_generator

    content = await test_generate_node_content_use_case.execute(test_user_root_node.pk)

    assert content == '<p>Generated content</p>'
    mock_generator.generate.assert_called_once()


@pytest.mark.asyncio
async def test_move_node_as_first_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    child_1 = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    child_2 = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    child_3 = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(child_1.pk, parent_b.pk, MovePosition.first_child)

    moved_node = await test_palace_node_repository.get(child_1.pk)
    assert moved_node.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 3
    assert children[0].pk == child_1.pk
    assert children[1].pk == child_2.pk
    assert children[2].pk == child_3.pk


@pytest.mark.asyncio
async def test_move_to_empty_parent_as_first_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_1 = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())

    await test_move_node_use_case.execute(node_1.pk, parent_b.pk, MovePosition.first_child)

    node_1_after = await test_palace_node_repository.get(node_1.pk)
    assert node_1_after.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 1
    assert children[0].pk == node_1.pk

    children_a = await test_palace_node_repository.get_children(parent_a.pk)
    assert len(children_a) == 0


@pytest.mark.asyncio
async def test_reorder_last_to_first_within_same_parent(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_c.pk, parent.pk, MovePosition.first_child)

    node_c_after = await test_palace_node_repository.get(node_c.pk)
    assert node_c_after.parent_pk == parent.pk

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_c.pk
    assert children[1].pk == node_a.pk
    assert children[2].pk == node_b.pk


@pytest.mark.asyncio
async def test_reorder_middle_to_first_within_same_parent(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_b.pk, parent.pk, MovePosition.first_child)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_b.pk
    assert children[1].pk == node_a.pk
    assert children[2].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_already_first_child_is_noop(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_a.pk, parent.pk, MovePosition.first_child)

    node_a_after = await test_palace_node_repository.get(node_a.pk)
    assert node_a_after.parent_pk == parent.pk

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_b.pk
    assert children[2].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_node_as_last_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    child_1 = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    child_2 = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    child_3 = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(child_1.pk, parent_b.pk, MovePosition.last_child)

    moved_node = await test_palace_node_repository.get(child_1.pk)
    assert moved_node.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 3
    assert children[-1].pk == child_1.pk
    assert children[0].pk == child_2.pk
    assert children[1].pk == child_3.pk


@pytest.mark.asyncio
async def test_move_to_empty_parent_as_last_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_1 = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())

    await test_move_node_use_case.execute(node_1.pk, parent_b.pk, MovePosition.last_child)

    node_1_after = await test_palace_node_repository.get(node_1.pk)
    assert node_1_after.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 1
    assert children[0].pk == node_1.pk

    children_a = await test_palace_node_repository.get_children(parent_a.pk)
    assert len(children_a) == 0


@pytest.mark.asyncio
async def test_reorder_first_to_last_within_same_parent(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_a.pk, parent.pk, MovePosition.last_child)

    node_a_after = await test_palace_node_repository.get(node_a.pk)
    assert node_a_after.parent_pk == parent.pk

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_b.pk
    assert children[1].pk == node_c.pk
    assert children[2].pk == node_a.pk


@pytest.mark.asyncio
async def test_reorder_middle_to_last_within_same_parent(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_b.pk, parent.pk, MovePosition.last_child)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_c.pk
    assert children[2].pk == node_b.pk


@pytest.mark.asyncio
async def test_move_already_last_child_is_noop(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_c.pk, parent.pk, MovePosition.last_child)

    node_c_after = await test_palace_node_repository.get(node_c.pk)
    assert node_c_after.parent_pk == parent.pk

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[-1].pk == node_c.pk
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_b.pk


@pytest.mark.asyncio
async def test_move_node_before_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_b.pk, MovePosition.before)

    node_x_after = await test_palace_node_repository.get(node_x.pk)
    assert node_x_after.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_x.pk
    assert children[2].pk == node_b.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_before_first_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_a.pk, MovePosition.before)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_x.pk
    assert children[1].pk == node_a.pk
    assert children[2].pk == node_b.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_before_last_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_c.pk, MovePosition.before)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_b.pk
    assert children[2].pk == node_x.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_reorder_within_same_parent_using_before(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_d = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_d.pk, node_b.pk, MovePosition.before)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_d.pk
    assert children[2].pk == node_b.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_before_adjacent_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_c.pk, node_b.pk, MovePosition.before)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_c.pk
    assert children[2].pk == node_b.pk


@pytest.mark.asyncio
async def test_move_before_with_single_target_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_y = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_y.pk, MovePosition.before)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 2
    assert children[0].pk == node_x.pk
    assert children[1].pk == node_y.pk


@pytest.mark.asyncio
async def test_move_node_after_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_b.pk, MovePosition.after)

    node_x_after = await test_palace_node_repository.get(node_x.pk)
    assert node_x_after.parent_pk == parent_b.pk

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_b.pk
    assert children[2].pk == node_x.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_after_last_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_c.pk, MovePosition.after)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_b.pk
    assert children[2].pk == node_c.pk
    assert children[3].pk == node_x.pk


@pytest.mark.asyncio
async def test_move_after_first_child(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_a.pk, MovePosition.after)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 4
    assert children[0].pk == node_a.pk
    assert children[1].pk == node_x.pk
    assert children[2].pk == node_b.pk
    assert children[3].pk == node_c.pk


@pytest.mark.asyncio
async def test_reorder_within_same_parent_using_after(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_d = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_a.pk, node_c.pk, MovePosition.after)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 4
    assert children[0].pk == node_b.pk
    assert children[1].pk == node_c.pk
    assert children[2].pk == node_a.pk
    assert children[3].pk == node_d.pk


@pytest.mark.asyncio
async def test_move_after_adjacent_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())
    node_a = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(parent.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_a.pk, node_b.pk, MovePosition.after)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 3
    assert children[0].pk == node_b.pk
    assert children[1].pk == node_a.pk
    assert children[2].pk == node_c.pk


@pytest.mark.asyncio
async def test_move_after_with_single_target_sibling(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_x = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    parent_b = await test_palace_node_repository.create(node_create_data_factory())
    node_y = await test_palace_node_service.add_child(parent_b.pk, node_create_data_factory())

    await test_move_node_use_case.execute(node_x.pk, node_y.pk, MovePosition.after)

    children = await test_palace_node_repository.get_children(parent_b.pk)
    assert len(children) == 2
    assert children[0].pk == node_y.pk
    assert children[1].pk == node_x.pk


@pytest.mark.asyncio
async def test_move_node_prevents_cycle_creation(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    node_a = await test_palace_node_repository.create(node_create_data_factory())
    node_b = await test_palace_node_service.add_child(node_a.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(node_b.pk, node_create_data_factory())

    with pytest.raises(ValueError):
        await test_move_node_use_case.execute(node_a.pk, node_c.pk, MovePosition.last_child)

    node_a_after = await test_palace_node_repository.get(node_a.pk)
    node_b_after = await test_palace_node_repository.get(node_b.pk)
    node_c_after = await test_palace_node_repository.get(node_c.pk)

    assert node_a_after.parent_pk is None
    assert node_b_after.parent_pk == node_a.pk
    assert node_c_after.parent_pk == node_b.pk


@pytest.mark.asyncio
async def test_move_node_prevents_self_reference(
    test_palace_node_repository: NodeRepository,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    node_a = await test_palace_node_repository.create(node_create_data_factory())

    with pytest.raises(ValueError, match='Cannot move node to itself'):
        await test_move_node_use_case.execute(node_a.pk, node_a.pk, MovePosition.last_child)

    node_a_after = await test_palace_node_repository.get(node_a.pk)
    assert node_a_after.parent_id is None


@pytest.mark.asyncio
async def test_move_nonexistent_node_fails(
    test_palace_node_repository: NodeRepository,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent = await test_palace_node_repository.create(node_create_data_factory())

    with pytest.raises(ValueError, match='Source node not found'):
        await test_move_node_use_case.execute('nonexistent_id', parent.pk, MovePosition.last_child)

    children = await test_palace_node_repository.get_children(parent.pk)
    assert len(children) == 0


@pytest.mark.asyncio
async def test_move_to_nonexistent_parent_fails(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())

    with pytest.raises(ValueError, match='Target node not found'):
        await test_move_node_use_case.execute(node.pk, 'nonexistent_parent_id', MovePosition.last_child)

    node_after = await test_palace_node_repository.get(node.pk)
    assert node_after.parent_pk == parent_a.pk


@pytest.mark.asyncio
async def test_move_node_with_subtree(
    test_palace_node_repository: NodeRepository,
    test_palace_node_service: NodeService,
    test_move_node_use_case: MoveNodeUseCase,
    node_create_data_factory: Callable[..., dict],
):
    parent_a = await test_palace_node_repository.create(node_create_data_factory())
    node_b = await test_palace_node_service.add_child(parent_a.pk, node_create_data_factory())
    node_c = await test_palace_node_service.add_child(node_b.pk, node_create_data_factory())
    node_d = await test_palace_node_service.add_child(node_b.pk, node_create_data_factory())

    parent_x = await test_palace_node_repository.create(node_create_data_factory())

    await test_move_node_use_case.execute(node_b.pk, parent_x.pk, MovePosition.last_child)

    node_b_after = await test_palace_node_repository.get(node_b.pk)
    assert node_b_after.parent_pk == parent_x.pk

    node_c_after = await test_palace_node_repository.get(node_c.pk)
    node_d_after = await test_palace_node_repository.get(node_d.pk)
    assert node_c_after.parent_pk == node_b.pk
    assert node_d_after.parent_pk == node_b.pk

    children_of_b = await test_palace_node_repository.get_children(node_b.pk)
    assert len(children_of_b) == 2
    child_pks = {child.pk for child in children_of_b}
    assert node_c.pk in child_pks
    assert node_d.pk in child_pks
