from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from minager.auth.jwt import jwt_service
from minager.auth.managers import UserManager
from minager.core.db.models import Model
from minager.settings import AuthBearerToken

from .settings import main_db


async def get_main_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with main_db() as session:
        yield session


def get_request_app(request: Request) -> FastAPI:
    return request.app


App = Annotated[FastAPI, Depends(get_request_app)]


async def get_request_user(token: str = Depends(AuthBearerToken)) -> dict | None:
    return jwt_service.verify_token_type(token, 'access')


RequestUser = Annotated[dict, Depends(get_request_user)]


async def get_request_db_user(request_user: RequestUser) -> Model:
    async with UserManager() as session:
        return await session.get(request_user['sub'])


RequestDBUser = Annotated[BaseModel, Depends(get_request_db_user)]
