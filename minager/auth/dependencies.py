from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from minager.auth.jwt import jwt_service
from minager.auth.managers import UserManager, UserProfileManager
from minager.auth.models import User, UserProfile

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> UUID:
    """
    Extract and validate user ID from JWT access token.
    Returns user ID if token valid.
    Raises 401 if token invalid or wrong type.
    """
    token = credentials.credentials
    payload = jwt_service.verify_token_type(token, 'access')
    return payload.sub


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> User:
    """
    Get current authenticated user from database.
    Requires valid access token.
    Raises 401 if user not found or inactive.
    """
    async with UserManager() as manager:
        user = await manager.get_active_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    return user


async def get_current_verified_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current verified user.
    Requires user to have verified email.
    Raises 403 if user email not verified.
    """
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Email not verified')

    return user


async def get_current_superuser(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current superuser.
    Requires user to be superuser.
    Raises 403 if user is not superuser.
    """
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough permissions')

    return user


async def get_current_user_profile(
    user: Annotated[User, Depends(get_current_user)],
) -> UserProfile:
    """
    Get current user's profile.
    Raises 404 if profile not found.
    """
    async with UserProfileManager() as manager:
        profile = await manager.get_by_user_id(user.id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User profile not found')

    return profile


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
CurrentUserProfile = Annotated[UserProfile, Depends(get_current_user_profile)]
