from contextlib import asynccontextmanager

from fastapi import FastAPI

from minager import settings
from minager.core.surorm.core.tester import SurrealConnectionTester


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = settings.config

    tester = SurrealConnectionTester(config.surreal)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with surreal db.')
    # TODO: Add connection testing for other databases

    app.state.config = config
    app.state.postgres_engine = settings.postgres_engine
    app.state.postgres_session_factory = settings.postgres_connection_factory
    app.state.surreal = settings.surreal
    app.state.mongo = settings.mongo

    await app.state.surreal.connect()
    await app.state.surreal.use(namespace=config.surreal.namespace, database=config.surreal.name)
    await app.state.surreal.signin(
        {
            'username': config.surreal.username,
            'password': config.surreal.password.get_secret_value(),
        }
    )

    yield

    await app.state.postgres_engine.dispose()
    await app.state.surreal.close()
    app.state.mongo.close()
