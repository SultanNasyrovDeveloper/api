from ..base import Function
from .base import FunctionMap


class Append(Function):
    name = 'array::append'


class Concat(Function):
    name = 'array::concat'


class First(Function):
    name = 'array::first'


class ArrayFunctionMap(FunctionMap):
    append = Append
    concat = Concat
    first = First
