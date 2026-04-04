from typing import ClassVar

from pydantic import BaseModel


class Table(BaseModel):
    __table_name__: ClassVar[str]


class Model(Table):
    pass


class Relation(Table):
    pass
