from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, computed_field

from . import enums
from .fields import MongoDBId


class StartLearningSessionSchema(BaseModel):
    target: str


class CreateLearningSessionSchema(BaseModel):
    user_id: str
    target: str
    current_node: str
    queue: list[str]
    bad_repetition_queue: list[str] = []
    traverse_strategy: enums.TraverseStrategy = enums.TraverseStrategy.outdated
    repetition_strategy: enums.RepetitionStrategy = enums.RepetitionStrategy.sm2

    @computed_field
    def is_active(self) -> bool:
        return True

    @computed_field
    def start_datetime(self) -> AwareDatetime:
        return datetime.now(tz=UTC)

    @computed_field
    def last_activity_datetime(self) -> AwareDatetime:
        return datetime.now(tz=UTC)


class LearningSessionSchema(BaseModel):
    id: Optional[MongoDBId] = Field(alias='_id', default=None)
    is_active: bool = True
    user_id: str
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    last_activity_datetime: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    finish_datetime: Optional[datetime] = None
    current_node: Optional[str]
    target: str
    queue: list[str] = []
    bad_repetition_queue: list[str] = []
    traverse_strategy: enums.TraverseStrategy = enums.TraverseStrategy.outdated
    repetition_strategy: enums.RepetitionStrategy = enums.RepetitionStrategy.sm2

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecordRepetitionDataSchema(BaseModel):

    node_id: str
    rating: int = Field(ge=0, le=5)
