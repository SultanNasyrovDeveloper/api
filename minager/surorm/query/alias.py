from .types import Expression, Renderable


class Alias(Renderable):
    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

    def sql(self) -> str:
        return f'{self.value if type(self.value) is str else self.value.sql()} as {self.name}'
