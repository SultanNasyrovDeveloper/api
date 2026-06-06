from fastapi import APIRouter, HTTPException, status

from . import dependencies, jwt, managers, models, schemas, services

auth_router = APIRouter(tags=['Authentication'])
users_router = APIRouter(prefix='/users', tags=['Users'])


@users_router.post(
    '/signup',
    response_model=schemas.UserDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def signup(user_data: schemas.UserCreateDataSchema) -> models.User:
    return await services.UserSignupService().signup(user_data)


@auth_router.post('/token', response_model=schemas.TokenPairSchema)
async def get_token(credentials: schemas.LoginCredentialsSchema) -> schemas.TokenPairSchema:
    async with managers.UserManager() as manager:
        user = await manager.authenticate(credentials.email, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        await manager.update_last_login(user.id)
    return jwt.jwt_service.create_token_pair(user.id)


@auth_router.post('/refresh', response_model=schemas.AccessTokenSchema)
async def refresh_token(request: schemas.RefreshTokenRequestSchema) -> schemas.AccessTokenSchema:
    return jwt.jwt_service.refresh_access_token(request.refresh_token)


@users_router.get('/me', response_model=schemas.UserWithProfileSchema)
async def get_me(
    user: dependencies.CurrentActiveUser,
    profile: dependencies.CurrentUserProfile,
) -> schemas.UserWithProfileSchema:
    return schemas.UserWithProfileSchema.build(user, profile)


@users_router.patch('/me', response_model=schemas.UserDetailSchema)
async def update_me(
    user: dependencies.CurrentActiveUser,
    user_data: schemas.UserUpdateDataSchema,
) -> models.User:
    """Update current user's authentication fields (email, password)."""
    try:
        async with managers.UserManager() as manager:
            updated_user = await manager.update_user(user.id, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@users_router.get('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def get_my_profile(profile: dependencies.CurrentUserProfile) -> models.UserProfile:
    """Get current user's profile."""
    return profile


@users_router.patch('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def update_my_profile(
    user: dependencies.CurrentActiveUser,
    profile_data: schemas.UserProfileUpdateDataSchema,
) -> models.UserProfile:
    """Update current user's profile (display name, bio)."""
    try:
        async with managers.UserProfileManager() as manager:
            updated_profile = await manager.update_profile(user.id, profile_data)
        return updated_profile
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
