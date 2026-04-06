from ..base import DataType
from ..orm.models import Table
from ..orm.utils import get_table_name


class Record(DataType):
    name = 'record'

    def __init__(self, table: str | type[Table], id_: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = table
        self.id_ = id_

    def sql(self) -> str:
        return f'{get_table_name(self.table)}:{self.id_}'
