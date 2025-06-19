from pydantic import BaseModel


class CorsConfiguration(BaseModel):
    allow_origins: list[str]
    allow_origin_regex: str = None
    allow_credentials: bool = False
    allow_methods: list[str] = ['*']
    allow_headers: list[str] = ['*']
    max_age: int = 600
