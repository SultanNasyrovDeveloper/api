from pydantic import field_validator


class IdMixin:
    id: str | None = None

    # noinspection PyNestedDecorators
    @field_validator('id', mode='before')
    @classmethod
    def extract_id(cls, v: str | None) -> str:
        if v and not isinstance(v, str):
            v = str(v)
        return v if v is None or ':' not in v else v.split(':')[-1]
