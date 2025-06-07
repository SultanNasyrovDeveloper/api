from typing import Annotated

from fastapi import Depends, FastAPI, Request
from jwt import decode


def get_user_data(request: Request) -> dict | None:
    auth_header = request.headers.get('authorization')
    if auth_header:
        return decode(auth_header.split(' ')[1], options={'verify_signature': False})


def get_request_app(request: Request) -> FastAPI:
    return request.app


RequestUser = Annotated[dict, Depends(get_user_data)]
App = Annotated[FastAPI, Depends(get_request_app)]
