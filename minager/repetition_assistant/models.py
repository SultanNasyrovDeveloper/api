from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from minager.core.db.mongodb import MongoDBModel

from . import enums


class UserMessage(BaseModel):
    role: Literal[enums.MessageRole.user] = enums.MessageRole.user
    content: str


class AssistantMessage(BaseModel):
    role: Literal[enums.MessageRole.assistant] = enums.MessageRole.assistant
    type: enums.MessageType = enums.MessageType.default
    content: str


class AssistantVerdictMessage(BaseModel):
    role: Literal[enums.MessageRole.assistant] = enums.MessageRole.assistant
    type: Literal[enums.MessageType.verdict] = enums.MessageType.verdict
    rating: int = Field(gt=0, le=5)
    topics_to_add: list[str] = Field(default_factory=list)
    # topics_to_repeat: list[str]  # Leaving it for now. Not sure if needed


Message = UserMessage | AssistantVerdictMessage | AssistantMessage
AssistantMessageT = AssistantVerdictMessage | AssistantMessage


class AssistantReviewConversation(MongoDBModel):
    session_id: str
    node_id: str
    user_id: str
    messages: list[Message] = Field(default_factory=list)

    created: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description='Time when chat started',
    )
    updated: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description='Last message datetime',
    )
