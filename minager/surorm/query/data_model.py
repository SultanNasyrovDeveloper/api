import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..utils import to_surreal_datetime_string
from .types import Expression, Renderable
from .utils import render


class DataType(Renderable):
    name: str

    @classmethod
    def get_type(cls):
        return cls.name


class Null(DataType):

    def sql(self) -> str:
        return 'null'


class Boolean(DataType):
    def __init__(self, value: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return 'true' if self._value else 'false'


class Record(DataType):
    def __init__(self, table: str, id_: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._table = table
        self._id = id_

    def sql(self) -> str:
        return f'{self._table}:{self._id}'


class Number(DataType):
    def __init__(self, value: int | float | complex | Decimal):
        self._value = value

    def sql(self) -> str:
        return str(self._value)


class String(DataType):
    def __init__(self, value: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return f'"{self._value}"'


class Datetime(DataType):
    def __init__(self, value: datetime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return to_surreal_datetime_string(self._value)


class Array[InnerType: Any](DataType):
    def __init__(self, *values: Expression, length: int | None = None):
        self.values = values
        self.length = length

    def sql(self) -> str:
        return f'[{','.join(map(render, self.values))}]'


class Json(DataType):
    def __init__(self, value: dict):
        self._value = value

    def sql(self) -> str:
        return json.dumps(self._value)


PYTHON_TO_SURREAL_TYPE_MAP = {str: String, datetime: Datetime}
