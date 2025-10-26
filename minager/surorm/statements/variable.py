from minager.surorm.types import Expression, Renderable
from minager.surorm.utils import render


class Variable(Renderable):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(**kwargs)
        self._name = name

    def sql(self) -> str:
        return f'${self._name}'


class DefineVariable(Renderable):
    def __init__(self, name: str | Expression, value: Expression, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self._value = value

    def sql(self) -> str:
        return f'let {Variable(self._name)} = {render(self._value)}'
