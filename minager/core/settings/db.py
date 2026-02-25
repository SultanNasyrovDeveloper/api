from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
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

    test: DBConnectionConfig | None = Field(default=None, validate_default=True)

    @field_validator('test', mode='plain')
    @classmethod
    def build_test_config(cls, v, info) -> DBConnectionConfig:
        """
        Auto-populate the test database config from the parent config.

        Rules:
        - Database name comes from `test_name` if set, otherwise `test_<name>`.
        - All connection details (host, port, credentials) are inherited.
        - The nested `test` field on the resulting instance is always None to
          prevent infinite recursion.
        """
        base_name = info.data.get('name')
        test_name = info.data.get('test_name') or (f'test_{base_name}' if base_name else 'test')
        base_fields = {
            'driver': info.data.get('driver', 'postgresql+asyncpg'),
            'name': test_name,
            'test_name': None,
            'namespace': info.data.get('namespace'),
            'host': info.data.get('host'),
            'port': info.data.get('port'),
            'username': info.data.get('username'),
            'password': info.data.get('password'),
            'test': None,
        }

        if v is None:
            return cls.model_construct(**base_fields)

        if isinstance(v, dict):
            for k, val in v.items():
                if k != 'test' and val is not None:
                    base_fields[k] = val
            return cls.model_construct(**base_fields)

        if isinstance(v, cls):
            for field_name, base_value in base_fields.items():
                if field_name == 'test':
                    continue
                if getattr(v, field_name, None) is None:
                    object.__setattr__(v, field_name, base_value)
            object.__setattr__(v, 'test', None)
            return v

        return v

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
