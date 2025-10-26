from typing import Self

from minager.surorm.types import Expression
from minager.surorm.utils import render

from ..base import Statement


class TransactionReturn(Statement):
    def __init__(self, expression: Expression, **kwargs):
        super().__init__(**kwargs)
        self.expression = expression

    def sql(self) -> str:
        return f'return {render(self.expression)};'


class Transaction(Statement):
    def __init__(self, *operations: Expression, **kwargs):
        super().__init__(**kwargs)
        self._operations = operations
        self._return = None

    def perform(self, *operations: Expression) -> Self:
        self._operations = operations
        return self

    def return_(self, value: Expression) -> Self:
        if isinstance(value, TransactionReturn):
            self._return = value
        self._return = TransactionReturn(value)
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
