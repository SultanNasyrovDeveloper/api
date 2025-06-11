from .types import Expression, Renderable
from .utils import render


class Variable(Renderable):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name

    def sql(self) -> str:
        return f'${self._name}'


class DefineVariable(Renderable):
    def __init__(self, name: str, value: Expression):
        self._name = name
        self._value = value

    def sql(self) -> str:
        return f'{Variable(self._name).sql()} = {render(self._value)}'
