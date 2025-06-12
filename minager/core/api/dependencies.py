from typing import Annotated

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from minager.core.db.models import Model
from minager.settings import AuthBearerToken


def get_request_app(request: Request) -> FastAPI:
    return request.app


App = Annotated[FastAPI, Depends(get_request_app)]


def get_request_user(app: App, token: str = Depends(AuthBearerToken)) -> dict | None:
    manager = app.state.users
    return manager.validate_token(token)


RequestUser = Annotated[dict, Depends(get_request_user)]


async def get_request_db_user(app: App, request_user: RequestUser) -> Model:
    manager = app.state.users
    async with manager:
        return await manager.get(request_user.get('id'))


RequestDBUser = Annotated[BaseModel, Depends(get_request_db_user)]
