from fastapi import APIRouter

from minager.core.api.dependencies import App, RequestUser
from minager.core.api.response import PaginatedResponse

from . import schemas

router = APIRouter(prefix='/user-profiles')


@router.get('/')
async def list_(
    app: App, page: int = 1, per_page: int = 10
) -> PaginatedResponse[schemas.UserProfileSchema]:
    manager = app.state.user_profiles
    async with manager:
        profiles = await manager.list_(page=page, per_page=per_page)
    return PaginatedResponse(count=0, page=page, per_page=per_page, results=profiles)


@router.get('/my')
async def get_my_profile(user: RequestUser, app: App) -> schemas.UserProfileSchema:
    manager = app.state.user_profiles
    async with manager:
        profile = await manager.get(user['id'])
    return profile


@router.get('/{user_id}')
async def get_user_profile(user_id: str, app: App) -> schemas.UserProfileSchema:
    manager = app.state.user_profiles
    async with manager:
        profile = await manager.get(user_id)
    return profile


@router.patch('/{user_id}')
async def patch(
    user_id: str, app: App, data: schemas.UserProfileEditSchema
) -> schemas.UserProfileSchema:
    manager = app.state.user_profiles
    async with manager:
        updated = await manager.update(user_id, data.model_dump(mode='json'))
    return updated
