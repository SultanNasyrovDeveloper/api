from ..base import Function
from .base import FunctionMap


class FromDays(Function):
    name = 'duration::from::days'


class DurationFunctionMap(FunctionMap):
    from_days = FromDays
