from typing import Type

from ..base import Function
from ..orm.models import Table
from ..orm.utils import get_table_name


class Thing(Function):
    name = 'type::thing'

    def __init__(self, type_: str | Type[Table], id_: str, **kwargs):
        table_name = (
            get_table_name(type_)
            if isinstance(type_, type) and issubclass(type_, Table)
            else str(type_)
        )
        super().__init__(*[table_name, id_], **kwargs)
        self.type_ = table_name
        self._id = id_

    def sql(self) -> str:
        return f'{self.name}("{self.type_}", "{self._id}")'
