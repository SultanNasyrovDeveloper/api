from functools import singledispatch
from typing import Any

from ..types import Renderable
from ..utils import render
from .models import Table


@singledispatch
def get_table_name(table: Any) -> str:
    raise TypeError(f"Unsupported type: {type(table)}")


@get_table_name.register(str)
def _(table: str) -> str:
    return table


@get_table_name.register(type)
def _(table: type[Table]) -> str:
    if issubclass(table, Table):
        return table.__table_name__
    raise TypeError(f"Expected Table class, got {table}")


@get_table_name.register(Table)
def _(table: Table) -> str:
    return table.__table_name__


@get_table_name.register(Renderable)
def _(table: Renderable) -> str:
    return render(table)


@get_table_name.register(int)
@get_table_name.register(float)
def _(table: int | float) -> str:
    raise render(table)
