from pydantic import BaseModel, SecretStr


class SurrealConfig(BaseModel):
    driver: str = 'surreal'
    name: str
    namespace: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: SecretStr | None = None
