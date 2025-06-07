from typing import Literal


class Renderable:
    def sql(self) -> str:
        raise NotImplemented

    def __str__(self) -> str:
        return self.sql()


type Expression = int | float | str | Renderable
type TableType = Literal['any', 'normal', 'relation']
type SearchAnalyzer = Literal['']
