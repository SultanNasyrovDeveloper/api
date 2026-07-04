from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from minager.auth import exceptions
from minager.auth.jwt import JWTService
from minager.auth.models import User, UserProfile
from minager.auth.repositories import UserProfileRepository, UserRepository
from minager.auth.schemas import TokenPayloadSchema
from minager.auth.services import UserProfileService, UserService
from minager.auth.use_cases import SignUpUseCase
from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import PostgresSession, SurrealConnection

security = HTTPBearer()
jwt_service = JWTService.from_config()


def get_knowledge_tree_client(connection: SurrealConnection) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(connection=connection)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_user_repository(session: PostgresSession) -> UserRepository:
    return UserRepository(session=session)


UserRepositoryDependency = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_profile_repository(session: PostgresSession) -> UserProfileRepository:
    return UserProfileRepository(session=session)


UserProfileRepositoryDependency = Annotated[UserProfileRepository, Depends(get_user_profile_repository)]


def get_user_service(repository: UserRepositoryDependency) -> UserService:
    return UserService(repository=repository)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]


def get_user_profile_service(repository: UserProfileRepositoryDependency) -> UserProfileService:
    return UserProfileService(repository=repository)


UserProfileServiceDependency = Annotated[UserProfileService, Depends(get_user_profile_service)]


def get_sign_up_use_case(
    user_service: UserServiceDependency,
    user_profile_service: UserProfileServiceDependency,
    knowledge_tree: KnowledgeTreeClientDependency,
) -> SignUpUseCase:
    return SignUpUseCase(
        user_service=user_service,
        user_profile_service=user_profile_service,
        knowledge_tree=knowledge_tree,
    )


SignUpUseCaseDependency = Annotated[SignUpUseCase, Depends(get_sign_up_use_case)]


def get_jwt_service() -> JWTService:
    return jwt_service


JWTServiceDependency = Annotated[JWTService, Depends(get_jwt_service)]


async def get_jwt_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: JWTServiceDependency,
) -> TokenPayloadSchema:
    token = credentials.credentials
    try:
        return jwt_service.verify_token_type(token, 'access')
    except exceptions.AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={'WWW-Authenticate': 'Bearer'},
        ) from e


TokenPayload = Annotated[TokenPayloadSchema, Depends(get_jwt_payload)]


async def get_current_user_id(token_payload: TokenPayload) -> UUID:
    return token_payload.sub


CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user(user_id: CurrentUserID, users: UserServiceDependency) -> User:
    user = await users.get_active_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_verified_user(user: CurrentUser) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Email not verified')
    return user


CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]


def get_current_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough permissions')
    return user


CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]


async def get_current_user_profile(
    user: CurrentUser, user_profiles: UserProfileServiceDependency
) -> UserProfile:
    profile = await user_profiles.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User profile not found')
    return profile


CurrentUserProfile = Annotated[UserProfile, Depends(get_current_user_profile)]
