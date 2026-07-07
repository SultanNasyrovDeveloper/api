from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from pydantic import Field as SchemaField
from surorm.data_model import Boolean, Datetime, Float, Int, RecordID, String
from surorm.functions import F
from surorm.orm import Field, Model, Relation
from surorm.statements import Select

from . import mixins


class ListNode(BaseModel, mixins.IdMixin):
    title: str
    order: str | None = SchemaField(default=None)
    ancestors: list[ListNode] = SchemaField(default_factory=list)


class TreeNode(BaseModel, mixins.IdMixin, mixins.ParentIdMixin):
    title: str
    order: str | None = ''
    ancestors: list[ListNode] = SchemaField(default_factory=list)
    children: list[TreeNode] = SchemaField(default_factory=list)


class Node(Model):
    __table__: ClassVar[str] = 'node'

    parent_id: RecordID | None = Field(computed=lambda _: F.array.first('->child.out'), default=None)

    is_learn: Boolean
    title: String
    order: String
    owner_id: String
    questions: String

    cpr: Int = Field(default=0)
    owner_views: Int = Field(default=0)
    difficulty: Float = Field(default=2.6)
    last_rating: Float = Field(default=0)
    size: Int = Field(default=0)
    repetitions: Int = Field(default=0)

    last_interval: Int | Float
    last_repetition: Datetime
    next_optimal_repetition: Datetime

    content: String

    ancestors: list[ListNode] | None = Field(
        computed=lambda _: Select('id', 'title').from_('$this.{..+collect}->child->node'), default=None
    )
    children: list[ListNode] | None = Field(default=None, exclude=True)

    @property
    def pk(self) -> str | None:
        # TODO: Return empty string here instead of node for types
        return self.id.id_

    @property
    def parent_pk(self) -> str | None:
        # TODO: Return empty string here instead of node for types
        return self.parent_id.id_ if bool(self.parent_id) else None


class Child(Relation):
    __table__ = 'child'
    in_: Node
    out: Node
