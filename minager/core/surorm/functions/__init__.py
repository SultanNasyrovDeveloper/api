from ..base import Function
from . import array, duration, math, time
from . import object as surreal_object_functions
from . import type as surreal_type_functions


class dotdict(dict):  # noqa: N801
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Count(Function):
    name = 'count'


class FunctionManager:
    count = Count
    array: array.ArrayFunctionMap = array.ArrayFunctionMap()
    duration = duration.DurationFunctionMap()
    math: math.MathFunctionMap = math.MathFunctionMap()
    object: surreal_object_functions.ObjectFunctionMap = surreal_object_functions.ObjectFunctionMap
    time = dotdict(
        {
            'ceil': time.Ceil,
            'now': time.Now,
        }
    )
    type = dotdict({'thing': surreal_type_functions.Thing})

    def __call__(self, *args, **kwargs) -> Function:
        pass


F = FunctionManager()
