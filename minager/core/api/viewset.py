import inspect
from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import Callable, Literal, TypeVar

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..db.managers import DatabaseManager
from .dependencies import App
from .filters import FilterSet
from .response import PaginatedResponse
from .types import PaginationData

ModelT = TypeVar('ModelT', bound=BaseModel)
CreateSchemaT = TypeVar('CreateSchemaT', bound=BaseModel)
UpdateSchemaT = TypeVar('UpdateSchemaT', bound=BaseModel)


type ViewsetMethodName = Literal['create', 'get', 'select', 'update', 'delete']


class BaseModelViewset(metaclass=ABCMeta):
    # TODO: Refactor viewset classes
    filterset: FilterSet | None

    model: ModelT
    router: APIRouter
    manager_state_parameter: str
    request_models: dict[Literal['default', 'create', 'update'], BaseModel]
    response_models: dict[Literal['default'] | ViewsetMethodName, BaseModel]

    def __init__(self, *args, **kwargs):
        if not self.router:
            return
        super().__init__(*args, **kwargs)

        # create
        wrapped_create = self.wrap_method(self.create, self.request_models, self.response_models)
        self.router.add_api_route('/', wrapped_create, methods=['POST'])

        # get
        wrapped_get = self.wrap_method(self.get, self.request_models, self.response_models)
        self.router.add_api_route('/{id_}', wrapped_get, methods=['GET'])

        # select
        wrapped_select = self.wrap_method(self.select, self.request_models, self.response_models)
        self.router.add_api_route('/', wrapped_select, methods=['GET'])

        # update
        wrapped_update = self.wrap_method(self.update, self.request_models, self.response_models)
        self.router.add_api_route('/{id_}', wrapped_update, methods=['PATCH'])

        # delete
        wrapped_delete = self.wrap_method(self.delete, self.request_models, self.response_models)
        self.router.add_api_route('/{id_}', wrapped_delete, methods=['DELETE'])

    def wrap_method(
        self, method: Callable, request_models: dict, response_models: dict
    ) -> Callable:
        """
        Wraps target class method in order to remove self as an argument.
        """
        method_annotations = method.__annotations__  # noqa
        method_signature = inspect.signature(method)
        if method.__name__ in ('create', 'update'):
            method_annotations['data'] = request_models.get(
                method.__name__, request_models.get('default')
            )
        no_self_params_required = []
        no_self_params_with_default = []
        for name, parameter in method_signature.parameters.items():
            if name == 'self':
                continue
            if name == 'data':
                parameter = parameter.replace(
                    annotation=request_models.get(method.__name__, request_models.get('default'))
                )

            if name == 'query' and method.__name__ == 'select' and getattr(self, 'filterset', None):
                parameter = inspect.Parameter(
                    name='query',
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=self.filterset,
                    default=Depends(self.filterset),
                )
            if name == 'pagination' and method.__name__ == 'select':
                parameter = inspect.Parameter(
                    name='pagination',
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=PaginationData,
                    default=Depends(PaginationData),
                )
            if parameter.default is inspect.Parameter.empty:
                no_self_params_required.append(parameter)
            else:
                no_self_params_with_default.append(parameter)
        return_annotation = None
        if method.__name__ != 'delete':
            return_annotation = response_models.get(method.__name__, response_models.get('default'))
        wrapper_signature = method_signature.replace(
            parameters=no_self_params_required + no_self_params_with_default,
            return_annotation=return_annotation,
        )

        @wraps(method)
        async def _wrapper(**kwargs):
            return await method.__get__(self)(**kwargs)

        _wrapper.__signature__ = wrapper_signature
        _wrapper.__name__ = method.__name__
        _wrapper.__qualname__ = method.__name__
        _wrapper.__annotations__ = {k: v for k, v in method.__annotations__.items() if k != 'self'}
        return _wrapper

    @abstractmethod
    def create(self, *args, **kwargs):
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def select(self, *args, **kwargs):
        pass

    @abstractmethod
    def update(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, *args, **kwargs):
        pass


class ModelViewSet(BaseModelViewset):

    async def create(self, app: App, data: BaseModel):
        manager = self.get_manager(app)
        async with manager:
            created = await manager.create(data.model_dump(mode='json'))
        return created

    async def get(self, app: App, id_: int):
        manager = self.get_manager(app)
        async with manager:
            return await manager.get(id_)

    async def select(self, app: App, pagination: PaginationData, query: FilterSet = Depends()):
        manager = self.get_manager(app)
        filters = query.get_filters()
        count = 0
        async with manager:
            items = await manager.list_(*filters, **pagination.model_dump())
            if items:
                count = await manager.count(*filters)
        return PaginatedResponse(
            count=count,
            page=pagination.page,
            per_page=pagination.per_page,
            results=items,
        )

    async def update(self, app: App, id_: int, data: BaseModel):
        manager = self.get_manager(app)
        async with manager:
            return await manager.update(id_, data.model_dump(mode='json', exclude_unset=True))

    async def delete(self, app: App, id_: int):
        manager = self.get_manager(app)
        async with manager:
            await manager.delete(id_)

    def get_manager(self, app: App) -> DatabaseManager | None:
        return getattr(app.state, self.manager_state_parameter, None)
