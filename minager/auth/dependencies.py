from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from minager.auth.jwt import jwt_service
from minager.auth.managers import UserManager, UserProfileManager
from minager.auth.models import User, UserProfile
from minager.auth.schemas import TokenPayloadSchema
from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import PostgresSession, SurrealConnection

security = HTTPBearer()


def get_knowledge_tree_client(connection: SurrealConnection) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(connection=connection)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_user_manager(session: PostgresSession) -> UserManager:
    return UserManager(session=session)


UserManagerDependency = Annotated[UserManager, Depends(get_user_manager)]


def get_user_profile_manager(session: PostgresSession) -> UserProfileManager:
    return UserProfileManager(session=session)


UserProfileManagerDependency = Annotated[UserProfileManager, Depends(get_user_profile_manager)]


async def get_jwt_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenPayloadSchema:
    token = credentials.credentials
    return jwt_service.verify_token_type(token, 'access')


TokenPayload = Annotated[TokenPayloadSchema, Depends(get_jwt_payload)]


async def get_current_user_id(token_payload: TokenPayload) -> UUID:
    return token_payload.sub


CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user(user_id: CurrentUserID, users: UserManagerDependency) -> User:
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
    user: CurrentUser, user_profiles: UserProfileManagerDependency
) -> UserProfile:
    profile = await user_profiles.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User profile not found')
    return profile


CurrentUserProfile = Annotated[UserProfile, Depends(get_current_user_profile)]
