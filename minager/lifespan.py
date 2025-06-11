from contextlib import asynccontextmanager

from fastapi import FastAPI

from minager.auth.managers import UserManager
from minager.surorm.tester import SurrealConnectionTester

from .settings import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    tester = SurrealConnectionTester(config.palace_node_db)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with palace db.')
    app.state.users = UserManager()
    await app.state.users.__aenter__()
    yield
    await app.state.users.__aexit__(None, None, None)
