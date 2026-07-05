from fastapi import APIRouter, HTTPException, status

from minager.core.auth.dependencies import CurrentUserID
from minager.core.types import PaginatedResult

from . import dependencies, dto, models, schemas
from .services.content_generation import HuggingFaceNodeContentGenerator

router = APIRouter(prefix='/nodes')


@router.get('/')
async def search(
    user_id: CurrentUserID,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
    query: str = '',
    page: int = 1,
    size: int = 10,
) -> PaginatedResult[schemas.SearchNodeResultSchema]:
    found_nodes = await nodes.search(
        user_id=str(user_id),
        page=page,
        per_page=size,
        query=query,
    )
    return PaginatedResult(page=page, results=found_nodes)


@router.post('/{id_}/add-child', status_code=status.HTTP_201_CREATED)
async def add_child(
    id_: str,
    data: schemas.NodeCreateSchema,
    user_id: CurrentUserID,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> schemas.NodeDetailSchema:
    data_as_dict = data.model_dump()
    data_as_dict['owner_id'] = user_id
    new_node = await nodes.add_child(id_, data=data_as_dict)
    if not new_node:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not able to create child node')
    return new_node


@router.get('/{id_}')
async def get(
    id_: str,
    user_id: CurrentUserID,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> schemas.NodeDetailSchema:
    node = await nodes.get(id_)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # TODO: update only once per some period of time(~30 min). Can be abused
    if node.owner_id == user_id:
        node = await nodes.patch(node.id.id, {'owner_views': node.owner_views + 1})
    return node


@router.get('/{id_}/generate-content')
async def generate_content(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> str:
    node = await nodes.get(id_)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    generator = HuggingFaceNodeContentGenerator.from_config()
    return await generator.generate(node)


@router.get('/{id_}/children')
async def get_children(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
    page: int = 1,
):
    children = await nodes.get_children(id_)
    # TODO: Raise 404 if node whose children we trying to access not found
    return PaginatedResult(page=page, results=[child.model_dump() for child in children])


@router.get('/{id_}/statistics')
async def get_statistics(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> dto.NodeOverallStatistics:
    return await nodes.get_statistics(id_)


@router.get('/{id_}/subtree')
async def get_subtree(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> models.TreeNode:
    return await nodes.get_subtree(id_)


@router.get('/{id_}/subtree/statistics')
async def get_subtree_statistics(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> dto.NodeSubtreeStatistics:
    # TODO: Make proper schema for statistics response
    # TODO: Check if node exists raise 404 if not
    return await nodes.get_subtree_statistics(id_)


@router.get('/{id_}/subtree/ids')
async def get_subtree_ids(
    id_: str,
    limit: int,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> list[str]:
    return await nodes.get_subtree_ids(id_, limit=limit)


@router.post('/{id_}/move')
async def move_node(
    id_: str,
    move_config: schemas.NodeMoveConfiguration,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> schemas.UpdatedNodeSchema:
    updated = await nodes.move(id_, move_config.target_id, move_config.position)
    # TODO: Show proper exceptions. If was not able to find node show 404. Show 400 only as a fallback
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not able to update child node')
    return updated


@router.patch('/{id_}')
async def update(
    id_: str,
    update_data: schemas.NodeEditSchema,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> schemas.NodeDetailSchema:
    updated = await nodes.patch(id_, update_data.model_dump(exclude_unset=True))
    # TODO: Show proper exceptions. If was not able to find node show 404. Show 400 only as a fallback
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not able to update child node')
    return updated


@router.delete('/{id_}')
async def delete(
    id_: str,
    nodes: dependencies.KnowledgeTreeNodeManagerDependency,
) -> None:
    await nodes.delete(id_)
