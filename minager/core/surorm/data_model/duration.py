from ..base import DataType


class Duration(DataType):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError

    def sql(self) -> str:
        raise NotImplementedError
