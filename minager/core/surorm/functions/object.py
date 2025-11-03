from ..base import Function
from .base import FunctionMap


class Entries(Function):
    name = 'object::entries'


class Extend(Function):
    name = 'object::extend'


class FromEntries(Function):
    name = 'object::from_entries'


class IsEmpty(Function):
    name = 'object::is_empty'


class Len(Function):
    name = 'object::len'


class Remove(Function):
    name = 'object::remove'


class Values(Function):
    name = 'object::values'


class ObjectFunctionMap(FunctionMap):
    entries = Entries
    extend = Extend
    from_entries = FromEntries
    is_empty = IsEmpty
    len = Len
    remove = Remove
    values = Values
