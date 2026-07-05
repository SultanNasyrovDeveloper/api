from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from minager.dependencies import PostgresSession
from minager.user import exceptions as user_exceptions
from minager.user.adapter import UserClient
from minager.user.repositories import UserProfileRepository, UserRepository
from minager.user.services import UserProfileService, UserService

from . import dto, exceptions
from .jwt import JWTService
from .port import AbstractUserClient

security = HTTPBearer()

jwt_service = JWTService.from_config()


def get_jwt_service() -> JWTService:
    return jwt_service


JWTServiceDependency = Annotated[JWTService, Depends(get_jwt_service)]


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_service: JWTServiceDependency,
) -> UUID:
    try:
        payload = jwt_service.verify_token_type(credentials.credentials, 'access')
    except exceptions.AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={'WWW-Authenticate': 'Bearer'},
        ) from e
    return payload.sub


CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]


def get_user_client(session: PostgresSession) -> AbstractUserClient:
    return UserClient(
        user_service=UserService(repository=UserRepository(session=session)),
        user_profile_service=UserProfileService(repository=UserProfileRepository(session=session)),
    )


UserClientDependency = Annotated[AbstractUserClient, Depends(get_user_client)]


async def get_current_user(user_id: CurrentUserID, user_client: UserClientDependency) -> dto.User:
    try:
        return await user_client.get_active_user(user_id)
    except user_exceptions.UserError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={'WWW-Authenticate': 'Bearer'},
        ) from e


CurrentUser = Annotated[dto.User, Depends(get_current_user)]


def get_current_verified_user(user: CurrentUser) -> dto.User:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Email not verified')
    return user


CurrentVerifiedUser = Annotated[dto.User, Depends(get_current_verified_user)]


def get_current_superuser(user: CurrentUser) -> dto.User:
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough permissions')
    return user


CurrentSuperuser = Annotated[dto.User, Depends(get_current_superuser)]


async def get_current_user_profile(user: CurrentUser, user_client: UserClientDependency) -> dto.UserProfile:
    try:
        return await user_client.get_user_profile(user.id)
    except user_exceptions.UserError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


CurrentUserProfile = Annotated[dto.UserProfile, Depends(get_current_user_profile)]
