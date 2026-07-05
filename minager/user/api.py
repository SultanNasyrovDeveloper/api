from fastapi import APIRouter, HTTPException, status

from minager.core.auth import dependencies as auth_dependencies
from minager.core.auth import exceptions as auth_exceptions
from minager.core.auth import schemas as auth_schemas

from . import dependencies, exceptions, schemas

auth_router = APIRouter(tags=['Authentication'])
users_router = APIRouter(prefix='/users', tags=['Users'])


@users_router.post(
    '/signup',
    response_model=schemas.UserDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    user_data: schemas.UserCreateDataSchema,
    sign_up: dependencies.SignUpUseCaseDependency,
) -> schemas.UserWithProfileSchema:
    try:
        user, profile = await sign_up.execute(user_data)
        return schemas.UserWithProfileSchema.build(user, profile)
    except exceptions.UserError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@auth_router.post('/token', response_model=auth_schemas.TokenPairSchema)
async def get_token(
    credentials: schemas.LoginCredentialsSchema,
    users: dependencies.UserServiceDependency,
    jwt_service: auth_dependencies.JWTServiceDependency,
) -> auth_schemas.TokenPairSchema:
    user = await users.authenticate(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    await users.update_last_login(user.id)
    return jwt_service.create_token_pair(user.id)


@auth_router.post('/refresh', response_model=auth_schemas.AccessTokenSchema)
async def refresh_token(
    request: auth_schemas.RefreshTokenRequestSchema,
    jwt_service: auth_dependencies.JWTServiceDependency,
) -> auth_schemas.AccessTokenSchema:
    try:
        return jwt_service.refresh_access_token(request.refresh_token)
    except auth_exceptions.AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={'WWW-Authenticate': 'Bearer'},
        ) from e


@users_router.get('/me', response_model=schemas.UserWithProfileSchema)
async def get_me(
    user: dependencies.CurrentUser,
    profile: dependencies.CurrentUserProfile,
) -> schemas.UserWithProfileSchema:
    return schemas.UserWithProfileSchema.build(user, profile)


@users_router.patch('/me', response_model=schemas.UserDetailSchema)
async def update_me(
    user: dependencies.CurrentUser,
    users: dependencies.UserServiceDependency,
    user_data: schemas.UserUpdateDataSchema,
) -> schemas.UserDetailSchema:
    try:
        updated_user = await users.update_user(user.id, user_data)
        return updated_user
    except exceptions.UserError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@users_router.get('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def get_my_profile(
    profile: dependencies.CurrentUserProfile,
) -> schemas.UserProfileDetailSchema:
    return profile


@users_router.patch('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def update_my_profile(
    user: dependencies.CurrentUser,
    user_profiles: dependencies.UserProfileServiceDependency,
    profile_data: schemas.UserProfileUpdateDataSchema,
) -> schemas.UserProfileDetailSchema:
    try:
        updated_profile = await user_profiles.update_profile(user.id, profile_data)
        return updated_profile
    except exceptions.ProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
