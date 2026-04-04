from typing import Literal

from ..base import Renderable

type InfoTarget = Literal['root', 'namespace', 'database', 'table']


class Info(Renderable):
    def __init__(self, target: InfoTarget, *args, **kwargs):
        self._target = target

    def sql(self) -> str:
        stmt = [f'info for {self._target}']
        return ' '.join(stmt)
