from fastapi import APIRouter, HTTPException, status

from . import dependencies, jwt, schemas

auth_router = APIRouter(tags=['Authentication'])
users_router = APIRouter(prefix='/users', tags=['Users'])


@users_router.post(
    '/signup',
    response_model=schemas.UserDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    user_data: schemas.UserCreateDataSchema,
    users: dependencies.UserManagerDependency,
    user_profiles: dependencies.UserProfileManagerDependency,
    knowledge_tree: dependencies.KnowledgeTreeClientDependency,
) -> schemas.UserWithProfileSchema:
    try:
        user = await users.create_user(user_data)
        root = await knowledge_tree.create(
            {
                'owner_id': str(user.id),
                'title': f"{user.username.title()}'s knowledge tree",
                'order': 'aaaaaa',
                'questions': 'What do I know?',
            }
        )
        if not root:
            await users.delete(str(user.id))
            raise ValueError('Unable to create knowledge tree root.')
        profile = await user_profiles.create_profile(
            schemas.UserProfileCreateSchema(
                user_id=user.id,
                knowledge_tree_root_id=root.id.id,
            )
        )
        return schemas.UserWithProfileSchema.build(user, profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@auth_router.post('/token', response_model=schemas.TokenPairSchema)
async def get_token(
    credentials: schemas.LoginCredentialsSchema, users: dependencies.UserManagerDependency
) -> schemas.TokenPairSchema:
    user = await users.authenticate(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    await users.update_last_login(user.id)
    return jwt.jwt_service.create_token_pair(user.id)


@auth_router.post('/refresh', response_model=schemas.AccessTokenSchema)
async def refresh_token(request: schemas.RefreshTokenRequestSchema) -> schemas.AccessTokenSchema:
    return jwt.jwt_service.refresh_access_token(request.refresh_token)


@users_router.get('/me', response_model=schemas.UserWithProfileSchema)
async def get_me(
    user: dependencies.CurrentUser,
    profile: dependencies.CurrentUserProfile,
) -> schemas.UserWithProfileSchema:
    return schemas.UserWithProfileSchema.build(user, profile)


@users_router.patch('/me', response_model=schemas.UserDetailSchema)
async def update_me(
    user: dependencies.CurrentUser,
    users: dependencies.UserManagerDependency,
    user_data: schemas.UserUpdateDataSchema,
) -> schemas.UserDetailSchema:
    try:
        updated_user = await users.update_user(user.id, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@users_router.get('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def get_my_profile(profile: dependencies.CurrentUserProfile) -> schemas.UserProfileDetailSchema:
    return profile


@users_router.patch('/me/profile', response_model=schemas.UserProfileDetailSchema)
async def update_my_profile(
    user: dependencies.CurrentUser,
    user_profiles: dependencies.UserProfileManagerDependency,
    profile_data: schemas.UserProfileUpdateDataSchema,
) -> schemas.UserProfileDetailSchema:
    try:
        updated_profile = await user_profiles.update_profile(user.id, profile_data)
        return updated_profile
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
