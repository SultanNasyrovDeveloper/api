from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.node.managers import PalaceNodeManager
from api.surorm.tester import SurrealConnectionTester


@asynccontextmanager
async def lifespan(app: FastAPI):
    tester = SurrealConnectionTester(app.state.config.palace_node_db)
    is_connected = tester.wait()
    if not is_connected:
        raise ValueError('Unable to establish connection with palace db.')
    node_manager = PalaceNodeManager(config=app.state.config.palace_node_db)
    await node_manager.connect()
    app.state.palace_node = node_manager
    yield
    await app.state.palace_node.close()
