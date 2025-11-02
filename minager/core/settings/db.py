from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, SecretStr
from yarl import URL

type DBDriver = Literal['postgresql+asyncpg', 'postgresql', 'motor', 'surreal']


class DBConnectionConfig(BaseModel):

    driver: DBDriver = 'postgresql+asyncpg'
    name: str
    test_name: str | None = None
    namespace: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None

    def to_url(self, **kwargs) -> URL:
        build_arguments = {
            'scheme': self.driver,
            'user': self.username,
            'password': self.password.get_secret_value() if self.password else '',
            'host': self.host,
            'port': int(self.port),
            'path': '/' + self.name,
            **kwargs,
        }
        return URL.build(**build_arguments)

    def to_str(self, **kwargs) -> str:
        return str(self.to_url(**kwargs))
