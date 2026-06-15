from abc import ABCMeta, abstractmethod


class AbstractPalaceClient(metaclass=ABCMeta):
    @abstractmethod
    async def get(self):
        pass

    @abstractmethod
    async def get_subtree_ids(self, limit: int = 50) -> list[str]:
        pass
