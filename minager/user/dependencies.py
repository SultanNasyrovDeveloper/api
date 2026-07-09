from typing import Annotated

from fastapi import Depends, HTTPException, status

from minager.core.auth.dependencies import CurrentUserID, PasswordServiceDependency
from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import PostgresSession, SurrealSession
from minager.user.models import User, UserProfile
from minager.user.repositories import UserProfileRepository, UserRepository
from minager.user.services import UserProfileService, UserService
from minager.user.use_cases import SignUpUseCase


def get_knowledge_tree_client(session: SurrealSession) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(session=session)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_user_repository(session: PostgresSession) -> UserRepository:
    return UserRepository(session=session)


UserRepositoryDependency = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_profile_repository(session: PostgresSession) -> UserProfileRepository:
    return UserProfileRepository(session=session)


UserProfileRepositoryDependency = Annotated[UserProfileRepository, Depends(get_user_profile_repository)]


def get_user_service(
    repository: UserRepositoryDependency, password: PasswordServiceDependency
) -> UserService:
    return UserService(repository=repository, password_service=password)


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


async def get_current_user(user_id: CurrentUserID, users: UserServiceDependency) -> User:
    """Full ORM user, unlike core.auth.dto.User which omits created_at/last_login/updated_at."""
    user = await users.get_active_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_user_profile(
    user: CurrentUser, user_profiles: UserProfileServiceDependency
) -> UserProfile:
    profile = await user_profiles.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User profile not found')
    return profile


CurrentUserProfile = Annotated[UserProfile, Depends(get_current_user_profile)]
