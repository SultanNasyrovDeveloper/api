from typing import Iterable

from .types import Expression, Renderable
from .utils import render


class Operation(Renderable):
    def __init__(self, operation: str, *operands: Expression, **kwargs):
        self.operation = operation
        self.operands = operands

    def sql(self) -> str:
        prepared = list(map(render, self.operands))
        if len(prepared) == 1:
            return f'{self.operation}{prepared[0]}'
        return f' {self.operation} '.join(prepared)


class AbstractOperation(Renderable):
    operation: str
    operands: Iterable

    def sql(self) -> str:
        prepared = list(map(render, self.operands))
        if len(prepared) == 1:
            return f'{self.operation}{prepared[0]}'
        return f' {self.operation} '.join(prepared)


class Add(AbstractOperation):
    operation = '+'

    def __init__(self, *operands: Expression):
        self.operands = operands


class Greater(Renderable):
    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right

    def sql(self) -> str:
        return f'{render(self.left)} > {render(self.right)}'


class Equals(Renderable):
    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right

    def sql(self) -> str:
        return f'{render(self.left)} == {render(self.right)}'
