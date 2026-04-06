from functools import singledispatch
from typing import Any

from ..base import Renderable
from ..utils import render
from .models import Table


@singledispatch
def get_table_name(table: Any) -> str:
    raise TypeError(f"Unsupported type: {type(table)}")


@get_table_name.register(type)
def _(table: type) -> str:
    if issubclass(table, Table):
        return table.__table_name__
    raise TypeError(f"Expected Table class, got {table}")


@get_table_name.register(type)
def _(table: Table) -> str:
    return table.__table_name__


@get_table_name.register(Renderable)
def _(table: Renderable) -> str:
    return render(table)


@get_table_name.register(int)
@get_table_name.register(float)
@get_table_name.register(str)
def _(table: int | float | str) -> str:
    return render(table)
