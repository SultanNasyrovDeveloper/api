from contextlib import asynccontextmanager

from fastapi import FastAPI

from minager.core.clients.knowledge_tree.client import PalaceNodeServiceClient
from minager.core.surorm.core.tester import SurrealConnectionTester
from minager.learning_session.managers import LearningSessionManager
from minager.node.managers import PalaceNodeManager

from .settings import config, main_db_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    tester = SurrealConnectionTester(config.palace_node_db)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with knowledge_tree db.')
    app.state.nodes = PalaceNodeManager(config.palace_node_db)
    palace_service_client = PalaceNodeServiceClient(config=config.palace_node_db)
    await palace_service_client.__aenter__()
    app.state.learning_session = LearningSessionManager(
        config=config.learning_session_db,
        palace_client=palace_service_client,
    )
    await app.state.nodes.__aenter__()
    await app.state.learning_session.__aenter__()
    yield
    await palace_service_client.__aexit__(None, None, None)
    await app.state.nodes.__aexit__(None, None, None)
    await app.state.learning_session.__aexit__(None, None, None)
    await main_db_engine.dispose()
