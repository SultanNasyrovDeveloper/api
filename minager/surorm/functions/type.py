from ..base import Function


class Thing(Function):
    name = 'type::thing'

    def __init__(self, type_: str, id_: str, **kwargs):
        super().__init__(*[type_, id_], **kwargs)
        self.type_ = type_
        self._id = id_

    def sql(self) -> str:
        return f'{self.name}("{self.type_}", "{self._id}")'
