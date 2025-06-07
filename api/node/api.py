from fastapi import APIRouter, HTTPException, status

from api.core.api.dependencies import App, RequestUser
from api.core.types import PaginatedResult

from . import schemas

router = APIRouter(prefix='/nodes')


@router.get('/my-palace-root')
async def get_my_palace_root(user: RequestUser, app: App) -> str | None:
    node_id = await app.state.palace_node.get_my_palace_root(user['sub'])
    if not node_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return node_id


@router.post('/{uid}/add-child', status_code=status.HTTP_201_CREATED)
async def add_child(
    uid: str,
    data: schemas.NodeCreateSchema,
    user: RequestUser,
    app: App,
) -> schemas.NodeDetailSchema:
    data.owner_id = user.get('sub')
    return await app.state.palace_node.create_child(parent_uid=uid, data=data)


@router.get('/search')
async def search(
    user: RequestUser,
    app: App,
    page: int,
    per_page: int,
    query: str,
) -> PaginatedResult[schemas.NodeListItemSchema]:
    nodes = await app.state.palace_node.search(
        user_id=user.get('sub'),
        page=page,
        per_page=per_page,
        query=query,
    )
    return PaginatedResult(page=page, results=nodes)


@router.get('/{uid}')
async def get(uid: str, app: App) -> schemas.NodeDetailSchema:
    node = await app.state.palace_node.get(uid)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return node


@router.get('/{uid}/subtree-ids')
async def get_subtree_ids(uid: str, app: App, limit: int = 50) -> list[str]:
    return await app.state.palace_node.get_subtree_ids(uid, limit=limit)


@router.get('/{uid}/subtree')
async def subtree(uid: str, app: App) -> schemas.TreeNodeItemSchema:
    return await app.state.palace_node.get_subtree(uid)


@router.post('/{uid}/move')
async def move_node(
    uid: str, app: App, move_config: schemas.NodeMoveConfiguration
) -> schemas.UpdatedNodeSchema:
    return await app.state.palace_node.move(uid, move_config.target_id, move_config.position)


@router.patch('/{uid}')
async def update(
    uid: str, app: App, update_data: schemas.NodeEditSchema
) -> schemas.NodeDetailSchema:
    return await app.state.palace_node.patch(uid, update_data)


@router.delete('/{uid}')
async def delete(uid: str, app: App) -> None:
    await app.state.palace_node.delete(uid)
