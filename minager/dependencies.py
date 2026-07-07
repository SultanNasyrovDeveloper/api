from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from surorm import Session

from .settings import ApplicationConfig


async def get_app(request: Request) -> FastAPI:
    return request.app


App = Annotated[FastAPI, Depends(get_app)]


async def get_config(app: App) -> ApplicationConfig:
    return app.state.config


AppConfig = Annotated[ApplicationConfig, Depends(get_config)]


async def get_postgres_session(app: App) -> AsyncGenerator[AsyncSession]:
    async with app.state.postgres_session_factory() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise


PostgresSession = Annotated[AsyncSession, Depends(get_postgres_session)]


async def get_mongo_session(app: App, config: AppConfig) -> AsyncIOMotorDatabase:
    return app.state.mongo[config.mongo.name]


MongoSession = Annotated[AsyncIOMotorDatabase, Depends(get_mongo_session)]


def get_surreal_session(app: App) -> Session:
    return Session(connection=app.state.surreal)


SurrealSession = Annotated[Session, Depends(get_surreal_session)]
