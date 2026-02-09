import jwt
import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config
from minager.app import app
from minager.auth.managers import UserManager, UserProfileManager
from minager.settings import config


@pytest.fixture
def fake():
    return Faker()


# ============================================================================
# PostgreSQL Test Database Setup
# ============================================================================
@pytest.fixture(scope='session')
async def main_db_test_engine():
    default_db_url = config.main_db.to_str(path='/postgres')
    default_engine = create_async_engine(default_db_url, isolation_level='AUTOCOMMIT')
    test_db_name = config.main_db.name
    async with default_engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
        )
        exists = result.scalar()
        if not exists:
            await conn.execute(text(f'CREATE DATABASE {test_db_name}'))
    await default_engine.dispose()
    test_db_url = config.main_db.to_str()
    test_engine = create_async_engine(test_db_url, echo=False)
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option(
        'sqlalchemy.url', config.main_db.to_str(scheme='postgresql+asyncpg')
    )
    command.upgrade(alembic_cfg, 'head')
    yield test_engine
    await test_engine.dispose()
    default_engine = create_async_engine(default_db_url, isolation_level='AUTOCOMMIT')
    async with default_engine.connect() as conn:
        await conn.execute(
            text(
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                AND pid <> pg_backend_pid()
                """
            )
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS {test_db_name}'))
    await default_engine.dispose()


@pytest.fixture(scope='session', autouse=True)
def main_db_test_session_factory(main_db_test_engine):
    """Creates async session factory for test database"""
    return async_sessionmaker(main_db_test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def main_db(main_db_test_session_factory):
    """Provides a database session with automatic rollback after each test"""
    async with main_db_test_session_factory() as session:
        yield session
        await session.rollback()


# ============================================================================
# Auth Fixtures
# ============================================================================
@pytest.fixture
async def test_user(main_db, fake):
    """Creates a test user in the database with profile"""
    user_manager = UserManager()
    username = fake.user_name()
    user_data = UserCreate(email=fake.email(), password='TestPassword123!', username=username)
    user = await user_manager.create_user(user_data, session=main_db)
    await main_db.commit()

    # Create user profile
    profile_manager = UserProfileManager()
    profile_data = UserProfileCreate(user_id=user.id, username=username)
    await profile_manager.create_profile(profile_data, session=main_db)
    await main_db.commit()

    user.plain_password = 'TestPassword123!'
    user.username = username
    return user


@pytest.fixture
def api_user():
    """Mock user data for JWT token"""
    return {'id': 'test_user', 'sub': 'test_user'}


@pytest.fixture
def unauthorized_api_client(api_user):
    """Test client with bearer token authentication"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_client(api_user):
    """Test client with bearer token authentication"""
    token = jwt.encode(
        api_user, config.secret_key.get_secret_value(), algorithm=config.jwt_hashing_algorithm
    )
    with TestClient(app, headers={'Authorization': f'Bearer {token}'}) as client:
        yield client


# ============================================================================
# SurrealDB Test Database Setup
# ============================================================================
@pytest.fixture(scope='session')
def surrealdb_test_config():
    """Creates test configuration for SurrealDB"""
    from minager.core.surorm.core.settings import SurrealConfig

    # Use separate namespace for tests
    test_config = SurrealConfig(
        driver='surreal',
        name=f'{config.palace_node_db.name}_test',
        namespace=f'{config.palace_node_db.namespace}_test',
        host=config.palace_node_db.host or 'localhost',
        port=config.palace_node_db.port or 8000,
        username=config.palace_node_db.username or 'root',
        password=config.palace_node_db.password,
    )
    return test_config


@pytest.fixture(scope='session')
async def surrealdb_test_manager(surrealdb_test_config):
    """Creates a SurrealDB manager for the test database with migrations"""
    from minager.node.managers import PalaceNodeManager

    manager = PalaceNodeManager(surrealdb_test_config)

    # Initialize connection and run migrations
    async with manager:
        # Test connection
        await manager.query('INFO FOR DB;')

        # Run migrations
        from scripts.migrate import run_migrations_for_app

        await run_migrations_for_app(manager, 'node')

        yield manager


@pytest.fixture
async def palace_node_db(surrealdb_test_manager):
    """
    Provides a clean SurrealDB instance for each test.
    Clears all data after each test.
    """
    # Yield the manager for the test
    yield surrealdb_test_manager

    # Cleanup: Remove all nodes and relations
    await surrealdb_test_manager.query('DELETE node;')
    await surrealdb_test_manager.query('DELETE child;')


@pytest.fixture
async def node_factory(palace_node_db, fake):
    """
    Factory fixture for creating test nodes with relationships.

    Usage:
        node = await node_factory()
        child = await node_factory(parent_id=node.id)
        sibling = await node_factory(parent_id=node.parent_id, order='zzz')
    """

    async def _create_node(
        owner_id: str = 'test_owner',
        title: str | None = None,
        parent_id: str | None = None,
        order: str | None = None,
        content: str | None = None,
        **kwargs,
    ):
        pass

        # Generate defaults
        node_data = {
            'owner_id': owner_id,
            'title': title or fake.sentence(nb_words=3),
            'content': content or fake.text(),
            'order': order or 'mmm',  # Middle lexorank
            **kwargs,
        }

        if parent_id:
            # Create as child
            node = await palace_node_db.create_child(parent_id, node_data)
        else:
            # Create as root
            node = await palace_node_db.create(node_data)

        return node

    return _create_node


@pytest.fixture
async def node_tree_factory(node_factory):
    """
    Factory for creating node trees for testing.

    Usage:
        tree = await node_tree_factory(depth=3, children_per_level=2)
        # Creates:
        # root
        #   ├── child1
        #   │   ├── grandchild1
        #   │   └── grandchild2
        #   └── child2
        #       ├── grandchild3
        #       └── grandchild4
    """

    async def _create_tree(
        depth: int = 2, children_per_level: int = 2, owner_id: str = 'test_owner'
    ):
        from minager.core.lexorank import Lexorank

        async def build_subtree(parent_id: str | None, current_depth: int):
            if current_depth > depth:
                return []

            nodes = []
            prev_order = None

            for i in range(children_per_level):
                # Calculate lexorank order
                if prev_order is None:
                    order = Lexorank.middle()
                else:
                    order = Lexorank.middle(previous=prev_order)

                node = await node_factory(
                    parent_id=parent_id,
                    owner_id=owner_id,
                    title=f'Node L{current_depth} #{i + 1}',
                    order=order,
                )
                nodes.append(node)
                prev_order = order

                # Recursively create children
                children = await build_subtree(node.id, current_depth + 1)
                if children:
                    node.children = children

            return nodes

        # Create root
        root = await node_factory(owner_id=owner_id, title='Root')

        # Build tree
        root.children = await build_subtree(root.id, 1)

        return root

    return _create_tree
