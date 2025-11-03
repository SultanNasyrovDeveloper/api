from typing import Iterable

from ..base import Operator
from ..types import Expression
from ..utils import render


class TwoOperandOperator(Operator):
    operation: Expression | None = None
    left_operand: Expression
    right_operand: Expression

    def __init__(
        self, left: Expression, right: Expression, operation: Expression | None = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.operation = operation or self.operation
        assert self.operation, 'Could not determine operation for this operator. Nothing provided.'
        self.left_operand = left
        self.right_operand = right

    def sql(self) -> str:
        return f'{render(self.left_operand)} {render(self.operation)} {render(self.right_operand)}'


class MultiOperandOperator(Operator):
    operation: Expression | None = None
    operands: Iterable[Expression] = []

    def __init__(self, *operands: Expression, operation: Expression | None = None, **kwargs):
        super().__init__(**kwargs)
        self.operation = operation or self.operation
        self.operands = operands

    def sql(self) -> str:
        prepared = list(map(render, self.operands))
        if len(prepared) == 1:
            return f'{self.operation}{prepared[0]}'
        return f' {self.operation} '.join(prepared)
