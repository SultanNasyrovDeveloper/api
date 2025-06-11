from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from minager.auth.api import router as user_router

from .lifespan import lifespan
from .settings import config

app = FastAPI(title='Minager', debug=config.debug, version='1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


v1_router = APIRouter(prefix='/api/v1')


@v1_router.get('/healthcheck')
async def healthcheck() -> str:
    return 'Ok'


v1_router.include_router(user_router, tags=['User'])


app.include_router(v1_router)
