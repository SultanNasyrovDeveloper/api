from pydantic import field_validator


class IdMixin:
    id: str | None = None

    # noinspection PyNestedDecorators
    @field_validator('id')
    @classmethod
    def extract_parent_id(cls, v: str | None) -> str:
        return v if v is None or ':' not in v else v.split(':')[-1]
