from ..types import Expression, Renderable


class Alias(Renderable):
    def __init__(self, name: str, value: Expression, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.value = value

    def sql(self) -> str:
        return f'{self.value} as {self.name}'
