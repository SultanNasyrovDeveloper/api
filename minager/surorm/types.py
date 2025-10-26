from typing import Literal

from .base import Renderable

type TransactionReturnType = Literal['']
type RecordDataSetMode = Literal['set', 'values', 'content']
type Expression = int | float | str | Renderable
type TableType = Literal['any', 'normal', 'relation']
type SearchAnalyzer = Literal['']
