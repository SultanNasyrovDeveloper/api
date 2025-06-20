from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from minager.core.utils import flatten_ancestors
from minager.palace.schemas import IdMixin
from minager.surorm.serializers import SurrealSerializer

from . import enums
from .utils import get_content_size


class PalaceStatistics(BaseModel):
    total_nodes: int = 1
    total_repetitions: int = 0
    total_size: int = 0
    outdated: int = 0
    empty_nodes: int = 0


class ParentIdMixin:
    parent_id: str | None = Field(default=None, validate_default=True)

    # noinspection PyNestedDecorators
    @field_validator('parent_id', mode='before')
    @classmethod
    def extract_id(cls, v: str | None) -> str:
        if v and not isinstance(v, str):
            v = str(v)
        return v if v is None or ':' not in v else v.split(':')[-1]


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


class NodeContentMixin(BaseModel):
    content: str = Field(default_factory=str, format='json')
    size: int = 0

    # noinspection PyNestedDecorators
    @model_validator(mode='before')
    @classmethod
    def calculate_content_size(cls, data: dict) -> dict:
        if 'content' in data:
            content = json.loads(data.get('content'))
            data['size'] = get_content_size(content.get('root', {}))
        return data


class CreateRootSchema(NodeStatisticsMixin, NodeContentMixin, SurrealSerializer):
    owner_id: str
    title: str = 'Mind Palace'
    questions: str = 'What is Mind Palace'
    order: str = 'aaaaaa'


class NodeListItemSchema(BaseModel, IdMixin):
    title: str


class TreeNodeItemSchema(BaseModel, IdMixin, ParentIdMixin):
    title: str
    order: str | None = ''
    ancestors: list[NodeListItemSchema] = Field(default_factory=list)
    children: list[TreeNodeItemSchema] = Field(default_factory=list)


class NodeDetailSchema(NodeStatisticsMixin, IdMixin, ParentIdMixin):
    title: str
    questions: str
    size: int
    content: str
    is_learn: bool = True
    created: datetime = None
    order: str
    owner_id: str = None
    tags: list[int] = Field(default_factory=list)
    ancestors: list[NodeListItemSchema] = Field(default_factory=list)
    children: list[NodeListItemSchema] = Field(default_factory=list)

    @classmethod
    def from_db_response(cls, db_response: dict) -> Self:
        db_response['ancestors'] = flatten_ancestors(db_response['parent'], 'parent')
        return cls.model_validate(db_response)


class UpdatedNodeSchema(NodeStatisticsMixin):
    title: str = ''
    questions: str = ''
    size: int = 0
    content: str = ''
    is_learn: bool = True
    order: str = ''
    parent_id: str = None
    children: list[NodeListItemSchema] = []
    tags: list[int] = Field(default_factory=list)
    data_rating: int

    model_config = ConfigDict(extra='ignore')


class NodeEditSchema(NodeContentMixin, SurrealSerializer):
    title: str = ''
    questions: str = ''
    is_learn: bool = True
    tags: list[int] = []


class NodeCreateSchema(NodeEditSchema, SurrealSerializer):
    owner_id: str = None
    order: str = Field(default='aaaaaa')


class NodeMoveConfiguration(BaseModel):
    target_id: str
    position: enums.MovePosition = enums.MovePosition.last_child


def model_validate_tree(root_data: dict) -> TreeNodeItemSchema:
    root_children_data = sorted(
        root_data.pop('children', []), key=lambda child: child.get('order', '')
    )
    root_ancestors_data = root_data.pop('ancestors', [])
    root_data['ancestors'] = [
        *root_ancestors_data,
        {'id': root_data['id'], 'title': root_data['title']},
    ]
    root = TreeNodeItemSchema.model_validate(root_data)
    root_children = []
    for child_data in root_children_data:
        child_data['parent_id'] = root.id
        child_data['ancestors'] = root.ancestors
        root_children.append(model_validate_tree(child_data))
    root.children = root_children
    return root
