from fastapi import APIRouter, HTTPException, status

from minager.core.auth.dependencies import CurrentUserID
from minager.core.types import PaginatedResult

from . import dependencies, dto, exceptions, models, schemas

router = APIRouter(prefix='/nodes')


@router.get('/')
async def search(
    user_id: CurrentUserID,
    nodes: dependencies.NodeRepositoryDependency,
    query: str = '',
    page: int = 1,
    size: int = 10,
) -> PaginatedResult[schemas.SearchNodeResultSchema]:
    found_nodes = await nodes.search(query=query, owner_id=str(user_id), page=page, size=size)
    return PaginatedResult(page=page, results=found_nodes)


@router.post('/{id_}/add-child', status_code=status.HTTP_201_CREATED, response_model=schemas.NodeDetailSchema)
async def add_child(
    id_: str,
    data: schemas.NodeCreateSchema,
    user_id: CurrentUserID,
    nodes: dependencies.NodeServiceDependency,
):
    validated_data = data.model_dump()
    validated_data['owner_id'] = str(user_id)
    try:
        new_node = await nodes.add_child(id_, data=validated_data)
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e
    if not new_node:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not able to create child node')
    return new_node


@router.get('/{id_}', response_model=schemas.NodeDetailSchema)
async def get(
    id_: str,
    user_id: CurrentUserID,
    nodes: dependencies.NodeServiceDependency,
):
    try:
        node = await nodes.get(id_, viewer_id=str(user_id))
        return node
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.get('/{id_}/generate-content')
async def generate_content(
    id_: str,
    generate_content_use_case: dependencies.GenerateNodeContentUseCaseDependency,
) -> str:
    try:
        return await generate_content_use_case.execute(id_)
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.get('/{id_}/children', response_model=PaginatedResult[models.ListNode])
async def get_children(
    id_: str,
    nodes: dependencies.NodeRepositoryDependency,
    page: int = 1,
):
    children = await nodes.get_children(id_)
    # TODO: Raise 404 if node whose children we trying to access not found
    return PaginatedResult(page=page, results=children)


@router.get('/{id_}/statistics')
async def get_statistics(
    id_: str,
    nodes: dependencies.NodeServiceDependency,
) -> dto.NodeOverallStatistics:
    try:
        return await nodes.get_statistics(id_)
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.get('/{id_}/subtree')
async def get_subtree(id_: str, nodes: dependencies.NodeServiceDependency) -> models.TreeNode:
    return await nodes.get_subtree(id_)


@router.get('/{id_}/subtree/statistics')
async def get_subtree_statistics(
    id_: str,
    nodes: dependencies.NodeRepositoryDependency,
) -> dto.NodeSubtreeStatistics:
    # TODO: Make proper schema for statistics response
    # TODO: Check if node exists raise 404 if not
    try:
        return await nodes.get_subtree_statistics(id_)
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.get('/{id_}/subtree/ids')
async def get_subtree_ids(
    id_: str,
    limit: int,
    nodes: dependencies.NodeRepositoryDependency,
) -> list[str]:
    return await nodes.get_subtree_ids([id_], limit=limit)


@router.post('/{id_}/move')
async def move_node(
    id_: str,
    move_config: schemas.NodeMoveConfiguration,
    move_node_use_case: dependencies.MoveNodeUseCaseDependency,
) -> schemas.UpdatedNodeSchema:
    updated = await move_node_use_case.execute(id_, move_config.target_id, move_config.position)
    # TODO: Show proper exceptions. If was not able to find node show 404. Show 400 only as a fallback
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not able to update child node')
    return updated


@router.patch('/{id_}', response_model=schemas.NodeDetailSchema)
async def update(
    id_: str,
    update_data: schemas.NodeEditSchema,
    nodes: dependencies.NodeServiceDependency,
):
    try:
        return await nodes.update(id_, update_data.model_dump(exclude_unset=True))
    except exceptions.NodeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.delete('/{id_}')
async def delete(
    id_: str,
    nodes: dependencies.NodeRepositoryDependency,
) -> None:
    await nodes.delete(id_)
