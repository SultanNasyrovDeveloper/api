from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.learning_session.api import router as learning_session_router
from api.node.api import router as palace_nodes_router
from api.palace.statistics import router as palace_statistics_router
from api.settings import config
from api.user_profile.api import router as user_profile_router

from .lifespan import lifespan

app = FastAPI(title='Minager', debug=config.debug, version='1.0', lifespan=lifespan)
app.state.config = config
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


v1_router = APIRouter(prefix='/api/v1/mind-palace')


@v1_router.get('/healthcheck')
async def healthcheck() -> str:
    return 'Ok'


v1_router.include_router(learning_session_router, tags=['Learning Session'])
v1_router.include_router(palace_nodes_router, tags=['Node'])
v1_router.include_router(palace_statistics_router, tags=['Palace Statistics'])
v1_router.include_router(user_profile_router, tags=['User Profile'])

app.include_router(v1_router)
