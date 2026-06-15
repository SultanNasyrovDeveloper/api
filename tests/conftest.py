from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from minager.app import app
from minager.auth.jwt import jwt_service
from minager.auth.managers import UserManager, UserProfileManager
from minager.auth.schemas import (
    UserCreateDataSchema,
    UserProfileCreateSchema,
    UserWithProfileSchema,
)
from minager.node.managers import KnowledgeTreeNodeManager

pytest_plugins = [
    'tests.fixtures.surreal_db',
    'tests.fixtures.postgres_db',
]

TEST_USER_PASSWORD = 'TestPassword123!'


@dataclass
class UserTestContext:
    sub: UUID  # user UUID — used in JWT and as owner_id in SurrealDB
    root_node_id: str | None  # bare SurrealDB node ID of the user's palace root


@pytest_asyncio.fixture(scope='session')
async def app_client(palace_node_db_setup: None) -> AsyncGenerator[AsyncClient, None]:
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client,
    ):
        yield client


@pytest_asyncio.fixture()
async def test_user(
    pg_session: AsyncSession,
    test_palace_node_manager: KnowledgeTreeNodeManager,
) -> UserWithProfileSchema:
    suffix = uuid4().hex[:8]
    user = await UserManager(session=pg_session).create_user(
        UserCreateDataSchema(
            email=f'test_{suffix}@test.example.com',
            username=f'testuser_{suffix}',
            password=TEST_USER_PASSWORD,
        )
    )
    root_node = await test_palace_node_manager.create(
        {
            'owner_id': str(user.id),
            'title': 'Mind Palace',
            'questions': 'What is Mind Palace?',
            'content': '{"root": {}}',
            'order': 'aaaaaa',
        }
    )
    user_profile = await UserProfileManager(session=pg_session).create_profile(
        UserProfileCreateSchema(
            user_id=user.id,
            knowledge_tree_root_id=root_node.id.id,
        )
    )
    return UserWithProfileSchema.build(user, user_profile)


@pytest.fixture()
def test_user_context(test_user: UserWithProfileSchema) -> UserTestContext:
    return UserTestContext(sub=test_user.id, root_node_id=test_user.knowledge_tree_root_id)


@pytest.fixture()
def auth_headers(test_user_context: UserTestContext) -> dict[str, str]:
    token = jwt_service.create_access_token(test_user_context.sub)
    return {'Authorization': f'Bearer {token}'}
