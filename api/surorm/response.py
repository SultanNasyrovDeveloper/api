from typing import Literal, Type, TypedDict

from pydantic import BaseModel


class SurrealClientResponseData[ResponseItemType](TypedDict):
    status: Literal['OK']
    result: list[ResponseItemType]
    time: str


class Response[ResponseData: dict]:
    """
    Single transaction response.
    """

    OK_STATUS = 'OK'

    def __init__(
        self,
        data: list[SurrealClientResponseData[ResponseData]],
        model: Type[BaseModel] = None,
    ):
        self._data = data[0] if isinstance(data, list) else {}
        self.model = model

    @property
    def is_ok(self) -> bool:
        return self._data.get('status', None) == self.OK_STATUS

    @property
    def is_contains_data(self) -> bool:
        return bool(self._data.get('result', []))

    def data(self) -> dict | list[dict] | None:
        return self._data.get('result')

    def raw(self, many: bool = True) -> ResponseData | list[ResponseData] | None:
        if not self.is_ok or not self.is_contains_data:
            return None
        return (
            self._data['result']
            if many
            else (
                self._data['result'][0]
                if isinstance(self._data['result'], list)
                else self._data['result']
            )
        )

    def instances(
        self, model: Type[BaseModel], many: bool = True
    ) -> list[BaseModel] | BaseModel | None:
        raw = self.raw(many)
        if not raw:
            return
        return model.model_validate(raw) if not many else map(model.model_validate, raw)

    def dict(self, model: Type[BaseModel], many: bool = True) -> dict | list[dict] | None:
        model_instances = self.instances(model, many)
        if not model_instances:
            return
        return (
            model_instances.model_dump()
            if not many
            else [instance.model_dump() for instance in model_instances]
        )
