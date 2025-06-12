from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from minager.core.api.dependencies import App, RequestDBUser, RequestUser

from . import schemas

user_router = APIRouter(prefix='/users')
auth_router = APIRouter()


@user_router.post('/')
async def create_user(app: App, data: schemas.UserCreateDataSchema) -> schemas.UserDetailSchema:
    manager = app.state.users
    async with manager:
        return await manager.add_user(data)


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
