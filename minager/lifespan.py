from contextlib import asynccontextmanager

from fastapi import FastAPI

from minager.auth.managers import UserManager
from minager.node.managers import PalaceNodeManager
from minager.surorm.tester import SurrealConnectionTester
from minager.user_profile.managers import UserProfileManager

from .settings import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    tester = SurrealConnectionTester(config.palace_node_db)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with palace db.')
    app.state.nodes = PalaceNodeManager(config.palace_node_db)
    app.state.users = UserManager()
    app.state.user_profiles = UserProfileManager()
    await app.state.nodes.__aenter__()
    await app.state.users.__aenter__()
    await app.state.user_profiles.__aenter__()
    yield
    await app.state.nodes.__aexit__(None, None, None)
    await app.state.users.__aexit__(None, None, None)
    await app.state.user_profiles.__aexit__(None, None, None)
