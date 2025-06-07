from .types import Expression, Renderable


def render(value: Expression):
    return value.sql() if isinstance(value, Renderable) else str(value)
