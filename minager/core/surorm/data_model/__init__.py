import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..base import DataType
from ..constants import DATETIME_FORMAT
from ..types import Expression
from ..utils import render


class Null(DataType):
    name = 'null'

    def sql(self) -> str:
        return 'null'


class Boolean(DataType):
    name = 'boolean'

    def __init__(self, value: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return 'true' if self._value else 'false'


class Record(DataType):
    name = 'record'

    def __init__(self, table: str, id_: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._table = table
        self._id = id_

    def sql(self) -> str:
        return f'{self._table}:{self._id}'


class Number(DataType):
    name = 'number'

    def __init__(self, value: int | float | complex | Decimal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return str(self._value)


class String(DataType):
    name = 'string'

    def __init__(self, value: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        value = self._value
        if not isinstance(value, str):
            value = str(value)
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'


class Datetime(DataType):
    name = 'datetime'

    def __init__(self, value: datetime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return f'd"{self._value.strftime(DATETIME_FORMAT)}"'


class Array[InnerType: Any](DataType):
    name = 'array'

    def __init__(self, *values: Expression, length: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.values = values
        self.length = length

    def sql(self) -> str:
        return f'[{','.join(map(render, self.values))}]'


class Sequence[InnerType: Any](DataType):
    name = 'sequence'
    values: list[Expression] = []

    def __init__(self, items: list[Expression], length: int | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.values = items
        self.length = length

    def sql(self) -> str:
        return f'[{','.join(map(render, self.values))}]'

    def __add__(self, other: Expression) -> Expression:
        if isinstance(other, Sequence):
            return Sequence(self.values + other.values)
        if isinstance(other, (list, tuple, set)):
            return Sequence([*self.values, *other])
        return self


class Json(DataType):
    name = 'json'

    def __init__(self, value: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return json.dumps(self._value)


class RecordID(DataType):
    name = 'record_id'

    def __init__(self, value: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return json.dumps(self._value)
