from decimal import Decimal

from ..base import DataType


class Number(DataType):
    name = 'number'

    def __init__(self, value: int | float | complex | Decimal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        if isinstance(self._value, Decimal):
            return f'{self._value}dec'
        return str(self._value)
