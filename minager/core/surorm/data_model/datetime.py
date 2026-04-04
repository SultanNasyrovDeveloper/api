from datetime import datetime

from ..base import DataType
from ..constants import DATETIME_FORMAT


class Datetime(DataType):
    name = 'datetime'

    def __init__(self, value: datetime, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    def sql(self) -> str:
        return f'd"{self._value.strftime(DATETIME_FORMAT)}"'
