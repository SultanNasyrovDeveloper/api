from ..base import Function
from .base import FunctionMap


class Append(Function):
    name = 'array::append'


class Concat(Function):
    name = 'array::concat'


class First(Function):
    name = 'array::first'


class IsEmpty(Function):
    name = 'array::is_empty'


class ArrayFunctionMap(FunctionMap):
    append = Append
    concat = Concat
    first = First
    is_empty = IsEmpty
