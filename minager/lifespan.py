from contextlib import asynccontextmanager

from fastapi import FastAPI

from minager.auth.managers import UserManager
from minager.core.clients.palace.client import PalaceNodeServiceClient
from minager.learning_session.db import LearningSessionClient
from minager.node.managers import PalaceNodeManager
from minager.surorm.core.tester import SurrealConnectionTester
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
    palace_service_client = PalaceNodeServiceClient(config=config.palace_node_db)
    await palace_service_client.__aenter__()
    app.state.learning_session = LearningSessionClient(
        config=config.learning_session_db, palace_client=palace_service_client
    )
    await app.state.nodes.__aenter__()
    await app.state.users.__aenter__()
    await app.state.user_profiles.__aenter__()
    yield
    await palace_service_client.__aexit__(None, None, None)
    await app.state.nodes.__aexit__(None, None, None)
    await app.state.users.__aexit__(None, None, None)
    await app.state.user_profiles.__aexit__(None, None, None)
