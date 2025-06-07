from .operation import Add
from .types import Expression, Renderable
from .utils import render


class Function(Renderable):
    name: str

    def __init__(self, *args: Expression):
        self.arguments = args or []

    def __add__(self, other: Expression) -> Add:
        return Add(self, other)

    def _prepare_arguments(self) -> list[str]:
        return list(map(render, self.arguments))


class DBFunction(Function):
    body: str
    args: list[str] | tuple[str]

    def sql(self):
        prepared = self._prepare_arguments()
        return f'{self.name}({','.join(prepared) if prepared else ''})'


class JSFunction(Function):
    args: list[str] | tuple[str]
    body: str

    def sql(self) -> str:
        return f'function ({','.join(map(render, self.arguments))}) {{ {self.body} }}'


# ARRAY
class ArrayAppend(DBFunction):
    name = 'array::append'


class ArrayConcat(DBFunction):
    name = 'array::concat'


class ArrayFirst(DBFunction):
    name = 'array::first'


class Count(DBFunction):
    name = 'count'


class MathSum(DBFunction):
    name = 'math::sum'


class TimeNow(DBFunction):
    name = 'time::now'


class DurationFromDays(DBFunction):
    name = 'duration::from::days'


class ObjectFromEntries(DBFunction):
    name = 'object::from_entries'


class ObjectEntries(DBFunction):
    name = 'object::entries'
