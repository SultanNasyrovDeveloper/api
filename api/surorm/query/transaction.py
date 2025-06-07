from typing import Self

from .types import Expression, Renderable
from .utils import render


class Return(Renderable):
    def __init__(self, expression: Expression):
        self.expression = expression

    def sql(self) -> str:
        return f'return {render(self.expression)};'


class Transaction(Renderable):
    def __init__(self):
        self._operations = []
        self._return = None

    def perform(self, *operations: Expression) -> Self:
        self._operations = operations
        return self

    def return_(self, value: Expression) -> Self:
        if isinstance(value, Return):
            self._return = value
        self._return = Return(value)
        return self

    def sql(self) -> str:
        q = [
            'begin transaction',
            *[render(operation) for operation in self._operations],
        ]
        if self._return:
            q.append(render(self._return))
        q.append('commit transaction;')
        return '; '.join(q)
