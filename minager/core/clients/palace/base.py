from abc import ABCMeta, abstractmethod


class AbstractPalaceClient(metaclass=ABCMeta):

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def get(self):
        pass

    @abstractmethod
    async def get_subtree_ids(self, limit: int = 50) -> list[str]:
        pass
