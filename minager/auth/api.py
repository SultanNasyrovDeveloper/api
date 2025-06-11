from fastapi import APIRouter

from minager.core.api.response import PaginatedResponse
from minager.core.api.viewset import ModelViewSet

from . import models, schemas

router = APIRouter(prefix='/users')


class UserViewSet(ModelViewSet):
    router = router
    model = models.User
    manager_state_parameter = 'users'

    request_models = {
        'default': schemas.UserDetailSchema,
        'create': schemas.UserCreateDataSchema,
        'update': schemas.UserCreateDataSchema,
    }
    response_models = {
        'default': schemas.UserDetailSchema,
        'select': PaginatedResponse[schemas.UserDetailSchema],
    }

    # @router.post('/token')
    # def token(self):
    #     return 'ok'
