from abc import ABCMeta, abstractmethod


class Renderable(metaclass=ABCMeta):
    @abstractmethod
    def sql(self) -> str:
        pass

    def __init__(self, **kwargs):
        pass

    def __str__(self) -> str:
        return self.sql()

    def print(self) -> str:
        return self.sql()


class Statement(Renderable, metaclass=ABCMeta):
    pass


class DataType(Renderable, metaclass=ABCMeta):
    name: str
    cast: bool = False

    def __init__(self, cast: bool = False, *args, **kwargs):
        super().__init__(**kwargs)
        self.cast = cast


class Operator(Renderable):
    pass


class Function(Renderable, metaclass=ABCMeta):
    name: str
    arguments: list[Renderable]

    def __init__(self, *arguments: Renderable, **kwargs):
        super().__init__(**kwargs)
        self.arguments = list(arguments)

    def sql(self) -> str:
        return f'{self.name}({', '.join(map(str, self.arguments))})'
