import pytest
from faker import Faker
from fastapi.testclient import TestClient
from jwt import encode
from surorm.manager import SurrealDBManager
from surorm.query import (
    DefineDatabase,
    DefineNamespace,
    Delete,
    Info,
    Remove,
    Transaction,
)
from surorm.surorm.migrations import PerformMigrationCommand

from minager.app import app
from minager.settings import config


@pytest.fixture
def fake():
    return Faker()


@pytest.fixture(scope='session')
def monkeypatch_session():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope='session', autouse=True)
def app_config(monkeypatch_session):
    monkeypatch_session.setattr(config.palace_node_db, 'name', 'test_palace')
    return config


@pytest.fixture(scope='session')
def db_client(app_config):
    return SurrealDBManager(config=app_config.palace_node_db)


@pytest.fixture(scope='session', autouse=True)
async def db(app_config, db_client):
    async with db_client as session:
        await session.query(
            DefineNamespace(app_config.palace_node_db.namespace).if_not_exists(True)
        )
        await session.query(Remove('database', app_config.palace_node_db.name).if_exists(True))
        await session.query(DefineDatabase(app_config.palace_node_db.name).if_not_exists(True))
        await PerformMigrationCommand(session, app_config.base_path).upgrade()
        response = await session.query(Info('database'))

    yield response.data()  # database info
    # clean up
    async with db_client as session:
        await session.query(Remove('database', app_config.palace_node_db.name))


@pytest.fixture(scope='function', autouse=True)
async def clean_db_data(db, db_client):
    tables = db['tables'].keys()
    query = Transaction().perform(*[Delete(table) for table in tables])
    async with db_client as session:
        await session.query(query)


@pytest.fixture
def api_user():
    return {'id': 'test_user', 'sub': 'test_user'}


@pytest.fixture
def api_client(api_user):
    with TestClient(app, headers={'Authorization': f'Bearer: {encode(api_user, '')}'}) as client:
        yield client
