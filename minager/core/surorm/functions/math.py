from ..base import Function
from .base import FunctionMap


class Mean(Function):
    name = 'math::mean'


class Sum(Function):
    name = 'math::sum'


class MathFunctionMap(FunctionMap):
    mean = Mean
    sum = Sum
