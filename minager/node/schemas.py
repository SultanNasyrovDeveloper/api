# TODO: Refactor this file
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from . import enums, mixins


class CreateRootSchema(mixins.NodeStatisticsMixin, mixins.NodeContentMixin):
    owner_id: str
    title: str = 'Mind Palace'
    questions: str = 'What is Mind Palace'
    order: str = 'aaaaaa'


class NodeListItemSchema(BaseModel, mixins.IdMixin):
    title: str
    order: str | None = Field(default=None)


class TreeNodeItemSchema(BaseModel, mixins.IdMixin, mixins.ParentIdMixin):
    title: str
    order: str | None = ''
    ancestors: list[NodeListItemSchema] = Field(default_factory=list)
    children: list[TreeNodeItemSchema] = Field(default_factory=list)


class NodeDetailSchema(mixins.NodeStatisticsMixin, mixins.IdMixin, mixins.ParentIdMixin):
    title: str
    questions: str
    size: int
    content: str
    is_learn: bool = True
    created: datetime | None = None
    order: str
    owner_id: str | None = None
    tags: list[int] = Field(default_factory=list)
    ancestors: list[NodeListItemSchema] = Field(default_factory=list)
    children: list[NodeListItemSchema] = Field(default_factory=list)


class UpdatedNodeSchema(mixins.NodeStatisticsMixin):
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


class NodeEditSchema(mixins.NodeContentMixin, mixins.NodeStatisticsMixin, BaseModel):
    title: str = ''
    questions: str = ''
    is_learn: bool = True
    tags: list[int] = []


class NodeCreateSchema(NodeEditSchema, BaseModel):
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
