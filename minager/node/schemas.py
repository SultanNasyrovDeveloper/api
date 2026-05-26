# TODO: Refactor this file
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from . import enums, mixins, models


class CreateRootSchema(mixins.NodeStatisticsMixin, mixins.NodeContentMixin):
    owner_id: str
    title: str = 'Mind Palace'
    questions: str = 'What is Mind Palace'
    order: str = 'aaaaaa'


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
    ancestors: list[models.ListNode] = Field(default_factory=list)
    children: list[models.ListNode] = Field(default_factory=list)


class UpdatedNodeSchema(mixins.NodeStatisticsMixin, mixins.IdMixin, mixins.ParentIdMixin):
    title: str = ''
    questions: str = ''
    size: int = 0
    content: str = ''
    is_learn: bool = True
    order: str = ''
    children: list[models.ListNode] = []
    tags: list[int] = Field(default_factory=list)
    ancestors: list[models.ListNode] = Field(default_factory=list)

    model_config = ConfigDict(extra='ignore')


class NodeEditSchema(mixins.NodeContentMixin, mixins.NodeStatisticsMixin, BaseModel):
    title: str = ''
    questions: str = ''
    is_learn: bool = True
    tags: list[int] = []


class NodeCreateSchema(BaseModel):
    title: str
    questions: str
    is_learn: bool = True
    order: str = Field(default='aaaaaa')


class NodeMoveConfiguration(BaseModel):
    target_id: str
    position: enums.MovePosition = enums.MovePosition.last_child


class SearchNodeResultSchema(BaseModel, mixins.IdMixin):
    title: str
    order: str | None = Field(default=None)
    ancestors: list[models.ListNode] = Field(default_factory=list)


def model_validate_tree(root_data: dict) -> models.TreeNode:
    root_children_data = sorted(root_data.pop('children', []), key=lambda child: child.get('order', ''))
    root_ancestors_data = root_data.pop('ancestors', [])
    root_data['ancestors'] = [
        *root_ancestors_data,
        {'id': root_data['id'], 'title': root_data['title']},
    ]
    root = models.TreeNode.model_validate(root_data)
    root_children = []
    for child_data in root_children_data:
        child_data['parent_id'] = root.id
        child_data['ancestors'] = root.ancestors
        root_children.append(model_validate_tree(child_data))
    root.children = root_children
    return root
