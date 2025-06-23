from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from minager.core.api.dependencies import App, RequestDBUser, RequestUser

from . import schemas

user_router = APIRouter(prefix='/users')
auth_router = APIRouter()


@user_router.post('/')
async def create_user(app: App, data: schemas.UserCreateDataSchema) -> schemas.UserDetailSchema:
    user_manager = app.state.users
    user_profile_manager = app.state.user_profiles
    palace_manager = app.state.nodes
    async with user_manager, user_profile_manager, palace_manager:
        user = await user_manager.add_user(data)
        node = await palace_manager.create(owner_id=str(user.id), title='Mind Palace')
        await user_profile_manager.create({'user_id': str(user.id), 'palace_root_id': node.id})
    return user


@user_router.get('/me')
async def get_current_user(user: RequestDBUser) -> schemas.UserDetailSchema:
    return user


@auth_router.post('/token')
async def get_token(app: App, data: OAuth2PasswordRequestForm = Depends()) -> schemas.Tokens:
    manager = app.state.users
    async with manager:
        user = await manager.authenticate(data)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return manager.make_user_tokens(user)


@auth_router.post('/refresh')
async def refresh_token(
    app: App, request_user: RequestUser, data: schemas.TokenRefreshDataSchema
) -> schemas.Tokens:
    if request_user:
        manager = app.state.users
        manager.validate_token(data.refresh)
        async with manager:
            db_user = manager.get(request_user.get('id'))
        return manager.make_user_tokens(db_user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
