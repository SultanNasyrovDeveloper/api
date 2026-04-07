from fastapi import APIRouter, HTTPException, status

from minager.core.api.dependencies import App
from minager.core.types import PaginatedResult
from minager.dependencies import RequestUser

from . import dto, schemas
from .services.content_generation import HuggingFaceNodeContentGenerator

router = APIRouter(prefix='/nodes')


@router.get('/')
async def list_(
    user: RequestUser,
    app: App,
    page: int,
    size: int,
    query: str,
) -> PaginatedResult[schemas.NodeListItemSchema]:
    nodes = await app.state.nodes.list_(
        user_id=user.get('id'),
        page=page,
        per_page=size,
        query=query,
    )
    return PaginatedResult(page=page, results=nodes)


@router.post('/{id_}/add-child', status_code=status.HTTP_201_CREATED)
async def add_child(
    id_: str,
    data: schemas.NodeCreateSchema,
    user: RequestUser,
    app: App,
) -> schemas.NodeDetailSchema:
    data.owner_id = user.sub
    return await app.state.nodes.add_child(id_, data=data.model_dump())


@router.get('/{id_}')
async def get(id_: str, app: App, user: RequestUser) -> schemas.NodeDetailSchema:
    node = await app.state.nodes.get(id_)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if node.owner_id == str(user.sub):
        node = await app.state.nodes.patch(node.id.id, {'owner_views': node.owner_views + 1})
    return node


@router.get('/{uid}/generate-content')
async def generate_content(uid: str, app: App) -> str:
    node = await app.state.nodes.get(uid)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    generator = HuggingFaceNodeContentGenerator.from_config()
    return await generator.generate(node)


@router.get('/{uid}/children')
async def get_children(uid: str, app: App, page: int = 1, size: int = 30):
    children = await app.state.nodes.get_children(uid)
    return PaginatedResult(page=page, results=[child.model_dump() for child in children])


@router.get('/{uid}/statistics')
async def get_statistics(uid: str, app: App) -> dto.NodeOverallStatistics:
    return await app.state.nodes.get_statistics(uid)


@router.get('/{uid}/subtree')
async def get_subtree(uid: str, app: App) -> schemas.TreeNodeItemSchema:
    return await app.state.nodes.get_subtree(uid)


@router.get('/{uid}/subtree/statistics')
async def get_subtree_statistics(uid: str, app: App) -> dto.NodeSubtreeStatistics:
    return await app.state.nodes.get_subtree_statistics(uid)


@router.get('/{uid}/subtree/ids')
async def get_subtree_ids(uid: str, app: App, limit: int = 50) -> list[str]:
    return await app.state.nodes.get_subtree_ids(uid, limit=limit)


@router.post('/{uid}/move')
async def move_node(
    uid: str, app: App, move_config: schemas.NodeMoveConfiguration
) -> schemas.UpdatedNodeSchema:
    return await app.state.nodes.move(uid, move_config.target_id, move_config.position)


@router.patch('/{uid}')
async def update(
    uid: str, app: App, update_data: schemas.NodeEditSchema
) -> schemas.NodeDetailSchema:
    response = await app.state.nodes.patch(uid, update_data.model_dump(exclude_unset=True))
    return response


@router.delete('/{uid}')
async def delete(uid: str, app: App) -> None:
    await app.state.nodes.delete(uid)
