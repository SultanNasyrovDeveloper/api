import json
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from .utils import get_content_size


class RecordID(BaseModel):
    id: str
    table_name: str = 'node'

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def parse_string_id(cls, data):
        """Allow RecordID to be created from a plain string."""
        if isinstance(data, str):
            # Extract table name and id from "table:id" format or use just the id
            if ':' in data:
                table_name, id_part = data.split(':', 1)
                return {'id': id_part, 'table_name': table_name}
            else:
                return {'id': data, 'table_name': 'node'}
        return data

    @model_serializer(mode='plain')
    def serialize_as_string(self) -> str:
        return self.id

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {'type': 'string'}


class IdMixin:
    id: RecordID | None = None

    @property
    def pk(self) -> str:
        return self.id.id


class ParentIdMixin:
    parent_id: RecordID | None = Field(default=None, validate_default=True)

    @property
    def parent_pk(self) -> str:
        return self.parent_id.id


class NodeContentMixin(BaseModel):
    content: str = Field(default_factory=str)
    size: int = 0

    # noinspection PyNestedDecorators
    @model_validator(mode='before')
    @classmethod
    def calculate_content_size(cls, data: dict) -> dict:
        if 'content' in data:
            content = json.loads(data.get('content'))
            data['size'] = get_content_size(content.get('root', {}))
        return data


class NodeStatisticsMixin(BaseModel):
    last_rating: int = 0
    repetitions: int = 0
    difficulty: float = 2.4
    owner_views: int = 0
    last_interval: float = 0
    last_repetition: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_optimal_repetition: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(days=1)
    )
    cpr: int = 0  # consecutive positive repetitions
