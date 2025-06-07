from typing import Literal

from pydantic import BaseModel, SecretStr

type DBDriver = Literal['postgresql+asyncpg', 'postgresql', 'motor', 'surreal']


class DBConnectionConfig(BaseModel):

    driver: DBDriver = 'postgresql+asyncpg'
    name: str
    namespace: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None
