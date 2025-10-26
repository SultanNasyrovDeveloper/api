from ..base import DataType
from ..types import RecordDataSetMode


class Object(DataType):
    name = 'object'

    def __init__(self, value: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self, mode: RecordDataSetMode = 'values'):
        return str(self._value)
