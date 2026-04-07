from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict


class SurrealConfig(BaseModel):
    driver: str = 'surreal'
    name: str
    namespace: str = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None

    test: SurrealConfig | None = Field(default=None, validate_default=True)

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))

    @field_validator('test', mode='plain')
    @classmethod
    def validate_test_configuration(cls, v, info):
        """
        Enrich the test config using the parent config as a base.

        Rules:
        - Any field not explicitly set in the test config is inherited from the parent.
        - namespace is kept identical to the parent (tests live in the same namespace).
        - name defaults to `test_<parent_name>` so the test database is isolated from
          production without requiring a separate namespace.

        Uses mode='plain' + model_construct so the returned instance is never
        re-validated by Pydantic, which prevents infinite recursion on the
        recursive `test: SurrealConfig | None` field.
        """
        base_name = info.data.get('name')
        base_fields = {
            'driver': info.data.get('driver', 'surreal'),
            'name': f'test_{base_name}' if base_name else 'test',
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
            # Apply only the explicitly provided (non-None) values over the base.
            for k, val in v.items():
                if k != 'test' and val is not None:
                    base_fields[k] = val
            return cls.model_construct(**base_fields)

        # Already a SurrealConfig instance: backfill any None fields from base.
        if isinstance(v, cls):
            for field_name, base_value in base_fields.items():
                if field_name == 'test':
                    continue
                if getattr(v, field_name, None) is None:
                    object.__setattr__(v, field_name, base_value)
            object.__setattr__(v, 'test', None)
            return v

        return v
