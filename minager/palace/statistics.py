from fastapi import APIRouter

from minager.core.api.dependencies import App, RequestUser
from minager.node import schemas

router = APIRouter(prefix='/statistics')


@router.get('/overall')
async def get(app: App, user: RequestUser) -> schemas.PalaceStatistics:
    return await app.state.palace_node.get_overall_statistics(owner_id=user['sub'])
