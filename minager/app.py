from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from minager.learning_session.api import router as learning_session_router
from minager.node.api import router as node_router
from minager.repetition_assistant.api import router as repetition_assistant_router
from minager.user.api import auth_router, users_router

from .lifespan import lifespan
from .settings import config

app = FastAPI(title='Minager', debug=config.debug, version='0.0.1', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # TODO: Fix
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


v1_router = APIRouter(prefix='/api/v1')


@app.get('/health')
async def health() -> dict:
    return {'status': 'healthy', 'service': 'minager-api'}


v1_router.include_router(router=auth_router, prefix='/auth')
v1_router.include_router(router=users_router, prefix='/auth')
v1_router.include_router(
    router=learning_session_router, prefix='/learning-session', tags=['Learning session']
)
v1_router.include_router(router=node_router, prefix='/node', tags=['Knowledge Tree'])
v1_router.include_router(
    router=repetition_assistant_router, prefix='/repetition-assistant', tags=['Repetition assistant']
)

app.include_router(v1_router)
