from abc import ABC, abstractmethod

from minager.surorm import Response, SurrealDBManager


class AbstractRequest[ConfigType](ABC):
    def __init__(self, db: SurrealDBManager, config: ConfigType, *args, **kwargs):
        self._db = db
        self._config = config
        super().__init__(*args, **kwargs)

    @abstractmethod
    async def perform(self) -> Response | None: ...
