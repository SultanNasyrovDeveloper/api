from ..base import Function
from . import array, math
from . import object as surreal_object_functions
from . import time
from . import type as surreal_type_functions


class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Count(Function):
    name = 'count'


class F:
    count = Count
    array = dotdict({'append': array.Append, 'concat': array.Concat, 'first': array.First})
    math = dotdict({'mean': math.Mean, 'sum': math.Sum})
    object = dotdict(
        {
            'entries': surreal_object_functions.Entries,
            'extend': surreal_object_functions.Extend,
            'from_entries': surreal_object_functions.FromEntries,
            'is_empty': surreal_object_functions.IsEmpty,
            'len': surreal_object_functions.Len,
            'remove': surreal_object_functions.Remove,
            'values': surreal_object_functions.Values,
        }
    )
    time = dotdict(
        {
            'ceil': time.Ceil,
            'now': time.Now,
        }
    )
    type = dotdict({'thing': surreal_type_functions.Thing})
