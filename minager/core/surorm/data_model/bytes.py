from ..base import DataType


class Boolean(DataType):
    name = 'bytes'

    def __init__(self, value: str | bytes | bytearray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return f'<bytes>{str(self._value)}'
